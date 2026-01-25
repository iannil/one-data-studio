#!/bin/bash
#
# 用户生命周期测试 - 测试用户清理脚本
# 用于清理测试环境中创建的测试用户
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
API_URL="${API_URL:-http://localhost:8000}"

# 测试用户列表
TEST_USERS=(
  "test_admin"
  "test_de"
  "test_ai"
  "test_da"
  "test_user"
  "test_guest"
  "test_pending"
  "test_inactive"
  "test_locked"
  "test_deleted"
)

# 附加清理：删除所有以 test_ 开头的用户
CLEANUP_ALL_TEST_USERS=true

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}用户生命周期测试 - 测试用户清理${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API URL: $API_URL"
echo ""

# 检查 API 是否可用
echo -e "${YELLOW}检查 API 连接...${NC}"
if ! curl -s -f "$API_URL/api/v1/health" > /dev/null 2>&1; then
  echo -e "${RED}错误: 无法连接到 API 服务器 $API_URL${NC}"
  echo "请确保后端服务正在运行"
  exit 1
fi
echo -e "${GREEN}API 连接正常${NC}"
echo ""

# 删除用户
delete_user() {
  local username=$1

  echo -e "${YELLOW}删除用户: $username${NC}"

  # 获取用户 ID
  local user_data=$(curl -s "$API_URL/api/v1/users/by-username/$username" || echo "")

  if [ -z "$user_data" ]; then
    echo "  用户 $username 不存在，跳过"
    return 0
  fi

  local user_id=$(echo "$user_data" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

  if [ -z "$user_id" ]; then
    echo "  无法获取用户 ID，跳过"
    return 0
  fi

  # 删除用户
  local result=$(curl -s -X DELETE "$API_URL/api/v1/users/$user_id" || echo "")

  if echo "$result" | grep -q '"code":0\|"status":"deleted"'; then
    echo -e "  ${GREEN}✓ 用户 $username 删除成功${NC}"
  else
    echo -e "  ${RED}✗ 用户 $username 删除失败${NC}"
    echo "  响应: $result"
  fi
}

# 询问确认
if [ "$AUTO_CONFIRM" != "true" ]; then
  echo -e "${YELLOW}警告: 此操作将删除所有测试用户${NC}"
  echo -n "确认继续? (y/N): "
  read -r confirm
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "操作已取消"
    exit 0
  fi
  echo ""
fi

# 删除预定义的测试用户
echo -e "${GREEN}开始删除测试用户...${NC}"
echo ""

for username in "${TEST_USERS[@]}"; do
  delete_user "$username"
  echo ""
done

# 删除所有以 test_ 开头的用户
if [ "$CLEANUP_ALL_TEST_USERS" = true ]; then
  echo -e "${YELLOW}清理所有 test_* 用户...${NC}"
  echo ""

  # 获取所有以 test_ 开头的用户
  local all_users=$(curl -s "$API_URL/api/v1/users" || echo "")
  local test_usernames=$(echo "$all_users" | grep -o '"username":"test_[^"]*"' | cut -d'"' -f4 | sort -u)

  if [ -n "$test_usernames" ]; then
    while IFS= read -r username; do
      if [ -n "$username" ]; then
        delete_user "$username"
        echo ""
      fi
    done <<< "$test_usernames"
  else
    echo "  没有找到额外的 test_ 用户"
    echo ""
  fi
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}测试用户清理完成${NC}"
echo -e "${GREEN}========================================${NC}"
