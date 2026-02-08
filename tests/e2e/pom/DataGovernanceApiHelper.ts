/**
 * Data Governance API Helper
 *
 * Provides API testing utilities for data governance features.
 * Includes response assertions, test data generation, and error handling.
 */

import { APIRequestContext, APIResponse } from '@playwright/test';

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
  timestamp?: number;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// =============================================================================
// Test Data Generators
// =============================================================================

export class TestDataGenerator {
  /**
   * Generate unique test name with timestamp
   */
  static generateName(prefix: string): string {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 1000);
    return `${prefix}_${timestamp}_${random}`;
  }

  /**
   * Generate test email
   */
  static generateEmail(prefix: string = 'test'): string {
    const timestamp = Date.now();
    return `${prefix}_${timestamp}@e2e.test`;
  }

  /**
   * Generate test phone number
   */
  static generatePhone(): string {
    return `138${Math.floor(Math.random() * 100000000).toString().padStart(8, '0')}`;
  }

  /**
   * Generate test ID card number
   */
  static generateIdCard(): string {
    const area = '110101';
    const birth = '19900101';
    const sequence = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    return `${area}${birth}${sequence}1`;
  }

  /**
   * Generate test data element code
   */
  static generateElementCode(name: string): string {
    const pinyin = name.toLowerCase().replace(/\s+/g, '_');
    return `DE_${pinyin.toUpperCase()}_${Date.now()}`;
  }

  /**
   * Generate test feature name
   */
  static generateFeatureName(): string {
    const prefixes = ['user', 'order', 'product', 'customer', 'transaction'];
    const suffixes = ['count', 'amount', 'status', 'type', 'flag'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const suffix = suffixes[Math.floor(Math.random() * suffixes.length)];
    return `test_${prefix}_${suffix}_${Date.now()}`;
  }

  /**
   * Generate test snapshot name
   */
  static generateSnapshotName(): string {
    const date = new Date().toISOString().split('T')[0];
    return `snapshot_${date}_${Date.now()}`;
  }
}

// =============================================================================
// API Response Assertions
// =============================================================================

export class ApiAssertions {
  /**
   * Assert API response is successful
   */
  static assertSuccess(response: ApiResponse): void {
    if (response.code !== 200 && response.code !== 0) {
      throw new Error(`API request failed: code=${response.code}, message=${response.message}`);
    }
  }

  /**
   * Assert response contains data
   */
  static assertHasData(response: ApiResponse): void {
    if (response.data === null || response.data === undefined) {
      throw new Error('API response data is null or undefined');
    }
  }

  /**
   * Assert response data is array
   */
  static assertIsArray(response: ApiResponse): void {
    if (!Array.isArray(response.data)) {
      throw new Error('API response data is not an array');
    }
  }

  /**
   * Assert pagination response has expected structure
   */
  static assertPagination(response: ApiResponse<PaginationResponse<any>>): void {
    this.assertSuccess(response);
    this.assertHasData(response);
    const data = response.data;
    if (!('items' in data) || !('total' in data)) {
      throw new Error('Pagination response missing items or total field');
    }
  }

  /**
   * Assert error response
   */
  static assertError(response: ApiResponse, expectedCode?: number, expectedMessage?: string): void {
    if (response.code === 200 || response.code === 0) {
      throw new Error('Expected error but got success response');
    }
    if (expectedCode && response.code !== expectedCode) {
      throw new Error(`Expected error code ${expectedCode} but got ${response.code}`);
    }
    if (expectedMessage && !response.message.includes(expectedMessage)) {
      throw new Error(`Expected error message to contain "${expectedMessage}" but got "${response.message}"`);
    }
  }
}

// =============================================================================
// Data Governance API Helper
// =============================================================================

export class DataGovernanceApiHelper {
  private request: APIRequestContext;
  private baseURL: string;

  constructor(request: APIRequestContext, baseURL: string = 'http://localhost:8000') {
    this.request = request;
    this.baseURL = baseURL;
  }

  // ==========================================================================
  // Metadata API Tests
  // ==========================================================================

