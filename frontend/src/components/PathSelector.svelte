<script>
  export let path = '';
  export let onSelect;
  export let disabled = false;

  async function handleClick() {
    if (disabled) return;
    const newPath = await window.go.main.App.SelectDownloadDirectory();
    if (newPath) {
      onSelect(newPath);
    }
  }

  $: displayedPath = path.length <= 40 ? path : '...' + path.slice(-37);
</script>

<div class="path-selector" class:disabled on:click={handleClick}>
  <span class="path-icon">📁</span>
  <span class="path-text" title={path}>{displayedPath}</span>
  <span class="change-btn">[更改]</span>
</div>

<style>
  .path-selector {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #f5f5f7;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
    user-select: none;
  }

  .path-selector:hover:not(.disabled) {
    background: #e5e5e7;
  }

  .path-selector.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .path-icon {
    font-size: 14px;
  }

  .path-text {
    flex: 1;
    font-size: 12px;
    color: #1d1d1f;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .change-btn {
    font-size: 11px;
    color: #007aff;
    font-weight: 500;
  }
</style>
