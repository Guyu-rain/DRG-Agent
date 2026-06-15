import type { TaskStatus } from './api';

export type TaskKind = 'grouping' | 'document' | 'testcase';

export interface TaskStep {
  stepName: string;
  stepOrder: number;
  status: TaskStatus | 'skipped';
  durationMs?: number;
  inputSummary?: string;
  outputSummary?: string;
  errorMessage?: string;
}

export interface TaskSummary {
  taskId: string;
  type: TaskKind;
  title: string;
  status: TaskStatus;
  createdAt: string;
  durationMs?: number;
}

export interface ExecutionLog {
  logId: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  agent: string;
  taskId?: string;
  message: string;
  inputSummary?: string;
  outputSummary?: string;
  errorDetail?: string;
}

export interface SystemConfig {
  llm: {
    apiBase: string;
    model: string;
    maxRetries: number;
    timeoutSeconds: number | null;
  };
  storage: {
    documentPath: string;
    ruleDataPath: string;
  };
  rules: {
    activeRuleVersionId?: string;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  components: Record<string, string>;
  uptime?: string;
}
