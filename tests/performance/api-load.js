/**
 * ONE-DATA-STUDIO API 性能测试脚本
 * Sprint 10: 性能基准测试
 *
 * 使用 k6 进行 API 负载测试
 * 运行: k6 run tests/performance/api-load.js
 *
 * 测试目标:
 * - API P95 响应时间 < 500ms
 * - 支持 100+ 并发用户
 * - 系统稳定性验证
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";

// 自定义指标
const apiErrors = new Counter('api_errors');
const apiSuccessRate = new Rate('api_success_rate');
const apiLatency = new Trend('api_latency', true);

// 环境配置
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';
const DATA_URL = __ENV.DATA_URL || 'http://localhost:8080';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

// 测试配置
export const options = {
  // 阶段配置 - 逐步增加负载
  stages: [
    { duration: '1m', target: 10 },   // 预热：1分钟内增加到 10 用户
    { duration: '3m', target: 50 },   // 加载：3分钟内增加到 50 用户
    { duration: '5m', target: 100 },  // 峰值：5分钟内增加到 100 用户
    { duration: '3m', target: 100 },  // 保持：维持 100 用户 3 分钟
    { duration: '2m', target: 50 },   // 降载：2分钟内降到 50 用户
    { duration: '1m', target: 0 },    // 冷却：1分钟内降到 0
  ],

  // 阈值配置 - 性能验收标准
  thresholds: {
    'http_req_duration': ['p(95)<500'],     // 95% 请求 < 500ms
    'http_req_duration{api:health}': ['p(99)<100'],  // 健康检查 < 100ms
    'http_req_duration{api:chat}': ['p(95)<2000'],   // 聊天接口 < 2s
    'api_success_rate': ['rate>0.95'],      // 成功率 > 95%
    'http_req_failed': ['rate<0.05'],       // 失败率 < 5%
  },

  // 其他配置
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
  userAgent: 'K6PerformanceTest/1.0',
};

// 请求头
const headers = {
  'Content-Type': 'application/json',
  'Authorization': AUTH_TOKEN ? `Bearer ${AUTH_TOKEN}` : '',
};

// 测试数据
const testData = {
  chatMessage: '你好，请介绍一下 ONE-DATA-STUDIO 平台的主要功能',
  sqlQuestion: '查询最近一个月的订单总金额',
  ragQuestion: '如何配置工作流的执行调度？',
};

// 主测试函数
export default function () {
  // 随机选择测试场景
  const scenarios = [
    () => healthCheck(),
    () => listWorkflows(),
    () => listDatasets(),
    () => testChat(),
    () => listConversations(),
    () => listDocuments(),
  ];

  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();

  sleep(1); // 模拟用户思考时间
}

// ==================== 测试场景 ====================

// 健康检查 - 轻量级请求
function healthCheck() {
  group('Health Check', function () {
    const res = http.get(`${BASE_URL}/api/v1/health`, {
      tags: { api: 'health' },
    });

    const success = check(res, {
      'health check status is 200': (r) => r.status === 200,
      'health check response time < 100ms': (r) => r.timings.duration < 100,
      'health check has valid body': (r) => r.json('code') === 0,
    });

    apiSuccessRate.add(success);
    apiLatency.add(res.timings.duration, { api: 'health' });

    if (!success) {
      apiErrors.add(1, { api: 'health' });
    }
  });
}

// 列出工作流
function listWorkflows() {
  group('List Workflows', function () {
    const res = http.get(`${BASE_URL}/api/v1/workflows`, {
      headers,
      tags: { api: 'workflows' },
    });

    const success = check(res, {
      'workflows status is 200': (r) => r.status === 200,
      'workflows response time < 500ms': (r) => r.timings.duration < 500,
      'workflows has data': (r) => r.json('data') !== null,
    });

    apiSuccessRate.add(success);
    apiLatency.add(res.timings.duration, { api: 'workflows' });

    if (!success) {
      apiErrors.add(1, { api: 'workflows' });
    }
  });
}

// 列出数据集（Data API）
function listDatasets() {
  group('List Datasets', function () {
    const res = http.get(`${DATA_URL}/api/v1/datasets`, {
      headers,
      tags: { api: 'datasets' },
    });

    const success = check(res, {
      'datasets status is 200': (r) => r.status === 200,
      'datasets response time < 500ms': (r) => r.timings.duration < 500,
    });

    apiSuccessRate.add(success);
    apiLatency.add(res.timings.duration, { api: 'datasets' });

    if (!success) {
      apiErrors.add(1, { api: 'datasets' });
    }
  });
}

// 聊天接口测试
function testChat() {
  group('Chat API', function () {
    const payload = JSON.stringify({
      message: testData.chatMessage,
      model: 'gpt-4o-mini',
      temperature: 0.7,
      max_tokens: 500,
    });

    const res = http.post(`${BASE_URL}/api/v1/chat`, payload, {
      headers,
      tags: { api: 'chat' },
      timeout: '30s',
    });

    const success = check(res, {
      'chat status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'chat response time < 10s': (r) => r.timings.duration < 10000,
    });

    apiSuccessRate.add(success);
    apiLatency.add(res.timings.duration, { api: 'chat' });

    if (!success) {
      apiErrors.add(1, { api: 'chat' });
    }
  });
}

// 列出会话
function listConversations() {
  group('List Conversations', function () {
    const res = http.get(`${BASE_URL}/api/v1/conversations`, {
      headers,
      tags: { api: 'conversations' },
    });

    const success = check(res, {
      'conversations status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'conversations response time < 500ms': (r) => r.timings.duration < 500,
    });

    apiSuccessRate.add(success);
    apiLatency.add(res.timings.duration, { api: 'conversations' });

    if (!success) {
      apiErrors.add(1, { api: 'conversations' });
    }
  });
}

// 列出文档
function listDocuments() {
  group('List Documents', function () {
    const res = http.get(`${BASE_URL}/api/v1/documents`, {
      headers,
      tags: { api: 'documents' },
    });

    const success = check(res, {
      'documents status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'documents response time < 500ms': (r) => r.timings.duration < 500,
    });

    apiSuccessRate.add(success);
    apiLatency.add(res.timings.duration, { api: 'documents' });

    if (!success) {
      apiErrors.add(1, { api: 'documents' });
    }
  });
}

// ==================== 报告生成 ====================

export function handleSummary(data) {
  return {
    "tests/performance/results/api-load-summary.html": htmlReport(data),
    stdout: textSummary(data, { indent: "  ", enableColors: true }),
  };
}

// 文本摘要
function textSummary(data, opts) {
  const lines = [];
  lines.push('');
  lines.push('=====================================');
  lines.push('  ONE-DATA-STUDIO Performance Report');
  lines.push('=====================================');
  lines.push('');

  // 请求统计
  const reqs = data.metrics.http_reqs;
  if (reqs) {
    lines.push(`Total Requests: ${reqs.values.count}`);
    lines.push(`Request Rate: ${(reqs.values.rate || 0).toFixed(2)}/s`);
  }

  // 延迟统计
  const duration = data.metrics.http_req_duration;
  if (duration) {
    lines.push('');
    lines.push('Response Time:');
    lines.push(`  Average: ${duration.values.avg.toFixed(2)}ms`);
    lines.push(`  Median:  ${duration.values.med.toFixed(2)}ms`);
    lines.push(`  P90:     ${duration.values['p(90)'].toFixed(2)}ms`);
    lines.push(`  P95:     ${duration.values['p(95)'].toFixed(2)}ms`);
    lines.push(`  P99:     ${duration.values['p(99)'].toFixed(2)}ms`);
    lines.push(`  Max:     ${duration.values.max.toFixed(2)}ms`);
  }

  // 成功率
  const successRate = data.metrics.api_success_rate;
  if (successRate) {
    lines.push('');
    lines.push(`Success Rate: ${(successRate.values.rate * 100).toFixed(2)}%`);
  }

  // 错误数
  const errors = data.metrics.api_errors;
  if (errors) {
    lines.push(`Total Errors: ${errors.values.count}`);
  }

  lines.push('');
  lines.push('=====================================');

  return lines.join('\n');
}
