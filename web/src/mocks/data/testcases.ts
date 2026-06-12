import type { TestCaseItem } from '@/types/testcase';

export const testcases: TestCaseItem[] = [
  {
    testCaseId: 'TC-D-001',
    title: '主诊断与手术正常命中 BB11',
    scenarioType: 'normal',
    priority: 'high',
    requirementRef: 'FR-D-05',
    ruleVersion: 'RV-20260519-001',
    inputCase: {
      primaryDiagnosis: 'A01.002+G01*',
      secondaryDiagnoses: ['J96.0'],
      primaryProcedure: '38.1000x002',
    },
    expectedResult: { mdc: 'MDCB', adrg: 'BB1', drg: 'BB11' },
    isPassed: null,
    createdAt: '2026-05-20T10:00:00Z',
  },
  {
    testCaseId: 'TC-D-014',
    title: 'MCC 被排除后降级',
    scenarioType: 'boundary',
    priority: 'medium',
    requirementRef: 'FR-D-06',
    ruleVersion: 'RV-20260519-001',
    inputCase: { primaryDiagnosis: 'I10', secondaryDiagnoses: ['I10'] },
    expectedResult: { complication: 'NONE' },
    isPassed: null,
    createdAt: '2026-05-20T10:12:00Z',
  },
  {
    testCaseId: 'TC-D-025',
    title: '主诊断缺失返回未入组',
    scenarioType: 'abnormal',
    priority: 'high',
    requirementRef: 'FR-D-07',
    ruleVersion: 'RV-20260519-001',
    inputCase: { primaryDiagnosis: null },
    expectedResult: { isGrouped: false, stage: 'mdc_matching' },
    isPassed: false,
    createdAt: '2026-05-20T10:25:00Z',
  },
];
