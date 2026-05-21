import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type {
  DocumentDetail,
  DocumentGenerateRequest,
  DocumentStatus,
  DocumentSummary,
  DocumentTaskResponse,
  DocumentVersion,
} from '@/types/document';

export const documentsApi = {
  generate: (data: DocumentGenerateRequest) =>
    request<ApiResponse<DocumentTaskResponse>>({ method: 'POST', url: '/documents/generate', data }),
  task: (docTaskId: string) =>
    request<ApiResponse<DocumentTaskResponse>>({ method: 'GET', url: `/documents/tasks/${docTaskId}` }),
  preview: (docId: string) =>
    request<ApiResponse<DocumentDetail>>({ method: 'GET', url: `/documents/${docId}/preview` }),
  list: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<DocumentSummary>>>({ method: 'GET', url: '/documents', params }),
  detail: (docId: string) =>
    request<ApiResponse<DocumentDetail>>({ method: 'GET', url: `/documents/${docId}` }),
  update: (docId: string, data: { title?: string; content: string }) =>
    request<ApiResponse<DocumentDetail>>({ method: 'PUT', url: `/documents/${docId}`, data }),
  submit: (docId: string) =>
    request<ApiResponse<DocumentDetail>>({ method: 'POST', url: `/documents/${docId}/submit` }),
  versions: (docId: string) =>
    request<ApiResponse<{ items: DocumentVersion[]; total: number }>>({
      method: 'GET',
      url: `/documents/${docId}/versions`,
    }),
  updateStatus: (docId: string, status: DocumentStatus) =>
    request<ApiResponse<DocumentDetail>>({ method: 'PATCH', url: `/documents/${docId}/status`, data: { status } }),
  remove: (docId: string) =>
    request<ApiResponse<{ docId: string }>>({ method: 'DELETE', url: `/documents/${docId}` }),
};
