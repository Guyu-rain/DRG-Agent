import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { server } from '@/mocks/server';
import { DocumentSystem } from '@/pages/DocumentSystem/DocumentSystem';
import { documentsApi } from '@/services';

const renderPage = () =>
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <DocumentSystem />
    </MemoryRouter>,
  );

afterEach(() => vi.restoreAllMocks());

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
    const { container } = renderPage();
    // 切到问答 Tab
    await userEvent.click(await screen.findByRole('tab', { name: /问答/ }));
    expect(container.querySelector('.doc-chat')).toHaveClass('doc-chat--qa');
    const input = await screen.findByPlaceholderText(/输入你的技术问题/);
    await userEvent.type(input, 'MDC 匹配怎么实现');
    await userEvent.click(screen.getByRole('button', { name: /发送/ }));

    // 助手回答的 Markdown 被渲染为真正的元素: 加粗 <strong> 与表格
    const strong = await screen.findByText('MDC 匹配', { selector: 'strong' }, { timeout: 3000 });
    expect(strong).toBeInTheDocument();
    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '文件' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'grouping_engine.py' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '展开思考过程' })).toBeInTheDocument();
  });

  it('keeps the reasoning summary collapsed when the user closes it while thinking', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('tab', { name: /问答/ }));
    const input = await screen.findByPlaceholderText(/输入你的技术问题/);
    await userEvent.type(input, '文档系统如何实现问答');
    await userEvent.click(screen.getByRole('button', { name: /发送/ }));

    const collapse = await screen.findByRole('button', { name: '收起思考过程' });
    expect(screen.getByText('正在建立流式连接并准备分析问题。')).toBeInTheDocument();
    await userEvent.click(collapse);
    expect(screen.queryByText('正在建立流式连接并准备分析问题。')).not.toBeInTheDocument();

    expect(await screen.findByText(/关于「文档系统如何实现问答」/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '展开思考过程' })).toBeInTheDocument();
    expect(screen.queryByText('已完成相关源码、接口和配置的检索与核对。')).not.toBeInTheDocument();
  });

  it('falls back to the compatible QA endpoint when streaming cannot start', async () => {
    server.use(
      http.post(
        '*/api/v1/documents/qa/conversations/:convId/messages/stream',
        () => HttpResponse.error(),
      ),
    );
    renderPage();
    await userEvent.click(await screen.findByRole('tab', { name: /问答/ }));
    const input = await screen.findByPlaceholderText(/输入你的技术问题/);
    await userEvent.type(input, 'MDC 匹配怎么实现');
    await userEvent.click(screen.getByRole('button', { name: /发送/ }));

    expect(await screen.findByText('MDC 匹配', { selector: 'strong' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '展开思考过程' }));
    expect(screen.getByText('兼容模式生成')).toBeInTheDocument();
  });

  it('does not submit a duplicate fallback request after streaming has started', async () => {
    const streamSpy = vi
      .spyOn(documentsApi, 'streamQaMessage')
      .mockImplementation(async (_convId, _instruction, onEvent) => {
        onEvent({
          type: 'reasoning',
          summary: {
            status: 'thinking',
            steps: [
              {
                id: 'inspect',
                title: '查阅项目实现',
                detail: '正在检索相关源码。',
                status: 'running',
              },
            ],
          },
        });
        throw new Error('stream interrupted');
      });
    const fallbackSpy = vi.spyOn(documentsApi, 'sendQaMessage');
    renderPage();
    await userEvent.click(await screen.findByRole('tab', { name: /问答/ }));
    const input = await screen.findByPlaceholderText(/输入你的技术问题/);
    await userEvent.type(input, '测试中断处理');
    await userEvent.click(screen.getByRole('button', { name: /发送/ }));

    expect(await screen.findByText('回答生成中断，请稍后重试。')).toBeInTheDocument();
    expect(fallbackSpy).not.toHaveBeenCalled();
    expect(streamSpy).toHaveBeenCalledOnce();
  });
});
