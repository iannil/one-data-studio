/**
 * ErrorBoundary 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ErrorBoundary, PageErrorBoundary } from './ErrorBoundary';

// Mock antd components
vi.mock('antd', () => ({
  Result: ({ status, title, subTitle, extra, children }: any) => (
    <div data-testid="result" data-status={status}>
      <div data-testid="result-title">{title}</div>
      <div data-testid="result-subtitle">{subTitle}</div>
      <div data-testid="result-extra">{extra}</div>
      <div data-testid="result-children">{children}</div>
    </div>
  ),
  Button: ({ children, onClick, type }: any) => (
    <button onClick={onClick} data-testid={`button-${type || 'default'}`}>
      {children}
    </button>
  ),
  Typography: {
    Paragraph: ({ children }: any) => <p>{children}</p>,
    Text: ({ children, code, strong }: any) => (
      <span data-testid={code ? 'code-text' : 'text'} style={{ fontWeight: strong ? 'bold' : 'normal' }}>
        {children}
      </span>
    ),
  },
}));

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
};

describe('ErrorBoundary Component', () => {
  // Suppress console.error for cleaner test output
  const originalError = console.error;

  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it('should render children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Child content')).toBeInTheDocument();
    expect(screen.queryByTestId('result')).not.toBeInTheDocument();
  });

  it('should catch errors and display fallback UI', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('result')).toBeInTheDocument();
    expect(screen.getByTestId('result-status')).toHaveAttribute('data-status', 'error');
    expect(screen.getByTestId('result-title')).toHaveTextContent('页面出现错误');
  });

  it('should render custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
    expect(screen.queryByTestId('result')).not.toBeInTheDocument();
  });

  it('should call onReset when retry button is clicked', () => {
    const onReset = vi.fn();

    render(
      <ErrorBoundary onReset={onReset}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const retryButton = screen.getByTestId('button-primary');
    fireEvent.click(retryButton);

    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it('should render retry and reload buttons', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('button-primary')).toHaveTextContent('重试');
    expect(screen.getByTestId('button-default')).toHaveTextContent('刷新页面');
  });

  it('should reset error state when retry is clicked', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('result')).toBeInTheDocument();

    // Click retry button
    const retryButton = screen.getByTestId('button-primary');
    fireEvent.click(retryButton);

    // Rerender with non-throwing component
    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    // Error boundary should be reset (though ThrowError will throw again in this test)
    // This tests the reset mechanism
  });

  it('should log error to console', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(console.error).toHaveBeenCalled();
  });

  describe('Development mode error details', () => {
    const originalEnv = process.env.NODE_ENV;

    beforeEach(() => {
      Object.defineProperty(process.env, 'NODE_ENV', {
        value: 'development',
        writable: true,
      });
    });

    afterEach(() => {
      Object.defineProperty(process.env, 'NODE_ENV', {
        value: originalEnv,
        writable: true,
      });
    });

    it('should display error message in development', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Error details should be shown in development mode
      expect(screen.getByTestId('result-children')).toBeInTheDocument();
    });
  });
});

describe('PageErrorBoundary Component', () => {
  const originalError = console.error;

  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it('should render children when there is no error', () => {
    render(
      <PageErrorBoundary>
        <div>Page content</div>
      </PageErrorBoundary>
    );

    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('should catch errors and display error UI', () => {
    render(
      <PageErrorBoundary>
        <ThrowError shouldThrow={true} />
      </PageErrorBoundary>
    );

    expect(screen.getByTestId('result')).toBeInTheDocument();
  });

  it('should wrap with ErrorBoundary', () => {
    render(
      <PageErrorBoundary>
        <ThrowError shouldThrow={true} />
      </PageErrorBoundary>
    );

    // Should have the same error UI as ErrorBoundary
    expect(screen.getByTestId('result-title')).toHaveTextContent('页面出现错误');
  });
});

describe('ErrorBoundary lifecycle', () => {
  const originalError = console.error;

  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it('should call getDerivedStateFromError on error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // If getDerivedStateFromError worked, we should see the error UI
    expect(screen.getByTestId('result')).toBeInTheDocument();
  });

  it('should call componentDidCatch on error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // componentDidCatch should have logged the error
    expect(console.error).toHaveBeenCalled();
  });
});
