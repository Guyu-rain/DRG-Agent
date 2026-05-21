import { create } from 'zustand';
import { casesApi, groupingApi } from '@/services';
import type { CaseCreateRequest, PatientCase, ParsedCaseData } from '@/types/case';
import type { GroupingResultResponse, GroupingTaskSummary } from '@/types/grouping';

interface GroupingState {
  currentCaseId: string | null;
  currentCase: PatientCase | null;
  currentResult: GroupingResultResponse | null;
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
  fetchResult: (taskId: string) => Promise<void>;
  fetchHistory: () => Promise<void>;
  clearResult: () => void;
}

export const useGroupingStore = create<GroupingState>((set, get) => ({
  currentCaseId: null,
  currentCase: null,
  currentResult: null,
  selectedRuleVersion: null,
  inputMode: 'text',
  isExecuting: false,
  isParsing: false,
  history: [],
  setRuleVersion: (id) => {
    const state = get();
    set({
      selectedRuleVersion: id,
      currentResult: state.currentResult ? null : state.currentResult,
    });
  },
  setInputMode: (mode) => set({ inputMode: mode }),
  submitCase: async (data) => {
    const response = await casesApi.create(data);
    set({ currentCaseId: response.data.caseId, currentResult: null });
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
    set({ isExecuting: true, currentResult: null });
    try {
      const response = await groupingApi.execute({ caseId: currentCaseId, ruleVersionId: selectedRuleVersion });
      return response.data.taskId;
    } finally {
      set({ isExecuting: false });
    }
  },
  fetchResult: async (taskId) => {
    const response = await groupingApi.result(taskId);
    set({ currentResult: response.data });
  },
  fetchHistory: async () => {
    const response = await groupingApi.tasks({ page: 1, pageSize: 10 });
    set({ history: response.data.items });
  },
  clearResult: () => set({ currentResult: null }),
}));
