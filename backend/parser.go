package backend

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
)

type FileInfo struct {
	URL  string `json:"url"`
	Path string `json:"path"`
}

type TaskInfo struct {
	TaskId   int64      `json:"taskId"`
	TaskName string     `json:"taskName"`
	Files    []FileInfo `json:"files"`
}

type DownloaderConfig struct {
	Tasks []TaskInfo `json:"tasks"`
}

// ParseScript 解析脚本（.ps1/.bat/.sh），提取 JSON
// scriptFileName 用于任务名称兜底显示
func ParseScript(content string, scriptFileName string) (*DownloaderConfig, error) {
	scriptType := detectScriptType(scriptFileName)

	jsonStr, err := extractJsonFromScript(content, scriptType)
	if err != nil {
		return nil, err
	}

	// 还原 __AMP__ 为 &
	jsonStr = strings.ReplaceAll(jsonStr, "__AMP__", "&")

	var config DownloaderConfig
	if err := json.Unmarshal([]byte(jsonStr), &config); err != nil {
		return nil, fmt.Errorf("%s 脚本 JSON 解析失败: %w", scriptType, err)
	}

	// 从文件路径提取任务名称（去掉ID和时间戳）
	for i := range config.Tasks {
		if len(config.Tasks[i].Files) > 0 {
			fullPath := filepath.ToSlash(config.Tasks[i].Files[0].Path)
			taskDir := strings.SplitN(fullPath, "/", 2)[0]
			// 格式: "演示用抓取任务_2013529099792277505_20260202_135655/xxx.zip"
			// 提取: "演示用抓取任务"
			parts := strings.Split(taskDir, "_")
			if len(parts) >= 4 {
				// 保留前面的部分作为任务名，去掉后3个部分（ID_日期_时间）
				config.Tasks[i].TaskName = strings.Join(parts[:len(parts)-3], "_")
			} else {
				// 兜底：从脚本文件名提取任务名称
				baseName := filepath.Base(scriptFileName)
				nameWithoutExt := strings.TrimSuffix(baseName, filepath.Ext(baseName))
				// 去掉时间戳部分 (_YYYYMMDD_HHMMSS)
				re := regexp.MustCompile(`_\d{8}_\d{6}$`)
				config.Tasks[i].TaskName = re.ReplaceAllString(nameWithoutExt, "")
			}
		}
	}

	return &config, nil
}

func extractJsonFromScript(content string, scriptType string) (string, error) {
	// 支持 PowerShell: $FilesJson = '...'
	// 支持 Batch: set FilesJson=...
	// 支持 Shell: FILES_JSON='...'
	patterns := []struct {
		pattern string
		isBatch bool
	}{
		{`(?m)^\s*\$FilesJson\s*=\s*'([^'\r\n]+)'`, false}, // PowerShell
		{`(?m)^\s*FILES_JSON\s*=\s*'([^'\r\n]+)'`, false},  // Shell
		{`(?m)^\s*FilesJson\s*=\s*'([^'\r\n]+)'`, false},   // Batch 变体
		{`(?m)^\s*set\s+FilesJson=(.+)$`, true},             // Batch set 语句
	}

	for _, p := range patterns {
		re := regexp.MustCompile(p.pattern)
		matches := re.FindStringSubmatch(content)
		if len(matches) >= 2 {
			jsonStr := matches[1]
			if p.isBatch {
				// Batch 可能包含末尾的干扰字符，清理
				jsonStr = strings.TrimSpace(jsonStr)
				if idx := strings.IndexAny(jsonStr, "\r\n"); idx > 0 {
					jsonStr = jsonStr[:idx]
				}
			}
			return jsonStr, nil
		}
	}

	return "", fmt.Errorf("%s 脚本未找到 JSON 配置，支持的格式：.ps1/.bat/.sh", scriptType)
}

func detectScriptType(scriptFileName string) string {
	switch strings.ToLower(filepath.Ext(scriptFileName)) {
	case ".ps1":
		return "PowerShell"
	case ".bat":
		return "Batch"
	case ".sh":
		return "Shell"
	default:
		return "未知"
	}
}
