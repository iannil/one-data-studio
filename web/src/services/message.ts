/**
 * Message 服务
 * 使用 Ant Design App context 来支持动态主题
 */
import { message } from 'antd';
import type { MessageInstance } from 'antd/es/message/interface';

let messageApi: MessageInstance | null = null;

/**
 * 初始化 message API（在 App 组件中调用）
 */
export function initMessageApi(api: MessageInstance): void {
  messageApi = api;
}

/**
 * 显示成功消息
 */
export function showSuccess(content: string, duration = 3): void {
  if (messageApi) {
    messageApi.success(content, duration);
  } else {
    message.success(content, duration);
  }
}

/**
 * 显示错误消息
 */
export function showError(content: string, duration = 3): void {
  if (messageApi) {
    messageApi.error(content, duration);
  } else {
    message.error(content, duration);
  }
}

/**
 * 显示信息消息
 */
export function showInfo(content: string, duration = 3): void {
  if (messageApi) {
    messageApi.info(content, duration);
  } else {
    message.info(content, duration);
  }
}

/**
 * 显示警告消息
 */
export function showWarning(content: string, duration = 3): void {
  if (messageApi) {
    messageApi.warning(content, duration);
  } else {
    message.warning(content, duration);
  }
}

/**
 * 显示加载消息
 */
export function showLoading(content = '加载中...', duration = 0): number {
  if (messageApi) {
    return messageApi.loading(content, duration);
  }
  return message.loading(content, duration);
}

// 导出类型
export type { MessageInstance };
