export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
  detail?: unknown;
}

export interface ApiErrorResponse {
  code: number;
  data: null;
  message: string;
  detail?: unknown;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface SimpleListResponse<T> {
  items: T[];
  total: number;
}

export type TaskStatus = 'pending' | 'executing' | 'running' | 'completed' | 'failed' | 'cancelled' | 'needs_review';

export type StatusTone = 'success' | 'processing' | 'warning' | 'error' | 'default';
