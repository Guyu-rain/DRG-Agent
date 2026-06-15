import { afterEach, describe, expect, it, vi } from 'vitest';
import { waitForTask } from '@/utils/taskPolling';

afterEach(() => vi.useRealTimers());

describe('waitForTask', () => {
  it('keeps polling beyond the previous attempt limit until completion', async () => {
    vi.useFakeTimers();
    let calls = 0;
    const resultPromise = waitForTask(async () => {
      calls += 1;
      return { status: calls > 200 ? 'completed' : 'running' };
    }, 10);

    await vi.runAllTimersAsync();

    await expect(resultPromise).resolves.toEqual({ status: 'completed' });
    expect(calls).toBe(201);
  });

  it('still stops immediately for failed tasks', async () => {
    await expect(waitForTask(async () => ({ status: 'failed' }), 0)).rejects.toThrow(
      '任务执行失败',
    );
  });
});
