import React, { useState, useCallback } from 'react';
import { Upload, Button, message, Card, Space, Typography, Alert } from 'antd';
import {
  InboxOutlined,
  FileImageOutlined,
  DeleteOutlined,
  EyeOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps, RcFile } from 'antd/es/upload';
import ImageViewer from '@/components/common/ImageViewer';
import { logError } from '@/services/logger';

const { Dragger } = Upload;
const { Text } = Typography;

interface ImageUploadProps {
  onUploadComplete?: (files: UploadedImage[]) => void;
  maxFiles?: number;
  maxFileSize?: number; // MB
  acceptedFormats?: string[];
  enableOCR?: boolean;
  workflowId?: string;
  documentId?: string;
}

interface UploadedImage {
  id: string;
  filename: string;
  url: string;
  thumbnailUrl?: string;
  metadata: {
    width: number;
    height: number;
    format: string;
    sizeBytes: number;
  };
  ocrText?: string;
  embedding?: number[];
}

const DEFAULT_ACCEPTED_FORMATS = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const DEFAULT_MAX_FILE_SIZE = 20; // MB
const DEFAULT_MAX_FILES = 10;

/**
 * 图片上传组件
 * Sprint 15: 多模态支持
 */
const ImageUpload: React.FC<ImageUploadProps> = ({
  onUploadComplete,
  maxFiles = DEFAULT_MAX_FILES,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  acceptedFormats = DEFAULT_ACCEPTED_FORMATS,
  enableOCR = true,
  workflowId,
  documentId,
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  // 验证文件
  const validateFile = useCallback((file: RcFile): boolean => {
    // 检查格式
    if (!acceptedFormats.includes(file.type)) {
      message.error(`不支持的文件格式: ${file.type}`);
      return false;
    }

    // 检查大小
    const isLt = file.size / 1024 / 1024 < maxFileSize;
    if (!isLt) {
      message.error(`文件大小不能超过 ${maxFileSize}MB`);
      return false;
    }

    // 检查数量
    if (fileList.length >= maxFiles) {
      message.error(`最多只能上传 ${maxFiles} 个文件`);
      return false;
    }

    return true;
  }, [acceptedFormats, maxFileSize, maxFiles, fileList.length]);

  // 处理上传前验证
  const beforeUpload: UploadProps['beforeUpload'] = (file) => {
    if (!validateFile(file)) {
      return Upload.LIST_IGNORE;
    }
    return false; // 阻止自动上传，使用手动上传
  };

  // 处理文件列表变化
  const handleChange: UploadProps['onChange'] = ({ fileList: newFileList }) => {
    setFileList(newFileList);
  };

  // 手动上传
  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择要上传的图片');
      return;
    }

    setUploading(true);
    const results: UploadedImage[] = [];

    try {
      for (const file of fileList) {
        if (!file.originFileObj) continue;

        const formData = new FormData();
        formData.append('file', file.originFileObj);
        formData.append('enable_ocr', String(enableOCR));
        if (workflowId) formData.append('workflow_id', workflowId);
        if (documentId) formData.append('document_id', documentId);

        // 更新进度
        file.status = 'uploading';
        setFileList([...fileList]);

        try {
          const response = await fetch('/api/v1/images/upload', {
            method: 'POST',
            body: formData,
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token')}`,
            },
          });

          if (!response.ok) {
            throw new Error(`上传失败: ${response.statusText}`);
          }

          const data = await response.json();
          file.status = 'done';
          file.response = data;

          results.push({
            id: data.id,
            filename: file.name,
            url: data.url,
            thumbnailUrl: data.thumbnail_url,
            metadata: data.metadata,
            ocrText: data.ocr_text,
            embedding: data.embedding,
          });
        } catch (err) {
          file.status = 'error';
          file.error = err;
          logError(`Upload failed for ${file.name}`, 'ImageUpload', err);
        }

        setFileList([...fileList]);
      }

      setUploadedImages((prev) => [...prev, ...results]);

      if (results.length > 0) {
        message.success(`成功上传 ${results.length} 个文件`);
        onUploadComplete?.(results);
      }

      // 清除已上传的文件
      setFileList((prev) => prev.filter((f) => f.status !== 'done'));
    } catch (error) {
      message.error('上传过程中发生错误');
      logError('Upload error', 'ImageUpload', error);
    } finally {
      setUploading(false);
    }
  };

  // 删除已上传的图片
  const handleRemoveUploaded = async (imageId: string) => {
    try {
      await fetch(`/api/v1/images/${imageId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      setUploadedImages((prev) => prev.filter((img) => img.id !== imageId));
      message.success('图片已删除');
    } catch (error) {
      message.error('删除失败');
      logError('Delete error', 'ImageUpload', error);
    }
  };

  // 预览图片
  const handlePreview = (url: string) => {
    setPreviewImage(url);
    setPreviewOpen(true);
  };

  return (
    <div className="image-upload-container">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 上传区域 */}
        <Card>
          <Dragger
            name="files"
            multiple
            fileList={fileList}
            beforeUpload={beforeUpload}
            onChange={handleChange}
            accept={acceptedFormats.join(',')}
            showUploadList={{
              showPreviewIcon: true,
              showRemoveIcon: true,
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ color: '#1890ff', fontSize: 48 }} />
            </p>
            <p className="ant-upload-text">
              点击或拖拽图片到此区域上传
            </p>
            <p className="ant-upload-hint">
              支持格式: {acceptedFormats.map((f) => f.replace('image/', '.')).join(', ')} |
              单文件最大 {maxFileSize}MB | 最多 {maxFiles} 个文件
            </p>
          </Dragger>

          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Button
              type="primary"
              onClick={handleUpload}
              disabled={fileList.length === 0}
              loading={uploading}
              icon={<CloudUploadOutlined />}
              size="large"
            >
              {uploading ? '上传中...' : `上传 ${fileList.length} 个文件`}
            </Button>
          </div>
        </Card>

        {/* OCR 提示 */}
        {enableOCR && (
          <Alert
            message="OCR 功能已启用"
            description="上传的图片将自动进行文字识别，识别结果可用于 RAG 检索"
            type="info"
            showIcon
          />
        )}

        {/* 已上传图片预览 */}
        {uploadedImages.length > 0 && (
          <Card title={<><FileImageOutlined /> 已上传的图片</>}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                gap: 16,
              }}
            >
              {uploadedImages.map((img) => (
                <Card
                  key={img.id}
                  size="small"
                  cover={
                    <img
                      alt={img.filename}
                      src={img.thumbnailUrl || img.url}
                      style={{ height: 120, objectFit: 'cover' }}
                    />
                  }
                  actions={[
                    <EyeOutlined
                      key="preview"
                      onClick={() => handlePreview(img.url)}
                    />,
                    <DeleteOutlined
                      key="delete"
                      onClick={() => handleRemoveUploaded(img.id)}
                      style={{ color: '#ff4d4f' }}
                    />,
                  ]}
                >
                  <Card.Meta
                    title={
                      <Text ellipsis style={{ width: '100%' }}>
                        {img.filename}
                      </Text>
                    }
                    description={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {img.metadata.width}x{img.metadata.height} |{' '}
                        {(img.metadata.sizeBytes / 1024).toFixed(1)}KB
                      </Text>
                    }
                  />
                  {img.ocrText && (
                    <div style={{ marginTop: 8 }}>
                      <Text
                        type="secondary"
                        style={{ fontSize: 11 }}
                        ellipsis={{ tooltip: img.ocrText }}
                      >
                        OCR: {img.ocrText.substring(0, 30)}...
                      </Text>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </Card>
        )}
      </Space>

      {/* 图片预览模态框 */}
      <ImageViewer
        visible={previewOpen}
        imageUrl={previewImage || ''}
        onClose={() => setPreviewOpen(false)}
      />
    </div>
  );
};

export default ImageUpload;
