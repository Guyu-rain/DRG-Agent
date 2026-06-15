import axios, { type AxiosError, type AxiosRequestConfig } from 'axios';
import { message } from 'antd';
import type { ApiErrorResponse } from '@/types/api';

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export const apiClient = axios.create({
  // 相对路径：开发环境经 Vite 代理转发到后端 :8000，避免跨域
  baseURL: apiBaseUrl,
  // 文档 / 测试用例生成可能进行多轮 LLM 工具调用，不设置固定超时
  timeout: 0,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiErrorResponse>) => {
    let msg = error.response?.data?.message;
    if (!msg) {
      if (error.code === 'ECONNABORTED') {
        msg = '请求超时，请稍后重试';
      } else if (error.code === 'ERR_NETWORK') {
        msg = '网络连接失败，请确认后端服务已启动';
      } else {
        msg = error.message || '网络错误';
      }
    }
    message.error(msg);
    return Promise.reject(error);
  },
);

export function request<T>(config: AxiosRequestConfig, signal?: AbortSignal): Promise<T> {
  return apiClient({ ...config, signal }) as Promise<T>;
}

export function apiUrl(path: string) {
  return `${apiBaseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}
