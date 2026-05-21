import type { PatientCase, PatientCaseSummary } from '@/types/case';

export const demoRawText =
  '主诊断：A01.002+G01* 伤寒性脑膜炎\n次要诊断：J96.0 急性呼吸衰竭\n主要手术：38.1000x002 动脉内膜剥脱术';

export const parsedDemoCase: PatientCase = {
  caseId: 'CASE-20260519-001',
  status: 'parsed',
  createdAt: '2026-05-19T10:30:00Z',
  updatedAt: '2026-05-19T10:31:00Z',
  patientId: 'P001',
  age: 45,
  gender: '男',
  rawText: demoRawText,
  primaryDiagnosis: {
    code: 'A01.002+G01*',
    name: '伤寒性脑膜炎',
    sourceText: '主诊断：A01.002+G01* 伤寒性脑膜炎',
  },
  secondaryDiagnoses: [
    { code: 'J96.0', name: '急性呼吸衰竭', sourceText: '次要诊断：J96.0 急性呼吸衰竭' },
  ],
  primaryProcedure: {
    code: '38.1000x002',
    name: '动脉内膜剥脱术',
    surgeryLevel: 3,
    sourceText: '主要手术：38.1000x002 动脉内膜剥脱术',
  },
  otherProcedures: [],
  dischargeType: '医嘱离院',
  groupingCount: 1,
};

export const caseSummaries: PatientCaseSummary[] = [
  {
    caseId: parsedDemoCase.caseId,
    summary: '主诊断：A01.002+G01* 伤寒性脑膜炎',
    status: 'parsed',
    createdAt: parsedDemoCase.createdAt,
    groupingCount: 1,
  },
  {
    caseId: 'CASE-20260519-002',
    summary: '主诊断：Z99.9 未映射诊断',
    status: 'validated',
    createdAt: '2026-05-19T11:00:00Z',
    groupingCount: 1,
  },
];
