/**
 * 统一内容管理组件
 * 管理文章、分类、标签、评论等内容
 */

import React, { useState } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Tag,
  Space,
  Typography,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Image,
  Upload,
  Breadcrumb,
  Tooltip,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SendOutlined,
  EyeOutlined,
  LikeOutlined,
  CommentOutlined,
  FolderOutlined,
  TagOutlined,
  SearchOutlined,
  CheckOutlined,
  CloseOutlined,
  FileTextOutlined,
  BellOutlined,
  BookOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getContentArticles,
  createContentArticle,
  updateContentArticle,
  deleteContentArticle,
  publishContentArticle,
  likeContentArticle,
  getContentCategories,
  createContentCategory,
  getContentTags,
  createContentTag,
  getContentComments,
  createContentComment,
  approveContentComment,
  deleteContentComment,
  searchContent,
  getContentStatistics,
  type ContentArticle,
  type ContentCategory,
  type ContentTag,
  type ContentComment,
  type ContentType,
  type ContentStatus,
} from '@/services/alldata';
import './ContentManager.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface ContentManagerProps {
  className?: string;
}

/**
 * 文章表单对话框
 */
const ArticleFormModal: React.FC<{
  visible: boolean;
  article?: ContentArticle;
  categories?: ContentCategory[];
  tags?: ContentTag[];
  onCancel: () => void;
  onOk: (values: any) => void;
  loading?: boolean;
}> = ({ visible, article, categories, tags, onCancel, onOk, loading }) => {
  const [form] = Form.useForm();

  React.useEffect(() => {
    if (visible) {
      if (article) {
        form.setFieldsValue(article);
      } else {
        form.resetFields();
      }
    }
  }, [visible, article, form]);

  return (
    <Modal
      title={article ? '编辑文章' : '创建文章'}
      open={visible}
      onCancel={onCancel}
      onOk={() => form.validateFields().then(onOk)}
      confirmLoading={loading}
      width={800}
    >
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={16}>
            <Form.Item
              name="title"
              label="文章标题"
              rules={[{ required: true, message: '请输入标题' }]}
            >
              <Input placeholder="请输入文章标题" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="content_type"
              label="内容类型"
              initialValue="article"
            >
              <Select>
                <Option value="article">文章</Option>
                <Option value="announcement">公告</Option>
                <Option value="document">文档</Option>
                <Option value="tutorial">教程</Option>
                <Option value="faq">常见问题</Option>
                <Option value="news">新闻</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="summary"
          label="文章摘要"
        >
          <TextArea rows={2} placeholder="简短描述文章内容..." />
        </Form.Item>

        <Form.Item
          name="content"
          label="文章内容"
          rules={[{ required: true, message: '请输入内容' }]}
        >
          <TextArea rows={10} placeholder="支持 HTML 格式..." />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="category_id"
              label="分类"
            >
              <Select placeholder="选择分类" allowClear>
                {categories?.map((cat) => (
                  <Option key={cat.category_id} value={cat.category_id}>
                    {cat.icon} {cat.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="tags"
              label="标签"
            >
              <Select mode="tags" placeholder="选择标签">
                {tags?.map((tag) => (
                  <Option key={tag.tag_id} value={tag.tag_id}>
                    <Tag color={tag.color}>{tag.name}</Tag>
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="cover_image"
              label="封面图片"
            >
              <Input placeholder="图片 URL" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="status"
              label="状态"
              initialValue="draft"
            >
              <Select>
                <Option value="draft">草稿</Option>
                <Option value="reviewing">审核中</Option>
                <Option value="published">已发布</Option>
                <Option value="archived">已归档</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="featured"
              label="精选"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="allow_comment"
              label="允许评论"
              valuePropName="checked"
              initialValue={true}
            >
              <Switch />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
};

/**
 * 文章列表标签页
 */
const ArticlesTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingArticle, setEditingArticle] = useState<ContentArticle | undefined>();
  const [filters, setFilters] = useState<{
    status?: ContentStatus;
    content_type?: ContentType;
    category_id?: string;
  }>({});

  const { data: categoriesData } = useQuery({
    queryKey: ['content', 'categories'],
    queryFn: async () => {
      const res = await getContentCategories();
      return res.data;
    },
  });

  const { data: tagsData } = useQuery({
    queryKey: ['content', 'tags'],
    queryFn: async () => {
      const res = await getContentTags();
      return res.data;
    },
  });

  const { data: articlesData, isLoading } = useQuery({
    queryKey: ['content', 'articles', filters],
    queryFn: async () => {
      const res = await getContentArticles(filters);
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: createContentArticle,
    onSuccess: () => {
      message.success('文章创建成功');
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['content', 'articles'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ContentArticle> }) =>
      updateContentArticle(id, data),
    onSuccess: () => {
      message.success('文章更新成功');
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['content', 'articles'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteContentArticle,
    onSuccess: () => {
      message.success('文章删除成功');
      queryClient.invalidateQueries({ queryKey: ['content', 'articles'] });
    },
  });

  const publishMutation = useMutation({
    mutationFn: publishContentArticle,
    onSuccess: () => {
      message.success('文章发布成功');
      queryClient.invalidateQueries({ queryKey: ['content', 'articles'] });
    },
  });

  const handleCreate = () => {
    setEditingArticle(undefined);
    setModalVisible(true);
  };

  const handleEdit = (article: ContentArticle) => {
    setEditingArticle(article);
    setModalVisible(true);
  };

  const handleDelete = (contentId: string) => {
    deleteMutation.mutate(contentId);
  };

  const handlePublish = (contentId: string) => {
    publishMutation.mutate(contentId);
  };

  const handleSubmit = (values: any) => {
    if (editingArticle) {
      updateMutation.mutate({ id: editingArticle.content_id, data: values });
    } else {
      createMutation.mutate({
        ...values,
        author_id: 'current_user',
        author_name: '当前用户',
      });
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      reviewing: 'processing',
      published: 'success',
      archived: 'warning',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      draft: '草稿',
      reviewing: '审核中',
      published: '已发布',
      archived: '已归档',
    };
    return texts[status] || status;
  };

  const getContentTypeIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      article: <FileTextOutlined />,
      announcement: <BellOutlined />,
      document: <BookOutlined />,
      tutorial: <BookOutlined />,
      faq: <QuestionCircleOutlined />,
      news: <FileTextOutlined />,
    };
    return icons[type] || <FileTextOutlined />;
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, record: ContentArticle) => (
        <Space direction="vertical" size={0}>
          <Space>
            {getContentTypeIcon(record.content_type)}
            <span>{title}</span>
            {record.featured && <Tag color="gold">精选</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.summary}
          </Text>
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category_id',
      key: 'category_id',
      width: 100,
      render: (categoryId: string) => {
        const category = categoriesData?.categories.find(c => c.category_id === categoryId);
        return category ? (
          <Space>
            <span>{category.icon}</span>
            <span>{category.name}</span>
          </Space>
        ) : '-';
      },
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 120,
      render: (tagIds: string[]) => (
        <Space size={4} wrap>
          {tagIds?.slice(0, 2).map(tagId => {
            const tag = tagsData?.tags.find(t => t.tag_id === tagId);
            return tag ? <Tag key={tagId} color={tag.color}>{tag.name}</Tag> : null;
          })}
          {tagIds?.length > 2 && <Tag>+{tagIds.length - 2}</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '数据',
      key: 'stats',
      width: 120,
      render: (_: unknown, record: ContentArticle) => (
        <Space size="small">
          <Tooltip title="阅读">
            <Text type="secondary"><EyeOutlined /> {record.view_count}</Text>
          </Tooltip>
          <Tooltip title="点赞">
            <Text type="secondary"><LikeOutlined /> {record.like_count}</Text>
          </Tooltip>
          <Tooltip title="评论">
            <Text type="secondary"><CommentOutlined /> {record.comment_count}</Text>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: ContentArticle) => (
        <Space size="small">
          {record.status === 'draft' || record.status === 'reviewing' ? (
            <Button
              size="small"
              type="primary"
              onClick={() => handlePublish(record.content_id)}
            >
              发布
            </Button>
          ) : null}
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此文章？"
            onConfirm={() => handleDelete(record.content_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title="内容管理"
        className="content-articles-card"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建文章
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="状态"
            style={{ width: 120 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, status: value })}
          >
            <Option value="draft">草稿</Option>
            <Option value="reviewing">审核中</Option>
            <Option value="published">已发布</Option>
            <Option value="archived">已归档</Option>
          </Select>
          <Select
            placeholder="类型"
            style={{ width: 120 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, content_type: value })}
          >
            <Option value="article">文章</Option>
            <Option value="announcement">公告</Option>
            <Option value="document">文档</Option>
            <Option value="tutorial">教程</Option>
            <Option value="faq">常见问题</Option>
            <Option value="news">新闻</Option>
          </Select>
          <Select
            placeholder="分类"
            style={{ width: 140 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, category_id: value })}
          >
            {categoriesData?.categories.map(cat => (
              <Option key={cat.category_id} value={cat.category_id}>
                {cat.icon} {cat.name}
              </Option>
            ))}
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={articlesData?.articles || []}
          rowKey="content_id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <ArticleFormModal
        visible={modalVisible}
        article={editingArticle}
        categories={categoriesData?.categories}
        tags={tagsData?.tags}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        loading={createMutation.isPending || updateMutation.isPending}
      />
    </>
  );
};

/**
 * 分类和标签标签页
 */
const CategoriesTagsTab: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: categoriesData } = useQuery({
    queryKey: ['content', 'categories'],
    queryFn: async () => {
      const res = await getContentCategories();
      return res.data;
    },
  });

  const { data: tagsData } = useQuery({
    queryKey: ['content', 'tags'],
    queryFn: async () => {
      const res = await getContentTags();
      return res.data;
    },
  });

  const createCategoryMutation = useMutation({
    mutationFn: createContentCategory,
    onSuccess: () => {
      message.success('分类创建成功');
      queryClient.invalidateQueries({ queryKey: ['content', 'categories'] });
    },
  });

  const createTagMutation = useMutation({
    mutationFn: createContentTag,
    onSuccess: () => {
      message.success('标签创建成功');
      queryClient.invalidateQueries({ queryKey: ['content', 'tags'] });
    },
  });

  const handleAddCategory = () => {
    Modal.confirm({
      title: '创建分类',
      content: (
        <Input id="new-category-name" placeholder="分类名称" />
      ),
      onOk: () => {
        const name = (document.getElementById('new-category-name') as HTMLInputElement)?.value;
        if (name) {
          createCategoryMutation.mutate({ name });
        }
      },
    });
  };

  const handleAddTag = () => {
    Modal.confirm({
      title: '创建标签',
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input id="new-tag-name" placeholder="标签名称" />
          <Input id="new-tag-color" placeholder="颜色 (如: #1890ff)" defaultValue="#1890ff" />
        </Space>
      ),
      onOk: () => {
        const name = (document.getElementById('new-tag-name') as HTMLInputElement)?.value;
        const color = (document.getElementById('new-tag-color') as HTMLInputElement)?.value;
        if (name) {
          createTagMutation.mutate({ name, color });
        }
      },
    });
  };

  return (
    <Row gutter={16}>
      <Col xs={24} md={12}>
        <Card
          title={
            <Space>
              <FolderOutlined />
              <span>分类管理</span>
            </Space>
          }
          extra={
            <Button size="small" icon={<PlusOutlined />} onClick={handleAddCategory}>
              新建
            </Button>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {categoriesData?.categories.map((cat) => (
              <Card key={cat.category_id} size="small" className="category-item">
                <Space>
                  <span style={{ fontSize: 20 }}>{cat.icon}</span>
                  <div>
                    <div>{cat.name}</div>
                    <Text type="secondary" style={{ fontSize: 12 }}>{cat.description}</Text>
                  </div>
                </Space>
              </Card>
            ))}
          </Space>
        </Card>
      </Col>
      <Col xs={24} md={12}>
        <Card
          title={
            <Space>
              <TagOutlined />
              <span>标签管理</span>
            </Space>
          }
          extra={
            <Button size="small" icon={<PlusOutlined />} onClick={handleAddTag}>
              新建
            </Button>
          }
        >
          <Space wrap>
            {tagsData?.tags.map((tag) => (
              <Tag key={tag.tag_id} color={tag.color} style={{ fontSize: 14, padding: '4px 12px' }}>
                {tag.name} ({tag.usage_count})
              </Tag>
            ))}
          </Space>
        </Card>
      </Col>
    </Row>
  );
};

/**
 * 统计标签页
 */
const StatisticsTab: React.FC = () => {
  const { data: statsData, isLoading } = useQuery({
    queryKey: ['content', 'statistics'],
    queryFn: async () => {
      const res = await getContentStatistics();
      return res.data;
    },
  });

  return (
    <Row gutter={[16, 16]}>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="总文章数"
            value={statsData?.total_articles || 0}
            prefix={<FileTextOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="总分类数"
            value={statsData?.total_categories || 0}
            prefix={<FolderOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="总标签数"
            value={statsData?.total_tags || 0}
            prefix={<TagOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="总评论数"
            value={statsData?.total_comments || 0}
            prefix={<CommentOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="总阅读量"
            value={statsData?.total_views || 0}
            prefix={<EyeOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="总点赞数"
            value={statsData?.total_likes || 0}
            prefix={<LikeOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="精选文章"
            value={statsData?.featured_count || 0}
            prefix={<BellOutlined />}
            loading={isLoading}
          />
        </Card>
      </Col>
    </Row>
  );
};

/**
 * 主内容管理组件
 */
const ContentManager: React.FC<ContentManagerProps> = ({ className }) => {
  return (
    <div className={`content-manager ${className || ''}`}>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>统一内容管理</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="articles"
          items={[
            {
              key: 'articles',
              label: '文章管理',
              children: <ArticlesTab />,
            },
            {
              key: 'categories-tags',
              label: '分类标签',
              children: <CategoriesTagsTab />,
            },
            {
              key: 'statistics',
              label: '统计分析',
              children: <StatisticsTab />,
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default ContentManager;
