export type DocType =
  | 'requirements'
  | 'design'
  | 'testing'
  | 'meeting_minutes'
  | 'management'
  | 'configuration'
  | 'general';
export type DocumentStatus = 'draft' | 'review' | 'submitted' | 'archived';

export interface DocumentGenerateRequest {
  docType: DocType;
  title: string;
  context: Record<string, unknown>;
  template?: string;
}

export interface DocumentTaskResponse {
  docTaskId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  createdAt: string;
  resultDocId?: string;
  errorMessage?: string;
}

export interface DocumentSummary {
  docId: string;
  title: string;
  type: DocType;
  status: DocumentStatus;
  version: string;
  createdAt: string;
  submittedAt?: string;
  generatedBy?: string;
  fileSize?: number;
}

export interface DocumentSection {
  id: string;
  title: string;
  status: 'generated' | 'pending' | 'edited';
}

export interface DocumentDetail extends DocumentSummary {
  content: string;
  metadata: {
    createdAt: string;
    generatedBy: string;
    sourceTasks: string[];
    modelUsed: string;
  };
  sections: DocumentSection[];
}

export interface DocumentVersion {
  version: string;
  changeDescription?: string;
  createdAt: string;
  createdBy?: string;
}

// ----------------------------------------------------- 对话式文档生成

export type ReasoningStepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ReasoningStep {
  id: string;
  title: string;
  detail?: string;
  status: ReasoningStepStatus;
}

export interface ReasoningSummary {
  status: 'thinking' | 'completed' | 'failed';
  steps: ReasoningStep[];
}

export interface DocumentConversationSummary {
  conversationId: string;
  title: string;
  docType?: DocType | null;
  documentId?: string | null;
  mode: 'doc_chat' | 'qa';
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentMessage {
  messageId: string;
  role: 'user' | 'assistant';
  content: string;
  docVersion?: string | null;
  reasoningSummary?: ReasoningSummary | null;
  createdAt: string;
}

export interface ConversationDetail extends DocumentConversationSummary {
  messages: DocumentMessage[];
  document: DocumentDetail | null;
}

export interface SendMessageResponse {
  conversationId: string;
  assistantMessage: DocumentMessage;
  document: DocumentDetail;
}

export interface DocumentSubmitResponse {
  docId: string;
  status: DocumentStatus;
  submittedAt: string;
  submissionRecord: {
    submitter: string;
    version: string;
    filePath: string;
    checksum: string;
  };
}

// ----------------------------------------------------- Q&A 模式
export interface QaSendResponse {
  conversationId: string;
  assistantMessage: DocumentMessage;
}

export type QaStreamEvent =
  | { type: 'reasoning'; summary: ReasoningSummary }
  | { type: 'answer'; assistantMessage: DocumentMessage }
  | { type: 'done' }
  | { type: 'error'; message: string };
