export type ScenarioType = 'normal' | 'boundary' | 'abnormal';
export type TestPriority = 'high' | 'medium' | 'low';

export interface TestCaseGenerateRequest {
  ruleVersionId: string;
  scenarioTypes: ScenarioType[];
  scope: {
    mdcList?: string[];
    adrgList?: string[];
    includeAllRules: boolean;
  };
  sampleCaseIds?: string[];
  maxCount?: number;
}

export interface TestTaskResponse {
  testTaskId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  createdAt: string;
  generatedCount?: number;
}

export interface TestCaseItem {
  testCaseId: string;
  id?: string;
  title: string;
  scenarioType: ScenarioType;
  priority: TestPriority;
  requirementRef?: string;
  ruleVersion?: string;
  inputCase: Record<string, unknown>;
  expectedResult: Record<string, unknown>;
  actualResult?: Record<string, unknown>;
  isPassed?: boolean | null;
  executedAt?: string;
  createdAt: string;
}

export interface TestExecutionResponse {
  testCaseId: string;
  actualResult: Record<string, unknown>;
  expectedResult: Record<string, unknown>;
  isPassed: boolean;
  executedAt: string;
}
