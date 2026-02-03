package backend

import (
	"os"
	"strings"
	"testing"
)

func TestParseRealScript(t *testing.T) {
	// 读取真实脚本文件
	content, err := os.ReadFile("../build/bin/演示用抓取任务_20260202_135655.ps1")
	if err != nil {
		t.Fatalf("读取脚本文件失败: %v", err)
	}

	config, err := ParseScript(string(content))
	if err != nil {
		t.Fatalf("ParseScript 失败: %v", err)
	}

	// 断言：1 个任务
	if len(config.Tasks) != 1 {
		t.Fatalf("期望 1 个任务，实际 %d 个", len(config.Tasks))
	}

	task := config.Tasks[0]

	// 断言：taskId
	expectedTaskId := int64(2013529099792277505)
	if task.TaskId != expectedTaskId {
		t.Errorf("期望 taskId=%d，实际 %d", expectedTaskId, task.TaskId)
	}

	// 断言：5 个文件
	if len(task.Files) != 5 {
		t.Fatalf("期望 5 个文件，实际 %d 个", len(task.Files))
	}

	// 断言：所有 URL 不含 __AMP__，包含 &；所有 Path 非空
	for i, f := range task.Files {
		if strings.Contains(f.URL, "__AMP__") {
			t.Errorf("文件[%d] URL 仍包含 __AMP__: %s", i, f.URL)
		}
		if !strings.Contains(f.URL, "&") {
			t.Errorf("文件[%d] URL 未包含 &: %s", i, f.URL)
		}
		if f.Path == "" {
			t.Errorf("文件[%d] Path 为空", i)
		}
	}
}
