import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { DRGGrouping } from '@/pages/DRGGrouping/DRGGrouping';
import { useGroupingStore } from '@/stores/groupingStore';

describe('DRGGrouping', () => {
  beforeEach(() => {
    useGroupingStore.setState({
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
    });
  });

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

  it('shows review and result download actions after grouping', async () => {
    render(<DRGGrouping />);
    await screen.findByText(/DRG 2.0 演示规则/);
    await userEvent.click(screen.getByRole('button', { name: /开始入组/ }));
    await waitFor(
      () => {
        expect(screen.getByRole('button', { name: /保存结果/ })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /提交复核/ })).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
    expect(screen.queryByText('生成文档')).not.toBeInTheDocument();
    expect(screen.queryByText('生成测试')).not.toBeInTheDocument();
  });

  it('imports a generated testcase into text mode', async () => {
    render(<DRGGrouping />);
    await screen.findByText(/DRG 2.0 演示规则/);
    await userEvent.click(screen.getByRole('button', { name: /导入测试用例/ }));
    await userEvent.click(await screen.findByText('主诊断与手术正常命中 BB11'));
    await userEvent.click(screen.getByRole('button', { name: '导入到文本模式' }));

    expect(screen.getByDisplayValue(/测试用例：主诊断与手术正常命中 BB11/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/主诊断：A01.002\+G01\*/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('解析结果')).not.toBeInTheDocument());
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('does not mark a result stale when the same rule version was used', async () => {
    render(<DRGGrouping />);
    await screen.findByText(/DRG 2.0 演示规则/);
    await userEvent.click(screen.getByRole('button', { name: /开始入组/ }));
    await screen.findByText('最终 DRG', {}, { timeout: 3000 });

    expect(screen.queryByText('规则版本已变化，当前结果可能已过期，请重新入组。')).not.toBeInTheDocument();
  });
});
