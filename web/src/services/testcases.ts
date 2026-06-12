import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type {
  TestCaseGenerateRequest,
  TestCaseItem,
  TestExecutionResponse,
  TestTaskResponse,
} from '@/types/testcase';

export const testcasesApi = {
  generate: (data: TestCaseGenerateRequest) =>
    request<ApiResponse<TestTaskResponse>>({ method: 'POST', url: '/testcases/generate', data }),
  task: (testTaskId: string) =>
    request<ApiResponse<TestTaskResponse>>({ method: 'GET', url: `/testcases/tasks/${testTaskId}` }),
  list: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<TestCaseItem>>>({ method: 'GET', url: '/testcases', params }),
  detail: (testCaseId: string) =>
    request<ApiResponse<TestCaseItem>>({ method: 'GET', url: `/testcases/${testCaseId}` }),
  execute: (testCaseId: string) =>
    request<ApiResponse<TestExecutionResponse>>({ method: 'POST', url: `/testcases/${testCaseId}/execute` }),
  export: (testCaseIds: string[]) =>
    request<ApiResponse<{ downloadUrl: string }>>({ method: 'POST', url: '/testcases/export', data: { testCaseIds } }),
  submitToDocuments: (testCaseIds: string[]) =>
    request<ApiResponse<{ docTaskId: string }>>({
      method: 'POST',
      url: '/testcases/submit-to-documents',
      data: { testCaseIds },
    }),
};
