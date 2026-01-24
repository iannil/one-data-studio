/**
 * 图片懒加载组件
 * Sprint 8: 性能优化 - 图片资源优化
 *
 * 使用 Intersection Observer API 实现图片懒加载
 * 支持占位符、加载状态和错误处理
 */

import React, { useState, useRef, useEffect } from 'react';
import { ImageProps } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface ImageLazyProps extends Omit<ImageProps, 'onLoad' | 'onError'> {
  /** 图片 URL */
  src: string;
  /** 占位图片 URL（可选） */
  placeholder?: string;
  /** 错误时显示的图片 */
  fallback?: string;
  /** 加载中显示的内容 */
  loadingContent?: React.ReactNode;
  /** 加载完成回调 */
  onLoad?: (event: React.SyntheticEvent<HTMLImageElement>) => void;
  /** 加载失败回调 */
  onError?: (event: React.SyntheticEvent<HTMLImageElement>) => void;
  /** 容器类名 */
  containerClassName?: string;
  /** 图片类名 */
  imageClassName?: string;
  /** Intersection Observer 配置 */
  observerOptions?: IntersectionObserverInit;
  /** 是否启用懒加载（默认 true） */
  lazy?: boolean;
  /** 图片高度（用于预留空间） */
  height?: number | string;
  /** 图片宽度（用于预留空间） */
  width?: number | string;
  /** 对象适配方式 */
  objectFit?: 'fill' | 'contain' | 'cover' | 'none' | 'scale-down';
}

/**
 * 图片懒加载组件
 */
export const ImageLazy: React.FC<ImageLazyProps> = ({
  src,
  placeholder,
  fallback = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiPuimgTwvdGV4dD48L3N2Zz4=',
  loadingContent = <LoadingOutlined />,
  onLoad,
  onError,
  containerClassName,
  imageClassName,
  observerOptions,
  lazy = true,
  height,
  width,
  objectFit = 'cover',
  alt,
  style,
  ...restProps
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(!lazy);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    if (!lazy) {
      return;
    }

    const imgElement = imgRef.current;
    if (!imgElement) {
      return;
    }

    // 创建 Intersection Observer
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            // 进入视野后停止观察
            observerRef.current?.unobserve(imgElement);
          }
        });
      },
      {
        rootMargin: '50px', // 提前 50px 开始加载
        threshold: 0.01,
        ...observerOptions,
      }
    );

    observerRef.current.observe(imgElement);

    return () => {
      if (observerRef.current && imgElement) {
        observerRef.current.unobserve(imgElement);
      }
    };
  }, [lazy, observerOptions]);

  const handleLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
    setIsLoaded(true);
    setHasError(false);
    onLoad?.(event);
  };

  const handleError = (event: React.SyntheticEvent<HTMLImageElement>) => {
    setHasError(true);
    setIsLoaded(true);
    onError?.(event);
  };

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: '#f0f0f0',
    ...style,
    ...(height && { height }),
    ...(width && { width }),
  };

  const imageStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit,
    opacity: isLoaded ? 1 : 0,
    transition: 'opacity 0.3s ease-in-out',
  };

  const loadingStyle: React.CSSProperties = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: '#999',
    fontSize: 24,
  };

  const currentSrc = hasError ? fallback : isInView ? src : placeholder || fallback;

  return (
    <div className={containerClassName} style={containerStyle}>
      <img
        ref={imgRef}
        src={currentSrc}
        alt={alt}
        className={imageClassName}
        style={imageStyle}
        onLoad={handleLoad}
        onError={handleError}
        loading={lazy ? 'lazy' : 'eager'}
        {...restProps}
      />
      {!isLoaded && <div style={loadingStyle}>{loadingContent}</div>}
    </div>
  );
};

/**
 * 响应式图片组件（支持多种分辨率）
 */
interface ResponsiveImageProps extends Omit<ImageLazyProps, 'src'> {
  /** 不同分辨率的图片源 */
  srcSet: {
    /** 默认图片 */
    default: string;
    /** 1x 分辨率 */
    '1x'?: string;
    /** 2x 分辨率 */
    '2x'?: string;
    /** 3x 分辨率 */
    '3x'?: string;
  };
}

export const ResponsiveImage: React.FC<ResponsiveImageProps> = ({
  srcSet,
  ...restProps
}) => {
  const devicePixelRatio = typeof window !== 'undefined' ? window.devicePixelRatio : 1;

  // 根据设备像素比选择图片
  const getSrcForDPR = (): string => {
    if (devicePixelRatio >= 3 && srcSet['3x']) return srcSet['3x'];
    if (devicePixelRatio >= 2 && srcSet['2x']) return srcSet['2x'];
    if (devicePixelRatio >= 1 && srcSet['1x']) return srcSet['1x'];
    return srcSet.default;
  };

  return <ImageLazy src={getSrcForDPR()} {...restProps} />;
};

/**
 * 渐进式图片加载组件
 * 先加载低质量图片，再加载高质量图片
 */
interface ProgressiveImageProps extends Omit<ImageLazyProps, 'src' | 'placeholder'> {
  /** 低质量图片（占位） */
  preview: string;
  /** 高质量图片 */
  full: string;
}

export const ProgressiveImage: React.FC<ProgressiveImageProps> = ({
  preview,
  full,
  ...restProps
}) => {
  const [src, setSrc] = useState(preview);

  useEffect(() => {
    const img = new Image();
    img.src = full;

    const handleLoad = () => {
      setSrc(full);
    };

    img.addEventListener('load', handleLoad);
    return () => {
      img.removeEventListener('load', handleLoad);
    };
  }, [full]);

  return <ImageLazy src={src} {...restProps} />;
};

/**
 * 批量预加载图片 Hook
 */
export function useImagePreload(urls: string[], enabled = true) {
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!enabled || urls.length === 0) {
      return;
    }

    setLoading(true);

    const loadPromises = urls.map((url) => {
      return new Promise<void>((resolve, reject) => {
        // 已经加载过的直接跳过
        if (loadedImages.has(url)) {
          resolve();
          return;
        }

        const img = new Image();
        img.src = url;

        const onLoad = () => {
          setLoadedImages((prev) => new Set(prev).add(url));
          resolve();
        };

        const onError = () => {
          setErrors((prev) => new Set(prev).add(url));
          reject(new Error(`Failed to load image: ${url}`));
        };

        img.addEventListener('load', onLoad);
        img.addEventListener('error', onError);
      });
    });

    Promise.allSettled(loadPromises).finally(() => {
      setLoading(false);
    });
  }, [urls, enabled]);

  return {
    loadedImages,
    loading,
    errors,
    isAllLoaded: urls.length > 0 && loadedImages.size === urls.length,
  };
}

/**
 * 图片压缩工具（客户端压缩）
 */
export async function compressImage(
  file: File,
  options: {
    maxWidth?: number;
    maxHeight?: number;
    quality?: number;
    format?: 'image/jpeg' | 'image/png' | 'image/webp';
  } = {}
): Promise<Blob> {
  const {
    maxWidth = 1920,
    maxHeight = 1080,
    quality = 0.8,
    format = 'image/jpeg',
  } = options;

  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.src = e.target?.result as string;
    };

    img.onload = () => {
      const canvas = document.createElement('canvas');
      let width = img.width;
      let height = img.height;

      // 计算缩放比例
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        width *= ratio;
        height *= ratio;
      }

      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Failed to get canvas context'));
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to compress image'));
          }
        },
        format,
        quality
      );
    };

    img.onerror = () => {
      reject(new Error('Failed to load image'));
    };

    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };

    reader.readAsDataURL(file);
  });
}

export default ImageLazy;
