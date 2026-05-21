export type CaseStatus = 'created' | 'parsing' | 'parsed' | 'validated' | 'error';
export type SourceType = 'text' | 'structured';

export interface DiagnosisInput {
  code?: string | null;
  name?: string | null;
  sourceText?: string;
}

export interface ProcedureInput {
  code?: string | null;
  name?: string | null;
  surgeryLevel?: number;
  level?: number;
  sourceText?: string;
}

export interface StructuredCaseInput {
  patientId?: string;
  age?: number;
  gender?: '男' | '女' | '未知' | string;
  primaryDiagnosis?: DiagnosisInput;
  secondaryDiagnoses?: DiagnosisInput[];
  primaryProcedure?: ProcedureInput;
  otherProcedures?: ProcedureInput[];
  dischargeType?: string;
  rawText?: string;
}

export interface CaseCreateRequest {
  rawText?: string;
  structuredData?: StructuredCaseInput;
  sourceType: SourceType;
}

export interface CaseCreateResponse {
  caseId: string;
  status: CaseStatus;
  createdAt: string;
}

export interface ParsedCaseData extends StructuredCaseInput {
  rawText?: string;
}

export interface CaseParseResponse {
  caseId: string;
  parsedData: ParsedCaseData;
  warnings: string[];
  parseStatus: 'completed' | 'failed';
}

export interface ValidationItem {
  field: string;
  isValid: boolean;
  code?: string | null;
  message?: string;
}

export interface CaseValidationResponse {
  caseId: string;
  isValid: boolean;
  validationResults: ValidationItem[];
  errors: string[];
  warnings: string[];
}

export interface PatientCaseSummary {
  caseId: string;
  summary: string;
  status: CaseStatus;
  createdAt: string;
  groupingCount: number;
}

export interface PatientCase extends ParsedCaseData {
  caseId: string;
  status: CaseStatus;
  createdAt: string;
  updatedAt?: string;
  groupingCount?: number;
}
