import { describe, expect, it } from 'vitest';
import { useTestcaseStore } from '@/stores/testcaseStore';

describe('testcaseStore', () => {
  it('fetches testcase list', async () => {
    await useTestcaseStore.getState().fetchTestcases();
    expect(useTestcaseStore.getState().testcases.length).toBeGreaterThan(0);
  });

  it('updates scenario filter', () => {
    useTestcaseStore.getState().setFilter({ scenarioType: 'normal' });
    expect(useTestcaseStore.getState().filter.scenarioType).toBe('normal');
  });
});
