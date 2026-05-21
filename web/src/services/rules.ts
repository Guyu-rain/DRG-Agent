import { request } from './api';
import type { ApiResponse, SimpleListResponse } from '@/types/api';
import type {
  RuleImportResponse,
  RuleSearchMatch,
  RuleType,
  RuleVersionDetail,
  RuleVersionSummary,
} from '@/types/rule';

export const rulesApi = {
  versions: () =>
    request<ApiResponse<SimpleListResponse<RuleVersionSummary>>>({ method: 'GET', url: '/rules/versions' }),
  detail: (versionId: string) =>
    request<ApiResponse<RuleVersionDetail>>({ method: 'GET', url: `/rules/versions/${versionId}` }),
  activate: (versionId: string) =>
    request<ApiResponse<RuleVersionSummary>>({ method: 'POST', url: `/rules/versions/${versionId}/activate` }),
  remove: (versionId: string) =>
    request<ApiResponse<{ versionId: string }>>({ method: 'DELETE', url: `/rules/versions/${versionId}` }),
  search: (code: string, ruleType?: RuleType) =>
    request<ApiResponse<{ matches: RuleSearchMatch[] }>>({
      method: 'GET',
      url: '/rules/search',
      params: { code, ruleType },
    }),
  importRules: (formData: FormData) =>
    request<ApiResponse<RuleImportResponse>>({
      method: 'POST',
      url: '/rules/import',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};
