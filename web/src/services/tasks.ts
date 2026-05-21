import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type { ExecutionLog, TaskStep, TaskSummary } from '@/types/task';

export const tasksApi = {
  list: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<TaskSummary>>>({ method: 'GET', url: '/tasks', params }),
  detail: (taskId: string) =>
    request<ApiResponse<TaskSummary & { steps: TaskStep[] }>>({ method: 'GET', url: `/tasks/${taskId}` }),
  cancel: (taskId: string) =>
    request<ApiResponse<{ taskId: string; status: string }>>({ method: 'POST', url: `/tasks/${taskId}/cancel` }),
  logs: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<ExecutionLog>>>({ method: 'GET', url: '/logs', params }),
};
