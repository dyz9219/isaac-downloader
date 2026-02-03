package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
	"isaac-downloader/backend"
)

type App struct {
	ctx      context.Context
	engine   *backend.DownloadEngine
	config   *backend.DownloaderConfig
	settings *Settings
}

type Settings struct {
	Concurrent   int    `json:"concurrent"`
	DownloadPath string `json:"downloadPath"`
}

type ScriptInfo struct {
	TotalTasks int `json:"totalTasks"`
	TotalFiles int `json:"totalFiles"`
}

type TaskDisplay struct {
	TaskId    string `json:"taskId"`
	TaskName  string `json:"taskName"`
	FileCount int    `json:"fileCount"`
}

type ProgressInfo struct {
	Downloaded int64   `json:"downloaded"`
	Total      int64   `json:"total"`
	Speed      int64   `json:"speed"`
	Percentage float64 `json:"percentage"`
}

// FileInfoExtended represents a file with extended information
type FileInfoExtended = backend.FileInfoExtended

func NewApp() *App {
	return &App{
		engine:   backend.NewDownloadEngine(3),
		settings: &Settings{Concurrent: 3, DownloadPath: "./downloads"},
	}
}

func (a *App) OnStartup(ctx context.Context) {
	a.ctx = ctx

	a.engine.SetCallbacks(
		func(task *backend.DownloadTask) {
			runtime.EventsEmit(a.ctx, "progress", taskToMap(task))
		},
		func(task *backend.DownloadTask) {
			runtime.EventsEmit(a.ctx, "complete", taskToMap(task))
		},
		func(task *backend.DownloadTask, err error) {
			runtime.EventsEmit(a.ctx, "error", map[string]any{
				"url":   task.URL,
				"error": err.Error(),
			})
		},
	)

	// 自动检测同目录下的脚本
	go a.autoDetectScript()
}

func (a *App) autoDetectScript() {
	// Wait for frontend event listeners to be ready
	time.Sleep(500 * time.Millisecond)

	exePath, err := os.Executable()
	if err != nil {
		return
	}
	exeDir := filepath.Dir(exePath)

	files, err := os.ReadDir(exeDir)
	if err != nil {
		return
	}

	for _, file := range files {
		name := file.Name()
		ext := filepath.Ext(name)
		if ext == ".ps1" || ext == ".bat" || ext == ".sh" {
			info, loadErr := a.LoadScript(filepath.Join(exeDir, name))
			if loadErr == nil && info != nil {
				runtime.EventsEmit(a.ctx, "scriptLoaded", info)
			}
			break
		}
	}
}

func (a *App) LoadScript(scriptPath string) (*ScriptInfo, error) {
	content, err := os.ReadFile(scriptPath)
	if err != nil {
		return nil, fmt.Errorf("读取脚本失败: %w", err)
	}

	config, err := backend.ParseScript(string(content), scriptPath)
	if err != nil {
		return nil, fmt.Errorf("解析脚本失败: %w", err)
	}

	a.config = config

	return &ScriptInfo{
		TotalTasks: len(config.Tasks),
		TotalFiles: countFiles(config.Tasks),
	}, nil
}

func (a *App) LoadScriptMerge(scriptPath string) (*ScriptInfo, error) {
	content, err := os.ReadFile(scriptPath)
	if err != nil {
		return nil, fmt.Errorf("读取脚本失败: %w", err)
	}

	config, err := backend.ParseScript(string(content), scriptPath)
	if err != nil {
		return nil, fmt.Errorf("解析脚本失败: %w", err)
	}

	if a.config == nil {
		a.config = config
	} else {
		// 基于 TaskId 去重合并
		existingIds := make(map[int64]bool)
		for _, task := range a.config.Tasks {
			existingIds[task.TaskId] = true
		}
		for _, task := range config.Tasks {
			if !existingIds[task.TaskId] {
				a.config.Tasks = append(a.config.Tasks, task)
			}
		}
	}

	return &ScriptInfo{
		TotalTasks: len(a.config.Tasks),
		TotalFiles: countFiles(a.config.Tasks),
	}, nil
}

func countFiles(tasks []backend.TaskInfo) int {
	total := 0
	for _, task := range tasks {
		total += len(task.Files)
	}
	return total
}

func (a *App) GetTasks() []TaskDisplay {
	if a.config == nil {
		return []TaskDisplay{}
	}

	result := make([]TaskDisplay, len(a.config.Tasks))
	for i, task := range a.config.Tasks {
		result[i] = TaskDisplay{
			TaskId:    fmt.Sprintf("%d", task.TaskId),
			TaskName:  task.TaskName,
			FileCount: len(task.Files),
		}
	}
	return result
}

func (a *App) StartAll() error {
	if a.config == nil {
		return fmt.Errorf("未加载配置")
	}

	for _, task := range a.config.Tasks {
		for _, file := range task.Files {
			downloadTask := &backend.DownloadTask{
				URL:       file.URL,
				LocalPath: filepath.Join(a.settings.DownloadPath, file.Path),
				Status:    backend.StatusPending,
			}
			a.engine.StartDownload(downloadTask)
		}
	}

	return nil
}

func (a *App) PauseAll() {
	tasks := a.engine.GetRunningTasks()
	for _, task := range tasks {
		a.engine.PauseDownload(task.URL)
	}
}

func (a *App) GetProgress() ProgressInfo {
	tasks := a.engine.GetRunningTasks()

	var downloaded, total, speed int64
	for _, task := range tasks {
		downloaded += task.DownloadedBytes
		total += task.TotalBytes
		speed += task.Speed
	}

	percentage := 0.0
	if total > 0 {
		percentage = float64(downloaded) / float64(total) * 100
	}

	return ProgressInfo{
		Downloaded: downloaded,
		Total:      total,
		Speed:      speed,
		Percentage: percentage,
	}
}

func (a *App) SelectScriptFile() (string, error) {
	selection, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{
		Title: "选择下载脚本",
		Filters: []runtime.FileFilter{
			{DisplayName: "PowerShell脚本 (*.ps1)", Pattern: "*.ps1"},
			{DisplayName: "批处理文件 (*.bat)", Pattern: "*.bat"},
			{DisplayName: "Shell脚本 (*.sh)", Pattern: "*.sh"},
			{DisplayName: "所有文件 (*.*)", Pattern: "*.*"},
		},
	})
	if err != nil {
		return "", err
	}
	if selection == "" {
		return "", fmt.Errorf("未选择文件")
	}
	return selection, nil
}

// ListScriptFiles returns script files in the executable directory
func (a *App) ListScriptFiles() ([]FileInfoExtended, error) {
	exePath, err := os.Executable()
	if err != nil {
		return nil, fmt.Errorf("无法获取可执行文件路径: %w", err)
	}

	exeDir := filepath.Dir(exePath)
	files, err := backend.ScanDirectoryWithDetails(exeDir, []string{".ps1", ".bat", ".sh"})
	if err != nil {
		return nil, err
	}

	// 设置完整路径，保留文件名
	for i := range files {
		files[i].FullPath = filepath.Join(exeDir, files[i].Name)
	}

	return files, nil
}

func (a *App) GetSettings() *Settings {
	return a.settings
}

func (a *App) SetSettings(settings *Settings) {
	a.settings = settings
	if len(a.engine.GetRunningTasks()) == 0 {
		a.engine = backend.NewDownloadEngine(settings.Concurrent)
	}
}

func taskToMap(task *backend.DownloadTask) map[string]any {
	return task.ToMap()
}
