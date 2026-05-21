import axios, { type AxiosError, type AxiosRequestConfig } from 'axios';
import { message } from 'antd';
import type { ApiErrorResponse } from '@/types/api';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiErrorResponse>) => {
    const msg = error.response?.data?.message || error.message || '网络错误';
    message.error(msg);
    return Promise.reject(error);
  },
);

export function request<T>(config: AxiosRequestConfig, signal?: AbortSignal): Promise<T> {
  return apiClient({ ...config, signal }) as Promise<T>;
}
