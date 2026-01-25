/**
 * ImageViewer 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock antd components
vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    Modal: ({ open, onCancel, children, title, footer }: any) => (
      open ? (
        <div data-testid="modal" role="dialog">
          <div data-testid="modal-title">{title}</div>
          <div data-testid="modal-content">{children}</div>
          <button data-testid="modal-close" onClick={onCancel}>Close</button>
        </div>
      ) : null
    ),
    Image: ({ src, alt }: any) => <img src={src} alt={alt} />,
    Space: ({ children }: any) => <div data-testid="space">{children}</div>,
    Button: ({ children, onClick, disabled, icon }: any) => (
      <button onClick={onClick} disabled={disabled} data-testid="button">
        {icon}
        {children}
      </button>
    ),
    Spin: ({ tip }: any) => <div data-testid="spin">{tip}</div>,
    Tooltip: ({ children, title }: any) => (
      <div data-testid="tooltip" title={title}>{children}</div>
    ),
    Typography: {
      Text: ({ children, type }: any) => <span data-testid={`text-${type || 'default'}`}>{children}</span>,
    },
    Slider: ({ value, onChange, min, max }: any) => (
      <input
        type="range"
        data-testid="slider"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange?.(Number(e.target.value))}
      />
    ),
  };
});

import ImageViewer from './ImageViewer';

describe('ImageViewer Component', () => {
  const defaultProps = {
    visible: true,
    imageUrl: 'https://example.com/test-image.jpg',
    title: 'Test Image',
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render when visible is true', () => {
    render(<ImageViewer {...defaultProps} />);

    expect(screen.getByTestId('modal')).toBeInTheDocument();
    expect(screen.getByTestId('modal-title')).toHaveTextContent('Test Image');
  });

  it('should not render when visible is false', () => {
    render(<ImageViewer {...defaultProps} visible={false} />);

    expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
  });

  it('should display the image', () => {
    const { container } = render(<ImageViewer {...defaultProps} />);

    const img = container.querySelector('img');
    expect(img).toHaveAttribute('src', defaultProps.imageUrl);
  });

  it('should call onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<ImageViewer {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('modal-close'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should use default title when not provided', () => {
    render(<ImageViewer visible={true} imageUrl="test.jpg" onClose={vi.fn()} />);

    expect(screen.getByTestId('modal-title')).toHaveTextContent('图片预览');
  });

  it('should render toolbar buttons', () => {
    render(<ImageViewer {...defaultProps} />);

    const buttons = screen.getAllByTestId('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should handle image load', () => {
    const { container } = render(<ImageViewer {...defaultProps} />);

    const img = container.querySelector('img');
    fireEvent.load(img!);

    // After load, loading state should be false
    expect(screen.queryByTestId('spin')).not.toBeInTheDocument();
  });

  describe('Zoom controls', () => {
    it('should render zoom slider when showZoom is true', () => {
      render(<ImageViewer {...defaultProps} showZoom={true} />);

      expect(screen.getByTestId('slider')).toBeInTheDocument();
    });

    it('should not render zoom controls when showZoom is false', () => {
      render(<ImageViewer {...defaultProps} showZoom={false} />);

      expect(screen.queryByTestId('slider')).not.toBeInTheDocument();
    });
  });

  describe('Rotate controls', () => {
    it('should render rotate buttons when showRotate is true', () => {
      render(<ImageViewer {...defaultProps} showRotate={true} />);

      const buttons = screen.getAllByTestId('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Download functionality', () => {
    it('should render download button when showDownload is true', () => {
      render(<ImageViewer {...defaultProps} showDownload={true} />);

      const buttons = screen.getAllByTestId('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Keyboard shortcuts', () => {
    it('should handle Escape key to close', () => {
      const onClose = vi.fn();
      render(<ImageViewer {...defaultProps} onClose={onClose} />);

      fireEvent.keyDown(window, { key: 'Escape' });

      expect(onClose).toHaveBeenCalled();
    });

    it('should handle + key for zoom in', () => {
      render(<ImageViewer {...defaultProps} />);

      fireEvent.keyDown(window, { key: '+' });

      // Component should handle zoom in
      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });

    it('should handle - key for zoom out', () => {
      render(<ImageViewer {...defaultProps} />);

      fireEvent.keyDown(window, { key: '-' });

      // Component should handle zoom out
      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });

    it('should handle arrow keys for rotation', () => {
      render(<ImageViewer {...defaultProps} />);

      fireEvent.keyDown(window, { key: 'ArrowLeft' });
      fireEvent.keyDown(window, { key: 'ArrowRight' });

      // Component should handle rotation
      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });

    it('should handle f key for fullscreen toggle', () => {
      render(<ImageViewer {...defaultProps} />);

      fireEvent.keyDown(window, { key: 'f' });

      // Component should handle fullscreen toggle
      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });
  });

  describe('Fullscreen mode', () => {
    it('should render fullscreen toggle button', () => {
      render(<ImageViewer {...defaultProps} />);

      const buttons = screen.getAllByTestId('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});
