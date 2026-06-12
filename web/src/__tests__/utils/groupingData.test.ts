import { describe, expect, it } from 'vitest';
import { successGroupingResult } from '@/mocks/data/grouping';
import type { PatientCase } from '@/types/case';
import { buildGroupingResultExport, testCaseToText } from '@/utils/groupingData';

const patientCase: PatientCase = {
  caseId: 'CASE-001',
  status: 'parsed',
  createdAt: '2026-06-12T00:00:00Z',
  gender: '男',
  age: 72,
  primaryDiagnosis: { code: 'C16.301', name: '胃窦恶性肿瘤' },
  secondaryDiagnoses: [{ code: 'K66.002', name: '肠粘连' }],
  primaryProcedure: { code: '43.7x03', name: '腹腔镜胃大部切除术', surgeryLevel: 3 },
  otherProcedures: [{ code: '40.5911', name: '腹腔淋巴结清扫术', level: 4 }],
};

describe('grouping data conversion', () => {
  it('exports one result using the example JSON field contract', () => {
    const exported = buildGroupingResultExport(successGroupingResult, patientCase);

    expect(exported).toHaveLength(1);
    expect(exported[0]).toMatchObject({
      性别: '男',
      年龄: 72,
      主要诊断: { 疾病名称: '胃窦恶性肿瘤', 疾病编码: 'C16.301' },
      次要诊断列表: [{ 疾病名称: '肠粘连', 疾病编码: 'K66.002' }],
      主要手术: { 手术名称: '腹腔镜胃大部切除术', 手术编码: '43.7x03', 手术级别: 3 },
      result: {
        success: true,
        mdc: 'MDCB',
        adrg: 'BB1',
        drg: 'BB11',
        complication: 'MCC',
      },
    });
    expect(exported[0].result.reason).toEqual(successGroupingResult.result?.evidence.map((item) => item.description));
  });

  it('converts testcase input into editable medical text without expected results', () => {
    const text = testCaseToText({
      testCaseId: 'TC-001',
      title: '测试标题',
      scenarioType: 'normal',
      priority: 'high',
      inputCase: {
        primaryDiagnosis: { code: 'A01.002', name: '伤寒' },
        secondaryDiagnoses: [{ code: 'J96.0', name: '急性呼吸衰竭' }],
        primaryProcedure: { code: '38.1000x002', name: '动脉内膜剥脱术' },
      },
      expectedResult: { drg: 'BB11' },
      createdAt: '2026-06-12T00:00:00Z',
    });

    expect(text).toContain('主诊断：A01.002 伤寒');
    expect(text).toContain('次要诊断：J96.0 急性呼吸衰竭');
    expect(text).toContain('主要手术：38.1000x002 动脉内膜剥脱术');
    expect(text).not.toContain('BB11');
  });
});
