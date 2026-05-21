import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { DRGGrouping } from '@/pages/DRGGrouping/DRGGrouping';

describe('DRGGrouping', () => {
  it('renders text mode by default', async () => {
    render(<DRGGrouping />);
    expect(screen.getByText('文本模式')).toBeInTheDocument();
    expect(screen.getByDisplayValue(/A01.002/)).toBeInTheDocument();
    expect(await screen.findByText(/DRG 2.0 演示规则/)).toBeInTheDocument();
  });

  it('switches to structured mode', async () => {
    render(<DRGGrouping />);
    await userEvent.click(screen.getByText('结构化模式'));
    expect(screen.getByPlaceholderText('伤寒性脑膜炎')).toBeInTheDocument();
  });

  it('executes grouping and shows successful result', async () => {
    render(<DRGGrouping />);
    await screen.findByText(/DRG 2.0 演示规则/);
    await userEvent.click(screen.getByRole('button', { name: /开始入组/ }));
    expect(await screen.findByText('最终 DRG', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(await screen.findByText('BB11')).toBeInTheDocument();
  });

  it('shows parsed fields after execution', async () => {
    render(<DRGGrouping />);
    await screen.findByText(/DRG 2.0 演示规则/);
    await userEvent.click(screen.getByRole('button', { name: /开始入组/ }));
    expect(await screen.findByText('解析结果', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getAllByText(/急性呼吸衰竭/).length).toBeGreaterThan(0);
  });

  it('keeps action buttons after result', async () => {
    render(<DRGGrouping />);
    await screen.findByText(/DRG 2.0 演示规则/);
    await userEvent.click(screen.getByRole('button', { name: /开始入组/ }));
    await waitFor(() => expect(screen.getByText('生成文档')).toBeInTheDocument(), { timeout: 3000 });
    expect(screen.getByText('生成测试')).toBeInTheDocument();
  });
});
