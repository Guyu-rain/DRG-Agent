import type { GroupingResultResponse, GroupingTaskSummary } from '@/types/grouping';

export const successGroupingResult: GroupingResultResponse = {
  taskId: 'TASK-GROUP-20260519-001',
  status: 'completed',
  caseId: 'CASE-20260519-001',
  ruleVersion: 'DRG 2.0 演示规则',
  startedAt: '2026-05-19T10:35:00Z',
  finishedAt: '2026-05-19T10:35:02Z',
  durationMs: 1534,
  result: {
    mdc: { code: 'MDCB', name: '神经系统疾病及功能障碍' },
    adrg: { code: 'BB1', name: '神经系统复合手术' },
    drg: { code: 'BB11', name: '神经系统复合手术，伴严重合并症或并发症' },
    complication: 'MCC',
    evidence: [
      {
        step: 1,
        type: 'mdc_match',
        description: '主诊断 A01.002+G01*（伤寒性脑膜炎）命中 ICD 前缀 A01，进入 MDCB',
        matchedCode: 'A01.002+G01*',
        matchedRule: 'MDCB ICD前缀：A01',
      },
      {
        step: 2,
        type: 'adrg_match',
        description: '主要手术 38.1000x002（动脉内膜剥脱术）在 MDCB 下命中 BB1',
        matchedCode: '38.1000x002',
        matchedRule: 'BB1 手术列表：38.1000x002',
      },
      {
        step: 3,
        type: 'cc_mcc_evaluation',
        description: '次要诊断 J96.0（急性呼吸衰竭）属于 MCC 列表',
        matchedCode: 'J96.0',
        ccLevel: 'MCC',
      },
      {
        step: 4,
        type: 'exclusion_check',
        description: 'J96.0 未被主诊断 A01.002+G01* 的排除表排除',
        excludedBy: [],
        excluded: false,
      },
      {
        step: 5,
        type: 'drg_final',
        description: 'BB1 支持 MCC 分层，最终进入 BB11',
        matchedRule: 'BB1→BB11：MCC=是',
      },
    ],
    explanation:
      '根据主诊断 A01.002+G01*，病例进入 MDCB。主要手术 38.1000x002 命中 BB1。次要诊断 J96.0 属于 MCC 且未被排除，因此最终进入 BB11。',
    candidateRules: [
      { adrg: 'BB1', drg: 'BB11', name: '伴严重合并症或并发症', reason: '命中（MCC：J96.0）' },
      { adrg: 'BB1', drg: 'BB15', name: '不伴合并症或并发症', reason: '未命中（存在 MCC）' },
    ],
    warnings: [],
  },
  inputSnapshot: {
    primaryDiagnosis: 'A01.002+G01*',
    secondaryDiagnoses: ['J96.0'],
    primaryProcedure: '38.1000x002',
  },
};

export const failedGroupingResult: GroupingResultResponse = {
  taskId: 'TASK-GROUP-20260519-003',
  status: 'failed',
  caseId: 'CASE-20260519-002',
  ruleVersion: 'DRG 2.0 演示规则',
  startedAt: '2026-05-19T11:10:00Z',
  finishedAt: '2026-05-19T11:10:01Z',
  durationMs: 611,
  result: null,
  error: {
    type: 'NO_RULE_MATCH',
    stage: 'mdc_matching',
    message: '主诊断 Z99.9 无法映射到任何 MDC',
    suggestions: ['检查诊断编码是否正确', '尝试使用结构化输入'],
    candidateMatches: [],
  },
};

export const groupingTasks: GroupingTaskSummary[] = [
  {
    taskId: successGroupingResult.taskId,
    status: 'completed',
    caseId: successGroupingResult.caseId,
    ruleVersion: successGroupingResult.ruleVersion,
    resultDrg: 'BB11',
    startedAt: successGroupingResult.startedAt,
    finishedAt: successGroupingResult.finishedAt,
    durationMs: successGroupingResult.durationMs,
  },
  {
    taskId: failedGroupingResult.taskId,
    status: 'failed',
    caseId: failedGroupingResult.caseId,
    ruleVersion: failedGroupingResult.ruleVersion,
    startedAt: failedGroupingResult.startedAt,
    finishedAt: failedGroupingResult.finishedAt,
    durationMs: failedGroupingResult.durationMs,
  },
];
