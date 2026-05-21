export type DocType = 'requirements' | 'design' | 'testing' | 'meeting_minutes' | 'management' | 'configuration';
export type DocumentStatus = 'draft' | 'review' | 'submitted' | 'archived';

export interface DocumentGenerateRequest {
  docType: DocType;
  title: string;
  context: Record<string, unknown>;
  template?: string;
}

export interface DocumentTaskResponse {
  docTaskId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
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
