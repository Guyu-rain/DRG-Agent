import type { TaskStatus } from './api';

export interface GroupingExecuteRequest {
  caseId: string;
  ruleVersionId: string;
}

export interface GroupingExecuteResponse {
  taskId: string;
  status: TaskStatus;
  startedAt: string;
}

export interface GroupingCodeName {
  code: string;
  name: string;
}

export interface EvidenceItem {
  step: number;
  type: string;
  description: string;
  matchedCode?: string;
  matchedRule?: string;
  ccLevel?: 'MCC' | 'CC' | 'NONE';
  excludedBy?: string[];
  excluded?: boolean;
}

export interface CandidateRule {
  adrg: string;
  drg: string;
  name: string;
  reason: string;
}

export interface GroupingResult {
  mdc: GroupingCodeName;
  adrg: GroupingCodeName;
  drg: GroupingCodeName;
  complication: 'MCC' | 'CC' | 'NONE';
  evidence: EvidenceItem[];
  explanation: string;
  candidateRules: CandidateRule[];
  warnings: string[];
}

export interface GroupingError {
  type: string;
  stage: string;
  message: string;
  suggestions: string[];
  candidateMatches?: unknown[];
}

export interface GroupingResultResponse {
  taskId: string;
  status: TaskStatus;
  caseId: string;
  ruleVersion: string;
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
  result: GroupingResult | null;
  error?: GroupingError;
  inputSnapshot?: Record<string, unknown>;
}

export interface GroupingTaskSummary {
  taskId: string;
  status: TaskStatus;
  caseId: string;
  ruleVersion: string;
  resultDrg?: string;
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
}
