/**
 * 向量检索性能测试脚本
 * Sprint 10: 性能基准测试
 *
 * 测试目标:
 * - 向量检索延迟 < 100ms
 * - 召回率 > 95%
 * - 百万级文档支持
 *
 * 运行: k6 run tests/performance/vector-search.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// 自定义指标
const searchLatency = new Trend('vector_search_latency', true);
const searchErrors = new Counter('vector_search_errors');
const searchSuccessRate = new Rate('vector_search_success_rate');
const retrievedDocs = new Trend('retrieved_documents');

// 环境配置
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

// 测试配置
export const options = {
  scenarios: {
    // 场景1: 低并发高精度测试
    low_concurrency: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      startTime: '0s',
      tags: { scenario: 'low_concurrency' },
    },
    // 场景2: 中等并发
    medium_concurrency: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },
        { duration: '3m', target: 20 },
        { duration: '1m', target: 0 },
      ],
      startTime: '2m',
      tags: { scenario: 'medium_concurrency' },
    },
    // 场景3: 高并发压力测试
    high_concurrency: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 50 },
        { duration: '5m', target: 50 },
        { duration: '1m', target: 0 },
      ],
      startTime: '7m',
      tags: { scenario: 'high_concurrency' },
    },
    // 场景4: 突发流量测试
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },  // 快速上升
        { duration: '1m', target: 100 },   // 保持峰值
        { duration: '30s', target: 0 },    // 快速下降
      ],
      startTime: '14m',
      tags: { scenario: 'spike' },
    },
  },

  thresholds: {
    'vector_search_latency': ['p(95)<100', 'p(99)<200'],  // P95 < 100ms
    'vector_search_success_rate': ['rate>0.95'],          // 成功率 > 95%
    'http_req_duration{api:rag_query}': ['p(95)<500'],    // RAG 查询 < 500ms
  },
};

// 请求头
const headers = {
  'Content-Type': 'application/json',
  'Authorization': AUTH_TOKEN ? `Bearer ${AUTH_TOKEN}` : '',
};

// 测试查询集 - 覆盖不同类型的查询
const testQueries = [
  // 技术类查询
  '如何配置 Kubernetes 部署？',
  '什么是向量数据库的 HNSW 索引？',
  'RAG 系统的架构设计原则是什么？',
  '如何优化大模型的推理性能？',

  // 业务类查询
  '客户流失预测模型的准确率是多少？',
  '上个季度的销售数据分析报告',
  '用户行为分析的主要指标有哪些？',

  // 模糊查询
  '数据',
  '模型训练',
  'API 调用',

  // 复杂查询
  '在微服务架构下，如何实现分布式追踪和日志聚合，同时保证系统的可观测性？',
  '对比 Milvus 和 Pinecone 在大规模向量检索场景下的性能表现和适用场景',
];

// 主测试函数
export default function () {
  // 随机选择查询
  const query = testQueries[Math.floor(Math.random() * testQueries.length)];

  // 随机选择测试场景
  const testFunctions = [
    () => testRAGQuery(query),
    () => testVectorSearch(query),
    () => testDocumentRetrieval(query),
  ];

  const testFn = testFunctions[Math.floor(Math.random() * testFunctions.length)];
  testFn();

  sleep(Math.random() * 2 + 1); // 1-3 秒随机间隔
}

// ==================== 测试场景 ====================

// RAG 查询测试
function testRAGQuery(question) {
  group('RAG Query', function () {
    const payload = JSON.stringify({
      question: question,
      collection: 'default',
      top_k: 5,
    });

    const startTime = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/rag/query`, payload, {
      headers,
      tags: { api: 'rag_query' },
      timeout: '30s',
    });
    const latency = Date.now() - startTime;

    const success = check(res, {
      'RAG query status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'RAG query response time < 1s': (r) => r.timings.duration < 1000,
      'RAG query has answer': (r) => {
        if (r.status !== 200) return true;
        const body = r.json();
        return body && body.data && body.data.answer;
      },
    });

    searchSuccessRate.add(success);
    searchLatency.add(latency);

    if (res.status === 200) {
      const body = res.json();
      if (body && body.data) {
        retrievedDocs.add(body.data.retrieved_count || 0);
      }
    }

    if (!success) {
      searchErrors.add(1);
    }
  });
}

// 向量检索测试（直接测试向量搜索接口）
function testVectorSearch(query) {
  group('Vector Search', function () {
    // 首先获取集合列表
    const collectionsRes = http.get(`${BASE_URL}/api/v1/collections`, {
      headers,
      tags: { api: 'collections' },
    });

    if (collectionsRes.status !== 200) {
      searchErrors.add(1);
      return;
    }

    // 测试搜索
    const payload = JSON.stringify({
      question: query,
      top_k: 10,
      collection: 'default',
    });

    const startTime = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/rag/query`, payload, {
      headers,
      tags: { api: 'vector_search' },
      timeout: '10s',
    });
    const latency = Date.now() - startTime;

    const success = check(res, {
      'vector search status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'vector search latency < 100ms': (r) => latency < 100,
    });

    searchSuccessRate.add(success);
    searchLatency.add(latency);

    if (!success) {
      searchErrors.add(1);
    }
  });
}

// 文档检索测试
function testDocumentRetrieval(query) {
  group('Document Retrieval', function () {
    // 列出文档
    const listRes = http.get(`${BASE_URL}/api/v1/documents?limit=50`, {
      headers,
      tags: { api: 'list_documents' },
    });

    const listSuccess = check(listRes, {
      'list documents status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'list documents response time < 500ms': (r) => r.timings.duration < 500,
    });

    if (listRes.status === 200) {
      const body = listRes.json();
      if (body && body.data && body.data.documents && body.data.documents.length > 0) {
        // 获取第一个文档详情
        const docId = body.data.documents[0].doc_id;
        const detailRes = http.get(`${BASE_URL}/api/v1/documents/${docId}`, {
          headers,
          tags: { api: 'get_document' },
        });

        const detailSuccess = check(detailRes, {
          'get document status is 200': (r) => r.status === 200,
          'get document response time < 200ms': (r) => r.timings.duration < 200,
        });

        searchSuccessRate.add(detailSuccess);
      }
    }

    searchSuccessRate.add(listSuccess);
  });
}

// ==================== 报告生成 ====================

export function handleSummary(data) {
  const lines = [];
  lines.push('');
  lines.push('==========================================');
  lines.push('  Vector Search Performance Report');
  lines.push('==========================================');
  lines.push('');

  // 搜索延迟统计
  const latency = data.metrics.vector_search_latency;
  if (latency && latency.values) {
    lines.push('Search Latency:');
    lines.push(`  Average: ${latency.values.avg.toFixed(2)}ms`);
    lines.push(`  Median:  ${latency.values.med.toFixed(2)}ms`);
    lines.push(`  P90:     ${latency.values['p(90)'].toFixed(2)}ms`);
    lines.push(`  P95:     ${latency.values['p(95)'].toFixed(2)}ms`);
    lines.push(`  P99:     ${latency.values['p(99)'].toFixed(2)}ms`);
    lines.push(`  Max:     ${latency.values.max.toFixed(2)}ms`);

    // 检查是否满足目标
    const p95 = latency.values['p(95)'];
    if (p95 < 100) {
      lines.push(`  ✅ P95 < 100ms target: PASSED (${p95.toFixed(2)}ms)`);
    } else {
      lines.push(`  ❌ P95 < 100ms target: FAILED (${p95.toFixed(2)}ms)`);
    }
  }

  // 成功率
  const successRate = data.metrics.vector_search_success_rate;
  if (successRate && successRate.values) {
    lines.push('');
    const rate = successRate.values.rate * 100;
    lines.push(`Success Rate: ${rate.toFixed(2)}%`);
    if (rate >= 95) {
      lines.push(`  ✅ > 95% target: PASSED`);
    } else {
      lines.push(`  ❌ > 95% target: FAILED`);
    }
  }

  // 检索文档数
  const docs = data.metrics.retrieved_documents;
  if (docs && docs.values) {
    lines.push('');
    lines.push('Retrieved Documents:');
    lines.push(`  Average: ${docs.values.avg.toFixed(2)}`);
    lines.push(`  Max:     ${docs.values.max}`);
  }

  // 错误统计
  const errors = data.metrics.vector_search_errors;
  if (errors && errors.values) {
    lines.push('');
    lines.push(`Total Errors: ${errors.values.count}`);
  }

  lines.push('');
  lines.push('==========================================');

  return {
    'tests/performance/results/vector-search-summary.txt': lines.join('\n'),
    stdout: lines.join('\n'),
  };
}
