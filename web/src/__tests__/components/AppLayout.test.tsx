import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppLayout } from '@/components/Layout/AppLayout';

async function renderLayout(initialEntry = '/') {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <div>任务中心页面</div> },
          { path: 'drg', element: <div>入组页面</div> },
          { path: 'docs', element: <div>文档工作台页面</div> },
        ],
      },
    ],
    {
      initialEntries: [initialEntry],
      future: { v7_relativeSplatPath: true },
    },
  );
  const view = render(
    <RouterProvider router={router} future={{ v7_startTransition: true }} />,
  );
  await act(async () => {
    await Promise.resolve();
  });
  return view;
}

describe('AppLayout', () => {
  it('renders the system shell', async () => {
    await renderLayout();
    // sidebar brand wordmark
    expect(screen.getByText('DRG-Agent')).toBeInTheDocument();
    // header breadcrumb root + nav items both render the labels — assert "all of"
    expect(screen.getAllByText('任务中心').length).toBeGreaterThan(0);
    expect(screen.getByText('DRG-AGENT')).toBeInTheDocument(); // breadcrumb root
  });

  it('renders routed child content', async () => {
    await renderLayout('/drg');
    expect(screen.getByText('入组页面')).toBeInTheDocument();
  });

  it('uses the full-width content area only for the document workspace', async () => {
    const { container, unmount } = await renderLayout('/docs');
    expect(container.querySelector('.app-content')).toHaveClass('app-content--workspace');

    unmount();
    const routedView = await renderLayout('/drg');
    expect(routedView.container.querySelector('.app-content')).not.toHaveClass(
      'app-content--workspace',
    );
  });

  it('can collapse the sider', async () => {
    await renderLayout();
    await userEvent.click(screen.getByRole('button', { name: /收起导航/ }));
    expect(screen.getByRole('button', { name: /展开导航/ })).toBeInTheDocument();
  });
});
