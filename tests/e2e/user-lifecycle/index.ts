/**
 * 用户生命周期测试套件 - 索引文件
 * 提供统一的导出接口
 */

// Fixtures
export {
  test,
  expect,
  UserManager,
  TestRole,
  UserStatus,
  TEST_USERS,
  type TestUser,
  type CreateUserRequest,
} from './fixtures/user-lifecycle.fixture';

export {
  test as testDataTest,
  expect as testDataExpect,
  TestDataManager,
  type TestDataset,
  type TestWorkflow,
  type TestModel,
} from './fixtures/test-data.fixture';

// Helpers
export * from './helpers/user-management';
export * from './helpers/role-management';
export * from './helpers/verification';

// Utils
export * from './utils/test-data-generator';
export * from './utils/api-mock';
export * from './utils/test-helpers';
export * from './utils/database-seeder';
