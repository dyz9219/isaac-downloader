package main

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
)

// TestScriptInfoSerialization 验证 ScriptInfo 的 JSON 序列化使用小写字段名
// 覆盖问题: undefined 显示
// 目的: 证明 Go 结构体序列化后字段名是小写，所以前端必须用小写字段名访问
func TestScriptInfoSerialization(t *testing.T) {
	info := &ScriptInfo{
		TotalTasks: 1,
		TotalFiles: 5,
	}

	data, err := json.Marshal(info)
	if err != nil {
		t.Fatalf("序列化失败: %v", err)
	}

	jsonStr := string(data)
	t.Logf("序列化结果: %s", jsonStr)

	// 验证字段名是小写
	if !strings.Contains(jsonStr, `"totalTasks"`) {
		t.Errorf("期望字段名 'totalTasks'，实际: %s", jsonStr)
	}
	if !strings.Contains(jsonStr, `"totalFiles"`) {
		t.Errorf("期望字段名 'totalFiles'，实际: %s", jsonStr)
	}

	// 验证值正确
	if !strings.Contains(jsonStr, "1") || !strings.Contains(jsonStr, "5") {
		t.Errorf("值不正确: %s", jsonStr)
	}
}

// TestTaskDisplaySerialization 验证 TaskDisplay 的 JSON 序列化
// 覆盖问题: undefined 显示
// 目的: 证明任务对象也使用小写字段名
func TestTaskDisplaySerialization(t *testing.T) {
	task := &TaskDisplay{
		TaskId:    2013529099792277505,
		FileCount: 5,
	}

	data, err := json.Marshal(task)
	if err != nil {
		t.Fatalf("序列化失败: %v", err)
	}

	jsonStr := string(data)
	t.Logf("序列化结果: %s", jsonStr)

	if !strings.Contains(jsonStr, `"taskId"`) {
		t.Errorf("期望字段名 'taskId'，实际: %s", jsonStr)
	}
	if !strings.Contains(jsonStr, `"fileCount"`) {
		t.Errorf("期望字段名 'fileCount'，实际: %s", jsonStr)
	}
}

// TestProgressInfoSerialization 验证 ProgressInfo 的 JSON 序列化
// 覆盖问题: 下载完成后进度条显示
// 目的: 证明进度对象使用小写字段名，前端需要正确访问才能显示进度
func TestProgressInfoSerialization(t *testing.T) {
	progress := &ProgressInfo{
		Downloaded: 1024000,
		Total:      2048000,
		Speed:      512000,
		Percentage: 50.0,
	}

	data, err := json.Marshal(progress)
	if err != nil {
		t.Fatalf("序列化失败: %v", err)
	}

	jsonStr := string(data)
	t.Logf("序列化结果: %s", jsonStr)

	expectedFields := []string{"downloaded", "total", "speed", "percentage"}
	for _, field := range expectedFields {
		if !strings.Contains(jsonStr, `"`+field+`"`) {
			t.Errorf("期望字段名 '%s'，实际: %s", field, jsonStr)
		}
	}
}

// TestLoadScriptRealScript 使用真实脚本测试 LoadScript
// 覆盖问题: 自动加载脚本 + undefined 显示
// 目的: 验证 LoadScript 函数能正确解析 .ps1 脚本，返回正确的任务数和文件数
func TestLoadScriptRealScript(t *testing.T) {
	// 读取真实的脚本文件
	scriptPath := "build/bin/演示用抓取任务_20260202_135655.ps1"
	_, err := os.ReadFile(scriptPath)
	if err != nil {
		t.Skipf("跳过测试：无法读取脚本文件 %s: %v", scriptPath, err)
		return
	}

	// 创建 App 实例并加载脚本
	app := NewApp()
	info, err := app.LoadScript(scriptPath)
	if err != nil {
		t.Fatalf("加载脚本失败: %v", err)
	}

	// 验证返回的 ScriptInfo 包含正确的数据
	t.Logf("任务数: %d, 文件数: %d", info.TotalTasks, info.TotalFiles)

	if info.TotalTasks != 1 {
		t.Errorf("期望任务数 1，实际: %d", info.TotalTasks)
	}
	if info.TotalFiles != 5 {
		t.Errorf("期望文件数 5，实际: %d", info.TotalFiles)
	}

	// 验证 GetTasks 能返回正确的任务列表
	tasks := app.GetTasks()
	if len(tasks) != 1 {
		t.Errorf("期望 1 个任务，实际: %d", len(tasks))
	}
	if len(tasks) > 0 && tasks[0].FileCount != 5 {
		t.Errorf("期望文件数 5，实际: %d", tasks[0].FileCount)
	}
}
