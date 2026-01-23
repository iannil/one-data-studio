import { Card, Col, Row, Statistic, Typography } from 'antd';
import {
  DatabaseOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  TableOutlined,
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

function HomePage() {
  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '32px' }}>
        <Title level={2}>欢迎来到 ONE-DATA-STUDIO</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          统一数据 + AI + LLM 融合平台，整合 Alldata、Cube Studio 和 Bisheng 三大平台能力
        </Paragraph>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: '32px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="数据集"
              value={0}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="模型"
              value={0}
              prefix={<NodeIndexOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="工作流"
              value={0}
              prefix={<TableOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="对话"
              value={0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Title level={4} style={{ marginBottom: '16px' }}>
        快速开始
      </Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card
            hoverable
            onClick={() => (window.location.href = '/datasets')}
            style={{ cursor: 'pointer' }}
          >
            <DatabaseOutlined style={{ fontSize: '32px', color: '#1677ff', marginBottom: '16px' }} />
            <Title level={5}>数据集管理</Title>
            <Paragraph type="secondary">
              管理数据集、定义 Schema、版本控制、文件上传
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            hoverable
            onClick={() => (window.location.href = '/chat')}
            style={{ cursor: 'pointer' }}
          >
            <MessageOutlined style={{ fontSize: '32px', color: '#52c41a', marginBottom: '16px' }} />
            <Title level={5}>AI 聊天</Title>
            <Paragraph type="secondary">
              与 AI 模型对话、流式输出、参数配置
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            hoverable
            onClick={() => (window.location.href = '/metadata')}
            style={{ cursor: 'pointer' }}
          >
            <TableOutlined style={{ fontSize: '32px', color: '#faad14', marginBottom: '16px' }} />
            <Title level={5}>元数据浏览</Title>
            <Paragraph type="secondary">
              浏览数据库和表结构、Text-to-SQL 查询
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default HomePage;
