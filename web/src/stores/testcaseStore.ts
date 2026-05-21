import { create } from 'zustand';
import { testcasesApi } from '@/services';
import type { ScenarioType, TestCaseGenerateRequest, TestCaseItem } from '@/types/testcase';

interface TestcaseState {
  testcases: TestCaseItem[];
  isGenerating: boolean;
  filter: {
    scenarioType?: ScenarioType;
  };
  setFilter: (filter: Partial<TestcaseState['filter']>) => void;
  fetchTestcases: () => Promise<void>;
  generateTestcases: (data: TestCaseGenerateRequest) => Promise<string>;
}

export const useTestcaseStore = create<TestcaseState>((set, get) => ({
  testcases: [],
  isGenerating: false,
  filter: {},
  setFilter: (filter) => set({ filter: { ...get().filter, ...filter } }),
  fetchTestcases: async () => {
    const response = await testcasesApi.list({ page: 1, pageSize: 20, ...get().filter });
    set({ testcases: response.data.items });
  },
  generateTestcases: async (data) => {
    set({ isGenerating: true });
    try {
      const response = await testcasesApi.generate(data);
      await get().fetchTestcases();
      return response.data.testTaskId;
    } finally {
      set({ isGenerating: false });
    }
  },
}));
