<script>
  import { onMount } from 'svelte';
  import { EventsOn } from '../wailsjs/runtime/runtime';
  import TaskList from './components/TaskList.svelte';
  import ProgressBar from './components/ProgressBar.svelte';
  import ControlBar from './components/ControlBar.svelte';
  import LogPanel from './components/LogPanel.svelte';
  import Settings from './components/Settings.svelte';
  import FileListDialog from './components/FileListDialog.svelte';

  let scriptInfo = null;
  let tasks = [];
  let progress = { downloaded: 0, total: 0, speed: 0, percentage: 0 };
  let isDownloading = false;
  let showSettings = false;
  let showCustomFileDialog = false;
  let settings = { concurrent: 3, downloadPath: './downloads' };
  let logs = [];
  let totalFilesToDownload = 0;
  let completedFiles = 0;

  onMount(() => {
    EventsOn('progress', (task) => {
      updateProgress();
    });

    EventsOn('complete', (task) => {
      completedFiles++;
      updateProgress();
      addLog(`完成: ${task.url}`);

      // Check if all files have completed downloading
      if (completedFiles >= totalFilesToDownload && totalFilesToDownload > 0) {
        isDownloading = false;
        addLog('所有文件下载完成！');
      }
    });

    EventsOn('error', (data) => {
      completedFiles++;
      addLog(`错误: ${data.url} - ${data.error}`);
      if (completedFiles >= totalFilesToDownload && totalFilesToDownload > 0) {
        isDownloading = false;
        addLog('所有文件处理完成');
      }
    });

    EventsOn('scriptLoaded', (info) => {
      scriptInfo = info;
      loadTasks();
    });

    loadSettings();
    loadAutoDetected();
  });

  async function loadSettings() {
    try {
      const s = await window.go.main.App.GetSettings();
      if (s) {
        console.log('加载设置:', s);
        console.log('下载路径:', s.downloadPath);
        settings = { ...s }; // 创建新对象确保响应式更新
      }
    } catch (e) {
      console.error('加载设置失败', e);
    }
  }

  async function updateProgress() {
    try {
      progress = await window.go.main.App.GetProgress();
    } catch (e) {
      console.error('获取进度失败', e);
    }
  }

  async function loadTasks() {
    try {
      tasks = await window.go.main.App.GetTasks();
    } catch (e) {
      console.error('获取任务失败', e);
    }
  }

  async function loadAutoDetected() {
    for (let i = 0; i < 5; i++) {
      await new Promise(r => setTimeout(r, 300));
      try {
        tasks = await window.go.main.App.GetTasks();
        if (tasks && tasks.length > 0) {
          scriptInfo = {
            totalTasks: tasks.length,
            totalFiles: tasks.reduce((sum, t) => sum + (t.fileCount || 0), 0)
          };
          addLog('自动检测到脚本文件');
          return;
        }
      } catch (e) {
        // 继续重试
      }
    }
  }

  async function loadScript() {
    showCustomFileDialog = true;
  }

  async function selectScriptFiles(files) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // 第一个文件替换，后续文件合并
      const merge = i > 0;
      await loadScriptFromFile(file.fullPath, merge);
    }
  }

  async function browseOtherDirectory() {
    showCustomFileDialog = false;
    try {
      const results = await window.go.main.App.SelectScriptFiles();
      if (results && results.length > 0) {
        // 全部替换：第一个文件 replace，后续 merge
        for (let i = 0; i < results.length; i++) {
          const merge = i > 0;
          await loadScriptFromFile(results[i], merge);
        }
      }
    } catch (e) {
      // 用户取消，不做任何处理
    }
  }

  async function loadScriptFromFile(filePath, merge = false) {
    try {
      if (!merge) {
        // 替换模式：重置相关状态
        totalFilesToDownload = 0;
        completedFiles = 0;
        isDownloading = false;
      }

      if (merge) {
        await window.go.main.App.LoadScriptMerge(filePath);
      } else {
        await window.go.main.App.LoadScript(filePath);
      }
      tasks = await window.go.main.App.GetTasks();
      scriptInfo = {
        totalTasks: tasks.length,
        totalFiles: tasks.reduce((sum, t) => sum + (t.fileCount || 0), 0)
      };

      const action = merge ? "追加" : "加载";
      addLog(`${action}脚本: ${filePath}`);
    } catch (e) {
      addLog(`加载脚本失败: ${e.message || e}`);
    }
  }

  async function startDownload() {
    try {
      completedFiles = 0;
      const startedCount = await window.go.main.App.StartAll();
      totalFilesToDownload = startedCount;
      if (startedCount === 0) {
        addLog('所有文件已下载完成');
        return;
      }
      isDownloading = true;
      addLog('开始下载');
    } catch (e) {
      addLog(`开始下载失败: ${e.message || e}`);
    }
  }

  async function pauseDownload() {
    try {
      await window.go.main.App.PauseAll();
      isDownloading = false;
      addLog('暂停下载');
    } catch (e) {
      addLog(`暂停下载失败: ${e.message || e}`);
    }
  }

  function toggleSettings() {
    showSettings = !showSettings;
  }

  async function handlePathChange(newPath) {
    try {
      console.log('设置新路径:', newPath);
      await window.go.main.App.SetSettings({
        ...settings,
        downloadPath: newPath
      });
      settings = { ...settings, downloadPath: newPath };
      console.log('更新后的 settings:', settings);
      addLog(`下载路径已更新: ${newPath}`);
    } catch (e) {
      addLog(`更新路径失败: ${e.message}`);
    }
  }

  async function saveSettings(newSettings) {
    try {
      await window.go.main.App.SetSettings(newSettings);
      settings = newSettings;
      showSettings = false;
      addLog('设置已更新');
    } catch (e) {
      addLog(`更新设置失败: ${e.message || e}`);
    }
  }

  // Bug 5 fix: use spread instead of push for Svelte reactivity
  function addLog(message) {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    logs = [...logs, `[${timestamp}] ${message}`];
  }
