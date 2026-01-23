import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LoadingProps {
  tip?: string;
  size?: 'small' | 'default' | 'large';
  fullScreen?: boolean;
}

function Loading({ tip = '加载中...', size = 'large', fullScreen = false }: LoadingProps) {
  const content = (
    <Spin
      size={size}
      indicator={<LoadingOutlined style={{ fontSize: size === 'large' ? 32 : 24 }} spin />}
      tip={tip}
    />
  );

  if (fullScreen) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          width: '100vw',
        }}
      >
        {content}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px',
      }}
    >
      {content}
    </div>
  );
}

export default Loading;
