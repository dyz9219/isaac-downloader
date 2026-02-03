<script>
  export let progress = { downloaded: 0, total: 0, speed: 0, percentage: 0 };

  $: downloadedMB = (progress.downloaded / (1024 * 1024)).toFixed(2);
  $: totalMB = (progress.total / (1024 * 1024)).toFixed(2);
  $: speedMB = (progress.speed / (1024 * 1024)).toFixed(2);
  $: percentage = progress.percentage.toFixed(1);
</script>

<div class="progress-bar">
  <div class="progress-info">
    <span class="progress-text">{downloadedMB} MB / {totalMB} MB</span>
    <span class="progress-percentage">{percentage}%</span>
  </div>
  <div class="progress-track">
    <div class="progress-fill" style="width: {percentage}%"></div>
  </div>
  {#if progress.speed > 0}
    <div class="progress-speed">{speedMB} MB/s</div>
  {/if}
</div>

<style>
  .progress-bar {
    background: white;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .progress-text {
    font-size: 12px;
    color: #1d1d1f;
  }

  .progress-percentage {
    font-size: 12px;
    font-weight: 600;
    color: #007aff;
  }

  .progress-track {
    height: 6px;
    background: #e5e5e7;
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #007aff, #0056b3);
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .progress-speed {
    margin-top: 4px;
    font-size: 11px;
    color: #86868b;
  }
</style>
