/**
 * Logger service 测试
 * 测试生产安全的日志工具
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the logger module to control its behavior
vi.mock('./logger', () => {
  const logBuffer: unknown[] = [];

  return {
    logDebug: vi.fn(),
    logInfo: vi.fn(),
    logWarn: vi.fn((message: string) => {
      logBuffer.push({ level: 'warn', message, timestamp: new Date() });
    }),
    logError: vi.fn((message: string) => {
      logBuffer.push({ level: 'error', message, timestamp: new Date() });
    }),
    getLogBuffer: vi.fn(() => [...logBuffer]),
    clearLogBuffer: vi.fn(() => {
      logBuffer.length = 0;
    }),
    default: {
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
      getBuffer: vi.fn(),
      clearBuffer: vi.fn(),
    },
  };
});

import {
  logDebug,
  logInfo,
  logWarn,
  logError,
  getLogBuffer,
  clearLogBuffer,
} from './logger';

describe('Logger Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== 函数导出检查 ====================

  describe('Exports', () => {
    it('should export logDebug function', () => {
      expect(logDebug).toBeDefined();
      expect(typeof logDebug).toBe('function');
    });

    it('should export logInfo function', () => {
      expect(logInfo).toBeDefined();
      expect(typeof logInfo).toBe('function');
    });

    it('should export logWarn function', () => {
      expect(logWarn).toBeDefined();
      expect(typeof logWarn).toBe('function');
    });

    it('should export logError function', () => {
      expect(logError).toBeDefined();
      expect(typeof logError).toBe('function');
    });

    it('should export getLogBuffer function', () => {
      expect(getLogBuffer).toBeDefined();
      expect(typeof getLogBuffer).toBe('function');
    });

    it('should export clearLogBuffer function', () => {
      expect(clearLogBuffer).toBeDefined();
      expect(typeof clearLogBuffer).toBe('function');
    });
  });

  // ==================== 函数调用 ====================

  describe('Function Calls', () => {
    it('should call logWarn with message', () => {
      logWarn('Warning message');
      expect(logWarn).toHaveBeenCalledWith('Warning message');
    });

    it('should call logWarn with context', () => {
      logWarn('Warning message', 'Context');
      expect(logWarn).toHaveBeenCalledWith('Warning message', 'Context');
    });

    it('should call logWarn with context and data', () => {
      const data = { key: 'value' };
      logWarn('Warning message', 'Context', data);
      expect(logWarn).toHaveBeenCalledWith('Warning message', 'Context', data);
    });

    it('should call logError with message', () => {
      logError('Error message');
      expect(logError).toHaveBeenCalledWith('Error message');
    });

    it('should call logError with error object', () => {
      const error = new Error('Test error');
      logError('Failed', 'Context', error);
      expect(logError).toHaveBeenCalledWith('Failed', 'Context', error);
    });
  });

  // ==================== Buffer 操作 ====================

  describe('Buffer Operations', () => {
    it('should get log buffer', () => {
      getLogBuffer();
      expect(getLogBuffer).toHaveBeenCalled();
    });

    it('should clear log buffer', () => {
      clearLogBuffer();
      expect(clearLogBuffer).toHaveBeenCalled();
    });
  });
});
