import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import Error from './Error';

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

describe('Error Component', () => {
  it('should render error message', () => {
    render(<Error title="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should render with default error title', () => {
    render(<Error />);
    expect(screen.getByText('出错了')).toBeInTheDocument();
  });

  it('should render with custom title', () => {
    render(<Error title="Custom Error" />);
    expect(screen.getByText('Custom Error')).toBeInTheDocument();
  });

  it('should render retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<Error onRetry={onRetry} />);
    expect(screen.getByRole('button', { name: /重试/i })).toBeInTheDocument();
  });

  it('should call onRetry when retry button is clicked', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();

    render(<Error onRetry={onRetry} />);

    const retryButton = screen.getByRole('button', { name: /重试/i });
    await user.click(retryButton);

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('should render home button', () => {
    render(<Error />);
    expect(screen.getByRole('button', { name: /返回首页/i })).toBeInTheDocument();
  });

  it('should render subtitle when provided', () => {
    render(<Error subTitle="Error details here" />);
    expect(screen.getByText('Error details here')).toBeInTheDocument();
  });

  it('should render default subtitle when not provided', () => {
    render(<Error />);
    expect(screen.getByText('页面加载失败，请稍后重试')).toBeInTheDocument();
  });
});
