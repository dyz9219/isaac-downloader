package backend

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type DownloadStatus string

const (
	StatusPending     DownloadStatus = "pending"
	StatusDownloading DownloadStatus = "downloading"
	StatusPaused      DownloadStatus = "paused"
	StatusCompleted   DownloadStatus = "completed"
	StatusFailed      DownloadStatus = "failed"
)

type DownloadTask struct {
	URL             string
	LocalPath       string
	TotalBytes      int64
	DownloadedBytes int64
	Status          DownloadStatus
	Speed           int64
	mu              sync.Mutex
	cancel          context.CancelFunc
}

type DownloadEngine struct {
	httpClient    *http.Client
	maxConcurrent int
	semaphore     chan struct{}
	runningTasks  map[string]*DownloadTask
	mu            sync.RWMutex
	onProgress    func(*DownloadTask)
	onComplete    func(*DownloadTask)
	onError       func(*DownloadTask, error)
}

func NewDownloadEngine(maxConcurrent int) *DownloadEngine {
	return &DownloadEngine{
		httpClient:    &http.Client{Timeout: 0},
		maxConcurrent: maxConcurrent,
		semaphore:     make(chan struct{}, maxConcurrent),
		runningTasks:  make(map[string]*DownloadTask),
	}
}

func (e *DownloadEngine) SetCallbacks(onProgress, onComplete func(*DownloadTask), onError func(*DownloadTask, error)) {
	e.onProgress = onProgress
	e.onComplete = onComplete
	e.onError = onError
}

func (e *DownloadEngine) StartDownload(task *DownloadTask) {
	e.mu.Lock()
	e.runningTasks[task.URL] = task
	e.mu.Unlock()

	go func() {
		e.semaphore <- struct{}{}
		defer func() { <-e.semaphore }()
		e.download(task)
	}()
}

func (e *DownloadEngine) PauseDownload(url string) {
	e.mu.RLock()
	task := e.runningTasks[url]
	e.mu.RUnlock()

	if task != nil && task.cancel != nil {
		task.cancel()
		task.mu.Lock()
		task.Status = StatusPaused
		task.mu.Unlock()
	}
}

func (e *DownloadEngine) download(task *DownloadTask) {
	ctx, cancel := context.WithCancel(context.Background())
	task.cancel = cancel
	task.Status = StatusDownloading

	// 确保目录存在
	if err := os.MkdirAll(filepath.Dir(task.LocalPath), 0755); err != nil {
		e.handleError(task, fmt.Errorf("创建目录失败: %w", err))
		return
	}

	// 检查已下载字节数（断点续传）
	downloadedBytes := int64(0)
	if info, err := os.Stat(task.LocalPath); err == nil {
		downloadedBytes = info.Size()
	}

	req, err := http.NewRequestWithContext(ctx, "GET", task.URL, nil)
	if err != nil {
		e.handleError(task, err)
		return
	}

	// 设置 Range 头支持断点续传
	if downloadedBytes > 0 {
		req.Header.Set("Range", fmt.Sprintf("bytes=%d-", downloadedBytes))
		task.DownloadedBytes = downloadedBytes
	}

	resp, err := e.httpClient.Do(req)
	if err != nil {
		e.handleError(task, err)
		return
	}
	defer resp.Body.Close()

	// 获取文件总大小
	if resp.StatusCode == http.StatusOK {
		if resp.ContentLength > 0 {
			task.TotalBytes = resp.ContentLength
		}
	} else if resp.StatusCode == http.StatusPartialContent {
		// 解析 Content-Range: bytes 0-123456/789012
		var total int64
		fmt.Sscanf(resp.Header.Get("Content-Range"), "bytes %*d-%d", &total)
		if total > 0 {
			task.TotalBytes = total
		}
	}

	// 打开文件（追加模式）
	file, err := os.OpenFile(task.LocalPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		e.handleError(task, err)
		return
	}
	defer file.Close()

	buf := make([]byte, 32*1024)
	lastUpdate := time.Now()
	var lastBytes int64

	for {
		select {
		case <-ctx.Done():
			task.Status = StatusPaused
			return
		default:
		}

		n, err := resp.Body.Read(buf)
		if n > 0 {
			if _, writeErr := file.Write(buf[:n]); writeErr != nil {
				e.handleError(task, writeErr)
				return
			}

			task.mu.Lock()
			task.DownloadedBytes += int64(n)
			task.mu.Unlock()

			// 每秒更新进度
			if time.Since(lastUpdate) > time.Second {
				task.mu.Lock()
				task.Speed = task.DownloadedBytes - lastBytes
				lastBytes = task.DownloadedBytes
				task.mu.Unlock()

				if e.onProgress != nil {
					e.onProgress(task)
				}
				lastUpdate = time.Now()
			}
		}

		if err != nil {
			if err == io.EOF {
				task.Status = StatusCompleted
				if e.onComplete != nil {
					e.onComplete(task)
				}
			} else {
				e.handleError(task, err)
			}
			return
		}
	}
}

func (e *DownloadEngine) handleError(task *DownloadTask, err error) {
	task.Status = StatusFailed
	if e.onError != nil {
		e.onError(task, err)
	}
}

func (e *DownloadEngine) GetRunningTasks() []*DownloadTask {
	e.mu.RLock()
	defer e.mu.RUnlock()

	tasks := make([]*DownloadTask, 0, len(e.runningTasks))
	for _, task := range e.runningTasks {
		tasks = append(tasks, task)
	}
	return tasks
}

func (t *DownloadTask) ToMap() map[string]any {
	t.mu.Lock()
	defer t.mu.Unlock()

	return map[string]any{
		"url":             t.URL,
		"localPath":       t.LocalPath,
		"totalBytes":      t.TotalBytes,
		"downloadedBytes": t.DownloadedBytes,
		"status":          string(t.Status),
		"speed":           t.Speed,
	}
}
