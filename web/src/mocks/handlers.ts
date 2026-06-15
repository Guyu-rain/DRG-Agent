import { delay, http, HttpResponse } from 'msw';
import { parsedDemoCase, caseSummaries } from './data/cases';
import { documentDetails, documents } from './data/documents';
import { failedGroupingResult, groupingTasks, successGroupingResult } from './data/grouping';
import { demoRuleDetail, ruleVersions } from './data/rules';
import { logs, tasks } from './data/tasks';
import { testcases } from './data/testcases';
import type { CaseCreateRequest } from '@/types/case';
import type { DocumentGenerateRequest } from '@/types/document';
import type { TestCaseGenerateRequest } from '@/types/testcase';

const api = '*/api/v1';

const ok = <T>(data: T, message = 'success', code = 200) => HttpResponse.json({ code, data, message });

const paged = <T>(items: T[], page = 1, pageSize = 20) => ({
  items,
  total: items.length,
  page,
  pageSize,
  totalPages: Math.max(1, Math.ceil(items.length / pageSize)),
});

const parsePaging = (request: Request) => {
  const url = new URL(request.url);
  return {
    page: Number(url.searchParams.get('page') ?? 1),
    pageSize: Number(url.searchParams.get('pageSize') ?? 20),
  };
};

// 对话式文档生成的内存态会话列表 (Mock)
interface MockConversation {
  conversationId: string;
  title: string;
  docType: string | null;
  documentId: string | null;
  mode: 'doc_chat' | 'qa';
  status: string;
  createdAt: string;
  updatedAt: string;
}
const mockConversations: MockConversation[] = [];

