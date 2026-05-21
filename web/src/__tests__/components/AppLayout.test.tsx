import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppLayout } from '@/components/Layout/AppLayout';

function renderLayout(initialEntry = '/') {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <div>任务中心页面</div> },
          { path: 'drg', element: <div>入组页面</div> },
        ],
      },
    ],
    { initialEntries: [initialEntry] },
  );
  render(<RouterProvider router={router} />);
}

describe('AppLayout', () => {
  it('renders the system shell', () => {
    renderLayout();
    expect(screen.getByText('DRG-Agent')).toBeInTheDocument();
    expect(screen.getByText('医保 DRG 入组智能体系统')).toBeInTheDocument();
  });

  it('renders routed child content', () => {
    renderLayout('/drg');
    expect(screen.getByText('入组页面')).toBeInTheDocument();
  });

  it('can collapse the sider', async () => {
    renderLayout();
    await userEvent.click(screen.getByRole('button', { name: /收起导航/ }));
    expect(screen.getByRole('button', { name: /展开导航/ })).toBeInTheDocument();
  });
});
