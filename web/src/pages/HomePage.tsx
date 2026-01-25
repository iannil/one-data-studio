import { Card, Col, Row, Statistic, Typography, Spin } from 'antd';
import {
  DatabaseOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  TableOutlined,
  UserOutlined,
  ExperimentOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

const { Title, Paragraph } = Typography;

// Types
interface StatsOverview {
  users: { total: number; active: number };
  datasets: { total: number; recent: number };
  models: { total: number; deployed: number };
  workflows: { total: number; running: number };
  experiments: { total: number; completed: number };
  api_calls: { today: number; total: number };
  storage: { used_gb: number; total_gb: number };
  compute: { gpu_hours_today: number; cpu_hours_today: number };
}

// API function
const fetchStatsOverview = async (): Promise<StatsOverview> => {
  const response = await fetch('/api/v1/stats/overview');
  if (!response.ok) throw new Error('Failed to fetch stats');
  const data = await response.json();
  return data.data;
};

function HomePage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats-overview'],
    queryFn: fetchStatsOverview,
    staleTime: 60000, // 1 minute
  });

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '32px' }}>
        <Title level={2}>欢迎来到 ONE-DATA-STUDIO</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          统一数据 + AI + LLM 融合平台，整合 Alldata、Cube Studio 和 Bisheng 三大平台能力
        </Paragraph>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: '32px' }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="数据集"
                  value={stats?.datasets?.total || 0}
                  prefix={<DatabaseOutlined />}
                  valueStyle={{ color: '#1677ff' }}
                  suffix={
                    stats?.datasets?.recent ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>+{stats.datasets.recent} 新增</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="模型"
                  value={stats?.models?.total || 0}
                  prefix={<NodeIndexOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                  suffix={
                    stats?.models?.deployed ? (
                      <span style={{ fontSize: 12, color: '#1677ff' }}>{stats.models.deployed} 已部署</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="工作流"
                  value={stats?.workflows?.total || 0}
                  prefix={<TableOutlined />}
                  valueStyle={{ color: '#faad14' }}
                  suffix={
                    stats?.workflows?.running ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>{stats.workflows.running} 运行中</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="用户"
                  value={stats?.users?.total || 0}
                  prefix={<UserOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                  suffix={
                    stats?.users?.active ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>{stats.users.active} 活跃</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: '32px' }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="实验"
                  value={stats?.experiments?.total || 0}
                  prefix={<ExperimentOutlined />}
                  valueStyle={{ color: '#13c2c2' }}
                  suffix={
                    stats?.experiments?.completed ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>{stats.experiments.completed} 已完成</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="今日 API 调用"
                  value={stats?.api_calls?.today || 0}
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: '#eb2f96' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="存储使用"
                  value={stats?.storage?.used_gb?.toFixed(1) || 0}
                  prefix={<CloudServerOutlined />}
                  suffix={`/ ${stats?.storage?.total_gb || 0} GB`}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="今日 GPU 小时"
                  value={stats?.compute?.gpu_hours_today || 0}
                  prefix={<MessageOutlined />}
                  valueStyle={{ color: '#2f54eb' }}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}

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