export const handlers = [
  http.get(`${api}/system/health`, async () => {
    await delay(180);
    return ok({
      status: 'healthy',
      components: {
        database: 'connected',
        redis: 'connected',
        celery: 'running',
        document_storage: 'available',
        llm_api: 'configured',
      },
      uptime: '0h 12m',
    });
  }),
  http.get(`${api}/system/config`, () =>
    ok({
      llm: {
        apiBase: 'https://api.deepseek.com',
        model: 'deepseek-chat',
        maxRetries: 3,
        timeoutSeconds: 60,
      },
      storage: {
        documentPath: './server/documents',
        ruleDataPath: './server/data/rules',
      },
      rules: {
        activeRuleVersionId: 'RV-20260519-001',
      },
    }),
  ),
  http.put(`${api}/system/config`, async ({ request }) => ok(await request.json())),
  http.post(`${api}/system/demo/init`, async () => {
    await delay(320);
    return ok({
      ruleVersionId: 'RV-20260519-001',
      sampleCaseIds: ['CASE-20260519-001', 'CASE-20260519-002'],
      message: '演示数据初始化成功',
    });
  }),

  http.post(`${api}/cases`, async ({ request }) => {
    await delay(260);
    const body = (await request.json()) as CaseCreateRequest;
    return ok(
      {
        caseId: body.rawText?.includes('Z99.9') ? 'CASE-20260519-002' : parsedDemoCase.caseId,
        status: 'created',
        createdAt: '2026-05-21T07:10:00Z',
      },
      '病历创建成功',
      201,
    );
  }),
  http.post(`${api}/cases/:caseId/parse`, async ({ params }) => {
    await delay(360);
    return ok(
      {
        caseId: String(params.caseId),
        parsedData: parsedDemoCase,
        warnings: ['未检测到出院方式时可由用户手动补充'],
        parseStatus: 'completed',
      },
      '解析完成',
    );
  }),
  http.post(`${api}/cases/:caseId/validate`, async ({ params }) =>
    ok({
      caseId: String(params.caseId),
      isValid: true,
      validationResults: [
        { field: 'primaryDiagnosis.code', isValid: true, code: 'A01.002+G01*' },
        { field: 'secondaryDiagnoses[0].code', isValid: true, code: 'J96.0' },
        { field: 'primaryProcedure.code', isValid: true, code: '38.1000x002' },
      ],
      errors: [],
      warnings: [],
    }),
  ),
  http.get(`${api}/cases`, ({ request }) => {
    const { page, pageSize } = parsePaging(request);
    return ok(paged(caseSummaries, page, pageSize));
  }),
  http.get(`${api}/cases/:caseId`, ({ params }) => ok({ ...parsedDemoCase, caseId: String(params.caseId) })),
  http.put(`${api}/cases/:caseId`, async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return ok({ ...parsedDemoCase, ...body, caseId: String(params.caseId), status: 'parsed' });
  }),
  http.delete(`${api}/cases/:caseId`, ({ params }) => ok({ caseId: String(params.caseId) })),

  http.get(`${api}/rules/versions`, () => ok({ items: ruleVersions, total: ruleVersions.length })),
  http.get(`${api}/rules/versions/:versionId`, ({ params }) =>
    ok({ ...demoRuleDetail, versionId: String(params.versionId) }),
  ),
  http.post(`${api}/rules/versions/:versionId/activate`, ({ params }) =>
    ok({ ...ruleVersions[0], versionId: String(params.versionId), status: 'active', isActive: true }),
  ),
  http.patch(`${api}/rules/versions/:versionId`, async ({ request, params }) => {
    const body = (await request.json()) as { versionName: string };
    const current = ruleVersions.find((item) => item.versionId === String(params.versionId)) ?? ruleVersions[0];
    return ok({ ...current, versionId: String(params.versionId), versionName: body.versionName });
  }),
  http.delete(`${api}/rules/versions/:versionId`, ({ params }) => ok({ versionId: String(params.versionId) })),
  http.get(`${api}/rules/search`, ({ request }) => {
    const url = new URL(request.url);
    const code = url.searchParams.get('code') || 'A01.002';
    return ok({
      matches: [
        {
          ruleType: 'mdc',
          code: 'MDCB',
          name: '神经系统疾病及功能障碍',
          matchedBy: `诊断编码 ${code} 命中前缀 A01`,
        },
      ],
    });
  }),
  http.post(`${api}/rules/import`, async () => {
    await delay(420);
    return ok(
      {
        versionId: 'RV-20260521-MOCK',
        versionName: '新导入规则',
        status: 'parsing',
        ruleCount: null,
        parseErrors: [],
      },
      '规则文件已上传，正在解析',
      201,
    );
  }),

  http.post(`${api}/grouping/execute`, async ({ request }) => {
    await delay(300);
    const body = (await request.json()) as { caseId?: string };
    return ok(
      {
        taskId: body.caseId === 'CASE-20260519-002' ? failedGroupingResult.taskId : successGroupingResult.taskId,
        status: 'executing',
        startedAt: '2026-05-21T07:20:00Z',
      },
      '入组任务已创建，正在执行',
      202,
    );
  }),
  http.get(`${api}/grouping/results/:taskId`, async ({ params }) => {
    await delay(420);
    return ok(String(params.taskId) === failedGroupingResult.taskId ? failedGroupingResult : successGroupingResult);
  }),
  http.get(`${api}/grouping/tasks`, ({ request }) => {
    const { page, pageSize } = parsePaging(request);
    return ok(paged(groupingTasks, page, pageSize));
  }),
  http.post(`${api}/grouping/batch`, async ({ request }) => {
    const body = (await request.json()) as { caseIds?: string[] };
    return ok({ batchTaskId: 'BATCH-20260521-001', totalCases: body.caseIds?.length ?? 0, status: 'executing' }, 'success', 202);
  }),

  http.post(`${api}/documents/generate`, async ({ request }) => {
    await delay(360);
    const body = (await request.json()) as DocumentGenerateRequest;
    return ok(
      {
        docTaskId: 'DOC-TASK-20260521-001',
        status: 'pending',
        createdAt: '2026-05-21T07:30:00Z',
        resultDocId: documents[0].docId,
        title: body.title,
      },
      'success',
      202,
    );
  }),
  http.get(`${api}/documents/tasks/:docTaskId`, ({ params }) =>
    ok({
      docTaskId: String(params.docTaskId),
      status: 'completed',
      createdAt: '2026-05-21T07:30:00Z',
      resultDocId: documents[0].docId,
    }),
  ),

  // 对话式文档生成 (注意: 须在 /documents/:docId 之前注册)
  http.get(`${api}/documents/conversations`, ({ request }) => {
    const { page, pageSize } = parsePaging(request);
    return ok(paged(mockConversations, page, pageSize));
  }),
  http.post(`${api}/documents/conversations`, async ({ request }) => {
    const body = (await request.json()) as { title?: string; docType?: string | null };
    const conv: MockConversation = {
      conversationId: `CONV-MOCK-${mockConversations.length + 1}`,
      title: body.title ?? '新文档对话',
      docType: body.docType ?? null,
      documentId: null,
      mode: 'doc_chat',
      status: 'active',
      createdAt: '2026-05-21T07:30:00Z',
      updatedAt: '2026-05-21T07:30:00Z',
    };
    mockConversations.unshift(conv);
    return ok(conv, 'success', 201);
  }),
  http.get(`${api}/documents/conversations/:convId`, ({ params }) => {
    const base = documentDetails[documents[0].docId];
    return ok({
      conversationId: String(params.convId),
      title: base.title,
      docType: base.type,
      documentId: base.docId,
      mode: 'doc_chat',
      status: 'active',
      createdAt: '2026-05-21T07:30:00Z',
      updatedAt: '2026-05-21T07:30:00Z',
      messages: [],
      document: base,
    });
  }),
  http.post(`${api}/documents/conversations/:convId/messages`, async ({ request, params }) => {
    await delay(120);
    const body = (await request.json()) as { instruction: string };
    const base = documentDetails[documents[0].docId];
    return ok({
      conversationId: String(params.convId),
      assistantMessage: {
        messageId: `MSG-MOCK-${Date.now()}`,
        role: 'assistant',
        content: `已根据你的要求更新《${base.title}》（V1.0）。`,
        docVersion: 'V1.0',
        createdAt: '2026-05-21T07:31:00Z',
      },
      document: { ...base, content: `${base.content}\n\n<!-- ${body.instruction} -->` },
    });
  }),
  http.delete(`${api}/documents/conversations/:convId`, ({ params }) => {
    const convId = String(params.convId);
    const index = mockConversations.findIndex((c) => c.conversationId === convId);
    if (index >= 0) mockConversations.splice(index, 1);
    return ok({ conversationId: convId });
  }),

  // Q&A 模式 (须在 /documents/:docId 之前注册)
  http.get(`${api}/documents/qa/conversations`, () => {
    const qa = mockConversations.filter((c) => c.mode === 'qa');
    return ok(paged(qa, 1, 50));
  }),
  http.post(`${api}/documents/qa/conversations`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as { title?: string };
    const conv: MockConversation = {
      conversationId: `QACONV-MOCK-${mockConversations.length + 1}`,
      title: body.title ?? '新问答',
      docType: null,
      documentId: null,
      mode: 'qa',
      status: 'active',
      createdAt: '2026-05-21T07:30:00Z',
      updatedAt: '2026-05-21T07:30:00Z',
    };
    mockConversations.unshift(conv);
    return ok(conv, 'success', 201);
  }),
  http.get(`${api}/documents/qa/conversations/:convId`, ({ params }) => {
    const conv = mockConversations.find((c) => c.conversationId === String(params.convId));
    return ok({
      conversationId: String(params.convId),
      title: conv?.title ?? '问答',
      docType: null,
      documentId: null,
      mode: 'qa',
      status: 'active',
      createdAt: '2026-05-21T07:30:00Z',
      updatedAt: '2026-05-21T07:30:00Z',
      messages: [],
    });
  }),
  http.post(`${api}/documents/qa/conversations/:convId/messages`, async ({ request, params }) => {
    await delay(120);
    const body = (await request.json()) as { instruction: string };
    return ok({
      conversationId: String(params.convId),
      assistantMessage: {
        messageId: `QAMSG-MOCK-${Date.now()}`,
        role: 'assistant',
        content: `关于「${body.instruction}」，结论如下：\n\n- **MDC 匹配**在 \`mdc_matcher.py\` 实现\n- 详见下表\n\n| 模块 | 文件 |\n| --- | --- |\n| 入组 | grouping_engine.py |`,
        docVersion: null,
        createdAt: '2026-05-21T07:31:00Z',
      },
    });
  }),
  http.post(`${api}/documents/qa/conversations/:convId/messages/stream`, async ({ request }) => {
    const body = (await request.json()) as { instruction: string };
    const encoder = new TextEncoder();
    const summary = {
      status: 'completed',
      steps: [
        {
          id: 'understand',
          title: '理解问题',
          detail: '识别问题范围、关键术语和需要核对的实现点。',
          status: 'completed',
        },
        {
          id: 'inspect',
          title: '查阅项目实现',
          detail: '已完成相关源码、接口和配置的检索与核对。',
          status: 'completed',
        },
        {
          id: 'compose',
          title: '组织回答',
          detail: '已完成结论组织和关键实现依据校验。',
          status: 'completed',
        },
      ],
    };
    const stream = new ReadableStream({
      async start(controller) {
        controller.enqueue(
          encoder.encode(
            `${JSON.stringify({
              type: 'reasoning',
              summary: {
                status: 'thinking',
                steps: [
                  {
                    id: 'understand',
                    title: '理解问题',
                    detail: '识别问题范围、关键术语和需要核对的实现点。',
                    status: 'completed',
                  },
                  {
                    id: 'inspect',
                    title: '查阅项目实现',
                    detail: '正在检索相关源码、接口和配置。',
                    status: 'running',
                  },
                ],
              },
            })}\n`,
          ),
        );
        await delay(80);
        controller.enqueue(encoder.encode(`${JSON.stringify({ type: 'reasoning', summary })}\n`));
        controller.enqueue(
          encoder.encode(
            `${JSON.stringify({
              type: 'answer',
              assistantMessage: {
                messageId: `QAMSG-MOCK-${Date.now()}`,
                role: 'assistant',
                content: `关于「${body.instruction}」，结论如下：\n\n- **MDC 匹配**在 \`mdc_matcher.py\` 实现\n- 详见下表\n\n| 模块 | 文件 |\n| --- | --- |\n| 入组 | grouping_engine.py |`,
                docVersion: null,
                reasoningSummary: summary,
                createdAt: '2026-05-21T07:31:00Z',
              },
            })}\n`,
          ),
        );
        controller.enqueue(encoder.encode(`${JSON.stringify({ type: 'done' })}\n`));
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      headers: { 'Content-Type': 'application/x-ndjson' },
    });
  }),

  http.get(`${api}/documents`, ({ request }) => {
    const url = new URL(request.url);
    const type = url.searchParams.get('type');
    const status = url.searchParams.get('status');
    const keyword = url.searchParams.get('keyword')?.trim();
    const filtered = documents.filter(
      (doc) =>
        (!type || doc.type === type) &&
        (!status || doc.status === status) &&
        (!keyword || doc.title.includes(keyword)),
    );
    const { page, pageSize } = parsePaging(request);
    return ok(paged(filtered, page, pageSize));
  }),
  http.get(`${api}/documents/:docId/preview`, ({ params }) =>
    ok(documentDetails[String(params.docId)] ?? documentDetails[documents[0].docId]),
  ),
  http.get(`${api}/documents/:docId`, ({ params }) =>
    ok(documentDetails[String(params.docId)] ?? documentDetails[documents[0].docId]),
  ),
  http.put(`${api}/documents/:docId`, async ({ request, params }) => {
    const body = (await request.json()) as { title?: string; content?: string };
    const base = documentDetails[String(params.docId)] ?? documentDetails[documents[0].docId];
    return ok({ ...base, title: body.title ?? base.title, content: body.content ?? base.content, version: 'V1.1' });
  }),
  http.post(`${api}/documents/:docId/submit`, ({ params }) => {
    const docId = String(params.docId);
    const base = documentDetails[docId] ?? documentDetails[documents[0].docId];
    return ok({
      docId,
      status: 'submitted',
      submittedAt: '2026-05-21T07:40:00Z',
      submissionRecord: {
        submitter: '用户/文档提交智能体',
        version: base.version,
        filePath: `/documents/${base.type}/${docId}_${base.version}.md`,
        checksum: 'sha256:demo-checksum',
      },
    });
  }),
  http.get(`${api}/documents/:docId/versions`, () =>
    ok({
      items: [
        { version: 'V1.0', changeDescription: '智能体初稿', createdAt: '2026-05-19T11:05:00Z' },
        { version: 'V1.1', changeDescription: '人工编辑保存', createdAt: '2026-05-21T07:40:00Z' },
      ],
      total: 2,
    }),
  ),
  http.patch(`${api}/documents/:docId/status`, async ({ request, params }) => {
    const body = (await request.json()) as { status: string };
    const base = documentDetails[String(params.docId)] ?? documentDetails[documents[0].docId];
    return ok({ ...base, status: body.status });
  }),
  http.get(`${api}/documents/:docId/download`, ({ params }) => ok({ docId: String(params.docId), fileUrl: '#' })),
  http.delete(`${api}/documents/:docId`, ({ params }) => ok({ docId: String(params.docId) })),

  http.post(`${api}/testcases/generate`, async ({ request }) => {
    await delay(360);
    const body = (await request.json()) as TestCaseGenerateRequest;
    return ok(
      {
        testTaskId: 'TEST-TASK-20260521-001',
        status: 'pending',
        createdAt: '2026-05-21T07:50:00Z',
        generatedCount: Math.min(body.maxCount ?? 3, testcases.length),
      },
      'success',
      202,
    );
  }),
  http.get(`${api}/testcases/tasks/:testTaskId`, ({ params }) =>
    ok({
      testTaskId: String(params.testTaskId),
      status: 'completed',
      createdAt: '2026-05-21T07:50:00Z',
      generatedCount: testcases.length,
    }),
  ),
  http.get(`${api}/testcases`, ({ request }) => {
    const url = new URL(request.url);
    const scenarioType = url.searchParams.get('scenarioType');
    const filtered = scenarioType ? testcases.filter((item) => item.scenarioType === scenarioType) : testcases;
    const { page, pageSize } = parsePaging(request);
    return ok(paged(filtered, page, pageSize));
  }),
  http.get(`${api}/testcases/:testCaseId`, ({ params }) =>
    ok(testcases.find((item) => item.testCaseId === String(params.testCaseId)) ?? testcases[0]),
  ),
  http.post(`${api}/testcases/:testCaseId/execute`, ({ params }) => {
    const item = testcases.find((testcase) => testcase.testCaseId === String(params.testCaseId)) ?? testcases[0];
    return ok({
      testCaseId: item.testCaseId,
      actualResult: item.expectedResult,
      expectedResult: item.expectedResult,
      isPassed: true,
      executedAt: '2026-05-21T08:00:00Z',
    });
  }),
  http.post(`${api}/testcases/export`, () => ok({ downloadUrl: '/api/v1/testcases/export/mock.xlsx' })),
  http.post(`${api}/testcases/submit-to-documents`, () => ok({ docTaskId: 'DOC-TASK-TEST-001' })),

  http.get(`${api}/tasks`, ({ request }) => {
    const { page, pageSize } = parsePaging(request);
    return ok(paged(tasks, page, pageSize));
  }),
  http.get(`${api}/tasks/:taskId`, ({ params }) =>
    ok({
      ...(tasks.find((task) => task.taskId === String(params.taskId)) ?? tasks[0]),
      steps: [
        { stepName: 'case_parse', stepOrder: 1, status: 'completed', durationMs: 221 },
        { stepName: 'rule_retrieve', stepOrder: 2, status: 'completed', durationMs: 114 },
        { stepName: 'drg_grouping', stepOrder: 3, status: 'completed', durationMs: 76 },
        { stepName: 'explain_generate', stepOrder: 4, status: 'completed', durationMs: 640 },
      ],
    }),
  ),
  http.post(`${api}/tasks/:taskId/cancel`, ({ params }) => ok({ taskId: String(params.taskId), status: 'cancelled' })),
  http.post(`${api}/tasks/:taskId/review`, ({ params }) => ok({ taskId: String(params.taskId), status: 'needs_review' })),
  http.get(`${api}/logs`, ({ request }) => {
    const { page, pageSize } = parsePaging(request);
    return ok(paged(logs, page, pageSize));
  }),
];
