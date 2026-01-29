/**
 * Cube Service 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as model from './cube';

// Mock apiClient
vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from './api';

describe('Cube Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('OpenAI Compatible API', () => {
    it('getModels should call correct endpoint', async () => {
      const mockResponse = {
        object: 'list',
        data: [
          { id: 'model-1', object: 'model', created: 1234567890, owned_by: 'system' },
        ],
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getModels();

      expect(apiClient.get).toHaveBeenCalledWith('/v1/models');
      expect(result).toEqual(mockResponse);
    });

    it('createChatCompletion should call correct endpoint', async () => {
      const mockResponse = {
        id: 'chatcmpl-123',
        object: 'chat.completion',
        created: 1234567890,
        model: 'gpt-4',
        choices: [{ index: 0, message: { role: 'assistant', content: 'Hello!' }, finish_reason: 'stop' }],
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        model: 'gpt-4',
        messages: [{ role: 'user' as const, content: 'Hi' }],
      };
      const result = await model.createChatCompletion(request);

      expect(apiClient.post).toHaveBeenCalledWith('/v1/chat/completions', { ...request, stream: false });
      expect(result).toEqual(mockResponse);
    });

    it('createCompletion should call correct endpoint', async () => {
      const mockResponse = {
        id: 'cmpl-123',
        object: 'text_completion',
        created: 1234567890,
        model: 'gpt-4',
        choices: [{ text: 'Hello!', index: 0, finish_reason: 'stop' }],
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { model: 'gpt-4', prompt: 'Hello' };
      const result = await model.createCompletion(request);

      expect(apiClient.post).toHaveBeenCalledWith('/v1/completions', request);
      expect(result).toEqual(mockResponse);
    });

    it('createEmbeddings should call correct endpoint', async () => {
      const mockResponse = {
        object: 'list',
        data: [{ object: 'embedding', embedding: [0.1, 0.2], index: 0 }],
        model: 'text-embedding-ada-002',
        usage: { prompt_tokens: 5, total_tokens: 5 },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { model: 'text-embedding-ada-002', input: ['Hello'] };
      const result = await model.createEmbeddings(request);

      expect(apiClient.post).toHaveBeenCalledWith('/v1/embeddings', request);
      expect(result).toEqual(mockResponse);
    });

    it('deployModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { model_id: 'model-1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        model_name: 'llama-7b',
        model_path: '/models/llama',
        replicas: 1,
        resources: { gpu: { type: 'A100', count: 1 }, cpu: '4', memory: '16Gi' },
        params: { tensor_parallel_size: 1 },
      };
      const result = await model.deployModel(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/models/deploy', request);
      expect(result).toEqual(mockResponse);
    });

    it('getModelStatus should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { model_id: 'model-1', model_name: 'llama', status: 'running', endpoint: '/v1' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getModelStatus('model-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/models/model-1/status');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Notebook API', () => {
    it('getNotebooks should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { notebooks: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getNotebooks({ status: 'running' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/notebooks', { params: { status: 'running' } });
      expect(result).toEqual(mockResponse);
    });

    it('getNotebook should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { notebook_id: 'nb-1', name: 'Test' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getNotebook('nb-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/notebooks/nb-1');
      expect(result).toEqual(mockResponse);
    });

    it('createNotebook should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { notebook_id: 'nb-new', url: 'http://localhost' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'New Notebook',
        image: 'jupyter/scipy-notebook',
        resources: { cpu: '2', memory: '4Gi' },
      };
      const result = await model.createNotebook(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/notebooks', request);
      expect(result).toEqual(mockResponse);
    });

    it('startNotebook should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { url: 'http://localhost' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.startNotebook('nb-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/notebooks/nb-1/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopNotebook should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.stopNotebook('nb-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/notebooks/nb-1/stop');
      expect(result).toEqual(mockResponse);
    });

    it('deleteNotebook should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteNotebook('nb-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/notebooks/nb-1');
      expect(result).toEqual(mockResponse);
    });

    it('getNotebookImages should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { images: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getNotebookImages();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/notebooks/images');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Experiments API', () => {
    it('getExperiments should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { experiments: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getExperiments({ project: 'test-project' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/experiments', { params: { project: 'test-project' } });
      expect(result).toEqual(mockResponse);
    });

    it('getExperiment should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { experiment_id: 'exp-1', name: 'Test' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getExperiment('exp-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/experiments/exp-1');
      expect(result).toEqual(mockResponse);
    });

    it('createExperiment should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { experiment_id: 'exp-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { name: 'New Experiment', project: 'test-project' };
      const result = await model.createExperiment(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/experiments', request);
      expect(result).toEqual(mockResponse);
    });

    it('stopExperiment should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.stopExperiment('exp-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/experiments/exp-1/stop');
      expect(result).toEqual(mockResponse);
    });

    it('deleteExperiment should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteExperiment('exp-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/experiments/exp-1');
      expect(result).toEqual(mockResponse);
    });

    it('getExperimentMetrics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: [] };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getExperimentMetrics('exp-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/experiments/exp-1/metrics');
      expect(result).toEqual(mockResponse);
    });

    it('getExperimentLogs should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { logs: 'test logs' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getExperimentLogs('exp-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/experiments/exp-1/logs');
      expect(result).toEqual(mockResponse);
    });

    it('compareExperiments should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { experiments: [] } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.compareExperiments(['exp-1', 'exp-2']);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/experiments/compare', { experiment_ids: ['exp-1', 'exp-2'] });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Registered Models API', () => {
    it('getRegisteredModels should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { models: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getRegisteredModels({ framework: 'pytorch' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/models/registered', { params: { framework: 'pytorch' } });
      expect(result).toEqual(mockResponse);
    });

    it('getRegisteredModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { model_id: 'model-1', name: 'Test' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getRegisteredModel('model-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/models/registered/model-1');
      expect(result).toEqual(mockResponse);
    });

    it('registerModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { model_id: 'model-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'New Model',
        version: '1.0',
        framework: 'pytorch',
        uri: 's3://models/new-model',
      };
      const result = await model.registerModel(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/models/registered', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateRegisteredModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { model_id: 'model-1' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const result = await model.updateRegisteredModel('model-1', { name: 'Updated' });

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/models/registered/model-1', { name: 'Updated' });
      expect(result).toEqual(mockResponse);
    });

    it('deleteRegisteredModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteRegisteredModel('model-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/models/registered/model-1');
      expect(result).toEqual(mockResponse);
    });

    it('getModelVersions should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { versions: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getModelVersions('test-model');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/models/registered/test-model/versions');
      expect(result).toEqual(mockResponse);
    });

    it('setModelStage should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.setModelStage('model-1', '1.0', 'production');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/models/registered/model-1/versions/1.0/stage', { stage: 'production' });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Training Jobs API', () => {
    it('getTrainingJobs should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { jobs: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getTrainingJobs({ status: 'running' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/training/jobs', { params: { status: 'running' } });
      expect(result).toEqual(mockResponse);
    });

    it('getTrainingJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'job-1', status: 'running' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getTrainingJob('job-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/training/jobs/job-1');
      expect(result).toEqual(mockResponse);
    });

    it('createTrainingJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'job-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'Training Job',
        project: 'test-project',
        model_name: 'test-model',
        framework: 'pytorch',
        hyperparameters: { lr: 0.001 },
        resources: { cpu: 4, memory: '16Gi' },
      };
      const result = await model.createTrainingJob(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/training/jobs', request);
      expect(result).toEqual(mockResponse);
    });

    it('stopTrainingJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.stopTrainingJob('job-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/training/jobs/job-1/stop');
      expect(result).toEqual(mockResponse);
    });

    it('deleteTrainingJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteTrainingJob('job-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/training/jobs/job-1');
      expect(result).toEqual(mockResponse);
    });

    it('getTrainingJobLogs should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { logs: 'test logs' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getTrainingJobLogs('job-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/training/jobs/job-1/logs');
      expect(result).toEqual(mockResponse);
    });

    it('getTrainingJobMetrics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { metrics: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getTrainingJobMetrics('job-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/training/jobs/job-1/metrics');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Serving Services API', () => {
    it('getServingServices should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { services: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getServingServices({ status: 'running' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/serving/services', { params: { status: 'running' } });
      expect(result).toEqual(mockResponse);
    });

    it('getServingService should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-1', status: 'running' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getServingService('svc-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/serving/services/svc-1');
      expect(result).toEqual(mockResponse);
    });

    it('createServingService should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-new', endpoint: '/v1/models/test' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'Test Service',
        model_id: 'model-1',
        model_version: '1.0',
        replicas: 1,
        resources: { cpu: '2', memory: '4Gi' },
      };
      const result = await model.createServingService(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/serving/services', request);
      expect(result).toEqual(mockResponse);
    });

    it('startServingService should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.startServingService('svc-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/serving/services/svc-1/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopServingService should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.stopServingService('svc-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/serving/services/svc-1/stop');
      expect(result).toEqual(mockResponse);
    });

    it('deleteServingService should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteServingService('svc-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/serving/services/svc-1');
      expect(result).toEqual(mockResponse);
    });

    it('scaleServingService should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.scaleServingService('svc-1', { replicas: 3 });

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/serving/services/svc-1/scale', { replicas: 3 });
      expect(result).toEqual(mockResponse);
    });

    it('getServingServiceMetrics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: [] };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getServingServiceMetrics('svc-1', '1h');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/serving/services/svc-1/metrics', { params: { period: '1h' } });
      expect(result).toEqual(mockResponse);
    });

    it('getServingServiceLogs should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { logs: 'test logs' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getServingServiceLogs('svc-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/serving/services/svc-1/logs');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Resources API', () => {
    it('getGPUResources should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { gpus: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getGPUResources();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/resources/gpu');
      expect(result).toEqual(mockResponse);
    });

    it('getResourcePools should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { pools: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getResourcePools();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/resources/pools');
      expect(result).toEqual(mockResponse);
    });

    it('getResourceQuota should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { user_id: 'user-1', quota: {}, used: {} } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getResourceQuota('user-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/resources/quota', { params: { user_id: 'user-1' } });
      expect(result).toEqual(mockResponse);
    });

    it('getCostAnalysis should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { period_start: '', period_end: '', total_cost: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getCostAnalysis({ period_start: '2024-01-01' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/resources/costs', { params: { period_start: '2024-01-01' } });
      expect(result).toEqual(mockResponse);
    });

    it('getResourceOverview should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { total_gpu: 8, used_gpu: 4 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getResourceOverview();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/resources/overview');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('AIHub API', () => {
    it('getHubModels should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { models: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getHubModels({ task_type: 'nlp' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/hub/models', { params: { task_type: 'nlp' } });
      expect(result).toEqual(mockResponse);
    });

    it('getHubModelDetail should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { model_id: 'hub-1', name: 'Test' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getHubModelDetail('hub-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/hub/models/hub-1');
      expect(result).toEqual(mockResponse);
    });

    it('deployHubModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const config = {
        model_id: 'hub-1',
        resources: { gpu_type: 'A100', gpu_count: 1, cpu: '4', memory: '16Gi' },
        replicas: 1,
      };
      const result = await model.deployHubModel('hub-1', config);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/hub/models/hub-1/deploy', config);
      expect(result).toEqual(mockResponse);
    });

    it('downloadHubModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { download_url: 'https://...' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.downloadHubModel('hub-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/hub/models/hub-1/download');
      expect(result).toEqual(mockResponse);
    });

    it('getHubCategories should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { categories: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getHubCategories();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/hub/categories');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Pipeline API', () => {
    it('getPipelineTemplates should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { templates: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getPipelineTemplates({ category: 'training' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/pipelines/templates', { params: { category: 'training' } });
      expect(result).toEqual(mockResponse);
    });

    it('getPipelines should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { pipelines: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getPipelines({ status: 'active' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/pipelines', { params: { status: 'active' } });
      expect(result).toEqual(mockResponse);
    });

    it('getPipeline should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { pipeline_id: 'pl-1', name: 'Test' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getPipeline('pl-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/pipelines/pl-1');
      expect(result).toEqual(mockResponse);
    });

    it('createPipeline should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { pipeline_id: 'pl-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { name: 'New Pipeline', nodes: [], edges: [] };
      const result = await model.createPipeline(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/pipelines', request);
      expect(result).toEqual(mockResponse);
    });

    it('updatePipeline should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { pipeline_id: 'pl-1' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const result = await model.updatePipeline('pl-1', { name: 'Updated' });

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/pipelines/pl-1', { name: 'Updated' });
      expect(result).toEqual(mockResponse);
    });

    it('deletePipeline should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deletePipeline('pl-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/pipelines/pl-1');
      expect(result).toEqual(mockResponse);
    });

    it('executePipeline should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { execution_id: 'exec-1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.executePipeline('pl-1', { param1: 'value1' });

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/pipelines/pl-1/execute', { variables: { param1: 'value1' } });
      expect(result).toEqual(mockResponse);
    });

    it('getPipelineExecutions should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { executions: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getPipelineExecutions('pl-1', { status: 'completed' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/pipelines/pl-1/executions', { params: { status: 'completed' } });
      expect(result).toEqual(mockResponse);
    });

    it('getPipelineExecution should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { execution_id: 'exec-1', status: 'completed' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getPipelineExecution('exec-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/pipelines/executions/exec-1');
      expect(result).toEqual(mockResponse);
    });

    it('stopPipelineExecution should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.stopPipelineExecution('exec-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/pipelines/executions/exec-1/stop');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('LLM Fine-tuning API', () => {
    it('getFineTuningJobs should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { jobs: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getFineTuningJobs({ status: 'running' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/llm/tuning', { params: { status: 'running' } });
      expect(result).toEqual(mockResponse);
    });

    it('getFineTuningJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'ft-1', status: 'running' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getFineTuningJob('ft-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/llm/tuning/ft-1');
      expect(result).toEqual(mockResponse);
    });

    it('createFineTuningJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'ft-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'LoRA Fine-tuning',
        base_model: 'llama-7b',
        method: 'lora' as const,
        dataset_id: 'ds-1',
        config: { learning_rate: 1e-4, batch_size: 4, num_epochs: 3 },
        resources: { gpu_type: 'A100', gpu_count: 1, cpu: '4', memory: '32Gi' },
      };
      const result = await model.createFineTuningJob(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/llm/tuning', request);
      expect(result).toEqual(mockResponse);
    });

    it('startFineTuningJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.startFineTuningJob('ft-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/llm/tuning/ft-1/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopFineTuningJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.stopFineTuningJob('ft-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/llm/tuning/ft-1/stop');
      expect(result).toEqual(mockResponse);
    });

    it('deleteFineTuningJob should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteFineTuningJob('ft-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/llm/tuning/ft-1');
      expect(result).toEqual(mockResponse);
    });

    it('getFineTuningMetrics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { metrics: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getFineTuningMetrics('ft-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/llm/tuning/ft-1/metrics');
      expect(result).toEqual(mockResponse);
    });

    it('getFineTuningDatasets should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { datasets: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getFineTuningDatasets({ format: 'jsonl' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/llm/datasets', { params: { format: 'jsonl' } });
      expect(result).toEqual(mockResponse);
    });

    it('exportModel should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { export_id: 'exp-1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.exportModel('ft-1', 'safetensors');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/llm/tuning/ft-1/export', { format: 'safetensors' });
      expect(result).toEqual(mockResponse);
    });

    it('getExportStatus should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { export_id: 'exp-1', status: 'completed' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getExportStatus('exp-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/llm/exports/exp-1');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('SQL Lab API', () => {
    it('getSqlLabConnections should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { connections: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getSqlLabConnections();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/cube/sql-lab/connections');
      expect(result).toEqual(mockResponse);
    });

    it('executeSqlQuery should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { query_id: 'q-1', columns: [], rows: [] } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { database_id: 'db-1', sql: 'SELECT * FROM users' };
      const result = await model.executeSqlQuery(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/cube/sql-lab/execute', request);
      expect(result).toEqual(mockResponse);
    });

    it('getQueryResult should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { query_id: 'q-1', columns: [], rows: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getQueryResult('q-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/cube/sql-lab/queries/q-1/result');
      expect(result).toEqual(mockResponse);
    });

    it('cancelQuery should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.cancelQuery('q-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/cube/sql-lab/queries/q-1/cancel');
      expect(result).toEqual(mockResponse);
    });

    it('getQueryHistory should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { history: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getQueryHistory({ database_id: 'db-1' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/cube/sql-lab/history', { params: { database_id: 'db-1' } });
      expect(result).toEqual(mockResponse);
    });

    it('getSavedQueries should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { queries: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getSavedQueries({ search: 'test' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/cube/sql-lab/saved', { params: { search: 'test' } });
      expect(result).toEqual(mockResponse);
    });

    it('saveQuery should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { saved_query_id: 'sq-1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { name: 'My Query', sql: 'SELECT * FROM users', database_id: 'db-1' };
      const result = await model.saveQuery(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/cube/sql-lab/saved', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteSavedQuery should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await model.deleteSavedQuery('sq-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/cube/sql-lab/saved/sq-1');
      expect(result).toEqual(mockResponse);
    });

    it('getSqlLabTables should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { tables: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getSqlLabTables('db-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/cube/sql-lab/connections/db-1/tables');
      expect(result).toEqual(mockResponse);
    });

    it('getSqlLabTableSchema should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { columns: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getSqlLabTableSchema('db-1', 'users');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/cube/sql-lab/connections/db-1/tables/users/schema');
      expect(result).toEqual(mockResponse);
    });

    it('formatSql should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { formatted_sql: 'SELECT *\nFROM users' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.formatSql('SELECT * FROM users');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/cube/sql-lab/format', { sql: 'SELECT * FROM users' });
      expect(result).toEqual(mockResponse);
    });

    it('validateSqlSyntax should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { valid: true } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await model.validateSqlSyntax('db-1', 'SELECT * FROM users');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/cube/sql-lab/validate', { database_id: 'db-1', sql: 'SELECT * FROM users' });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Monitoring API', () => {
    it('getTrainingMetricsRealtime should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'job-1', metrics: {} } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getTrainingMetricsRealtime('job-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/training/job-1/metrics');
      expect(result).toEqual(mockResponse);
    });

    it('getSystemMetrics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { timestamp: '', cpu: {}, memory: {}, disk: {}, network: {}, gpu: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getSystemMetrics();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/system');
      expect(result).toEqual(mockResponse);
    });

    it('getAlertRules should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rules: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getAlertRules({ enabled: true });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/alerts/rules', { params: { enabled: true } });
      expect(result).toEqual(mockResponse);
    });

    it('createAlertRule should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rule_id: 'rule-1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'GPU Alert',
        metric_type: 'gpu_utilization' as const,
        condition: 'greater_than' as const,
        threshold: 90,
        severity: 'warning' as const,
        target_type: 'resource' as const,
        notification_channels: ['email' as const],
      };
      const result = await model.createAlertRule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/monitoring/alerts/rules', request);
      expect(result).toEqual(mockResponse);
    });

    it('getDashboards should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { dashboards: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getDashboards({ is_public: true });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/dashboards', { params: { is_public: true } });
      expect(result).toEqual(mockResponse);
    });

    it('getMetricsOverview should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { active_jobs: 5, active_services: 3 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await model.getMetricsOverview();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/overview');
      expect(result).toEqual(mockResponse);
    });
  });
});
