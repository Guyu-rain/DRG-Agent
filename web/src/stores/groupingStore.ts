import { create } from 'zustand';
import { casesApi, groupingApi, tasksApi } from '@/services';
import type { CaseCreateRequest, PatientCase, ParsedCaseData } from '@/types/case';
import type { GroupingResultResponse, GroupingTaskSummary } from '@/types/grouping';

interface GroupingState {
  currentCaseId: string | null;
  currentCase: PatientCase | null;
  currentResult: GroupingResultResponse | null;
  resultRuleVersion: string | null;
  currentTaskId: string | null;
  selectedRuleVersion: string | null;
  inputMode: 'text' | 'structured';
  isExecuting: boolean;
  isParsing: boolean;
  history: GroupingTaskSummary[];
  setRuleVersion: (id: string) => void;
  setInputMode: (mode: 'text' | 'structured') => void;
  submitCase: (data: CaseCreateRequest) => Promise<string>;
  parseCase: (caseId: string) => Promise<ParsedCaseData>;
  executeGrouping: () => Promise<string>;
  fetchResult: (taskId: string) => Promise<GroupingResultResponse>;
  fetchHistory: () => Promise<void>;
  resetWorkspace: () => void;
  submitForReview: () => Promise<void>;
}

export const useGroupingStore = create<GroupingState>((set, get) => ({
  currentCaseId: null,
  currentCase: null,
  currentResult: null,
  resultRuleVersion: null,
  currentTaskId: null,
  selectedRuleVersion: null,
  inputMode: 'text',
  isExecuting: false,
  isParsing: false,
  history: [],
  setRuleVersion: (id) => set({ selectedRuleVersion: id }),
  setInputMode: (mode) => set({ inputMode: mode }),
  submitCase: async (data) => {
    const response = await casesApi.create(data);
    set({ currentCaseId: response.data.caseId, currentResult: null, resultRuleVersion: null });
    return response.data.caseId;
  },
  parseCase: async (caseId) => {
    set({ isParsing: true });
    try {
      const response = await casesApi.parse(caseId);
      set({
        currentCase: {
          ...response.data.parsedData,
          caseId,
          status: 'parsed',
          createdAt: new Date().toISOString(),
        },
      });
      return response.data.parsedData;
    } finally {
      set({ isParsing: false });
    }
  },
  executeGrouping: async () => {
    const { currentCaseId, selectedRuleVersion } = get();
    if (!currentCaseId || !selectedRuleVersion) {
      throw new Error('请先提交病历并选择规则版本');
    }
    set({ isExecuting: true, currentResult: null, resultRuleVersion: null });
    try {
      const response = await groupingApi.execute({ caseId: currentCaseId, ruleVersionId: selectedRuleVersion });
      const taskId = response.data.taskId;
      set({ currentTaskId: taskId });
      return taskId;
    } finally {
      set({ isExecuting: false });
    }
  },
  fetchResult: async (taskId) => {
    const response = await groupingApi.result(taskId);
    set({ currentResult: response.data, resultRuleVersion: response.data.ruleVersionId });
    return response.data;
  },
  fetchHistory: async () => {
    const response = await groupingApi.tasks({ page: 1, pageSize: 10 });
    set({ history: response.data.items });
  },
  resetWorkspace: () =>
    set({
      currentCaseId: null,
      currentCase: null,
      currentResult: null,
      currentTaskId: null,
      resultRuleVersion: null,
    }),
  submitForReview: async () => {
    const { currentTaskId } = get();
    if (!currentTaskId) throw new Error('无当前入组任务');
    await tasksApi.review(currentTaskId);
  },
}));
