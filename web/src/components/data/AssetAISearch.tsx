/**
 * AI 资产智能搜索组件
 * 支持自然语言搜索、语义检索、智能补全
 */

import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, List, Tag, Space, Tooltip, Spin, Empty, Divider, AutoComplete } from 'antd';
import {
  SearchOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  FireOutlined,
  StarOutlined,
  CloseCircleFilled
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { message } from 'antd';
import alldata from '@/services/alldata';
import type {
  AIAssetSearchResult,
  AutocompleteSuggestion,
  QueryIntent
} from '@/services/alldata';
import './AssetAISearch.css';

const { Search } = Input;
const { TextArea } = Input;

interface AssetAISearchProps {
  onResultSelect?: (asset: any) => void;
  placeholder?: string;
  showTrending?: boolean;
}

export const AssetAISearch: React.FC<AssetAISearchProps> = ({
  onResultSelect,
  placeholder = "用自然语言描述你要找的数据资产，例如：'用户订单相关的表'",
  showTrending = true
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<AIAssetSearchResult[]>([]);
  const [searchIntent, setSearchIntent] = useState<QueryIntent | null>(null);
  const [autocompleteOptions, setAutocompleteOptions] = useState<Array<{ value: string; label: string | React.ReactNode }>>([]);
  const [showTrendingPanel, setShowTrendingPanel] = useState(false);

  const searchInputRef = useRef<any>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 获取热门资产
  const { data: trendingData, isLoading: trendingLoading } = useQuery({
    queryKey: ['trending-assets'],
    queryFn: () => alldata.getTrendingAssets({ days: 7, limit: 10 }),
    enabled: showTrending,
  });

  // 搜索处理
  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setSearchIntent(null);
      return;
    }

    setIsSearching(true);
    try {
      const response = await alldata.aiSearchAssets(query, { limit: 20 });
      const data = response.data?.data;

      if (data) {
        setSearchResults(data.results || []);
        setSearchIntent(data.intent || null);

        if (data.results?.length === 0) {
          message.info('未找到匹配的资产，请尝试其他关键词');
        }
      }
    } catch (error) {
      message.error('搜索失败，请稍后重试');
      setSearchResults([]);
      setSearchIntent(null);
    } finally {
      setIsSearching(false);
    }
  };

  // 防抖搜索
  const handleInputChange = (value: string) => {
    setSearchQuery(value);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // 获取补全建议
    if (value.length >= 2) {
      getAutocompleteSuggestions(value);
    } else {
      setAutocompleteOptions([]);
    }

    // 延迟搜索
    if (value.length >= 3) {
      searchTimeoutRef.current = setTimeout(() => {
        handleSearch(value);
      }, 500);
    } else {
      setSearchResults([]);
      setSearchIntent(null);
    }
  };

  // 获取补全建议
  const getAutocompleteSuggestions = async (prefix: string) => {
    try {
      const response = await alldata.getAssetAutocomplete(prefix, { limit: 8 });
      const suggestions = response.data?.data?.suggestions || [];

      setAutocompleteOptions(
        suggestions.map((s: AutocompleteSuggestion) => ({
          value: s.full_name || s.text,
          label: (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>
                {s.type === 'asset' && <Tag color="blue" style={{ marginRight: 4 }}>资产</Tag>}
                {s.type === 'table' && <Tag color="green" style={{ marginRight: 4 }}>表</Tag>}
                {s.type === 'column' && <Tag color="orange" style={{ marginRight: 4 }}>列</Tag>}
                {s.text}
              </span>
              <span style={{ fontSize: 12, color: '#999' }}>
                {s.database && `${s.database}.`}{s.table && `${s.table}.`}
              </span>
            </div>
          ),
        }))
      );
    } catch (error) {
      setAutocompleteOptions([]);
    }
  };

  // 清空搜索
  const handleClear = () => {
    setSearchQuery('');
    setSearchResults([]);
    setSearchIntent(null);
    setAutocompleteOptions([]);
    searchInputRef.current?.focus();
  };

  // 选择结果
  const handleResultClick = (result: AIAssetSearchResult) => {
    onResultSelect?.(result.asset);
  };

  // 渲染意图标签
  const renderIntentTags = () => {
    if (!searchIntent) return null;

    const tags: React.ReactNode[] = [];

    if (searchIntent.asset_types.length > 0) {
      searchIntent.asset_types.forEach(type => {
        const typeLabels: Record<string, string> = {
          table: '表',
          view: '视图',
          dataset: '数据集',
          file: '文件',
          api: '接口'
        };
        tags.push(<Tag key={`type-${type}`} color="blue">{typeLabels[type] || type}</Tag>);
      });
    }

    if (searchIntent.data_level) {
      const levelLabels: Record<string, string> = {
        public: '公开',
        internal: '内部',
        confidential: '机密',
        restricted: '绝密'
      };
      tags.push(<Tag key="level" color="orange">{levelLabels[searchIntent.data_level]}</Tag>);
    }

    if (searchIntent.sensitive) {
      tags.push(<Tag key="sensitive" color="red">敏感数据</Tag>);
    }

    if (searchIntent.time_filter === 'recent') {
      tags.push(<Tag key="time" color="green">最近更新</Tag>);
    }

    if (tags.length > 0) {
      return (
        <div className="ai-search-intent">
          <span style={{ marginRight: 8, color: '#666' }}>AI 理解：</span>
          {tags}
        </div>
      );
    }

    return null;
  };

  // 渲染相关性分数
  const renderRelevanceScore = (score: number) => {
    const percentage = Math.min(Math.round(score), 100);
    const color = percentage >= 80 ? '#52c41a' : percentage >= 50 ? '#faad14' : '#999';
    return (
      <Tooltip title={`相关性: ${percentage}%`}>
        <Tag color={color} style={{ margin: 0 }}>
          {percentage}%
        </Tag>
      </Tooltip>
    );
  };

  return (
    <div className="asset-ai-search">
      {/* 搜索输入框 */}
      <Card className="search-card" bordered={false}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div className="search-header">
            <RobotOutlined className="ai-icon" />
            <span className="search-title">AI 智能搜索</span>
            <Tooltip title="用自然语言描述你要找的数据">
              <SearchOutlined style={{ color: '#999' }} />
            </Tooltip>
          </div>

          <AutoComplete
            ref={searchInputRef}
            value={searchQuery}
            onChange={handleInputChange}
            options={autocompleteOptions}
            style={{ width: '100%' }}
            placeholder={placeholder}
            size="large"
            notFoundContent={null}
          >
            <TextArea
              autoSize={{ minRows: 1, maxRows: 4 }}
              placeholder={placeholder}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch(searchQuery);
                }
              }}
            />
          </AutoComplete>

          {searchQuery && (
            <div className="search-actions">
              <Button
                type="primary"
                icon={<SearchOutlined />}
                loading={isSearching}
                onClick={() => handleSearch(searchQuery)}
              >
                搜索
              </Button>
              <Button
                icon={<CloseCircleFilled />}
                onClick={handleClear}
              >
                清空
              </Button>
            </div>
          )}

          {/* 示例查询 */}
          {!searchQuery && !showTrendingPanel && (
            <div className="example-queries">
              <div style={{ marginBottom: 8, color: '#666' }}>试试这样搜索：</div>
              <Space wrap>
                {[
                  '用户订单相关的表',
                  '包含手机号的数据',
                  '最近更新的客户表',
                  '机密级别的财务数据'
                ].map((example, index) => (
                  <Tag
                    key={index}
                    className="example-tag"
                    onClick={() => handleInputChange(example)}
                  >
                    {example}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
        </Space>
      </Card>

      {/* 搜索意图 */}
      {searchIntent && renderIntentTags()}

      {/* 搜索结果 */}
      {searchResults.length > 0 && (
        <Card
          title={
            <Space>
              <span>搜索结果</span>
              <Tag color="blue">{searchResults.length}</Tag>
            </Space>
          }
          className="results-card"
          bordered={false}
        >
          <List
            dataSource={searchResults}
            renderItem={(result, index) => (
              <List.Item
                key={index}
                className="result-item"
                onClick={() => handleResultClick(result)}
              >
                <List.Item.Meta
                  avatar={
                    <div className="result-avatar">
                      {index + 1}
                    </div>
                  }
                  title={
                    <Space>
                      <span className="result-name">{result.asset.name}</span>
                      {renderRelevanceScore(result.relevance_score)}
                      <Tag>{result.asset.type}</Tag>
                      {result.asset.tags?.slice(0, 3).map(tag => (
                        <Tag key={tag} color="default">{tag}</Tag>
                      ))}
                    </Space>
                  }
                  description={
                    <div>
                      <div style={{ marginBottom: 4 }}>
                        {result.asset.description}
                      </div>
                      {result.matched_fields.length > 0 && (
                        <Space size={4}>
                          <span style={{ color: '#999', fontSize: 12 }}>匹配:</span>
                          {result.matched_fields.map(field => (
                            <Tag key={field} color="cyan" style={{ fontSize: '12px' }}>
                              {field === 'name' && '名称'}
                              {field === 'description' && '描述'}
                              {field === 'table_name' && '表名'}
                            </Tag>
                          ))}
                        </Space>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 热门资产 */}
      {showTrending && !searchQuery && searchResults.length === 0 && (
        <Card
          title={
            <Space>
              <FireOutlined style={{ color: '#ff4d4f' }} />
              <span>热门资产</span>
            </Space>
          }
          bordered={false}
          loading={trendingLoading}
        >
          {trendingData?.data?.data?.assets?.length > 0 ? (
            <List
              dataSource={trendingData.data.data.assets}
              renderItem={(asset: any, index: number) => (
                <List.Item
                  key={asset.asset_id}
                  onClick={() => onResultSelect?.(asset)}
                  style={{ cursor: 'pointer' }}
                >
                  <List.Item.Meta
                    avatar={
                      <div className={`trending-rank rank-${Math.min(index + 1, 3)}`}>
                        {index + 1}
                      </div>
                    }
                    title={
                      <Space>
                        <span>{asset.name}</span>
                        <Tag>{asset.type}</Tag>
                      </Space>
                    }
                    description={
                      <Space>
                        <span>访问 {asset.view_count || 0}</span>
                        <span>使用 {asset.usage_count || 0}</span>
                        <span>收藏 {asset.collect_count || 0}</span>
                      </Space>
                    }
                  />
                  <StarOutlined style={{ color: '#faad14' }} />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无热门资产" />
          )}
        </Card>
      )}

      {/* 加载状态 */}
      {isSearching && (
        <div className="search-loading">
          <Spin tip="AI 正在理解你的需求..." />
        </div>
      )}
    </div>
  );
};

export default AssetAISearch;
