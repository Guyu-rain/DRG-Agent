import { apiUrl, request } from './api';
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
  QaStreamEvent,
  QaSendResponse,
  SendMessageResponse,
} from '@/types/document';

async function readNdjson(
  response: Response,
  onEvent: (event: QaStreamEvent) => void,
) {
  if (!response.ok) {
    throw new Error(`流式问答请求失败 (${response.status})`);
  }
  if (!response.body) {
    throw new Error('浏览器不支持流式响应');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const consumeLine = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    onEvent(JSON.parse(trimmed) as QaStreamEvent);
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      lines.forEach(consumeLine);
      if (done) break;
    }
    consumeLine(buffer);
  } catch (error) {
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally {
    reader.releaseLock();
  }
}

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
  streamQaMessage: async (
    convId: string,
    instruction: string,
    onEvent: (event: QaStreamEvent) => void,
    signal?: AbortSignal,
  ) => {
    const response = await fetch(
      apiUrl(`/documents/qa/conversations/${convId}/messages/stream`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction }),
        signal,
      },
    );
    await readNdjson(response, onEvent);
  },
};
