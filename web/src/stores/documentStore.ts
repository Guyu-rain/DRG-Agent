import { create } from 'zustand';
import { documentsApi } from '@/services';
import type { DocumentDetail, DocumentGenerateRequest, DocumentStatus, DocumentSummary, DocType } from '@/types/document';

interface DocumentState {
  documents: DocumentSummary[];
  currentDocument: DocumentDetail | null;
  isLoading: boolean;
  filter: {
    type?: DocType;
    status?: DocumentStatus;
    keyword?: string;
  };
  setFilter: (filter: Partial<DocumentState['filter']>) => void;
  fetchDocuments: () => Promise<void>;
  viewDocument: (docId: string) => Promise<void>;
  generateDocument: (data: DocumentGenerateRequest) => Promise<string>;
  submitDocument: (docId: string) => Promise<void>;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  currentDocument: null,
  isLoading: false,
  filter: {},
  setFilter: (filter) => set({ filter: { ...get().filter, ...filter } }),
  fetchDocuments: async () => {
    set({ isLoading: true });
    try {
      const response = await documentsApi.list({ page: 1, pageSize: 20, ...get().filter });
      set({ documents: response.data.items });
    } finally {
      set({ isLoading: false });
    }
  },
  viewDocument: async (docId) => {
    const response = await documentsApi.detail(docId);
    set({ currentDocument: response.data });
  },
  generateDocument: async (data) => {
    const response = await documentsApi.generate(data);
    await get().fetchDocuments();
    return response.data.docTaskId;
  },
  submitDocument: async (docId) => {
    const response = await documentsApi.submit(docId);
    set({ currentDocument: response.data });
    await get().fetchDocuments();
  },
}));
