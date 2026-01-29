# Behavior Service 集成文档

## 概述

**Behavior Service** 是用户行为分析服务，负责收集、分析和审计用户在平台上的行为数据。该服务为平台提供用户画像、行为漏斗分析、异常检测等能力。

## 服务信息

| 属性 | 值 |
|------|------|
| **服务名称** | behavior-service |
| **技术栈** | FastAPI + MySQL + Redis |
| **端口** | 8008 |
| **状态** | ✅ 已实现，已部署 |

## 功能模块

### 1. 行为采集 (Behavior Collection)

采集用户在平台上的各类行为事件：

- **页面浏览** (Page Views) - 记录用户访问的页面
- **点击事件** (Click Events) - 记录用户点击操作
- **通用事件** (Custom Events) - 支持自定义行为事件
- **会话跟踪** (Session Tracking) - 跟踪用户会话生命周期

### 2. 用户画像 (User Profiles)

基于行为数据构建用户画像：

- **自动画像生成** - 基于行为模式自动生成用户画像
- **用户分群** - 支持自定义标签分群
- **相似用户** - 识别行为相似的用户
- **活跃度分析** - 分析用户活跃度趋势

### 3. 行为分析 (Behavior Analytics)

提供多维度的行为数据分析：

- **漏斗分析** - 分析用户转化路径
- **留存分析** - 计算用户留存率
- **时段分析** - 按小时统计活动模式
- **功能统计** - 功能模块使用统计

### 4. 行为审计 (Behavior Audit)

安全审计和异常检测：

- **异常检测** - 登录异常、权限异常、行为异常、数据异常
- **规则引擎** - 自定义监控规则
- **审计日志** - 完整的审计日志记录
- **实时告警** - 异常行为实时告警

## API 端点

### 行为采集 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/behaviors/page-view` | POST | 记录页面浏览事件 |
| `/api/v1/behaviors/click` | POST | 记录点击事件 |
| `/api/v1/behaviors/track` | POST | 记录通用行为事件 |
| `/api/v1/behaviors/batch` | POST | 批量记录行为事件 |
| `/api/v1/behaviors/user/{user_id}` | GET | 获取用户行为列表 |
| `/api/v1/behaviors/type/{behavior_type}` | GET | 按类型获取行为 |
| `/api/v1/behaviors/session/start` | POST | 开始用户会话 |
| `/api/v1/behaviors/session/end` | POST | 结束用户会话 |

### 用户画像 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/profiles/user/{user_id}` | GET | 获取/刷新用户画像 |
| `/api/v1/profiles/user/{user_id}/refresh` | POST | 刷新用户画像 |
| `/api/v1/profiles/segment/{segment_tag}` | GET | 按分群标签获取用户 |
| `/api/v1/profiles/segments` | GET | 列出所有分群 |
| `/api/v1/profiles/user/{user_id}/similar` | GET | 获取相似用户 |
| `/api/v1/profiles/activity/user/{user_id}` | GET | 用户活跃度分析 |
| `/api/v1/profiles/activity/modules` | GET | 功能模块使用统计 |
| `/api/v1/profiles/activity/users` | GET | 活跃用户列表 |
| `/api/v1/profiles/activity/hourly` | GET | 按小时活动统计 |
| `/api/v1/profiles/funnel` | POST | 行为漏斗分析 |
| `/api/v1/profiles/retention` | GET | 用户留存率 |
| `/api/v1/profiles/refresh-all` | POST | 批量刷新画像 |

### 行为审计 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/audit/anomalies` | GET | 获取异常行为列表 |
| `/api/v1/audit/anomalies/{id}` | GET | 获取异常详情 |
| `/api/v1/audit/anomalies/{id}/status` | PUT | 更新异常状态 |
| `/api/v1/audit/detect` | POST | 运行异常检测 |
| `/api/v1/audit/audit-log` | GET | 获取审计日志 |
| `/api/v1/audit/rules` | GET | 获取规则列表 |
| `/api/v1/audit/rules` | POST | 创建规则 |
| `/api/v1/audit/rules/{id}` | GET | 获取规则详情 |
| `/api/v1/audit/rules/{id}` | PUT | 更新规则 |
| `/api/v1/audit/rules/{id}` | DELETE | 删除规则 |
| `/api/v1/audit/rules/{id}/toggle` | POST | 启用/禁用规则 |
| `/api/v1/audit/statistics/overview` | GET | 获取统计概览 |

