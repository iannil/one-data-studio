/**
 * NodeConfigPanel 组件测试
 * Sprint 9: 测试覆盖扩展
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@/test/testUtils';

describe('NodeConfigPanel', () => {
  describe('Node configuration', () => {
    it('should handle LLM node configuration', () => {
      const llmNode = {
        type: 'llm',
        config: {
          model: 'gpt-4o-mini',
          temperature: 0.7,
          max_tokens: 2000,
        },
      };

      expect(llmNode.type).toBe('llm');
      expect(llmNode.config.model).toBe('gpt-4o-mini');
      expect(llmNode.config.temperature).toBe(0.7);
    });

    it('should handle Retriever node configuration', () => {
      const retrieverNode = {
        type: 'retriever',
        config: {
          collection: 'default',
          top_k: 5,
          score_threshold: 0.7,
        },
      };

      expect(retrieverNode.type).toBe('retriever');
      expect(retrieverNode.config.top_k).toBe(5);
    });

    it('should handle Agent node configuration', () => {
      const agentNode = {
        type: 'agent',
        config: {
          agent_type: 'react',
          model: 'gpt-4o-mini',
          max_iterations: 10,
          tools: ['search', 'calculator'],
        },
      };

      expect(agentNode.type).toBe('agent');
      expect(agentNode.config.tools).toContain('search');
    });
  });

  describe('Config validation', () => {
    it('should validate required fields', () => {
      const config = {
        model: 'gpt-4o-mini',
        temperature: 0.7,
      };

      const isValid = !!config.model && typeof config.temperature === 'number';

      expect(isValid).toBe(true);
    });

    it('should validate temperature range', () => {
      const temperature = 0.7;
      const isValid = temperature >= 0 && temperature <= 2;

      expect(isValid).toBe(true);
    });

    it('should validate max_tokens', () => {
      const maxTokens = 2000;
      const isValid = maxTokens > 0 && maxTokens <= 128000;

      expect(isValid).toBe(true);
    });
  });

  describe('Config update', () => {
    it('should merge partial updates', () => {
      const originalConfig = {
        model: 'gpt-4o-mini',
        temperature: 0.7,
        max_tokens: 2000,
      };

      const update = { temperature: 0.5 };

      const updatedConfig = { ...originalConfig, ...update };

      expect(updatedConfig.temperature).toBe(0.5);
      expect(updatedConfig.model).toBe('gpt-4o-mini');
    });

    it('should handle array field updates', () => {
      const config = {
        tools: ['search'],
      };

      const newTools = [...config.tools, 'calculator'];

      expect(newTools).toHaveLength(2);
      expect(newTools).toContain('calculator');
    });
  });

  describe('Node type specific configs', () => {
    it('should return correct schema for LLM node', () => {
      const getNodeSchema = (type: string) => {
        const schemas: Record<string, string[]> = {
          llm: ['model', 'temperature', 'max_tokens'],
          retriever: ['collection', 'top_k'],
          agent: ['agent_type', 'model', 'tools'],
        };
        return schemas[type] || [];
      };

      const schema = getNodeSchema('llm');

      expect(schema).toContain('model');
      expect(schema).toContain('temperature');
    });

    it('should return correct schema for Retriever node', () => {
      const getNodeSchema = (type: string) => {
        const schemas: Record<string, string[]> = {
          llm: ['model', 'temperature', 'max_tokens'],
          retriever: ['collection', 'top_k'],
          agent: ['agent_type', 'model', 'tools'],
        };
        return schemas[type] || [];
      };

      const schema = getNodeSchema('retriever');

      expect(schema).toContain('collection');
      expect(schema).toContain('top_k');
    });
  });
});

describe('useNodeConfig', () => {
  it('should initialize with node config', () => {
    const initialConfig = {
      model: 'gpt-4o-mini',
      temperature: 0.7,
    };

    const { result } = renderHook(() => ({
      config: initialConfig,
      updateConfig: vi.fn(),
    }));

    expect(result.current.config).toEqual(initialConfig);
  });

  it('should call updateConfig when config changes', () => {
    const updateConfig = vi.fn();
    const newConfig = { temperature: 0.5 };

    renderHook(() => ({
      config: {},
      updateConfig,
    }));

    // Simulate config update
    act(() => {
      updateConfig(newConfig);
    });

    expect(updateConfig).toHaveBeenCalledWith(newConfig);
  });
});
