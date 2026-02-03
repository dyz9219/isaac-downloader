<script>
  export let logs = [];

  $: logText = logs.slice(-50).join('\n');
</script>

<div class="log-panel">
  <h3 class="log-title">日志</h3>
  <pre class="log-content">{logText}</pre>
</div>

<style>
  .log-panel {
    background: white;
    border-radius: 8px;
    padding: 10px 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    max-height: 180px;
  }

  .log-title {
    font-size: 13px;
    font-weight: 600;
    margin: 0 0 8px 0;
  }

  .log-content {
    font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
    font-size: 11px;
    color: #1d1d1f;
    background: #f5f5f7;
    padding: 8px;
    border-radius: 6px;
    overflow-y: auto;
    max-height: 130px;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
  }
</style>
