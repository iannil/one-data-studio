/**
 * Playwright 全局设置
 * 在所有测试运行前执行
 */

import { FullConfig } from '@playwright/test';
import { logger } from './helpers/logger';

async function globalSetup(config: FullConfig) {
  logger.section('ONE-DATA-STUDIO E2E 测试 - 全局设置');

  // 输出环境信息
  logger.info('环境信息:');
  logger.info(`  BASE_URL: ${process.env.BASE_URL || 'http://localhost:3000'}`);
  logger.info(`  AGENT_API_URL: ${process.env.AGENT_API_URL || 'http://localhost:8000'}`);
  logger.info(`  DATA_API_URL: ${process.env.DATA_API_URL || 'http://localhost:8001'}`);
  logger.info(`  MODEL_API_URL: ${process.env.MODEL_API_URL || 'http://localhost:8002'}`);
  logger.info(`  HEADLESS: ${process.env.HEADED === 'true' ? 'false' : 'true'}`);
  logger.info(`  WORKERS: ${process.env.WORKERS || '4'}`);

  // 检查环境变量
  if (!process.env.BASE_URL) {
    logger.warn('BASE_URL 未设置，使用默认值');
  }

  // 可选：在这里进行额外的全局设置
  // 例如：创建全局测试数据、初始化服务等

  logger.success('全局设置完成');
}

export default globalSetup;
