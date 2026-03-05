package backend

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestStartDownload_PreventDuplicateWriterByLocalPath(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("test-payload"))
	}))
	defer server.Close()

	tmpDir := t.TempDir()
	localPath := filepath.Join(tmpDir, "same.zip")

	engine := NewDownloadEngine(4)
	var completeCount int32
	var wg sync.WaitGroup
	wg.Add(1)
	engine.SetCallbacks(nil, func(task *DownloadTask) {
		if atomic.AddInt32(&completeCount, 1) == 1 {
			wg.Done()
		}
	}, func(task *DownloadTask, err error) {
		t.Errorf("unexpected error: %v", err)
		wg.Done()
	})

	task1 := &DownloadTask{URL: server.URL + "/a", LocalPath: localPath, Status: StatusPending}
	task2 := &DownloadTask{URL: server.URL + "/a", LocalPath: localPath, Status: StatusPending}

	engine.StartDownload(task1)
	engine.StartDownload(task2)

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("timeout waiting for first completion")
	}

	// Wait a bit more to catch unexpected second completion.
	time.Sleep(500 * time.Millisecond)
	if got := atomic.LoadInt32(&completeCount); got != 1 {
		t.Fatalf("expected one completion for duplicated local path, got %d", got)
	}

	content, err := os.ReadFile(localPath)
	if err != nil {
		t.Fatalf("failed to read downloaded file: %v", err)
	}
	if string(content) != "test-payload" {
		t.Fatalf("downloaded content mismatch: %q", string(content))
	}
}

func TestStartDownload_AllowSameURLDifferentLocalPaths(t *testing.T) {
	t.Parallel()

	block := make(chan struct{})
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		<-block
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("same-source"))
	}))
	defer server.Close()

	tmpDir := t.TempDir()
	engine := NewDownloadEngine(4)

	task1 := &DownloadTask{URL: server.URL + "/same", LocalPath: filepath.Join(tmpDir, "a.zip"), Status: StatusPending}
	task2 := &DownloadTask{URL: server.URL + "/same", LocalPath: filepath.Join(tmpDir, "b.zip"), Status: StatusPending}

	engine.StartDownload(task1)
	engine.StartDownload(task2)

	time.Sleep(150 * time.Millisecond)
	if got := len(engine.GetRunningTasks()); got != 2 {
		close(block)
		t.Fatalf("expected 2 running tasks for same URL with different local paths, got %d", got)
	}

	close(block)
	waitForTaskStatus(t, task1, StatusCompleted, 2*time.Second)
	waitForTaskStatus(t, task2, StatusCompleted, 2*time.Second)

	for _, p := range []string{task1.LocalPath, task2.LocalPath} {
		content, err := os.ReadFile(p)
		if err != nil {
			t.Fatalf("failed to read %s: %v", p, err)
		}
		if string(content) != "same-source" {
			t.Fatalf("content mismatch for %s: %q", p, string(content))
		}
	}
}

func waitForTaskStatus(t *testing.T, task *DownloadTask, expected DownloadStatus, timeout time.Duration) {
	t.Helper()

	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		task.mu.Lock()
		status := task.Status
		task.mu.Unlock()
		if status == expected {
			return
		}
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatalf("task did not reach status %s within %s", expected, timeout)
}
