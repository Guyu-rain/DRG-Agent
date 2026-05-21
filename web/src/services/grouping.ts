import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type {
  GroupingExecuteRequest,
  GroupingExecuteResponse,
  GroupingResultResponse,
  GroupingTaskSummary,
} from '@/types/grouping';

export const groupingApi = {
  execute: (data: GroupingExecuteRequest) =>
    request<ApiResponse<GroupingExecuteResponse>>({ method: 'POST', url: '/grouping/execute', data }),
  result: (taskId: string) =>
    request<ApiResponse<GroupingResultResponse>>({ method: 'GET', url: `/grouping/results/${taskId}` }),
  tasks: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<GroupingTaskSummary>>>({ method: 'GET', url: '/grouping/tasks', params }),
  batch: (caseIds: string[], ruleVersionId: string) =>
    request<ApiResponse<{ batchTaskId: string; totalCases: number; status: string }>>({
      method: 'POST',
      url: '/grouping/batch',
      data: { caseIds, ruleVersionId },
    }),
};
