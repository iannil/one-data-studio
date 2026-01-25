/**
 * Playwright 全局设置
 * 在所有测试运行前执行
 */

import { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('='.repeat(60));
  console.log('ONE-DATA-STUDIO E2E 测试 - 全局设置');
  console.log('='.repeat(60));

  // 输出环境信息
  console.log('环境信息:');
  console.log(`  BASE_URL: ${process.env.BASE_URL || 'http://localhost:3000'}`);
  console.log(`  BISHENG_API_URL: ${process.env.BISHENG_API_URL || 'http://localhost:8000'}`);
  console.log(`  ALLDATA_API_URL: ${process.env.ALLDATA_API_URL || 'http://localhost:8001'}`);
  console.log(`  CUBE_API_URL: ${process.env.CUBE_API_URL || 'http://localhost:8002'}`);
  console.log(`  HEADLESS: ${process.env.HEADED === 'true' ? 'false' : 'true'}`);
  console.log(`  WORKERS: ${process.env.WORKERS || '4'}`);
  console.log('');

  // 检查环境变量
  if (!process.env.BASE_URL) {
    console.warn('警告: BASE_URL 未设置，使用默认值');
  }

  // 可选：在这里进行额外的全局设置
  // 例如：创建全局测试数据、初始化服务等

  console.log('全局设置完成');
  console.log('='.repeat(60));
}

export default globalSetup;
