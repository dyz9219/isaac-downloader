<script>
  export let tasks = [];
</script>

<div class="task-list">
  <h2 class="task-list-title">任务列表</h2>
  {#if tasks.length === 0}
    <p class="empty-message">暂无任务</p>
  {:else}
    <div class="task-items">
      {#each tasks as task}
        <div class="task-item">
          <div class="task-info">
            <span class="task-name">{task.taskName}</span>
            <span class="file-count">{task.fileCount} 个文件</span>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .task-list {
    background: white;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .task-list-title {
    font-size: 13px;
    font-weight: 600;
    margin: 0 0 8px 0;
  }

  .empty-message {
    color: #86868b;
    text-align: center;
    padding: 12px;
    font-size: 13px;
  }

  .task-items {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .task-item {
    padding: 8px 10px;
    background: #f5f5f7;
    border-radius: 6px;
  }

  .task-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .task-name {
    font-weight: 500;
    font-size: 13px;
    color: #1d1d1f;
  }

  .file-count {
    font-size: 12px;
    color: #86868b;
  }
</style>
