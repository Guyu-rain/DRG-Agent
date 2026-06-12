import { afterEach, describe, expect, it, vi } from 'vitest';
import { downloadJson } from '@/utils/download';

describe('downloadJson', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates and downloads a formatted JSON blob', () => {
    const anchor = document.createElement('a');
    const click = vi.spyOn(anchor, 'click').mockImplementation(() => undefined);
    const createObjectURL = vi.fn((blob: Blob) => {
      void blob;
      return 'blob:drg-result';
    });
    const revokeObjectURL = vi.fn((url: string) => {
      void url;
    });

    vi.spyOn(document, 'createElement').mockReturnValueOnce(anchor);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });

    downloadJson([{ result: { drg: 'BL15' } }], 'drg_result_TASK-001.json');

    expect(anchor.download).toBe('drg_result_TASK-001.json');
    expect(anchor.href).toBe('blob:drg-result');
    expect(click).toHaveBeenCalledOnce();
    expect(createObjectURL).toHaveBeenCalledOnce();
    const blob = createObjectURL.mock.calls[0]?.[0];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob?.type).toBe('application/json;charset=utf-8');
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:drg-result');
  });
});
