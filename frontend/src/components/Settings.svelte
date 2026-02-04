<script>
  export let settings = { concurrent: 3, downloadPath: './downloads' };
  export let onClose;
  export let onSave;

  let localSettings = { ...settings };

  function handleSave() {
    onSave(localSettings);
  }

  function handleCancel() {
    localSettings = { ...settings };
    onClose();
  }
</script>

<div class="settings-overlay" on:click={handleCancel}>
  <div class="settings-panel" on:click|stopPropagation>
    <div class="settings-header">
      <h2>设置</h2>
      <button class="close-btn" on:click={handleCancel}>✕</button>
    </div>

    <div class="settings-body">
      <div class="setting-item">
        <label for="concurrent">并发下载数</label>
        <input
          id="concurrent"
          type="number"
          min="1"
          max="10"
          bind:value={localSettings.concurrent}
          class="setting-input"
        />
      </div>
    </div>

    <div class="settings-footer">
      <button class="btn btn-secondary" on:click={handleCancel}>取消</button>
      <button class="btn btn-primary" on:click={handleSave}>保存</button>
    </div>
  </div>
</div>

<style>
  .settings-overlay {
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
  }

  .settings-panel {
    background: white;
    border-radius: 10px;
    width: calc(100vw - 24px);
    max-width: 440px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  }

  .settings-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
    border-bottom: 1px solid #e5e5e7;
  }

  .settings-header h2 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
    color: #86868b;
  }

  .close-btn:hover {
    color: #1d1d1f;
  }

  .settings-body {
    padding: 14px 16px;
  }

  .setting-item {
    margin-bottom: 12px;
  }

  .setting-item:last-child {
    margin-bottom: 0;
  }

  .setting-item label {
    display: block;
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 500;
    color: #1d1d1f;
  }

  .setting-input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid #e5e5e7;
    border-radius: 6px;
    font-size: 13px;
    background: #f5f5f7;
    box-sizing: border-box;
  }

  .setting-input:focus {
    outline: none;
    border-color: #007aff;
    background: white;
  }

  .settings-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 12px 16px;
    border-top: 1px solid #e5e5e7;
  }

  .btn {
    padding: 7px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  }

  .btn-primary {
    background: #007aff;
    color: white;
  }

  .btn-primary:hover {
    background: #0056b3;
  }

  .btn-secondary {
    background: #e5e5e7;
    color: #1d1d1f;
  }

  .btn-secondary:hover {
    background: #d1d1d3;
  }
</style>
