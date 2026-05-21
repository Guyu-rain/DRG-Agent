import dayjs from 'dayjs';
import type { TaskStatus } from '@/types/api';

export function formatDateTime(value?: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

export function formatDuration(ms?: number) {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function taskStatusText(status: TaskStatus | string) {
  const map: Record<string, string> = {
    pending: '等待中',
    executing: '执行中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    needs_review: '待复核',
  };
  return map[status] ?? status;
}

export function taskStatusColor(status: TaskStatus | string) {
  const map: Record<string, string> = {
    pending: 'default',
    executing: 'processing',
    running: 'processing',
    completed: 'success',
    failed: 'error',
    needs_review: 'warning',
  };
  return map[status] ?? 'default';
}

export function fileSizeText(size?: number) {
  if (!size) return '-';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}
