import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DocumentSystem } from '@/pages/DocumentSystem/DocumentSystem';

const renderPage = () =>
  render(
    <MemoryRouter>
      <DocumentSystem />
    </MemoryRouter>,
  );

describe('DocumentSystem (对话工作台)', () => {
  it('renders the chat workbench with quick prompts', async () => {
    renderPage();
    expect(await screen.findByText('虚拟文档系统 · 对话式生成')).toBeInTheDocument();
    expect(screen.getByText(/起草一份 DRG-Agent 的需求分析文档/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /新建文档对话/ })).toBeInTheDocument();
  });

  it('sends an instruction and renders the generated document preview', async () => {
    renderPage();
    const input = await screen.findByPlaceholderText(/描述你想要的文档/);
    await userEvent.type(input, '帮我写一份需求文档');
    await userEvent.click(screen.getByRole('button', { name: /发送/ }));

    // 用户气泡 + 助手回复出现
    expect(await screen.findByText('帮我写一份需求文档')).toBeInTheDocument();
    expect(await screen.findByText(/已根据你的要求更新/)).toBeInTheDocument();
    // 右侧预览出现提交按钮 (AntD 会在双 CJK 字符间插入空格)
    expect(
      await screen.findByRole('button', { name: /提\s*交/ }, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  it('renders QA answer markdown (bold + table) properly', async () => {
    renderPage();
    // 切到问答 Tab
    await userEvent.click(await screen.findByRole('tab', { name: /问答/ }));
    const input = await screen.findByPlaceholderText(/输入你的技术问题/);
    await userEvent.type(input, 'MDC 匹配怎么实现');
    await userEvent.click(screen.getByRole('button', { name: /发送/ }));

    // 助手回答的 Markdown 被渲染为真正的元素: 加粗 <strong> 与表格
    const strong = await screen.findByText('MDC 匹配', { selector: 'strong' }, { timeout: 3000 });
    expect(strong).toBeInTheDocument();
    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '文件' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'grouping_engine.py' })).toBeInTheDocument();
  });
});
