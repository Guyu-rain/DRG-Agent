import { request } from './api';
import type { ApiResponse, PaginationResponse } from '@/types/api';
import type {
  ConversationDetail,
  DocType,
  DocumentConversationSummary,
  DocumentDetail,
  DocumentGenerateRequest,
  DocumentStatus,
  DocumentSubmitResponse,
  DocumentSummary,
  DocumentTaskResponse,
  DocumentVersion,
  QaSendResponse,
  SendMessageResponse,
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
    request<ApiResponse<DocumentSubmitResponse>>({ method: 'POST', url: `/documents/${docId}/submit` }),
  versions: (docId: string) =>
    request<ApiResponse<{ items: DocumentVersion[]; total: number }>>({
      method: 'GET',
      url: `/documents/${docId}/versions`,
    }),
  updateStatus: (docId: string, status: DocumentStatus) =>
    request<ApiResponse<DocumentDetail>>({ method: 'PATCH', url: `/documents/${docId}/status`, data: { status } }),
  remove: (docId: string) =>
    request<ApiResponse<{ docId: string }>>({ method: 'DELETE', url: `/documents/${docId}` }),

  // ----------------------------------------------------- 对话式文档生成
  createConversation: (data: { title?: string; docType?: DocType | null }) =>
    request<ApiResponse<DocumentConversationSummary>>({
      method: 'POST',
      url: '/documents/conversations',
      data,
    }),
  listConversations: (params?: Record<string, unknown>) =>
    request<ApiResponse<PaginationResponse<DocumentConversationSummary>>>({
      method: 'GET',
      url: '/documents/conversations',
      params,
    }),
  conversation: (convId: string) =>
    request<ApiResponse<ConversationDetail>>({
      method: 'GET',
      url: `/documents/conversations/${convId}`,
    }),
  sendMessage: (convId: string, instruction: string) =>
    request<ApiResponse<SendMessageResponse>>({
      method: 'POST',
      url: `/documents/conversations/${convId}/messages`,
      data: { instruction },
    }),
  removeConversation: (convId: string) =>
    request<ApiResponse<{ conversationId: string }>>({
      method: 'DELETE',
      url: `/documents/conversations/${convId}`,
    }),

  // ----------------------------------------------------- Q&A 模式
  createQaConversation: (data?: { title?: string }) =>
    request<ApiResponse<DocumentConversationSummary>>({
      method: 'POST',
      url: '/documents/qa/conversations',
      data,
    }),
  listQaConversations: () =>
    request<ApiResponse<PaginationResponse<DocumentConversationSummary>>>({
      method: 'GET',
      url: '/documents/qa/conversations',
    }),
  qaConversation: (convId: string) =>
    request<ApiResponse<ConversationDetail>>({
      method: 'GET',
      url: `/documents/qa/conversations/${convId}`,
    }),
  sendQaMessage: (convId: string, instruction: string) =>
    request<ApiResponse<QaSendResponse>>({
      method: 'POST',
      url: `/documents/qa/conversations/${convId}/messages`,
      data: { instruction },
    }),
};
