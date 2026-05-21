import { request } from './api';
import type { ApiResponse } from '@/types/api';
import type { HealthStatus, SystemConfig } from '@/types/task';

export const systemApi = {
  health: () => request<ApiResponse<HealthStatus>>({ method: 'GET', url: '/system/health' }),
  config: () => request<ApiResponse<SystemConfig>>({ method: 'GET', url: '/system/config' }),
  updateConfig: (data: SystemConfig) =>
    request<ApiResponse<SystemConfig>>({ method: 'PUT', url: '/system/config', data }),
  initDemo: () =>
    request<ApiResponse<{ ruleVersionId?: string; sampleCaseIds?: string[]; message: string }>>({
      method: 'POST',
      url: '/system/demo/init',
    }),
};
