import { describe, expect, it } from 'vitest';
import { useGroupingStore } from '@/stores/groupingStore';
import { demoCaseText } from '@/utils/constants';

describe('groupingStore', () => {
  it('sets rule version', () => {
    useGroupingStore.getState().setRuleVersion('RV-TEST');
    expect(useGroupingStore.getState().selectedRuleVersion).toBe('RV-TEST');
  });

  it('submits and parses a case', async () => {
    const caseId = await useGroupingStore.getState().submitCase({ rawText: demoCaseText, sourceType: 'text' });
    await useGroupingStore.getState().parseCase(caseId);
    expect(useGroupingStore.getState().currentCase?.primaryDiagnosis?.code).toBe('A01.002+G01*');
  });
});
