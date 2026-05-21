import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmptyState } from '@/components/Common/EmptyState';

describe('EmptyState', () => {
  it('renders a friendly empty description', () => {
    render(<EmptyState description="没有记录" />);
    expect(screen.getByText('没有记录')).toBeInTheDocument();
  });
});
