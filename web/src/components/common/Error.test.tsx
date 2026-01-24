/**
 * Error 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorDisplay } from './Error';

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

describe('ErrorDisplay Component', () => {
  it('should render error message', () => {
    render(<ErrorDisplay message="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should render with default error title', () => {
    render(<ErrorDisplay message="Error occurred" />);
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('should render with custom title', () => {
    render(<ErrorDisplay title="Custom Error" message="Error occurred" />);
    expect(screen.getByText('Custom Error')).toBeInTheDocument();
  });

  it('should render retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<ErrorDisplay message="Error" onRetry={onRetry} />);
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('should call onRetry when retry button is clicked', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();

    render(<ErrorDisplay message="Error" onRetry={onRetry} />);

    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('should render error code when provided', () => {
    render(<ErrorDisplay message="Error" code={500} />);
    expect(screen.getByText('500')).toBeInTheDocument();
  });

  it('should render stack trace in dev mode', () => {
    const originalEnv = import.meta.env.MODE;
    vi.stubEnv('MODE', 'development');

    render(
      <ErrorDisplay
        message="Error"
        error={new Error('Test error')}
        showDetails
      />
    );
    expect(screen.getByText(/Test error/)).toBeInTheDocument();

    vi.unstubAllEnvs();
  });

  it('should render home button when showHome is true', () => {
    render(<ErrorDisplay message="Error" showHome />);
    expect(screen.getByRole('button', { name: /home/i })).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <ErrorDisplay message="Error" className="custom-error" />
    );
    expect(container.firstChild).toHaveClass('custom-error');
  });

  it('should render different error types', () => {
    const { rerender } = render(<ErrorDisplay type="404" message="Not found" />);
    expect(screen.getByText('404')).toBeInTheDocument();

    rerender(<ErrorDisplay type="500" message="Server error" />);
    expect(screen.getByText('500')).toBeInTheDocument();

    rerender(<ErrorDisplay type="403" message="Forbidden" />);
    expect(screen.getByText('403')).toBeInTheDocument();
  });
});
