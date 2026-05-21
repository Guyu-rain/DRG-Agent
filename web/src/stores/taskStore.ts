import { create } from 'zustand';
import { tasksApi } from '@/services';
import type { ExecutionLog, TaskSummary } from '@/types/task';

interface TaskState {
  tasks: TaskSummary[];
  logs: ExecutionLog[];
  fetchTasks: () => Promise<void>;
  fetchLogs: (params?: Record<string, unknown>) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  logs: [],
  fetchTasks: async () => {
    const response = await tasksApi.list({ page: 1, pageSize: 20 });
    set({ tasks: response.data.items });
  },
  fetchLogs: async (params) => {
    const response = await tasksApi.logs({ page: 1, pageSize: 50, ...params });
    set({ logs: response.data.items });
  },
}));
