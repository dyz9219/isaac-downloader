<script>
  export let onClose = () => {};
  export let onSelect = (files) => {};
  export let onBrowse = () => {};

  let files = [];
  let loading = true;
  let error = null;
  let selectedSet = new Set();

  async function loadFiles() {
    try {
      loading = true;
      error = null;
      const result = await window.go.main.App.ListScriptFiles();
      files = result || [];
    } catch (e) {
      error = e.message || e.toString();
      console.error('Failed to load script files:', e);
    } finally {
      loading = false;
    }
  }

  function toggleFile(file) {
    if (selectedSet.has(file.name)) {
      selectedSet.delete(file.name);
    } else {
      selectedSet.add(file.name);
    }
    selectedSet = new Set(selectedSet); // trigger reactivity
  }

  function confirmSelection() {
    const selected = files.filter(f => selectedSet.has(f.name));
    if (selected.length > 0) {
      onSelect(selected);
      onClose();
    }
  }

  function getExtensionLabel(ext) {
    const labels = {
      '.ps1': 'PowerShell',
      '.bat': 'Batch',
      '.sh': 'Shell'
    };
    return labels[ext] || ext;
  }

  $: hasSelection = selectedSet.size > 0;
  $: allSelected = files.length > 0 && selectedSet.size === files.length;

  function toggleAll() {
    if (allSelected) {
      selectedSet = new Set();
    } else {
      selectedSet = new Set(files.map(f => f.name));
    }
  }

  loadFiles();
</script>

<div class="dialog-overlay" on:click={onClose} role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <div class="dialog" on:click|stopPropagation>
    <div class="dialog-header">
      <h2 id="dialog-title">选择脚本文件</h2>
      <button class="close-btn" on:click={onClose} aria-label="关闭">✕</button>
    </div>

    <div class="dialog-body">
      {#if loading}
        <div class="loading">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>
      {:else if error}
        <div class="error">
          <p>加载失败</p>
          <p class="error-detail">{error}</p>
          <button class="btn-retry" on:click={loadFiles}>重试</button>
        </div>
      {:else if files.length === 0}
        <div class="empty">
          <p>未找到脚本文件</p>
          <p class="empty-hint">请将 .ps1、.bat 或 .sh 文件放在可执行文件所在目录</p>
        </div>
      {:else}
        <div class="select-all-bar">
          <button class="btn-toggle-all" on:click={toggleAll}>
            {allSelected ? '取消全选' : '全选'}
          </button>
        </div>
        <div class="file-list">
          {#each files as file (file.name)}
            <div class="file-item" class:selected={selectedSet.has(file.name)} on:click={() => toggleFile(file)} role="checkbox" aria-checked={selectedSet.has(file.name)} tabindex="0" on:keydown={(e) => e.key === 'Enter' && toggleFile(file)}>
              <div class="file-checkbox">
                <input type="checkbox" checked={selectedSet.has(file.name)} on:click|stopPropagation={() => toggleFile(file)} />
              </div>
              <div class="file-icon">
                <span class="ext-badge">{getExtensionLabel(file.extension)}</span>
              </div>
              <div class="file-info">
                <div class="file-name">{file.name}</div>
                <div class="file-meta">
                  <span class="file-size">{Math.round(file.size / 1024)} KB</span>
                  <span class="separator">|</span>
                  <span class="file-encoding">{file.encodingGuess}</span>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="dialog-footer">
      <button class="btn-secondary" on:click={onBrowse}>浏览其他目录...</button>
      <div class="footer-right">
        <button class="btn-secondary" on:click={onClose}>取消</button>
        <button class="btn-primary" on:click={confirmSelection} disabled={!hasSelection}>
          确认加载{hasSelection ? ` (${selectedSet.size})` : ''}
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }

  .dialog {
    background: white;
    border-radius: 12px;
    width: 90%;
    max-width: 640px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  }

  .dialog-header {
    padding: 16px 20px;
    border-bottom: 1px solid #e5e5e7;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .dialog-header h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
  }

  .close-btn {
    background: #f5f5f7;
    border: none;
    font-size: 18px;
    cursor: pointer;
    padding: 6px 10px;
    border-radius: 6px;
    transition: background 0.2s;
  }

  .close-btn:hover {
    background: #e5e5e7;
  }

  .dialog-body {
    padding: 0;
    overflow-y: auto;
    flex: 1;
  }

  .loading, .error, .empty {
    text-align: center;
    padding: 48px 32px;
    color: #86868b;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid #e5e5e7;
    border-top-color: #007aff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error {
    color: #ff3b30;
  }

  .error-detail {
    font-size: 13px;
    margin-top: 8px;
    opacity: 0.8;
  }

  .btn-retry {
    margin-top: 16px;
    padding: 8px 16px;
    background: #007aff;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
  }

  .empty-hint {
    font-size: 13px;
    margin-top: 8px;
    opacity: 0.7;
  }

  .select-all-bar {
    padding: 8px 12px 0;
  }

  .btn-toggle-all {
    padding: 6px 14px;
    border: 1px solid #e5e5e7;
    background: white;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-toggle-all:hover {
    background: #f5f5f7;
    border-color: #d1d1d6;
  }

  .file-list {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .file-item {
    display: flex;
    align-items: center;
    padding: 14px 16px;
    border: 1px solid transparent;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
    background: #f9f9fa;
  }

  .file-item:hover {
    background: #f0f0f2;
    transform: translateX(2px);
  }

  .file-item:focus {
    outline: none;
    border-color: #007aff;
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
  }

  .file-icon {
    flex-shrink: 0;
    margin-right: 14px;
  }

  .ext-badge {
    display: inline-block;
    padding: 4px 10px;
    background: #007aff;
    color: white;
    font-size: 11px;
    font-weight: 600;
    border-radius: 6px;
    text-transform: uppercase;
  }

  .file-info {
    flex: 1;
    min-width: 0;
  }

  .file-name {
    font-weight: 500;
    margin-bottom: 4px;
    word-break: break-all;
    font-size: 14px;
  }

  .file-meta {
    font-size: 12px;
    color: #86868b;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .separator {
    opacity: 0.5;
  }

  .file-checkbox {
    flex-shrink: 0;
    margin-right: 10px;
    display: flex;
    align-items: center;
  }

  .file-checkbox input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
    accent-color: #007aff;
  }

  .file-item.selected {
    background: #e8f0fe;
    border-color: #007aff;
  }

  .dialog-footer {
    padding: 16px 20px;
    border-top: 1px solid #e5e5e7;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .footer-right {
    display: flex;
    gap: 8px;
  }

  .btn-secondary {
    padding: 10px 20px;
    border: 1px solid #e5e5e7;
    background: white;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    background: #f5f5f7;
    border-color: #d1d1d6;
  }

  .btn-primary {
    padding: 10px 20px;
    border: none;
    background: #007aff;
    color: white;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-primary:hover {
    background: #0066d6;
  }

  .btn-primary:disabled {
    background: #c7c7cc;
    cursor: not-allowed;
  }
</style>
