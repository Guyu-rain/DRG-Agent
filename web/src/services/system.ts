import { request } from './api';
import type { ApiResponse } from '@/types/api';
import type { SystemConfig } from '@/types/task';

export const systemApi = {
  health: () =>
    request<
      ApiResponse<{
        status: 'healthy' | 'degraded';
        database: string;
        redis: string;
        llm: string;
        activeRuleVersionId?: string;
      }>
    >({ method: 'GET', url: '/system/health' }),
  config: () => request<ApiResponse<SystemConfig>>({ method: 'GET', url: '/system/config' }),
  updateConfig: (data: SystemConfig) =>
    request<ApiResponse<SystemConfig>>({ method: 'PUT', url: '/system/config', data }),
  initDemo: () =>
    request<ApiResponse<{ initialized: boolean; message: string }>>({
      method: 'POST',
      url: '/system/init-demo',
    }),
};
