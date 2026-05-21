import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type { TestCaseGenerateRequest, TestCaseItem, TestTaskResponse } from '@/types/testcase';

export const testcasesApi = {
  generate: (data: TestCaseGenerateRequest) =>
    request<ApiResponse<TestTaskResponse>>({ method: 'POST', url: '/testcases/generate', data }),
  list: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<TestCaseItem>>>({ method: 'GET', url: '/testcases', params }),
  detail: (testCaseId: string) =>
    request<ApiResponse<TestCaseItem>>({ method: 'GET', url: `/testcases/${testCaseId}` }),
  export: (testCaseIds: string[]) =>
    request<ApiResponse<{ fileUrl: string }>>({ method: 'POST', url: '/testcases/export', data: { testCaseIds } }),
  submitToDocuments: (testCaseIds: string[]) =>
    request<ApiResponse<{ docTaskId: string }>>({
      method: 'POST',
      url: '/testcases/submit-to-documents',
      data: { testCaseIds },
    }),
};