  /**
   * DM-MD-API-001: Get database list
   */
  async testGetDatabases(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/databases`);
    return await this.parseResponse(response);
  }

  /**
   * DM-MD-API-002: Get table list for a database
   */
  async testGetTables(database: string): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/databases/${database}/tables`);
    return await this.parseResponse(response);
  }

  /**
   * DM-MD-API-003: Get table details
   */
  async testGetTableDetails(database: string, table: string): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/databases/${database}/tables/${table}`);
    return await this.parseResponse(response);
  }

  /**
   * DM-MD-API-004: AI annotate table
   */
  async testAiAnnotate(database: string, table: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/metadata/annotate`, {
      data: { database, table }
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-MD-API-005: Sensitivity analysis
   */
  async testSensitivityAnalysis(database: string, table: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/metadata/sensitivity`, {
      data: { database, table }
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-MD-API-006: Text2SQL
   */
  async testText2Sql(query: string, database?: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/metadata/text2sql`, {
      data: { query, database }
    });
    return await this.parseResponse(response);
  }

  // ==========================================================================
  // Version Management API Tests
  // ==========================================================================

  /**
   * DM-MV-API-001: Get version list
   */
  async testGetVersions(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/metadata/versions`);
    return await this.parseResponse(response);
  }

  /**
   * DM-MV-API-002: Create snapshot
   */
  async testCreateSnapshot(name: string, description?: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/metadata/versions`, {
      data: { name, description }
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-MV-API-003: Compare versions
   */
  async testCompareVersions(versionId1: string, versionId2: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/metadata/versions/compare`, {
      data: { version1: versionId1, version2: versionId2 }
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-MV-API-004: Rollback to version
   */
  async testRollbackVersion(versionId: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/metadata/versions/${versionId}/rollback`);
    return await this.parseResponse(response);
  }

  /**
   * DM-MV-API-005: Delete snapshot
   */
  async testDeleteSnapshot(versionId: string): Promise<ApiResponse> {
    const response = await this.request.delete(`${this.baseURL}/api/v1/metadata/versions/${versionId}`);
    return await this.parseResponse(response);
  }

  // ==========================================================================
  // Feature Management API Tests
  // ==========================================================================

  /**
   * DM-FG-API-001: Get feature list
   */
  async testGetFeatures(params?: { page?: number; pageSize?: number; groupId?: string }): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/features`, {
      params: params as any
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-002: Create feature
   */
  async testCreateFeature(data: {
    name: string;
    description?: string;
    groupId: string;
    dataType: string;
    valueType: string;
    sourceTable: string;
    sourceColumn: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/features`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-003: Update feature
   */
  async testUpdateFeature(featureId: string, data: Partial<any>): Promise<ApiResponse> {
    const response = await this.request.put(`${this.baseURL}/api/v1/features/${featureId}`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-004: Delete feature
   */
  async testDeleteFeature(featureId: string): Promise<ApiResponse> {
    const response = await this.request.delete(`${this.baseURL}/api/v1/features/${featureId}`);
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-005: Get feature groups
   */
  async testGetFeatureGroups(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/features/groups`);
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-006: Create feature group
   */
  async testCreateFeatureGroup(data: {
    name: string;
    description?: string;
    sourceTable?: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/features/groups`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-007: Get feature sets
   */
  async testGetFeatureSets(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/features/sets`);
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-008: Create feature set
   */
  async testCreateFeatureSet(data: {
    name: string;
    description?: string;
    featureIds: string[];
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/features/sets`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-009: Get feature services
   */
  async testGetFeatureServices(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/features/services`);
    return await this.parseResponse(response);
  }

  /**
   * DM-FG-API-010: Publish feature service
   */
  async testPublishFeatureService(data: {
    name: string;
    setId: string;
    endpoint: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/features/services`, { data });
    return await this.parseResponse(response);
  }

  // ==========================================================================
  // Data Standards API Tests
  // ==========================================================================

  /**
   * DM-DS-API-001: Get data elements
   */
  async testGetDataElements(params?: { page?: number; pageSize?: number }): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/standards/elements`, {
      params: params as any
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-002: Create data element
   */
  async testCreateDataElement(data: {
    name: string;
    code: string;
    dataType: string;
    length?: number;
    description?: string;
    libraryId?: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/standards/elements`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-003: Update data element
   */
  async testUpdateDataElement(elementId: string, data: Partial<any>): Promise<ApiResponse> {
    const response = await this.request.put(`${this.baseURL}/api/v1/standards/elements/${elementId}`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-004: Delete data element
   */
  async testDeleteDataElement(elementId: string): Promise<ApiResponse> {
    const response = await this.request.delete(`${this.baseURL}/api/v1/standards/elements/${elementId}`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-005: Get word libraries
   */
  async testGetWordLibraries(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/standards/libraries`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-006: Create word library
   */
  async testCreateWordLibrary(data: {
    name: string;
    category?: string;
    description?: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/standards/libraries`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-007: Get standard documents
   */
  async testGetStandardDocuments(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/standards/documents`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-008: Upload standard document
   */
  async testUploadDocument(file: Buffer, name: string, category?: string): Promise<ApiResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    if (category) {
      formData.append('category', category);
    }

    const response = await this.request.post(`${this.baseURL}/api/v1/standards/documents/upload`, {
      multipart: { file, name, category }
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-009: Get standard mappings
   */
  async testGetStandardMappings(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/standards/mappings`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DS-API-010: Create standard mapping
   */
  async testCreateStandardMapping(data: {
    fieldId: string;
    elementId: string;
    transformRule?: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/standards/mappings`, { data });
    return await this.parseResponse(response);
  }

  // ==========================================================================
  // Data Assets API Tests
  // ==========================================================================

  /**
   * DM-DA-API-001: Get asset list
   */
  async testGetAssets(params?: { page?: number; pageSize?: number; type?: string }): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/assets`, {
      params: params as any
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-002: Get asset details
   */
  async testGetAssetDetails(assetId: string): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/assets/${assetId}`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-003: Get asset tree
   */
  async testGetAssetTree(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/assets/tree`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-004: Update asset
   */
  async testUpdateAsset(assetId: string, data: Partial<any>): Promise<ApiResponse> {
    const response = await this.request.put(`${this.baseURL}/api/v1/assets/${assetId}`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-005: Create inventory task
   */
  async testCreateInventoryTask(data: {
    name: string;
    scope?: string[];
    schedule?: string;
  }): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/assets/inventories`, { data });
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-006: Get inventory tasks
   */
  async testGetInventoryTasks(): Promise<ApiResponse> {
    const response = await this.request.get(`${this.baseURL}/api/v1/assets/inventories`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-007: Execute inventory
   */
  async testExecuteInventory(taskId: string): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/assets/inventories/${taskId}/execute`);
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-008: Value assessment
   */
  async testAssessValue(assetId: string, rules?: any): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/assets/${assetId}/assess`, {
      data: { rules }
    });
    return await this.parseResponse(response);
  }

  /**
   * DM-DA-API-009: AI semantic search
   */
  async testAiSearch(query: string, filters?: any): Promise<ApiResponse> {
    const response = await this.request.post(`${this.baseURL}/api/v1/assets/search`, {
      data: { query, filters }
    });
    return await this.parseResponse(response);
  }

  // ==========================================================================
  // Helper Methods
  // ==========================================================================

  /**
   * Parse API response
   */
  private async parseResponse(response: APIResponse): Promise<ApiResponse> {
    const text = await response.text();
    try {
      return JSON.parse(text);
    } catch {
      return { code: response.status(), message: text, data: null };
    }
  }

  /**
   * Set auth token for requests
   */
  setAuthToken(token: string): void {
    this.request = this.request;
    // Token would be set via headers in actual implementation
  }

  /**
   * Wait for async operation to complete
   */
  async waitForOperation(operationId: string, timeout: number = 30000): Promise<ApiResponse> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const response = await this.request.get(`${this.baseURL}/api/v1/operations/${operationId}`);
      const result = await this.parseResponse(response);
      if (result.data?.status === 'completed') {
        return result;
      }
      if (result.data?.status === 'failed') {
        throw new Error(`Operation failed: ${result.data?.error}`);
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('Operation timeout');
  }
}

// =============================================================================
// API Test Runner
// =============================================================================

export class ApiTestRunner {
  private helper: DataGovernanceApiHelper;
  private results: Map<string, any> = new Map();

  constructor(request: APIRequestContext, baseURL?: string) {
    this.helper = new DataGovernanceApiHelper(request, baseURL);
  }

  /**
   * Run API test with assertion
   */
  async runTest(testName: string, testFn: () => Promise<ApiResponse>): Promise<boolean> {
    try {
      const response = await testFn();
      this.results.set(testName, { success: true, response });
      ApiAssertions.assertSuccess(response);
      return true;
    } catch (error) {
      this.results.set(testName, { success: false, error: (error as Error).message });
      return false;
    }
  }

  /**
   * Get test results
   */
  getResults(): Map<string, any> {
    return this.results;
  }

  /**
   * Get API helper instance
   */
  getApiHelper(): DataGovernanceApiHelper {
    return this.helper;
  }
}
