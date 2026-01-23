import { Result, Button } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

interface ErrorProps {
  title?: string;
  subTitle?: string;
  onRetry?: () => void;
}

function Error({ title = '出错了', subTitle, onRetry }: ErrorProps) {
  const navigate = useNavigate();

  return (
    <Result
      status="error"
      title={title}
      subTitle={subTitle || '页面加载失败，请稍后重试'}
      extra={[
        onRetry && (
          <Button type="primary" key="retry" icon={<ReloadOutlined />} onClick={onRetry}>
            重试
          </Button>
        ),
        <Button key="home" icon={<HomeOutlined />} onClick={() => navigate('/')}>
          返回首页
        </Button>,
      ]}
    />
  );
}

export default Error;