## 部署配置

### Docker Compose

服务已在 `deploy/local/docker-compose.yml` 中配置：

```yaml
behavior-service:
  build:
    context: ../../services/behavior-service
    dockerfile: Dockerfile
  environment:
    DATABASE_URL: mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DATABASE}
    REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
    AUTH_MODE: "false"
  ports:
    - "8008:8008"
  depends_on:
    mysql:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - one-data-network
  restart: unless-stopped
```

### 启动服务

```bash
# 仅启动 Behavior Service
docker-compose -f deploy/local/docker-compose.yml up -d behavior-service

# 启动所有服务
docker-compose -f deploy/local/docker-compose.yml up -d
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | MySQL 数据库连接 | - |
| `REDIS_URL` | Redis 连接 (使用 db 1) | - |
| `AUTH_MODE` | 是否启用认证 | false |

## 数据模型

### UserBehavior

用户行为数据模型：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 主键 |
| `user_id` | String | 用户 ID |
| `session_id` | String | 会话 ID |
| `behavior_type` | String | 行为类型 |
| `page_url` | String | 页面 URL |
| `element_id` | String | 元素 ID |
| `metadata` | JSON | 扩展数据 |
| `timestamp` | DateTime | 行为时间 |

### UserProfile

用户画像数据模型：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 主键 |
| `user_id` | String | 用户 ID |
| `tags` | JSON | 用户标签 |
| `preferences` | JSON | 用户偏好 |
| `activity_score` | Float | 活跃度评分 |
| `last_updated` | DateTime | 更新时间 |

## 与其他服务的集成

### 前端集成

前端页面可通过以下方式集成行为采集：

```typescript
import { behaviorTracker } from '@/services/behavior';

// 页面浏览
behaviorTracker.trackPageView('/datasets');

// 点击事件
behaviorTracker.trackClick('button-submit', { formId: 'login-form' });

// 自定义事件
behaviorTracker.trackEvent('custom_action', { detail: 'value' });
```

### 与 Admin API 集成

行为审计数据可与 Admin API 的审计日志整合：

1. **统一审计日志** - Behavior Service 的审计日志可同步到 Admin API
2. **异常告警** - 异常行为可触发 Admin API 的告警通知
3. **用户画像** - 用户画像数据可丰富用户管理功能

## 使用示例

### 记录行为事件

```bash
curl -X POST http://localhost:8008/api/v1/behaviors/track \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "behavior_type": "click",
    "page_url": "/datasets",
    "element_id": "create-dataset-btn",
    "metadata": {"dataset_name": "test"}
  }'
```

### 获取用户画像

```bash
curl http://localhost:8008/api/v1/profiles/user/user123
```

### 漏斗分析

```bash
curl -X POST http://localhost:8008/api/v1/profiles/funnel \
  -H "Content-Type: application/json" \
  -d '{
    "steps": [
      {"event_type": "page_view", "page_url": "/datasets"},
      {"event_type": "click", "element_id": "create-dataset-btn"},
      {"event_type": "page_view", "page_url": "/datasets/create"}
    ],
    "time_range": "7d"
  }'
```

## 监控指标

| 指标 | 说明 |
|------|------|
| 每日活跃用户 (DAU) | 当日有行为的用户数 |
| 每月活跃用户 (MAU) | 当月有行为的用户数 |
| 平均会话时长 | 用户平均会话持续时间 |
| 跳出率 | 单页面访问比例 |
| 转化率 | 完成目标流程的用户比例 |

## 故障排查

### 服务无法启动

1. 检查 MySQL 连接是否正常
2. 检查 Redis 连接是否正常
3. 查看服务日志：`docker-compose logs behavior-service`

### 行为数据未记录

1. 检查前端 SDK 是否正确初始化
2. 检查网络请求是否成功
3. 查看服务日志中的错误信息

## 参考资料

- FastAPI 文档: https://fastapi.tiangolo.com/
- 用户行为分析最佳实践
- 数据隐私与合规要求
