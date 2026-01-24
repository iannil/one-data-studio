import React, { Component, ReactNode } from 'react';
import { Button, Result, Typography } from 'antd';

const { Paragraph, Text } = Typography;

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * ErrorBoundary 组件
 *
 * 捕获子组件的 JavaScript 错误，显示回退 UI，防止整个应用崩溃
 *
 * 使用方式:
 * ```tsx
 * <ErrorBoundary>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * // 带自定义回退UI
 * <ErrorBoundary fallback={<div>出错了</div>}>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * // 带重置回调
 * <ErrorBoundary onReset={() => refetchData()}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.setState({ errorInfo });

    // 记录错误到控制台 (生产环境应该发送到错误追踪服务)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = (): void => {
    const { onReset } = this.props;

    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    if (onReset) {
      onReset();
    }
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // 如果提供了自定义回退 UI，使用它
      if (fallback) {
        return fallback;
      }

      // 默认错误 UI
      return (
        <Result
          status="error"
          title="页面出现错误"
          subTitle="抱歉，页面遇到了一些问题。您可以尝试重试或刷新页面。"
          extra={[
            <Button key="retry" type="primary" onClick={this.handleReset}>
              重试
            </Button>,
            <Button key="reload" onClick={this.handleReload}>
              刷新页面
            </Button>,
          ]}
        >
          {process.env.NODE_ENV === 'development' && error && (
            <div style={{ textAlign: 'left', marginTop: 16 }}>
              <Paragraph>
                <Text strong style={{ fontSize: 16 }}>
                  错误信息:
                </Text>
              </Paragraph>
              <Paragraph>
                <Text code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {error.message}
                </Text>
              </Paragraph>
              {errorInfo && (
                <>
                  <Paragraph>
                    <Text strong style={{ fontSize: 16 }}>
                      组件堆栈:
                    </Text>
                  </Paragraph>
                  <Paragraph>
                    <Text
                      code
                      style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        fontSize: 12,
                        display: 'block',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}
                    >
                      {errorInfo.componentStack}
                    </Text>
                  </Paragraph>
                </>
              )}
            </div>
          )}
        </Result>
      );
    }

    return children;
  }
}

/**
 * 页面级 ErrorBoundary
 * 用于包裹整个页面，提供页面级别的错误恢复
 */
export const PageErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary
      onReset={() => {
        // 重置页面状态 - 可以添加额外的清理逻辑
      }}
    >
      {children}
    </ErrorBoundary>
  );
};

export default ErrorBoundary;
