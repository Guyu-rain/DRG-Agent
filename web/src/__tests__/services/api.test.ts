import { describe, expect, it } from 'vitest';
import { apiClient } from '@/services/api';

describe('API client', () => {
  it('does not impose a fixed request timeout on long LLM tasks', () => {
    expect(apiClient.defaults.timeout).toBe(0);
  });
});
