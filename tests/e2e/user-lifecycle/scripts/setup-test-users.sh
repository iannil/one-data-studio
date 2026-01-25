#!/bin/bash
#
# 用户生命周期测试 - 测试用户初始化脚本
# 用于在测试环境中创建预定义的测试用户
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
BASE_URL="${BASE_URL:-http://localhost:3000}"
API_URL="${API_URL:-http://localhost:8000}"

# 测试用户配置
declare -A USERS=(
  ["test_admin"]="admin:Admin1234!:testadmin@example.com"
  ["test_de"]="data_engineer:De1234!:testde@example.com"
  ["test_ai"]="ai_developer:Ai1234!:testai@example.com"
  ["test_da"]="data_analyst:Da1234!:testda@example.com"
  ["test_user"]="user:User1234!:testuser@example.com"
  ["test_guest"]="guest:Guest1234!:testguest@example.com"
  ["test_pending"]="user:Pending1234!:testpending@example.com:pending"
  ["test_inactive"]="user:Inactive1234!:testinactive@example.com:inactive"
  ["test_locked"]="user:Locked1234!:testlocked@example.com:locked"
)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}用户生命周期测试 - 测试用户初始化${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API URL: $API_URL"
echo "BASE URL: $BASE_URL"
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

# 创建或更新用户
create_user() {
  local username=$1
  local role=$2
  local password=$3
  local email=$4
  local status=${5:-active}

  echo -e "${YELLOW}创建/更新用户: $username (角色: $role, 状态: $status)${NC}"

  # 检查用户是否已存在
  local existing=$(curl -s "$API_URL/api/v1/users/by-username/$username" || echo "")

  if [ -n "$existing" ]; then
    echo "  用户 $username 已存在，跳过创建"
    return 0
  fi

  # 创建用户
  local result=$(curl -s -X POST "$API_URL/api/v1/users" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$username\",
      \"email\": \"$email\",
      \"password\": \"$password\",
      \"roles\": [\"$role\"],
      \"status\": \"$status\"
    }" || echo "")

  if echo "$result" | grep -q '"code":0'; then
    echo -e "  ${GREEN}✓ 用户 $username 创建成功${NC}"
  else
    echo -e "  ${RED}✗ 用户 $username 创建失败${NC}"
    echo "  响应: $result"
  fi
}

# 批量创建用户
echo -e "${GREEN}开始创建测试用户...${NC}"
echo ""

for username in "${!USERS[@]}"; do
  IFS=':' read -r role password email status <<< "${USERS[$username]}"
  create_user "$username" "$role" "$password" "$email" "$status"
  echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}测试用户初始化完成${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "已创建的用户："
for username in "${!USERS[@]}"; do
  IFS=':' read -r role password email status <<< "${USERS[$username]}"
  echo "  - $username (角色: $role, 状态: ${status:-active})"
done
