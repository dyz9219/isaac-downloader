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
	globalCtx     context.Context
	globalCancel  context.CancelFunc
	onProgress    func(*DownloadTask)
	onComplete    func(*DownloadTask)
	onError       func(*DownloadTask, error)
}

func NewDownloadEngine(maxConcurrent int) *DownloadEngine {
	ctx, cancel := context.WithCancel(context.Background())
	return &DownloadEngine{
		httpClient:    &http.Client{Timeout: 0},
		maxConcurrent: maxConcurrent,
		semaphore:     make(chan struct{}, maxConcurrent),
		runningTasks:  make(map[string]*DownloadTask),
		globalCtx:     ctx,
		globalCancel:  cancel,
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
		// 等待 semaphore 时也检查全局 context，以便暂停能取消队列中的任务
		select {
		case e.semaphore <- struct{}{}:
			// 获得槽位
		case <-e.globalCtx.Done():
			task.mu.Lock()
			task.Status = StatusPaused
			task.mu.Unlock()
			return
		}
		defer func() { <-e.semaphore }()

		// 获得槽位后再次检查，防止在获取槽位的瞬间被取消
		select {
		case <-e.globalCtx.Done():
			task.mu.Lock()
			task.Status = StatusPaused
			task.mu.Unlock()
			return
		default:
		}

		e.download(task)
	}()
}

// ResetGlobalCtx 重置全局 context，用于恢复下载前调用
func (e *DownloadEngine) ResetGlobalCtx() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.globalCtx, e.globalCancel = context.WithCancel(context.Background())
}

// ClearCompletedTasks 清除已完成的任务记录
func (e *DownloadEngine) ClearCompletedTasks() {
	e.mu.Lock()
	defer e.mu.Unlock()
	for url, task := range e.runningTasks {
		if task.Status == StatusCompleted {
			delete(e.runningTasks, url)
		}
	}
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

// PauseAll 通过全局 context 取消所有任务（包括队列中等待的）
func (e *DownloadEngine) PauseAll() {
	e.mu.RLock()
	cancel := e.globalCancel
	e.mu.RUnlock()

	if cancel != nil {
		cancel()
	}

	// 同时取消每个任务自己的 context
	e.mu.RLock()
	tasks := make([]*DownloadTask, 0, len(e.runningTasks))
	for _, task := range e.runningTasks {
		tasks = append(tasks, task)
	}
	e.mu.RUnlock()

	for _, task := range tasks {
		task.mu.Lock()
		if task.cancel != nil {
			task.cancel()
		}
		if task.Status == StatusDownloading || task.Status == StatusPending {
			task.Status = StatusPaused
		}
		task.mu.Unlock()
	}
}

func (e *DownloadEngine) download(task *DownloadTask) {
	ctx, cancel := context.WithCancel(e.globalCtx)
	task.cancel = cancel
	task.Status = StatusDownloading

	// 确保目录存在
	if err := os.MkdirAll(filepath.Dir(task.LocalPath), 0755); err != nil {
		e.handleError(task, fmt.Errorf("创建目录失败: %w", err))
		return
	}

	// 检查已下载字节数（断点续传）
	downloadedBytes := int64(0)
	requestedRange := false
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
		requestedRange = true
	}

	resp, err := e.httpClient.Do(req)
	if err != nil {
		// context 被取消不视为错误
		if ctx.Err() == nil {
			e.handleError(task, err)
		}
		return
	}
	defer resp.Body.Close()

	// 处理 416 Range Not Satisfiable：文件已完全下载
	if resp.StatusCode == http.StatusRequestedRangeNotSatisfiable {
		task.mu.Lock()
		task.DownloadedBytes = downloadedBytes
		task.TotalBytes = downloadedBytes
		task.Status = StatusCompleted
		task.mu.Unlock()
		if e.onComplete != nil {
			e.onComplete(task)
		}
		return
	}

	// 确定文件打开模式和已下载字节数
	openFlag := os.O_CREATE | os.O_WRONLY
	if resp.StatusCode == http.StatusPartialContent {
		// 服务器支持 Range，追加写入
		openFlag |= os.O_APPEND
		task.DownloadedBytes = downloadedBytes

		// 解析 Content-Range: bytes start-end/total
		var total int64
		fmt.Sscanf(resp.Header.Get("Content-Range"), "bytes %*d-%*d/%d", &total)
		if total > 0 {
			task.TotalBytes = total
		}
	} else if resp.StatusCode == http.StatusOK {
		if requestedRange {
			// 发送了 Range 请求但服务器返回 200，说明不支持 Range
			// 必须截断文件从头写入，否则会导致文件损坏
			openFlag |= os.O_TRUNC
			task.DownloadedBytes = 0
		}
		if resp.ContentLength > 0 {
			task.TotalBytes = resp.ContentLength
		}
	} else {
		e.handleError(task, fmt.Errorf("服务器返回异常状态码: %d", resp.StatusCode))
		return
	}

	file, err := os.OpenFile(task.LocalPath, openFlag, 0644)
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
			} else if ctx.Err() != nil {
				// context 被取消（暂停），不是真正的下载错误
				task.Status = StatusPaused
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

func (e *DownloadEngine) GetTask(url string) *DownloadTask {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.runningTasks[url]
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
