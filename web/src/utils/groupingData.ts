import type { DiagnosisInput, PatientCase, ProcedureInput, StructuredCaseInput } from '@/types/case';
import type { GroupingResultResponse } from '@/types/grouping';
import type { TestCaseItem } from '@/types/testcase';

function compact<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== null && item !== ''),
  ) as T;
}

function diagnosisToExample(diagnosis?: DiagnosisInput) {
  if (!diagnosis) return '';
  if (!diagnosis.code) return diagnosis.name ?? '';
  return compact({
    疾病名称: diagnosis.name,
    疾病编码: diagnosis.code,
  });
}

function diagnosisListToExample(diagnoses?: DiagnosisInput[]) {
  return (diagnoses ?? []).map((diagnosis) =>
    compact({
      疾病名称: diagnosis.name,
      疾病编码: diagnosis.code,
    }),
  );
}

function procedureToExample(procedure?: ProcedureInput) {
  return compact({
    手术名称: procedure?.name,
    手术编码: procedure?.code,
    手术级别: procedure?.surgeryLevel ?? procedure?.level,
  });
}

export function buildGroupingResultExport(response: GroupingResultResponse, patientCase: PatientCase) {
  if (!response.result) throw new Error('没有可保存的入组结果');

  return [
    compact({
      性别: patientCase.gender,
      年龄: patientCase.age,
      主要诊断: diagnosisToExample(patientCase.primaryDiagnosis),
      次要诊断列表: diagnosisListToExample(patientCase.secondaryDiagnoses),
      主要手术: procedureToExample(patientCase.primaryProcedure),
      其他手术列表: (patientCase.otherProcedures ?? []).map(procedureToExample),
      result: {
        success: true,
        mdc: response.result.mdc.code,
        adrg: response.result.adrg.code,
        drg: response.result.drg.code,
        complication: response.result.complication,
        reason: response.result.evidence.map((item) => item.description),
      },
    }),
  ];
}

function toDiagnosis(value: unknown): DiagnosisInput | undefined {
  if (typeof value === 'string') return { code: value };
  if (!value || typeof value !== 'object') return undefined;
  const item = value as Record<string, unknown>;
  return {
    code: typeof item.code === 'string' ? item.code : null,
    name: typeof item.name === 'string' ? item.name : null,
  };
}

function toProcedure(value: unknown): ProcedureInput | undefined {
  if (typeof value === 'string') return { code: value };
  if (!value || typeof value !== 'object') return undefined;
  const item = value as Record<string, unknown>;
  return {
    code: typeof item.code === 'string' ? item.code : null,
    name: typeof item.name === 'string' ? item.name : null,
    surgeryLevel: typeof item.surgeryLevel === 'number' ? item.surgeryLevel : undefined,
    level: typeof item.level === 'number' ? item.level : undefined,
  };
}

function formatCodeName(value?: DiagnosisInput | ProcedureInput) {
  if (!value) return '';
  return [value.code, value.name].filter(Boolean).join(' ');
}

function formatList(values: Array<DiagnosisInput | ProcedureInput>) {
  return values.map(formatCodeName).filter(Boolean).join('；');
}

export function testCaseToText(testCase: TestCaseItem): string {
  const input = testCase.inputCase as StructuredCaseInput & Record<string, unknown>;
  const primaryDiagnosis = toDiagnosis(input.primaryDiagnosis);
  const secondaryDiagnoses = Array.isArray(input.secondaryDiagnoses)
    ? input.secondaryDiagnoses.map(toDiagnosis).filter((item): item is DiagnosisInput => Boolean(item))
    : [];
  const primaryProcedure = toProcedure(input.primaryProcedure);
  const otherProcedures = Array.isArray(input.otherProcedures)
    ? input.otherProcedures.map(toProcedure).filter((item): item is ProcedureInput => Boolean(item))
    : [];

  return [
    `测试用例：${testCase.title}`,
    input.patientId ? `患者编号：${input.patientId}` : null,
    input.gender ? `性别：${input.gender}` : null,
    input.age != null ? `年龄：${input.age}` : null,
    `主诊断：${formatCodeName(primaryDiagnosis)}`,
    `次要诊断：${formatList(secondaryDiagnoses)}`,
    `主要手术：${formatCodeName(primaryProcedure)}`,
    `其他手术：${formatList(otherProcedures)}`,
  ]
    .filter((line): line is string => line !== null)
    .join('\n');
}
