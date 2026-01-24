/**
 * Loading 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Loading } from './Loading';

describe('Loading Component', () => {
  it('should render with default props', () => {
    render(<Loading />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should render custom tip text', () => {
    render(<Loading tip="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('should render with small size', () => {
    const { container } = render(<Loading size="small" />);
    const spinner = container.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('should render with large size', () => {
    const { container } = render(<Loading size="large" />);
    const spinner = container.querySelector('.ant-spin-lg');
    expect(spinner).toBeInTheDocument();
  });

  it('should render inline spinning', () => {
    const { container } = render(<Loading inline />);
    expect(container.querySelector('.ant-spin-inline')).toBeInTheDocument();
  });

  it('should render fullscreen with overlay', () => {
    render(<Loading fullscreen />);
    const overlay = screen.getByText('Loading').closest('.fullscreen-loading');
    expect(overlay).toHaveClass('fullscreen-loading');
  });
});
