package backend

import (
	"os"
	"strings"
	"testing"
)

func TestParseShellScriptWithTrailingSingleQuotes(t *testing.T) {
	content := `#!/bin/bash
FILES_JSON='{"tasks":[{"files":[{"path":"真机真机_2019353507798704130_20260311_103722/custom_task_pick_the_fruit_20260205182414.zip","url":"http://example.com/file.zip?X-Amz-Date=20260311T023722Z__AMP__X-Amz-Signature=abc"}],"taskId":2019353507798704130}]}'

echo "$FILES_JSON" | grep -oE '\{"(url|path)":"[^"]+","(url|path)":"[^"]+"\}' | {
while IFS= read -r file_entry; do
    tmp_url=$(printf '%s' "$file_entry" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')
done
}`

	config, err := ParseScript(content, "download.sh")
	if err != nil {
		t.Fatalf("ParseScript 失败: %v", err)
	}

	if len(config.Tasks) != 1 {
		t.Fatalf("期望 1 个任务，实际 %d 个", len(config.Tasks))
	}

	task := config.Tasks[0]
	if task.TaskId != 2019353507798704130 {
		t.Fatalf("期望 taskId=2019353507798704130，实际 %d", task.TaskId)
	}

	if len(task.Files) != 1 {
		t.Fatalf("期望 1 个文件，实际 %d 个", len(task.Files))
	}

	if strings.Contains(task.Files[0].URL, "__AMP__") {
		t.Fatalf("URL 未还原 __AMP__: %s", task.Files[0].URL)
	}

	if !strings.Contains(task.Files[0].URL, "&") {
		t.Fatalf("URL 未包含 &: %s", task.Files[0].URL)
	}
}

func TestParseRealScript(t *testing.T) {
	// 读取真实脚本文件
	content, err := os.ReadFile("../build/bin/演示用抓取任务_20260202_135655.ps1")
	if err != nil {
		t.Skipf("跳过测试：读取脚本文件失败: %v", err)
	}

	config, err := ParseScript(string(content), "../build/bin/演示用抓取任务_20260202_135655.ps1")
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
