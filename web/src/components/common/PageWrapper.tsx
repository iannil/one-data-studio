import { Card } from 'antd';
import { ReactNode } from 'react';

interface PageWrapperProps {
  title?: string;
  extra?: ReactNode;
  children: ReactNode;
  style?: React.CSSProperties;
}

function PageWrapper({ title, extra, children, style }: PageWrapperProps) {
  return (
    <div style={{ padding: '24px', ...style }}>
      <Card
        title={title}
        extra={extra}
        bordered={false}
        style={{ borderRadius: '8px' }}
      >
        {children}
      </Card>
    </div>
  );
}

export default PageWrapper;
