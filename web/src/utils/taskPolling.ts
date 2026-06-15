const terminalStatuses = new Set(['completed', 'failed', 'cancelled']);

export async function waitForTask<T extends { status: string }>(
  fetchTask: () => Promise<T>,
  intervalMs = 750,
): Promise<T> {
  while (true) {
    const task = await fetchTask();
    if (terminalStatuses.has(task.status)) {
      if (task.status !== 'completed') {
        throw new Error(`任务${task.status === 'cancelled' ? '已取消' : '执行失败'}`);
      }
      return task;
    }
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
  }
}
