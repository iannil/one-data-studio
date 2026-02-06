/**
 * ImageLazy 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@/test/testUtils';
import '@testing-library/jest-dom';
import { ImageLazy, ResponsiveImage, ProgressiveImage, useImagePreload, compressImage } from './ImageLazy';

// Mock IntersectionObserver
const mockIntersectionObserver = vi.fn();
const mockObserve = vi.fn();
const mockUnobserve = vi.fn();
const mockDisconnect = vi.fn();

beforeEach(() => {
  mockIntersectionObserver.mockImplementation((callback) => {
    return {
      observe: mockObserve,
      unobserve: mockUnobserve,
      disconnect: mockDisconnect,
    };
  });

  vi.stubGlobal('IntersectionObserver', mockIntersectionObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('ImageLazy Component', () => {
  it('should render with src', () => {
    render(<ImageLazy src="https://example.com/image.jpg" alt="Test image" />);

    const img = document.querySelector('img');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('alt', 'Test image');
  });

  it('should show loading content initially', () => {
    render(<ImageLazy src="https://example.com/image.jpg" />);

    // Loading indicator should be present before image loads
    const img = document.querySelector('img');
    expect(img).toBeInTheDocument();
    expect((img as HTMLImageElement).style.opacity).toBe('0');
  });

  it('should handle image load event', async () => {
    const onLoad = vi.fn();
    render(
      <ImageLazy
        src="https://example.com/image.jpg"
        onLoad={onLoad}
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    fireEvent.load(img!);

    expect(onLoad).toHaveBeenCalled();
  });

  it('should handle image error', async () => {
    const onError = vi.fn();
    render(
      <ImageLazy
        src="https://example.com/broken.jpg"
        onError={onError}
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    fireEvent.error(img!);

    expect(onError).toHaveBeenCalled();
  });

  it('should use fallback image on error', () => {
    const fallbackSrc = 'https://example.com/fallback.jpg';
    render(
      <ImageLazy
        src="https://example.com/broken.jpg"
        fallback={fallbackSrc}
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    fireEvent.error(img!);

    expect(img).toHaveAttribute('src', fallbackSrc);
  });

  it('should apply custom dimensions', () => {
    const { container } = render(
      <ImageLazy
        src="https://example.com/image.jpg"
        width={200}
        height={150}
      />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toBeInTheDocument();
    expect(wrapper.style.width).toBe('200px');
    expect(wrapper.style.height).toBe('150px');
  });

  it('should apply custom objectFit', () => {
    render(
      <ImageLazy
        src="https://example.com/image.jpg"
        objectFit="contain"
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    expect(img).toBeInTheDocument();
    expect((img as HTMLImageElement).style.objectFit).toBe('contain');
  });

  it('should apply custom className', () => {
    const { container } = render(
      <ImageLazy
        src="https://example.com/image.jpg"
        containerClassName="custom-container"
        imageClassName="custom-image"
      />
    );

    expect(container.querySelector('.custom-container')).toBeInTheDocument();
  });

  it('should not lazy load when lazy is false', () => {
    render(
      <ImageLazy
        src="https://example.com/image.jpg"
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    expect(img).toHaveAttribute('loading', 'eager');
  });

  it('should use lazy loading by default', () => {
    render(<ImageLazy src="https://example.com/image.jpg" />);

    const img = document.querySelector('img');
    expect(img).toHaveAttribute('loading', 'lazy');
  });

  it('should set up IntersectionObserver when lazy is true', () => {
    render(<ImageLazy src="https://example.com/image.jpg" lazy={true} />);

    expect(mockObserve).toHaveBeenCalled();
  });

  it('should clean up observer on unmount', () => {
    const { unmount } = render(<ImageLazy src="https://example.com/image.jpg" lazy={true} />);

    unmount();

    expect(mockUnobserve).toHaveBeenCalled();
  });
});

describe('ResponsiveImage Component', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'devicePixelRatio', {
      value: 2,
      writable: true,
    });
  });

  it('should select 2x image for devicePixelRatio of 2', () => {
    render(
      <ResponsiveImage
        responsiveSrcSet={{
          default: 'image.jpg',
          '1x': 'image-1x.jpg',
          '2x': 'image-2x.jpg',
          '3x': 'image-3x.jpg',
        }}
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    expect(img).toHaveAttribute('src', 'image-2x.jpg');
  });

  it('should fall back to default when resolution not available', () => {
    Object.defineProperty(window, 'devicePixelRatio', { value: 1, writable: true });

    render(
      <ResponsiveImage
        responsiveSrcSet={{
          default: 'image.jpg',
        }}
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    expect(img).toHaveAttribute('src', 'image.jpg');
  });
});

describe('ProgressiveImage Component', () => {
  it('should start with preview image', () => {
    render(
      <ProgressiveImage
        previewSrc="preview.jpg"
        full="full.jpg"
        lazy={false}
      />
    );

    const img = document.querySelector('img');
    expect(img).toHaveAttribute('src', 'preview.jpg');
  });
});

describe('useImagePreload Hook', () => {
  it('should initialize with empty loaded images', async () => {
    const { result } = await import('@testing-library/react').then(({ renderHook }) =>
      renderHook(() => useImagePreload([]))
    );

    expect(result.current.loadedImages.size).toBe(0);
    expect(result.current.loading).toBe(false);
  });

  it('should not load when enabled is false', async () => {
    const { result } = await import('@testing-library/react').then(({ renderHook }) =>
      renderHook(() => useImagePreload(['image.jpg'], false))
    );

    expect(result.current.loading).toBe(false);
  });
});

describe('compressImage Function', () => {
  it('should be a function', () => {
    expect(typeof compressImage).toBe('function');
  });

  it('should accept options parameter', async () => {
    const mockFile = new File([''], 'test.jpg', { type: 'image/jpeg' });

    // The function should not throw when called with valid options
    const promise = compressImage(mockFile, {
      maxWidth: 800,
      maxHeight: 600,
      quality: 0.7,
      format: 'image/jpeg',
    });

    expect(promise).toBeInstanceOf(Promise);
  });
});
