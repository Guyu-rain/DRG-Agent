import type { DocumentDetail, DocumentSummary } from '@/types/document';

export const documents: DocumentSummary[] = [
  {
    docId: 'DOC-20260519-001',
    title: 'DRG-Agent 需求分析文档',
    type: 'requirements',
    status: 'submitted',
    version: 'V1.0',
    createdAt: '2026-05-19T11:05:00Z',
    submittedAt: '2026-05-19T11:30:00Z',
    generatedBy: '文档生成智能体',
    fileSize: 245760,
  },
  {
    docId: 'DOC-20260520-002',
    title: 'DRG-Agent 概要设计文档',
    type: 'design',
    status: 'draft',
    version: 'V1.0',
    createdAt: '2026-05-20T13:24:00Z',
    generatedBy: '文档生成智能体',
    fileSize: 183200,
  },
  {
    docId: 'DOC-20260520-003',
    title: 'DRG-Agent 测试报告草稿',
    type: 'testing',
    status: 'review',
    version: 'V1.0',
    createdAt: '2026-05-20T15:10:00Z',
    generatedBy: '测试用例生成智能体',
    fileSize: 88210,
  },
];

export const documentDetails: Record<string, DocumentDetail> = Object.fromEntries(
  documents.map((doc) => [
    doc.docId,
    {
      ...doc,
      content:
        '# ' +
        doc.title +
        '\n\n## 1. 概述\n\n本文件由 DRG-Agent 智能体根据规则版本、入组任务和项目结构生成。\n\n## 2. 核心流程\n\n- 病历输入与结构化解析\n- 规则版本选择与确定性入组\n- 证据链解释与文档归档\n',
      metadata: {
        createdAt: doc.createdAt,
        generatedBy: doc.generatedBy ?? '文档生成智能体',
        sourceTasks: ['TASK-GROUP-20260519-001'],
        modelUsed: 'deepseek-v3',
      },
      sections: [
        { id: 'sec-1', title: '概述', status: 'generated' },
        { id: 'sec-2', title: '核心流程', status: 'generated' },
        { id: 'sec-3', title: '接口说明', status: 'pending' },
      ],
    },
  ]),
);
