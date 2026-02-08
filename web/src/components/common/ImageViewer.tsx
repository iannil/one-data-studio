import React, { useState, useCallback, useEffect } from 'react';
import { Modal, Space, Button, Spin, Tooltip, Typography, Slider } from 'antd';
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  RotateLeftOutlined,
  RotateRightOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  CloseOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface ImageViewerProps {
  visible: boolean;
  imageUrl: string;
  title?: string;
  onClose: () => void;
  showDownload?: boolean;
  showRotate?: boolean;
  showZoom?: boolean;
}

/**
 * 图片预览组件
 * Sprint 15: 多模态支持
 */
const ImageViewer: React.FC<ImageViewerProps> = ({
  visible,
  imageUrl,
  title,
  onClose,
  showDownload = true,
  showRotate = true,
  showZoom = true,
}) => {
  const [loading, setLoading] = useState(true);
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });

  // 重置状态
  useEffect(() => {
    if (visible) {
      setScale(1);
      setRotation(0);
      setLoading(true);
    }
  }, [visible, imageUrl]);

  // 处理图片加载完成
  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    setLoading(false);
    const img = e.target as HTMLImageElement;
    setImageDimensions({
      width: img.naturalWidth,
      height: img.naturalHeight,
    });
  };

  // 缩放
  const handleZoomIn = useCallback(() => {
    setScale((prev) => Math.min(prev + 0.25, 3));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale((prev) => Math.max(prev - 0.25, 0.25));
  }, []);

  const handleZoomChange = useCallback((value: number) => {
    setScale(value / 100);
  }, []);

  // 旋转
  const handleRotateLeft = useCallback(() => {
    setRotation((prev) => prev - 90);
  }, []);

  const handleRotateRight = useCallback(() => {
    setRotation((prev) => prev + 90);
  }, []);

  // 下载
  const handleDownload = useCallback(() => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = title || 'image';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [imageUrl, title]);

  // 全屏
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // 键盘快捷键
  useEffect(() => {
    if (!visible) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          if (isFullscreen) {
            setIsFullscreen(false);
          } else {
            onClose();
          }
          break;
        case '+':
        case '=':
          handleZoomIn();
          break;
        case '-':
          handleZoomOut();
          break;
        case 'ArrowLeft':
          handleRotateLeft();
          break;
        case 'ArrowRight':
          handleRotateRight();
          break;
        case 'f':
          toggleFullscreen();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [visible, isFullscreen, onClose, handleZoomIn, handleZoomOut, handleRotateLeft, handleRotateRight, toggleFullscreen]);

  // 工具栏
  const toolbar = (
    <Space size="middle" style={{ marginBottom: 16 }}>
      {showZoom && (
        <>
          <Tooltip title="缩小 (-)">
            <Button
              icon={<ZoomOutOutlined />}
              onClick={handleZoomOut}
              disabled={scale <= 0.25}
            />
          </Tooltip>
          <Slider
            min={25}
            max={300}
            value={scale * 100}
            onChange={handleZoomChange}
            style={{ width: 120 }}
            tooltip={{ formatter: (value) => `${value}%` }}
          />
          <Tooltip title="放大 (+)">
            <Button
              icon={<ZoomInOutlined />}
              onClick={handleZoomIn}
              disabled={scale >= 3}
            />
          </Tooltip>
        </>
      )}

      {showRotate && (
        <>
          <Tooltip title="逆时针旋转 (←)">
            <Button icon={<RotateLeftOutlined />} onClick={handleRotateLeft} />
          </Tooltip>
          <Tooltip title="顺时针旋转 (→)">
            <Button icon={<RotateRightOutlined />} onClick={handleRotateRight} />
          </Tooltip>
        </>
      )}

      <Tooltip title="全屏 (F)">
        <Button
          icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          onClick={toggleFullscreen}
        />
      </Tooltip>

      {showDownload && (
        <Tooltip title="下载">
          <Button icon={<DownloadOutlined />} onClick={handleDownload} />
        </Tooltip>
      )}
    </Space>
  );

  // 图片信息
  const imageInfo = imageDimensions.width > 0 && (
    <Text type="secondary" style={{ fontSize: 12 }}>
      {imageDimensions.width} × {imageDimensions.height} | 缩放: {Math.round(scale * 100)}%
    </Text>
  );

  return (
    <Modal
      open={visible}
      onCancel={onClose}
      footer={null}
      title={title || '图片预览'}
      width={isFullscreen ? '100vw' : '80vw'}
      style={isFullscreen ? { top: 0, paddingBottom: 0, margin: 0 } : { top: 20 }}
      styles={{
        content: {
          height: isFullscreen ? 'calc(100vh - 55px)' : 'auto',
          maxHeight: isFullscreen ? undefined : '80vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 16,
          backgroundColor: '#f0f0f0',
        }
      }}
      closeIcon={<CloseOutlined />}
      centered={!isFullscreen}
      destroyOnClose
    >
      {/* 工具栏 */}
      <div style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
        {toolbar}
      </div>

      {/* 图片容器 */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'auto',
          width: '100%',
          position: 'relative',
        }}
      >
        {loading && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <Spin size="large" />
            <div style={{ color: '#666' }}>加载中...</div>
          </div>
        )}
        <img
          src={imageUrl}
          alt={title || 'Preview'}
          onLoad={handleImageLoad}
          style={{
            maxWidth: '100%',
            maxHeight: isFullscreen ? 'calc(100vh - 150px)' : '60vh',
            transform: `scale(${scale}) rotate(${rotation}deg)`,
            transition: 'transform 0.2s ease',
            opacity: loading ? 0 : 1,
            cursor: 'grab',
            objectFit: 'contain',
          }}
          draggable={false}
        />
      </div>

      {/* 图片信息 */}
      <div style={{ marginTop: 8, textAlign: 'center' }}>
        {imageInfo}
      </div>
    </Modal>
  );
};

export default ImageViewer;
