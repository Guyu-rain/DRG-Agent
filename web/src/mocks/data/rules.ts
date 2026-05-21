import type { RuleVersionDetail, RuleVersionSummary } from '@/types/rule';

export const demoRuleDetail: RuleVersionDetail = {
  versionId: 'RV-20260519-001',
  versionName: 'DRG 2.0 演示规则',
  description: '课程演示用规则，覆盖神经系统复合手术示例',
  status: 'active',
  isActive: true,
  importedAt: '2026-05-19T10:00:00Z',
  ruleCount: { mdc: 26, adrg: 376, drg: 628, mcc: 2457, cc: 4553 },
  mdcList: [
    { code: 'MDCB', name: '神经系统疾病及功能障碍', icdPrefix: ['G00-G99', 'A01'] },
    { code: 'MDCF', name: '循环系统疾病及功能障碍', icdPrefix: ['I00-I99'] },
    { code: 'MDCK', name: '内分泌、营养及代谢疾病', icdPrefix: ['E00-E99'] },
  ],
  adrgList: [
    { code: 'BB1', name: '神经系统复合手术', mdc: 'MDCB', surgeryList: ['38.1000x002'] },
    { code: 'BB2', name: '神经系统其他手术', mdc: 'MDCB', surgeryList: ['01.2400'] },
    { code: 'BF1', name: '循环系统复杂介入', mdc: 'MDCF', surgeryList: ['36.0600'] },
  ],
  drgList: [
    { code: 'BB11', name: '神经系统复合手术，伴严重合并症或并发症', adrg: 'BB1', ccLevel: 'MCC' },
    { code: 'BB13', name: '神经系统复合手术，伴一般合并症或并发症', adrg: 'BB1', ccLevel: 'CC' },
    { code: 'BB15', name: '神经系统复合手术，不伴合并症或并发症', adrg: 'BB1', ccLevel: 'NONE' },
  ],
  mccList: [{ code: 'J96.0', name: '急性呼吸衰竭', level: 'MCC', exclusionDiags: [] }],
  ccList: [{ code: 'I10', name: '原发性高血压', level: 'CC', exclusionDiags: ['I10'] }],
  exclusionTable: [{ diagCode: 'J96.0', excludedBy: [] }],
};

export const ruleVersions: RuleVersionSummary[] = [
  demoRuleDetail,
  {
    versionId: 'RV-20260512-002',
    versionName: 'DRG 2.0 导入草稿',
    description: '用于导入流程演示的非活跃版本',
    status: 'imported',
    ruleCount: { mdc: 2, adrg: 8, drg: 14, mcc: 12, cc: 22 },
    importedAt: '2026-05-12T09:28:00Z',
    isActive: false,
  },
];
