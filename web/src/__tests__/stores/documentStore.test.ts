import { describe, expect, it } from 'vitest';
import { useDocumentStore } from '@/stores/documentStore';

describe('documentStore', () => {
  it('fetches documents', async () => {
    await useDocumentStore.getState().fetchDocuments();
    expect(useDocumentStore.getState().documents.length).toBeGreaterThan(0);
  });

  it('views document detail', async () => {
    await useDocumentStore.getState().viewDocument('DOC-20260519-001');
    expect(useDocumentStore.getState().currentDocument?.title).toContain('需求分析');
  });
});
