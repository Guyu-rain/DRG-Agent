import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { RuleManagement } from '@/pages/RuleManagement/RuleManagement';

describe('RuleManagement', () => {
  it('loads rule versions', async () => {
    render(<RuleManagement />);
    expect(await screen.findByText('DRG 2.0 演示规则')).toBeInTheDocument();
  });

  it('shows active version tag', async () => {
    render(<RuleManagement />);
    expect(await screen.findByText('活跃')).toBeInTheDocument();
  });

  it('searches rule by code', async () => {
    render(<RuleManagement />);
    await userEvent.type(screen.getByPlaceholderText('按编码搜索规则'), 'A01.002');
    await userEvent.keyboard('{Enter}');
    expect((await screen.findAllByText(/MDCB/)).length).toBeGreaterThan(0);
  });
});
