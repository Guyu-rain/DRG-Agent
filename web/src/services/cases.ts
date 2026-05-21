import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type {
  CaseCreateRequest,
  CaseCreateResponse,
  CaseParseResponse,
  CaseValidationResponse,
  PatientCase,
  PatientCaseSummary,
  StructuredCaseInput,
} from '@/types/case';

export const casesApi = {
  create: (data: CaseCreateRequest) =>
    request<ApiResponse<CaseCreateResponse>>({ method: 'POST', url: '/cases', data }),
  parse: (caseId: string) =>
    request<ApiResponse<CaseParseResponse>>({ method: 'POST', url: `/cases/${caseId}/parse` }),
  validate: (caseId: string) =>
    request<ApiResponse<CaseValidationResponse>>({ method: 'POST', url: `/cases/${caseId}/validate` }),
  list: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<PatientCaseSummary>>>({ method: 'GET', url: '/cases', params }),
  detail: (caseId: string) =>
    request<ApiResponse<PatientCase>>({ method: 'GET', url: `/cases/${caseId}` }),
  update: (caseId: string, data: StructuredCaseInput) =>
    request<ApiResponse<PatientCase>>({ method: 'PUT', url: `/cases/${caseId}`, data }),
  remove: (caseId: string) =>
    request<ApiResponse<{ caseId: string }>>({ method: 'DELETE', url: `/cases/${caseId}` }),
};
