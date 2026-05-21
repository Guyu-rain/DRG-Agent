export type RuleStatus = 'imported' | 'parsing' | 'active' | 'archived' | 'error';
export type RuleType = 'mdc' | 'adrg' | 'drg' | 'mcc' | 'cc';

export interface RuleCount {
  mdc: number;
  adrg: number;
  drg: number;
  mcc?: number;
  cc?: number;
}

export interface RuleVersionSummary {
  versionId: string;
  versionName: string;
  description?: string;
  status: RuleStatus;
  ruleCount: RuleCount;
  importedAt: string;
  isActive: boolean;
}

export interface MdcRule {
  code: string;
  name: string;
  icdPrefix?: string[];
  icdPrefixes?: string[];
}

export interface AdrgRule {
  code: string;
  name: string;
  mdc: string;
  conditions?: Record<string, unknown>;
  surgeryList?: string[];
}

export interface DrgRule {
  code: string;
  name: string;
  adrg: string;
  ccLevel?: 'MCC' | 'CC' | 'NONE';
}

export interface CcMccRule {
  code: string;
  name: string;
  level: 'MCC' | 'CC';
  exclusionDiags?: string[];
}

export interface ExclusionRule {
  diagCode: string;
  excludedBy: string[];
}

export interface RuleVersionDetail extends RuleVersionSummary {
  mdcList: MdcRule[];
  adrgList: AdrgRule[];
  drgList: DrgRule[];
  mccList: CcMccRule[];
  ccList: CcMccRule[];
  exclusionTable: ExclusionRule[];
}

export interface RuleImportResponse {
  versionId: string;
  versionName: string;
  status: RuleStatus;
  ruleCount: RuleCount | null;
  parseErrors: string[];
}

export interface RuleSearchMatch {
  ruleType: RuleType;
  code: string;
  name: string;
  matchedBy: string;
}
