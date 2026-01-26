/**
 * 内容管理页面
 * 用于管理文章、分类和标签
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Modal,
  Form,
  message,
  Tabs,
  Popconfirm,
  Upload,
  Card,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  FileTextOutlined,
  FolderOutlined,
  TagOutlined,
  UploadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { TabsProps } from 'antd';
import { RichTextEditor } from '../../components/RichTextEditor';
import {
  getArticles,
  createArticle,
  updateArticle,
  deleteArticle,
  submitArticleForApproval,
  getContentCategories,
  createContentCategory,
  updateContentCategory,
  deleteContentCategory,
  getContentTags,
  createContentTag,
  updateContentTag,
  deleteContentTag,
  type Article,
  type ContentCategory,
  type ContentTag,
} from '../../services/admin';

const { TextArea } = Input;
const { Option } = Select;

export const ContentPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('articles');
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<ContentCategory[]>([]);
  const [tags, setTags] = useState<ContentTag[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  // Modal states
  const [articleModalVisible, setArticleModalVisible] = useState(false);
  const [categoryModalVisible, setCategoryModalVisible] = useState(false);
  const [tagModalVisible, setTagModalVisible] = useState(false);
  const [currentArticle, setCurrentArticle] = useState<Partial<Article>>({});
  const [currentCategory, setCurrentCategory] = useState<Partial<ContentCategory>>({});
  const [currentTag, setCurrentTag] = useState<Partial<ContentTag>>({});
  const [previewVisible, setPreviewVisible] = useState(false);

  // Filters
  const [articleFilter, setArticleFilter] = useState({ status: '', category_id: '' });

  // Forms
  const [articleForm] = Form.useForm();
  const [categoryForm] = Form.useForm();
  const [tagForm] = Form.useForm();

  // Fetch articles
  const fetchArticles = useCallback(async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const res = await getArticles({
        page,
        page_size: pageSize,
        status: articleFilter.status || undefined,
        category_id: articleFilter.category_id || undefined,
      });
      if (res.code === 0) {
        setArticles(res.data.articles);
        setPagination({
          current: res.data.page,
          pageSize: res.data.page_size,
          total: res.data.total,
        });
      }
    } catch (error) {
      message.error('获取文章列表失败');
    } finally {
      setLoading(false);
    }
  }, [articleFilter]);

  // Fetch categories
  const fetchCategories = useCallback(async () => {
    try {
      const res = await getContentCategories();
      if (res.code === 0) {
        setCategories(res.data.categories || []);
      }
    } catch (error) {
      message.error('获取分类列表失败');
    }
  }, []);

  // Fetch tags
  const fetchTags = useCallback(async () => {
    try {
      const res = await getContentTags();
      if (res.code === 0) {
        setTags(res.data.tags);
      }
    } catch (error) {
      message.error('获取标签列表失败');
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'articles') {
      fetchArticles();
    } else if (activeTab === 'categories') {
      fetchCategories();
    } else if (activeTab === 'tags') {
      fetchTags();
    }
  }, [activeTab, fetchArticles, fetchCategories, fetchTags]);

  // Article operations
  const handleCreateArticle = () => {
    setCurrentArticle({ status: 'draft', content_type: 'markdown' });
    articleForm.resetFields();
    setArticleModalVisible(true);
  };

  const handleEditArticle = (article: Article) => {
    setCurrentArticle(article);
    articleForm.setFieldsValue(article);
    setArticleModalVisible(true);
  };

  const handleSaveArticle = async () => {
    try {
      const values = await articleForm.validateFields();
      const data = {
        ...currentArticle,
        ...values,
      };

      const res = currentArticle.article_id
        ? await updateArticle(currentArticle.article_id, data)
        : await createArticle(data);

      if (res.code === 0) {
        message.success(currentArticle.article_id ? '更新成功' : '创建成功');
        setArticleModalVisible(false);
        fetchArticles();
      } else {
        message.error(res.message || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeleteArticle = async (articleId: string) => {
    try {
      const res = await deleteArticle(articleId);
      if (res.code === 0) {
        message.success('删除成功');
        fetchArticles();
      } else {
        message.error(res.message || '删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmitForApproval = async (articleId: string) => {
    try {
      const res = await submitArticleForApproval(articleId);
      if (res.code === 0) {
        message.success('已提交审核');
        fetchArticles();
      } else {
        message.error(res.message || '提交失败');
      }
    } catch (error) {
      message.error('提交失败');
    }
  };

  // Category operations
  const handleCreateCategory = () => {
    setCurrentCategory({});
    categoryForm.resetFields();
    setCategoryModalVisible(true);
  };

  const handleEditCategory = (category: ContentCategory) => {
    setCurrentCategory(category);
    categoryForm.setFieldsValue(category);
    setCategoryModalVisible(true);
  };

  const handleSaveCategory = async () => {
    try {
      const values = await categoryForm.validateFields();
      const data = { ...currentCategory, ...values };

      const res = currentCategory.category_id
        ? await updateContentCategory(currentCategory.category_id, data)
        : await createContentCategory(data);

      if (res.code === 0) {
        message.success(currentCategory.category_id ? '更新成功' : '创建成功');
        setCategoryModalVisible(false);
        fetchCategories();
      } else {
        message.error(res.message || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeleteCategory = async (categoryId: string) => {
    try {
      const res = await deleteContentCategory(categoryId);
      if (res.code === 0) {
        message.success('删除成功');
        fetchCategories();
      } else {
        message.error(res.message || '删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  // Tag operations
  const handleCreateTag = () => {
    setCurrentTag({});
    tagForm.resetFields();
    setTagModalVisible(true);
  };

  const handleEditTag = (tag: ContentTag) => {
    setCurrentTag(tag);
    tagForm.setFieldsValue(tag);
    setTagModalVisible(true);
  };

  const handleSaveTag = async () => {
    try {
      const values = await tagForm.validateFields();
      const data = { ...currentTag, ...values };

      const res = currentTag.tag_id
        ? await updateContentTag(currentTag.tag_id, data)
        : await createContentTag(data);

      if (res.code === 0) {
        message.success(currentTag.tag_id ? '更新成功' : '创建成功');
        setTagModalVisible(false);
        fetchTags();
      } else {
        message.error(res.message || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeleteTag = async (tagId: string) => {
    try {
      const res = await deleteContentTag(tagId);
      if (res.code === 0) {
        message.success('删除成功');
        fetchTags();
      } else {
        message.error(res.message || '删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  // Status tag colors
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      pending: 'processing',
      published: 'success',
      rejected: 'error',
      archived: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      draft: '草稿',
      pending: '待审核',
      published: '已发布',
      rejected: '已拒绝',
      archived: '已归档',
    };
    return texts[status] || status;
  };

  // Tab items
  const tabItems: TabsProps['items'] = [
    {
      key: 'articles',
      label: (
        <span>
          <FileTextOutlined />
          文章管理
        </span>
      ),
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="搜索标题"
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              onChange={(e) => {
                // Implement search
              }}
            />
            <Select
              placeholder="状态筛选"
              style={{ width: 120 }}
              allowClear
              value={articleFilter.status || undefined}
              onChange={(value) => {
                setArticleFilter({ ...articleFilter, status: value || '' });
              }}
            >
              <Option value="draft">草稿</Option>
              <Option value="pending">待审核</Option>
              <Option value="published">已发布</Option>
              <Option value="rejected">已拒绝</Option>
              <Option value="archived">已归档</Option>
            </Select>
            <Select
              placeholder="分类筛选"
              style={{ width: 150 }}
              allowClear
              value={articleFilter.category_id || undefined}
              onChange={(value) => {
                setArticleFilter({ ...articleFilter, category_id: value || '' });
              }}
            >
              {categories.map((cat) => (
                <Option key={cat.category_id} value={cat.category_id}>
                  {cat.name}
                </Option>
              ))}
            </Select>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateArticle}>
              新建文章
            </Button>
          </Space>

          <Table
            dataSource={articles}
            loading={loading}
            rowKey="article_id"
            pagination={{
              ...pagination,
              onChange: (page, pageSize) => fetchArticles(page, pageSize),
            }}
            columns={[
              {
                title: '标题',
                dataIndex: 'title',
                key: 'title',
                ellipsis: true,
              },
              {
                title: '分类',
                dataIndex: 'category_name',
                key: 'category_name',
                width: 120,
              },
              {
                title: '状态',
                dataIndex: 'status',
                key: 'status',
                width: 100,
                render: (status) => (
                  <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
                ),
              },
              {
                title: '作者',
                dataIndex: 'author_name',
                key: 'author_name',
                width: 120,
              },
              {
                title: '浏览',
                dataIndex: 'view_count',
                key: 'view_count',
                width: 80,
              },
              {
                title: '创建时间',
                dataIndex: 'created_at',
                key: 'created_at',
                width: 180,
                render: (date) => new Date(date).toLocaleString('zh-CN'),
              },
              {
                title: '操作',
                key: 'actions',
                width: 200,
                render: (_, record) => (
                  <Space size="small">
                    <Button
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => {
                        setCurrentArticle(record);
                        setPreviewVisible(true);
                      }}
                    >
                      预览
                    </Button>
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEditArticle(record)}
                    >
                      编辑
                    </Button>
                    {record.status === 'draft' && (
                      <Button
                        type="link"
                        size="small"
                        onClick={() => handleSubmitForApproval(record.article_id)}
                      >
                        提交审核
                      </Button>
                    )}
                    <Popconfirm
                      title="确定删除这篇文章吗？"
                      onConfirm={() => handleDeleteArticle(record.article_id)}
                    >
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </div>
      ),
    },
    {
      key: 'categories',
      label: (
        <span>
          <FolderOutlined />
          分类管理
        </span>
      ),
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateCategory}>
              新建分类
            </Button>
          </Space>

          <Table
            dataSource={categories}
            loading={loading}
            rowKey="category_id"
            pagination={false}
            columns={[
              {
                title: '名称',
                dataIndex: 'name',
                key: 'name',
              },
              {
                title: 'URL别名',
                dataIndex: 'slug',
                key: 'slug',
              },
              {
                title: '描述',
                dataIndex: 'description',
                key: 'description',
                ellipsis: true,
              },
              {
                title: '内容数',
                dataIndex: 'content_count',
                key: 'content_count',
                width: 100,
              },
              {
                title: '排序',
                dataIndex: 'sort_order',
                key: 'sort_order',
                width: 80,
              },
              {
                title: '操作',
                key: 'actions',
                width: 150,
                render: (_, record) => (
                  <Space size="small">
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEditCategory(record)}
                    >
                      编辑
                    </Button>
                    <Popconfirm
                      title="确定删除这个分类吗？"
                      onConfirm={() => handleDeleteCategory(record.category_id)}
                    >
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </div>
      ),
    },
    {
      key: 'tags',
      label: (
        <span>
          <TagOutlined />
          标签管理
        </span>
      ),
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateTag}>
              新建标签
            </Button>
          </Space>

          <Table
            dataSource={tags}
            loading={loading}
            rowKey="tag_id"
            pagination={false}
            columns={[
              {
                title: '名称',
                dataIndex: 'name',
                key: 'name',
                render: (name, record) => (
                  <Tag color={record.color}>{name}</Tag>
                ),
              },
              {
                title: 'URL别名',
                dataIndex: 'slug',
                key: 'slug',
              },
              {
                title: '颜色',
                dataIndex: 'color',
                key: 'color',
                width: 100,
                render: (color) => (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        width: 16,
                        height: 16,
                        backgroundColor: color,
                        border: '1px solid #d9d9d9',
                        borderRadius: 2,
                      }}
                    />
                    {color}
                  </span>
                ),
              },
              {
                title: '使用次数',
                dataIndex: 'usage_count',
                key: 'usage_count',
                width: 100,
              },
              {
                title: '操作',
                key: 'actions',
                width: 150,
                render: (_, record) => (
                  <Space size="small">
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEditTag(record)}
                    >
                      编辑
                    </Button>
                    <Popconfirm
                      title="确定删除这个标签吗？"
                      onConfirm={() => handleDeleteTag(record.tag_id)}
                    >
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </div>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="文章总数"
              value={articles.length}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="分类数"
              value={categories.length}
              prefix={<FolderOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="标签数" value={tags.length} prefix={<TagOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已发布" value={articles.filter((a) => a.status === 'published').length} />
          </Card>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} items={tabItems} onChange={setActiveTab} />

      {/* Article Modal */}
      <Modal
        title={currentArticle.article_id ? '编辑文章' : '新建文章'}
        open={articleModalVisible}
        onOk={handleSaveArticle}
        onCancel={() => setArticleModalVisible(false)}
        width={900}
        okText="保存"
        cancelText="取消"
      >
        <Form form={articleForm} layout="vertical">
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="请输入文章标题" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="slug" label="URL别名">
                <Input placeholder="自动生成或手动输入" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="category_id"
                label="分类"
                rules={[{ required: true, message: '请选择分类' }]}
              >
                <Select placeholder="请选择分类">
                  {categories.map((cat) => (
                    <Option key={cat.category_id} value={cat.category_id}>
                      {cat.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="summary" label="摘要">
            <TextArea rows={3} placeholder="请输入文章摘要" />
          </Form.Item>

          <Form.Item name="content" label="内容" rules={[{ required: true, message: '请输入内容' }]}>
            <RichTextEditor />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="tags" label="标签">
                <Select mode="tags" placeholder="选择或输入标签">
                  {tags.map((tag) => (
                    <Option key={tag.tag_id} value={tag.name}>
                      {tag.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cover_image" label="封面图">
                <Input placeholder="封面图URL" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="allow_comment" label="允许评论" valuePropName="checked">
                <Select defaultValue={true}>
                  <Option value={true}>是</Option>
                  <Option value={false}>否</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_featured" label="精选" valuePropName="checked">
                <Select defaultValue={false}>
                  <Option value={true}>是</Option>
                  <Option value={false}>否</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_top" label="置顶" valuePropName="checked">
                <Select defaultValue={false}>
                  <Option value={true}>是</Option>
                  <Option value={false}>否</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Category Modal */}
      <Modal
        title={currentCategory.category_id ? '编辑分类' : '新建分类'}
        open={categoryModalVisible}
        onOk={handleSaveCategory}
        onCancel={() => setCategoryModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={categoryForm} layout="vertical">
          <Form.Item
            name="name"
            label="分类名称"
            rules={[{ required: true, message: '请输入分类名称' }]}
          >
            <Input placeholder="请输入分类名称" />
          </Form.Item>

          <Form.Item
            name="slug"
            label="URL别名"
            rules={[{ required: true, message: '请输入URL别名' }]}
          >
            <Input placeholder="请输入URL别名" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="请输入分类描述" />
          </Form.Item>

          <Form.Item name="icon" label="图标">
            <Input placeholder="图标名称，如: FolderOutlined" />
          </Form.Item>

          <Form.Item name="sort_order" label="排序">
            <Input type="number" placeholder="数字越小越靠前" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Tag Modal */}
      <Modal
        title={currentTag.tag_id ? '编辑标签' : '新建标签'}
        open={tagModalVisible}
        onOk={handleSaveTag}
        onCancel={() => setTagModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={tagForm} layout="vertical">
          <Form.Item
            name="name"
            label="标签名称"
            rules={[{ required: true, message: '请输入标签名称' }]}
          >
            <Input placeholder="请输入标签名称" />
          </Form.Item>

          <Form.Item
            name="slug"
            label="URL别名"
            rules={[{ required: true, message: '请输入URL别名' }]}
          >
            <Input placeholder="请输入URL别名" />
          </Form.Item>

          <Form.Item name="color" label="颜色">
            <Input type="color" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="请输入标签描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title="文章预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
      >
        {currentArticle && (
          <div>
            <h1>{currentArticle.title}</h1>
            <Space style={{ marginBottom: 16 }}>
              <Tag>{currentArticle.category_name}</Tag>
              <span>{currentArticle.author_name}</span>
              <span>{new Date(currentArticle.created_at || '').toLocaleString('zh-CN')}</span>
            </Space>
            {currentArticle.summary && (
              <p style={{ color: '#666', marginBottom: 16 }}>{currentArticle.summary}</p>
            )}
            <div
              dangerouslySetInnerHTML={{ __html: currentArticle.content || '' }}
              style={{ lineHeight: 1.8 }}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ContentPage;