</script>

<div class="app">
  <header class="header">
    <div class="header-left">
      <h1>文件下载器</h1>
      {#if scriptInfo}
        <span class="badge">{scriptInfo.totalTasks} 个任务, {scriptInfo.totalFiles} 个文件</span>
      {/if}
    </div>
    <button class="icon-btn" on:click={toggleSettings} title="设置">⚙️</button>
  </header>

  <main class="main">
    {#if showSettings}
      <Settings {settings} onSave={saveSettings} onClose={toggleSettings} />
    {:else}
      {#if scriptInfo}
        <TaskList {tasks} />
        <ProgressBar {progress} />
      {/if}
      <!-- Bug 3 fix: ControlBar and LogPanel always visible -->
      <ControlBar
        {isDownloading}
        hasScript={scriptInfo !== null}
        downloadPath={settings.downloadPath}
        onPathChange={handlePathChange}
        onStart={startDownload}
        onPause={pauseDownload}
        onLoadScript={loadScript} />
      <LogPanel {logs} />
    {/if}
  </main>
</div>

{#if showCustomFileDialog}
  <FileListDialog
    onClose={() => showCustomFileDialog = false}
    onSelect={selectScriptFiles}
    onBrowse={browseOtherDirectory} />
{/if}

<style>
  .app {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f7;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .header {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(20px);
    padding: 10px 16px;
    border-bottom: 1px solid #e5e5e7;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-left {
    display: flex;
    align-items: center;
  }

  .header h1 {
    font-size: 15px;
    font-weight: 600;
    margin: 0;
  }

  .badge {
    margin-left: 10px;
    padding: 2px 8px;
    background: #e5e5e7;
    border-radius: 10px;
    font-size: 11px;
    color: #86868b;
  }

  .icon-btn {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    padding: 6px;
  }

  .main {
    flex: 1;
    padding: 12px;
    overflow-y: auto;
  }
</style>
