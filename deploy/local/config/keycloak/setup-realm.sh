#!/bin/sh
# Keycloak Realm 初始化脚本
# 自动创建 one-data-studio realm 和客户端

set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak:8080}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
REALM_NAME="one-data-studio"

# 等待 Keycloak 启动
echo "等待 Keycloak 启动..."
until curl -s -f "${KEYCLOAK_URL}/realms/master/.well-known/openid-configuration" > /dev/null 2>&1; do
    echo "等待 Keycloak 就绪..."
    sleep 5
done
echo "Keycloak 已就绪"

# 获取管理员 token
echo "获取管理员 token..."
TOKEN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${ADMIN_USER}" \
    -d "password=${ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=admin-cli")

# 使用 sed 和 grep 提取 access_token（替代 jq）
ADMIN_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo "错误: 无法获取管理员 token"
    echo "响应: $TOKEN_RESPONSE"
    exit 1
fi

echo "管理员 token 获取成功"

# 检查 realm 是否已存在
echo "检查 realm 是否存在..."
REALMS=$(curl -s -X GET "${KEYCLOAK_URL}/admin/realms" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")

if echo "$REALMS" | grep -q "\"${REALM_NAME}\""; then
    echo "Realm '${REALM_NAME}' 已存在，跳过创建"
else
    echo "创建 realm: ${REALM_NAME}"

    # 创建 realm
    curl -s -X POST "${KEYCLOAK_URL}/admin/realms" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "realm": "'${REALM_NAME}'",
            "enabled": true,
            "displayName": "ONE-DATA-STUDIO",
            "registrationAllowed": true,
            "loginWithEmailAllowed": true,
            "duplicateEmailsAllowed": false,
            "resetPasswordAllowed": true,
            "editUsernameAllowed": true,
            "bruteForceProtected": true,
            "sslRequired": "external"
        }'

    echo "Realm '${REALM_NAME}' 创建成功"
fi

# 创建 web-frontend 客户端
echo "创建客户端: web-frontend"
CLIENTS=$(curl -s -X GET "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients?clientId=web-frontend" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")

if echo "$CLIENTS" | grep -q '"web-frontend"'; then
    echo "客户端 'web-frontend' 已存在"
else
    echo "创建新客户端 'web-frontend'"

    curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "clientId": "web-frontend",
            "name": "Web Frontend",
            "description": "ONE-DATA-STUDIO Web Frontend Application",
            "enabled": true,
            "publicClient": true,
            "protocol": "openid-connect",
            "redirectUris": ["http://localhost:3000/*"],
            "webOrigins": ["http://localhost:3000"],
            "consentRequired": false,
            "standardFlowEnabled": true,
            "implicitFlowEnabled": false,
            "directAccessGrantsEnabled": true
        }'

    echo "客户端 'web-frontend' 创建成功"
fi

# 创建 data-api 客户端
echo "创建客户端: data-api"
CLIENTS=$(curl -s -X GET "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients?clientId=data-api" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")

if echo "$CLIENTS" | grep -q '"data-api"'; then
    echo "客户端 'data-api' 已存在"
else
    curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "clientId": "data-api",
            "name": "Data API",
            "description": "ONE-DATA-STUDIO Data API Service",
            "enabled": true,
            "clientAuthenticatorType": "client-secret",
            "secret": "data-api-secret",
            "redirectUris": ["http://localhost:8001/*"],
            "webOrigins": ["http://localhost:8001"],
            "publicClient": false,
            "protocol": "openid-connect",
            "consentRequired": false,
            "standardFlowEnabled": false,
            "directAccessGrantsEnabled": true,
            "serviceAccountsEnabled": true
        }'
    echo "客户端 'data-api' 创建成功"
fi

# 创建 agent-api 客户端
echo "创建客户端: agent-api"
CLIENTS=$(curl -s -X GET "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients?clientId=agent-api" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")

if echo "$CLIENTS" | grep -q '"agent-api"'; then
    echo "客户端 'agent-api' 已存在"
else
    curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "clientId": "agent-api",
            "name": "Agent API",
            "description": "ONE-DATA-STUDIO Agent API Service",
            "enabled": true,
            "clientAuthenticatorType": "client-secret",
            "secret": "agent-api-secret",
            "redirectUris": ["http://localhost:8000/*"],
            "webOrigins": ["http://localhost:8000"],
            "publicClient": false,
            "protocol": "openid-connect",
            "consentRequired": false,
            "standardFlowEnabled": false,
            "directAccessGrantsEnabled": true,
            "serviceAccountsEnabled": true
        }'
    echo "客户端 'agent-api' 创建成功"
fi

# 创建默认用户
echo "创建默认用户..."
USERS=$(curl -s -X GET "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/users?username=admin" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")

if echo "$USERS" | grep -q '"admin"'; then
    echo "用户 'admin' 已存在"
else
    curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/users" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "admin",
            "firstName": "Admin",
            "lastName": "User",
            "email": "admin@onedata.local",
            "enabled": true,
            "emailVerified": true,
            "credentials": [{
                "type": "password",
                "value": "admin123",
                "temporary": false
            }]
        }'
    echo "用户 'admin' 创建成功"
fi

echo ""
echo "=========================================="
echo "Keycloak Realm 初始化完成!"
echo "=========================================="
echo "Realm: ${REALM_NAME}"
echo "Admin Console: http://localhost:8080/admin/master/console/"
echo "Realm Account: http://localhost:8080/realms/${REALM_NAME}/account/"
echo ""
echo "Master Realm 管理员账号:"
echo "  用户名: ${ADMIN_USER}"
echo "  密码: ${ADMIN_PASSWORD}"
echo ""
echo "${REALM_NAME} Realm 默认用户:"
echo "  用户名: admin"
echo "  密码: admin123"
echo "=========================================="
