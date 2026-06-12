import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DocumentSystem } from '@/pages/DocumentSystem/DocumentSystem';

describe('DocumentSystem', () => {
  it('renders document type entries', () => {
    render(
      <MemoryRouter>
        <DocumentSystem />
      </MemoryRouter>,
    );
    expect(screen.getByText('需求分析')).toBeInTheDocument();
    expect(screen.getByText('概要设计')).toBeInTheDocument();
  });

  it('opens generate dialog', async () => {
    render(
      <MemoryRouter>
        <DocumentSystem />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: /生成文档/ }));
    expect(screen.getByLabelText('文档标题')).toBeInTheDocument();
  });

  it('submits generate document task', async () => {
    render(
      <MemoryRouter>
        <DocumentSystem />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: /生成文档/ }));
    await screen.findByLabelText('文档标题');
    await userEvent.click(screen.getByRole('button', { name: '确认生成文档' }));
    expect(await screen.findByText(/文档生成完成/)).toBeInTheDocument();
  });
});
