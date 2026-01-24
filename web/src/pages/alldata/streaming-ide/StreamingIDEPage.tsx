import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Button,
  Input,
  message,
  Space,
  Divider,
  Typography,
  Select,
  Alert,
  Tag,
} from 'antd';
import {
  PlayCircleOutlined,
  SaveOutlined,
  FolderOpenOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';

const { TextArea } = Input;
const { Paragraph, Text } = Typography;
const { Option } = Select;

function StreamingIDEPage() {
  const [sqlCode, setSqlCode] = useState(`-- Flink SQL 示例
-- 创建源表
CREATE TABLE kafka_source (
  user_id BIGINT,
  user_name STRING,
  event_time TIMESTAMP(3),
  metadata MAP<STRING, STRING>
) WITH (
  'connector' = 'kafka',
  'topic' = 'user_events',
  'properties.bootstrap.servers' = 'localhost:9092',
  'properties.group.id' = 'flink_sql_group',
  'scan.startup.mode' = 'latest-offset'
);

-- 创建结果表
CREATE TABLE mysql_sink (
  user_id BIGINT,
  user_name STRING,
  last_event_time TIMESTAMP(3),
  event_count BIGINT,
  PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
  'connector' = 'jdbc',
  'url' = 'jdbc:mysql://localhost:3306/flink_results',
  'table-name' = 'user_events_summary',
  'driver' = 'com.mysql.cj.jdbc.Driver'
);

-- 数据处理和插入
INSERT INTO mysql_sink
SELECT
  user_id,
  user_name,
  MAX(event_time) as last_event_time,
  COUNT(*) as event_count
FROM kafka_source
GROUP BY user_id, user_name;
`);

  const [selectedJob, setSelectedJob] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors?: string[] } | null>(null);

  // 查询模拟作业列表
  const { data: jobsData, refetch } = useQuery({
    queryKey: ['flink-jobs'],
    queryFn: () => alldata.getFlinkJobs({ page: 1, page_size: 100 }),
  });

  // 验证 SQL
  const handleValidate = async () => {
    try {
      const result = await alldata.validateFlinkSql(sqlCode);
      setValidationResult(result.data);
      if (result.data.valid) {
        message.success('SQL 语法验证通过');
      } else {
        message.error('SQL 语法错误');
      }
    } catch (error) {
      message.error('验证失败');
    }
  };

  // 提交作业
  const handleSubmit = async () => {
    if (!sqlCode.trim()) {
      message.error('请输入 SQL 代码');
      return;
    }
    setIsRunning(true);
    // 模拟提交
    setTimeout(() => {
      setIsRunning(false);
      message.success('作业提交成功');
      refetch();
    }, 1000);
  };

  const examples = [
    {
      name: 'Kafka 到 MySQL',
      sql: `-- 从 Kafka 读取数据写入 MySQL
CREATE TABLE kafka_source (
  id BIGINT,
  data STRING,
  ts TIMESTAMP(3)
) WITH (
  'connector' = 'kafka',
  'topic' = 'events',
  'properties.bootstrap.servers' = 'localhost:9092'
);

CREATE TABLE mysql_sink (
  id BIGINT PRIMARY KEY,
  data STRING,
  ts TIMESTAMP(3)
) WITH (
  'connector' = 'jdbc',
  'url' = 'jdbc:mysql://localhost:3306/db'
);

INSERT INTO mysql_sink SELECT id, data, ts FROM kafka_source;`,
    },
    {
      name: '数据聚合',
      sql: `-- 实时聚合统计
CREATE TABLE aggregated_stats AS
SELECT
  TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end,
  user_id,
  COUNT(*) as event_count,
  SUM(amount) as total_amount
FROM events
GROUP BY
  TUMBLE(event_time, INTERVAL '1' MINUTE),
  user_id;`,
    },
    {
      name: '数据清洗',
      sql: `-- 数据清洗和过滤
CREATE TABLE cleaned_data AS
SELECT
  id,
  TRIM(name) as name,
  LOWER(email) as email,
  CASE
    WHEN age < 0 THEN NULL
    ELSE age
  END as age
FROM raw_source
WHERE email IS NOT NULL
  AND email LIKE '%@%';`,
    },
  ];

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* 工具栏 */}
      <Card size="small" style={{ borderRadius: 0, borderBottom: 'none' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button icon={<FolderOpenOutlined />}>打开</Button>
              <Button icon={<SaveOutlined />}>保存</Button>
              <Select
                placeholder="选择作业"
                style={{ width: 200 }}
                value={selectedJob}
                onChange={setSelectedJob}
                allowClear
              >
                {jobsData?.data?.jobs?.map((job) => (
                  <Option key={job.job_id} value={job.job_id}>
                    {job.name}
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button onClick={handleValidate}>
                <CheckCircleOutlined /> 验证
              </Button>
              <Button type="primary" onClick={handleSubmit} loading={isRunning}>
                <PlayCircleOutlined /> 提交运行
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row style={{ flex: 1, overflow: 'hidden' }}>
        {/* 左侧编辑器 */}
        <Col span={18} style={{ borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}>
          <div style={{ borderBottom: '1px solid #f0f0f0', padding: '8px 16px', background: '#fafafa' }}>
            <Space split={<Divider type="vertical" />}>
              <Text type="secondary">main.sql</Text>
              {validationResult && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  {validationResult.valid ? (
                    <Text style={{ color: '#52c41a' }}><CheckCircleOutlined /> 语法正确</Text>
                  ) : (
                    <Text style={{ color: '#ff4d4f' }}><CloseCircleOutlined /> 语法错误</Text>
                  )}
                </span>
              )}
            </Space>
          </div>
          <TextArea
            value={sqlCode}
            onChange={(e) => {
              setSqlCode(e.target.value);
              setValidationResult(null);
            }}
            style={{
              flex: 1,
              border: 'none',
              borderRadius: 0,
              resize: 'none',
              fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
              fontSize: 13,
              lineHeight: '1.6',
              padding: 16,
            }}
            placeholder="-- 在此编写 Flink SQL 代码..."
            spellCheck={false}
          />
        </Col>

        {/* 右侧边栏 */}
        <Col span={6} style={{ background: '#fafafa', overflowY: 'auto' }}>
          {/* SQL 示例 */}
          <Card title={<><CodeOutlined /> SQL 示例</>} size="small" style={{ borderRadius: 0 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {examples.map((example, index) => (
                <Button
                  key={index}
                  block
                  type="text"
                  style={{ textAlign: 'left', height: 'auto', padding: '8px' }}
                  onClick={() => setSqlCode(example.sql)}
                >
                  <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{example.name}</div>
                  <div style={{ fontSize: 12, color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {example.sql.slice(0, 50)}...
                  </div>
                </Button>
              ))}
            </Space>
          </Card>

          {/* SQL 语法提示 */}
          <Card title="语法提示" size="small" style={{ borderRadius: 0, marginTop: 8 }}>
            <Paragraph style={{ fontSize: 12 }}>
              <Text strong>常用语句:</Text>
              <ul style={{ paddingLeft: 16, marginTop: 8 }}>
                <li>CREATE TABLE - 创建表</li>
                <li>INSERT INTO - 插入数据</li>
                <li>SELECT - 查询数据</li>
                <li>WHERE - 过滤条件</li>
                <li>GROUP BY - 分组聚合</li>
                <li>JOIN - 表连接</li>
              </ul>
            </Paragraph>
            <Paragraph style={{ fontSize: 12 }}>
              <Text strong>内置函数:</Text>
              <ul style={{ paddingLeft: 16, marginTop: 8 }}>
                <li>COUNT/SUM/AVG - 聚合函数</li>
                <li>CAST/CONCAT - 类型转换/字符串连接</li>
                <li>DATE/TIMESTAMP - 日期函数</li>
                <li>TUMBLE/HOP - 窗口函数</li>
              </ul>
            </Paragraph>
          </Card>

          {/* 最近作业 */}
          <Card title="最近作业" size="small" style={{ borderRadius: 0, marginTop: 8 }}>
            {jobsData?.data?.jobs?.slice(0, 5).map((job) => (
              <div
                key={job.job_id}
                style={{
                  padding: '8px 0',
                  borderBottom: '1px solid #f0f0f0',
                  cursor: 'pointer',
                }}
                onClick={() => setSelectedJob(job.job_id)}
              >
                <div style={{ fontSize: 12, fontWeight: 'bold' }}>{job.name}</div>
                <div style={{ fontSize: 11, color: '#999' }}>
                  <Tag color={job.status === 'running' ? 'green' : 'default'}>
                    {job.status === 'running' ? '运行中' : '已停止'}
                  </Tag>
                  <span style={{ marginLeft: 8 }}>
                    {dayjs(job.created_at).format('MM-DD HH:mm')}
                  </span>
                </div>
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      {/* 验证错误提示 */}
      {validationResult && !validationResult.valid && validationResult.errors && (
        <Alert
          style={{ margin: '16px 24px' }}
          message="SQL 语法错误"
          description={validationResult.errors?.map((err, i) => (
            <div key={i}>• {err}</div>
          ))}
          type="error"
          closable
          onClose={() => setValidationResult(null)}
        />
      )}
    </div>
  );
}

export default StreamingIDEPage;
