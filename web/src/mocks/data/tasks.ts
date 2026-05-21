import type { ExecutionLog, TaskSummary } from '@/types/task';

export const tasks: TaskSummary[] = [
  {
    taskId: 'TASK-GROUP-20260519-001',
    type: 'grouping',
    title: '课程示例入组',
    status: 'completed',
    createdAt: '2026-05-19T10:35:00Z',
    durationMs: 1534,
  },
  {
    taskId: 'DOC-TASK-20260519-001',
    type: 'document',
    title: '生成需求分析文档',
    status: 'completed',
    createdAt: '2026-05-19T11:00:00Z',
    durationMs: 8200,
  },
  {
    taskId: 'TEST-TASK-20260520-001',
    type: 'testcase',
    title: '生成 MDCB 测试用例',
    status: 'completed',
    createdAt: '2026-05-20T10:00:00Z',
    durationMs: 6400,
  },
  {
    taskId: 'TASK-GROUP-20260519-003',
    type: 'grouping',
    title: '未映射诊断入组',
    status: 'failed',
    createdAt: '2026-05-19T11:10:00Z',
    durationMs: 611,
  },
];

export const logs: ExecutionLog[] = [
  {
    logId: 'LOG-20260519-001',
    timestamp: '2026-05-19T10:35:00Z',
    level: 'info',
    agent: 'AgentOrchestrator',
    taskId: 'TASK-GROUP-20260519-001',
    message: '入组工作流启动',
    inputSummary: 'CASE-20260519-001 + RV-20260519-001',
    outputSummary: '进入 case_parse',
  },
  {
    logId: 'LOG-20260519-002',
    timestamp: '2026-05-19T10:35:01Z',
    level: 'info',
    agent: 'DRGGroupingAgent',
    taskId: 'TASK-GROUP-20260519-001',
    message: '规则引擎完成 MDC→ADRG→DRG 匹配',
    outputSummary: '{"mdc":"MDCB","adrg":"BB1","drg":"BB11"}',
  },
  {
    logId: 'LOG-20260519-003',
    timestamp: '2026-05-19T11:10:01Z',
    level: 'error',
    agent: 'MDCMatcher',
    taskId: 'TASK-GROUP-20260519-003',
    message: '主诊断无法匹配 MDC',
    errorDetail: 'Z99.9 未命中当前规则索引',
  },
];
