/**
 * Bisheng 服务 (已废弃)
 *
 * 此模块为向后兼容保留，实际功能已迁移到 agent-service.ts (agent_api)
 * 请在新代码中使用 import from '@/services/agent-service' 替代
 *
 * @deprecated Use '@/services/agent-service' instead
 */

// Re-export everything from agent-service.ts
export * from './agent-service';
export { default } from './agent-service';
