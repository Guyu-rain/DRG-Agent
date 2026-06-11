import { create } from 'zustand';
import { casesApi, groupingApi, documentsApi, testcasesApi, tasksApi } from '@/services';
import type { CaseCreateRequest, PatientCase, ParsedCaseData } from '@/types/case';
import type { GroupingResultResponse, GroupingTaskSummary } from '@/types/grouping';
import type { DocumentGenerateRequest } from '@/types/document';

interface GroupingState {
  currentCaseId: string | null;
  currentCase: PatientCase | null;
  currentResult: GroupingResultResponse | null;
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
  fetchResult: (taskId: string) => Promise<void>;
  fetchHistory: () => Promise<void>;
  clearResult: () => void;
  submitForReview: () => Promise<void>;
  generateDocument: (docType: DocumentGenerateRequest['docType']) => Promise<string>;
  generateTestcases: () => Promise<string>;
}

export const useGroupingStore = create<GroupingState>((set, get) => ({
  currentCaseId: null,
  currentCase: null,
  currentResult: null,
  currentTaskId: null,
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
      const taskId = response.data.taskId;
      set({ currentTaskId: taskId });
      return taskId;
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
  clearResult: () => set({ currentResult: null, currentTaskId: null }),
  submitForReview: async () => {
    const { currentTaskId } = get();
    if (!currentTaskId) throw new Error('无当前入组任务');
    await tasksApi.review(currentTaskId);
  },
  generateDocument: async (docType) => {
    const { currentTaskId, currentResult, currentCase } = get();
    if (!currentTaskId || !currentResult?.result) throw new Error('请先完成入组');
    const res = await documentsApi.generate({
      docType,
      title: `DRG入组报告 - ${currentResult.result.drg?.code ?? ''} ${currentResult.result.drg?.name ?? ''}`,
      context: {
        taskId: currentTaskId,
        mdc: currentResult.result.mdc,
        adrg: currentResult.result.adrg,
        drg: currentResult.result.drg,
        complication: currentResult.result.complication,
        explanation: currentResult.result.explanation,
        caseId: currentResult.caseId,
        primaryDiagnosis: currentCase?.primaryDiagnosis ?? null,
      },
    });
    return res.data.docTaskId;
  },
  generateTestcases: async () => {
    const { selectedRuleVersion, currentCaseId } = get();
    if (!selectedRuleVersion) throw new Error('请先选择规则版本');
    const res = await testcasesApi.generate({
      ruleVersionId: selectedRuleVersion,
      scenarioTypes: ['normal', 'boundary', 'abnormal'],
      scope: { includeAllRules: false },
      sampleCaseIds: currentCaseId ? [currentCaseId] : [],
      maxCount: 10,
    });
    return res.data.testTaskId;
  },
}));
