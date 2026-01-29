/**
 * Bisheng Service 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as agentService from './bisheng';

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

describe('Bisheng Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Workflow API', () => {
    it('getWorkflows should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { workflows: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getWorkflows();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/workflows');
      expect(result).toEqual(mockResponse);
    });

    it('getWorkflow should call correct endpoint with id', async () => {
      const mockResponse = {
        code: 0,
        data: { workflow_id: 'wf-123', name: 'Test Workflow' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getWorkflow('wf-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/workflows/wf-123');
      expect(result).toEqual(mockResponse);
    });

    it('createWorkflow should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { workflow_id: 'wf-new' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'New Workflow',
        type: 'custom' as const,
      };
      const result = await agentService.createWorkflow(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/workflows', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateWorkflow should put to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { workflow_id: 'wf-123' },
      };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { name: 'Updated Workflow' };
      const result = await agentService.updateWorkflow('wf-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/workflows/wf-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteWorkflow should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteWorkflow('wf-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/workflows/wf-123');
      expect(result).toEqual(mockResponse);
    });

    it('startWorkflow should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { execution_id: 'exec-123', workflow_id: 'wf-123', status: 'running' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await agentService.startWorkflow('wf-123', { inputs: { query: 'test' } });

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/workflows/wf-123/start', { inputs: { query: 'test' } });
      expect(result).toEqual(mockResponse);
    });

    it('stopWorkflow should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await agentService.stopWorkflow('wf-123', { execution_id: 'exec-123' });

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/workflows/wf-123/stop', { execution_id: 'exec-123' });
      expect(result).toEqual(mockResponse);
    });

    it('getWorkflowExecutions should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { executions: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getWorkflowExecutions('wf-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/workflows/wf-123/executions?limit=20');
      expect(result).toEqual(mockResponse);
    });

    it('getExecutionLogs should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { logs: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getExecutionLogs('exec-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/executions/exec-123/logs');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Conversation API', () => {
    it('getConversations should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { conversations: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getConversations();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/conversations');
      expect(result).toEqual(mockResponse);
    });

    it('getConversation should call correct endpoint with id', async () => {
      const mockResponse = {
        code: 0,
        data: { conversation_id: 'conv-123', title: 'Test' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getConversation('conv-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/conversations/conv-123');
      expect(result).toEqual(mockResponse);
    });

    it('createConversation should post with title', async () => {
      const mockResponse = {
        code: 0,
        data: { conversation_id: 'conv-new' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await agentService.createConversation('New Chat');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/conversations', { title: 'New Chat' });
      expect(result).toEqual(mockResponse);
    });

    it('deleteConversation should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteConversation('conv-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/conversations/conv-123');
      expect(result).toEqual(mockResponse);
    });

    it('renameConversation should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const result = await agentService.renameConversation('conv-123', 'New Title');

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/conversations/conv-123', { title: 'New Title' });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Document API', () => {
    it('getDocuments should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { documents: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getDocuments();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/documents');
      expect(result).toEqual(mockResponse);
    });

    it('getDocument should call correct endpoint with id', async () => {
      const mockResponse = {
        code: 0,
        data: { doc_id: 'doc-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getDocument('doc-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/documents/doc-123');
      expect(result).toEqual(mockResponse);
    });

    it('deleteDocument should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteDocument('doc-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/documents/doc-123');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Agent API', () => {
    it('listAgentTemplates should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { templates: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.listAgentTemplates();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/agent/templates');
      expect(result).toEqual(mockResponse);
    });

    it('getAgentTemplate should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { template_id: 'tpl-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getAgentTemplate('tpl-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/agent/templates/tpl-123');
      expect(result).toEqual(mockResponse);
    });

    it('runAgent should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { success: true, answer: 'Test answer' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        query: 'Test query',
        agent_type: 'react',
        model: 'gpt-4',
      };
      const result = await agentService.runAgent(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/agent/run', request);
      expect(result).toEqual(mockResponse);
    });

    it('listTools should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { tools: [], total: 0 },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.listTools();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/tools');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Prompt Template API', () => {
    it('getPromptTemplates should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { templates: [], total: 0 },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getPromptTemplates();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/templates', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getPromptTemplate should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { template_id: 'tpl-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getPromptTemplate('tpl-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/templates/tpl-123');
      expect(result).toEqual(mockResponse);
    });

    it('createPromptTemplate should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { template_id: 'tpl-123' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'Test Template',
        content: 'You are a helpful assistant.',
      };
      const result = await agentService.createPromptTemplate(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/templates', request);
      expect(result).toEqual(mockResponse);
    });

    it('updatePromptTemplate should put to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { template_id: 'tpl-123' },
      };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { name: 'Updated Template' };
      const result = await agentService.updatePromptTemplate('tpl-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/templates/tpl-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deletePromptTemplate should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deletePromptTemplate('tpl-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/templates/tpl-123');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Human Task API', () => {
    it('getPendingHumanTasks should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { tasks: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getPendingHumanTasks();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/human-tasks', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getHumanTask should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { task_id: 'task-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getHumanTask('task-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/human-tasks/task-123');
      expect(result).toEqual(mockResponse);
    });

    it('submitHumanTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        approved: true,
        comment: 'Approved',
      };
      const result = await agentService.submitHumanTask('task-123', request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/human-tasks/task-123/submit', request);
      expect(result).toEqual(mockResponse);
    });

    it('getMyTaskStatistics should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { pending_count: 5, approved_count: 10 },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getMyTaskStatistics();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/human-tasks/my-tasks/statistics');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Schedule API', () => {
    it('listSchedules should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { schedules: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.listSchedules('wf-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/workflows/wf-123/schedules');
      expect(result).toEqual(mockResponse);
    });

    it('createSchedule should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { schedule_id: 'sch-123' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await agentService.createSchedule('wf-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/workflows/wf-123/schedules', undefined);
      expect(result).toEqual(mockResponse);
    });

    it('pauseSchedule should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { schedule_id: 'sch-123', paused: true } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await agentService.pauseSchedule('sch-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/schedules/sch-123/pause');
      expect(result).toEqual(mockResponse);
    });

    it('resumeSchedule should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { schedule_id: 'sch-123', paused: false } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await agentService.resumeSchedule('sch-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/schedules/sch-123/resume');
      expect(result).toEqual(mockResponse);
    });

    it('deleteSchedule should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteSchedule('sch-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/schedules/sch-123');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Knowledge Base API', () => {
    it('getKnowledgeBases should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { knowledge_bases: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getKnowledgeBases();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/knowledge-bases', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getKnowledgeBase should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { kb_id: 'kb-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getKnowledgeBase('kb-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/knowledge-bases/kb-123');
      expect(result).toEqual(mockResponse);
    });

    it('deleteKnowledgeBase should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteKnowledgeBase('kb-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/knowledge-bases/kb-123');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('RAG API', () => {
    it('ragQuery should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { answer: 'Test answer', sources: [] },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        query: 'What is AI?',
        collection: 'default',
      };
      const result = await agentService.ragQuery(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/rag/query', request);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Text2SQL API', () => {
    it('text2Sql should post to correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { sql: 'SELECT * FROM users', explanation: 'Selects all users' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        question: 'Show me all users',
        database: 'default',
      };
      const result = await agentService.text2Sql(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/text2sql', request);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Evaluation API', () => {
    it('getEvaluationTasks should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { tasks: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getEvaluationTasks();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/evaluation/tasks', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getEvaluationTask should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { task_id: 'eval-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getEvaluationTask('eval-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/evaluation/tasks/eval-123');
      expect(result).toEqual(mockResponse);
    });

    it('deleteEvaluationTask should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteEvaluationTask('eval-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/evaluation/tasks/eval-123');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('SFT API', () => {
    it('getSFTTasks should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { tasks: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getSFTTasks();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/sft/tasks', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getSFTTask should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { task_id: 'sft-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getSFTTask('sft-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/sft/tasks/sft-123');
      expect(result).toEqual(mockResponse);
    });

    it('deleteSFTTask should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteSFTTask('sft-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/sft/tasks/sft-123');
      expect(result).toEqual(mockResponse);
    });

    it('getBaseModels should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { models: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getBaseModels();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/sft/base-models');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('App API', () => {
    it('getPublishedApps should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { apps: [] },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getPublishedApps();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/apps', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getPublishedApp should call correct endpoint', async () => {
      const mockResponse = {
        code: 0,
        data: { app_id: 'app-123' },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await agentService.getPublishedApp('app-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/apps/app-123');
      expect(result).toEqual(mockResponse);
    });

    it('deleteApp should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await agentService.deleteApp('app-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/apps/app-123');
      expect(result).toEqual(mockResponse);
    });
  });
});
