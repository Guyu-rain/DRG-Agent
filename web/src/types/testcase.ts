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
  status: 'pending' | 'running' | 'completed' | 'failed';
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
  inputCase: Record<string, unknown>;
  expectedResult: Record<string, unknown>;
  actualResult?: Record<string, unknown>;
  isPassed?: boolean | null;
  createdAt: string;
}
