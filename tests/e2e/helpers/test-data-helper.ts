/**
 * Test Data Manager for Playwright E2E Tests
 *
 * 功能：
 * - 管理测试数据状态
 * - 保存创建的数据源 ID
 * - 追踪测试创建的资源
 */

import { writeFileSync, readFileSync, existsSync } from 'fs';
import { join } from 'path';

export interface DatasourceInfo {
  id?: string;
  name: string;
  type: 'mysql' | 'postgresql' | 'oracle' | 'sqlserver' | 'mongodb';
  config: {
    host: string;
    port: string;
    username: string;
    password: string;
    database: string;
  };
  createdAt: string;
}

export interface TestDataManagerState {
  datasources: Record<string, DatasourceInfo>;
  metadata: Record<string, any>;
  versions: Record<string, any>;
  features: Record<string, any>;
  standards: Record<string, any>;
  assets: Record<string, any>;
}

const STATE_FILE_PATH = join(process.cwd(), 'test-results', 'test-data-state.json');

export class TestDataManager {
  private state: TestDataManagerState = {
    datasources: {},
    metadata: {},
    versions: {},
    features: {},
    standards: {},
    assets: {},
  };

  constructor() {
    this.loadState();
  }

  /**
   * 加载之前保存的状态
   */
  private loadState(): void {
    if (existsSync(STATE_FILE_PATH)) {
      try {
        const content = readFileSync(STATE_FILE_PATH, 'utf-8');
        this.state = JSON.parse(content);
        console.log('Test data state loaded from:', STATE_FILE_PATH);
      } catch (error) {
        console.error('Failed to load test data state:', error);
      }
    }
  }

  /**
   * 保存状态到文件
   */
  private saveState(): void {
    try {
      const { writeFile, mkdirSync } = require('fs');
      const dir = join(process.cwd(), 'test-results');

      // 确保目录存在
      if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
      }

      writeFile(STATE_FILE_PATH, JSON.stringify(this.state, null, 2), 'utf-8', (err: any) => {
        if (err) {
          console.error('Failed to save test data state:', err);
        } else {
          console.log('Test data state saved to:', STATE_FILE_PATH);
        }
      });
    } catch (error) {
      console.error('Error saving state:', error);
    }
  }

  /**
   * 保存数据源信息
   */
  async saveDatasource(type: string, name: string, config?: any): Promise<string> {
    const datasourceId = `${type}_${Date.now()}`;

    this.state.datasources[datasourceId] = {
      id: datasourceId,
      name,
      type: type as any,
      config: config || {},
      createdAt: new Date().toISOString(),
    };

    this.saveState();
    return datasourceId;
  }

  /**
   * 获取数据源信息
   */
  getDatasource(id: string): DatasourceInfo | undefined {
    return this.state.datasources[id];
  }

  /**
   * 通过名称查找数据源
   */
  findDatasourceByName(name: string): DatasourceInfo | undefined {
    return Object.values(this.state.datasources).find(ds => ds.name === name);
  }

  /**
   * 通过类型查找数据源
   */
  findDatasourceByType(type: string): DatasourceInfo[] {
    return Object.values(this.state.datasources).filter(ds => ds.type === type);
  }

  /**
   * 保存元数据信息
   */
  saveMetadata(key: string, value: any): void {
    this.state.metadata[key] = {
      ...value,
      createdAt: new Date().toISOString(),
    };
    this.saveState();
  }

  /**
   * 保存版本信息
   */
  saveVersion(key: string, value: any): void {
    this.state.versions[key] = {
      ...value,
      createdAt: new Date().toISOString(),
    };
    this.saveState();
  }

  /**
   * 保存特征信息
   */
  saveFeature(key: string, value: any): void {
    this.state.features[key] = {
      ...value,
      createdAt: new Date().toISOString(),
    };
    this.saveState();
  }

  /**
   * 保存标准信息
   */
  saveStandard(key: string, value: any): void {
    this.state.standards[key] = {
      ...value,
      createdAt: new Date().toISOString(),
    };
    this.saveState();
  }

  /**
   * 保存资产信息
   */
  saveAsset(key: string, value: any): void {
    this.state.assets[key] = {
      ...value,
      createdAt: new Date().toISOString(),
    };
    this.saveState();
  }

  /**
   * 获取所有数据源
   */
  getAllDatasources(): DatasourceInfo[] {
    return Object.values(this.state.datasources);
  }

  /**
   * 获取所有状态
   */
  getState(): TestDataManagerState {
    return { ...this.state };
  }

  /**
   * 清空状态
   */
  clearState(): void {
    this.state = {
      datasources: {},
      metadata: {},
      versions: {},
      features: {},
      standards: {},
      assets: {},
    };
    this.saveState();
  }

  /**
   * 生成测试数据报告
   */
  generateReport(): string {
    const lines = [
      '='.repeat(60),
      'Test Data Report',
      '='.repeat(60),
      '',
      'Datasources:',
      ...Object.values(this.state.datasources).map(ds =>
        `  - ${ds.name} (${ds.type}) - Created at: ${ds.createdAt}`
      ),
      '',
      `Total datasources: ${Object.keys(this.state.datasources).length}`,
      `Total metadata items: ${Object.keys(this.state.metadata).length}`,
      `Total versions: ${Object.keys(this.state.versions).length}`,
      `Total features: ${Object.keys(this.state.features).length}`,
      `Total standards: ${Object.keys(this.state.standards).length}`,
      `Total assets: ${Object.keys(this.state.assets).length}`,
      '',
      '='.repeat(60),
    ];

    return lines.join('\n');
  }

  /**
   * 打印报告到控制台
   */
  printReport(): void {
    console.log(this.generateReport());
  }

  /**
   * 保存报告到文件
   */
  async saveReport(filePath: string): Promise<void> {
    const { writeFile } = await import('fs/promises');
    await writeFile(filePath, this.generateReport(), 'utf-8');
    console.log(`Test data report saved to: ${filePath}`);
  }
}
