<script>
  export let isDownloading = false;
  export let hasScript = false;
  export let onStart;
  export let onPause;
  export let onLoadScript;
</script>

<div class="control-bar">
  {#if hasScript}
    {#if !isDownloading}
      <button class="btn btn-primary" on:click={onStart}>
        <span class="btn-icon">▶</span>
        开始下载
      </button>
    {:else}
      <button class="btn btn-warning" on:click={onPause}>
        <span class="btn-icon">⏸</span>
        暂停下载
      </button>
    {/if}
  {/if}
  <button class="btn btn-secondary" on:click={onLoadScript}>
    <span class="btn-icon">📁</span>
    加载脚本
  </button>
</div>

<style>
  .control-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
  }

  .btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background: #007aff;
    color: white;
  }

  .btn-primary:hover {
    background: #0056b3;
  }

  .btn-warning {
    background: #ff9500;
    color: white;
  }

  .btn-warning:hover {
    background: #cc7700;
  }

  .btn-secondary {
    background: #e5e5e7;
    color: #1d1d1f;
  }

  .btn-secondary:hover {
    background: #d1d1d3;
  }

  .btn-icon {
    font-size: 14px;
  }
</style>
