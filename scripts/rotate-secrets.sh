#!/bin/bash
# Secret Rotation Script
# Sprint 21: Security Hardening
#
# This script rotates secrets for ONE-DATA-STUDIO services.
# It supports rotating JWT keys, database passwords, and API keys.
#
# Usage:
#   ./rotate-secrets.sh [secret-type] [options]
#
# Secret types:
#   jwt          - Rotate JWT signing key
#   database     - Rotate database password
#   redis        - Rotate Redis password
#   minio        - Rotate MinIO credentials
#   all          - Rotate all secrets
#
# Options:
#   --dry-run    - Show what would be changed without making changes
#   --force      - Skip confirmation prompts
#   --namespace  - K8s namespace (default: one-data-system)

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-one-data-system}"
DRY_RUN=false
FORCE=false
SECRET_TYPE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Generate secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -base64 "$length" | tr -d '/+=' | head -c "$length"
}

# Generate password with special characters
generate_password() {
    local length=${1:-24}
    openssl rand -base64 "$length" | head -c "$length"
}

# Check prerequisites
check_prerequisites() {
    local missing=()

    if ! command -v kubectl &> /dev/null; then
        missing+=("kubectl")
    fi

    if ! command -v openssl &> /dev/null; then
        missing+=("openssl")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi

    # Check kubectl connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
}

# Confirm action
confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    local message="$1"
    read -p "$message [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi
}

# Rotate JWT secret key
rotate_jwt() {
    log_info "Rotating JWT secret key..."

    local new_secret
    new_secret=$(generate_secret 64)
    local new_csrf_secret
    new_csrf_secret=$(generate_secret 32)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would update jwt-credentials secret"
        log_info "[DRY RUN] New JWT_SECRET_KEY: ${new_secret:0:8}..."
        return
    fi

    confirm "This will rotate the JWT secret key. All existing tokens will be invalidated. Continue?"

    # Update K8s secret
    kubectl create secret generic jwt-credentials \
        --from-literal=JWT_SECRET_KEY="$new_secret" \
        --from-literal=CSRF_SECRET_KEY="$new_csrf_secret" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Trigger rolling restart of affected deployments
    kubectl rollout restart deployment/bisheng-api -n "$NAMESPACE" || true
    kubectl rollout restart deployment/alldata-api -n "$NAMESPACE" || true

    log_info "JWT secret key rotated successfully"
    log_info "Note: Users will need to re-authenticate"
}

# Rotate database password
rotate_database() {
    log_info "Rotating database password..."

    local new_password
    new_password=$(generate_password 24)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would update mysql-credentials secret"
        log_info "[DRY RUN] New password: ${new_password:0:4}..."
        return
    fi

    confirm "This will rotate the database password. Ensure the database user is updated first. Continue?"

    # Get current secret
    local current_secret
    current_secret=$(kubectl get secret mysql-credentials -n "$NAMESPACE" -o jsonpath='{.data.MYSQL_PASSWORD}' 2>/dev/null | base64 -d || echo "")

    if [ -z "$current_secret" ]; then
        log_warn "Current secret not found, creating new one"
    fi

    # Update K8s secret
    kubectl create secret generic mysql-credentials \
        --from-literal=MYSQL_PASSWORD="$new_password" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_warn "IMPORTANT: You must also update the password in MySQL!"
    log_info "Run: ALTER USER 'one_data'@'%' IDENTIFIED BY '${new_password}';"

    # Trigger rolling restart
    kubectl rollout restart deployment/bisheng-api -n "$NAMESPACE" || true
    kubectl rollout restart deployment/alldata-api -n "$NAMESPACE" || true

    log_info "Database secret updated. Remember to update the actual database password!"
}

# Rotate Redis password
rotate_redis() {
    log_info "Rotating Redis password..."

    local new_password
    new_password=$(generate_password 24)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would update redis-credentials secret"
        return
    fi

    confirm "This will rotate the Redis password. Continue?"

    kubectl create secret generic redis-credentials \
        --from-literal=REDIS_PASSWORD="$new_password" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_warn "IMPORTANT: You must also update the Redis configuration!"
    log_info "Update redis.conf: requirepass $new_password"

    kubectl rollout restart deployment/bisheng-api -n "$NAMESPACE" || true
    kubectl rollout restart deployment/alldata-api -n "$NAMESPACE" || true

    log_info "Redis secret updated"
}

# Rotate MinIO credentials
rotate_minio() {
    log_info "Rotating MinIO credentials..."

    local new_access_key
    new_access_key=$(generate_secret 20)
    local new_secret_key
    new_secret_key=$(generate_secret 40)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would update minio-credentials secret"
        return
    fi

    confirm "This will rotate the MinIO credentials. Continue?"

    kubectl create secret generic minio-credentials \
        --from-literal=MINIO_ACCESS_KEY="$new_access_key" \
        --from-literal=MINIO_SECRET_KEY="$new_secret_key" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_warn "IMPORTANT: You must also update MinIO server configuration!"
    log_info "Use mc admin user to update the credentials"

    kubectl rollout restart deployment/bisheng-api -n "$NAMESPACE" || true
    kubectl rollout restart deployment/alldata-api -n "$NAMESPACE" || true

    log_info "MinIO secrets updated"
}

# Rotate all secrets
rotate_all() {
    log_info "Rotating all secrets..."

    confirm "This will rotate ALL secrets. This is a major operation. Continue?"

    rotate_jwt
    rotate_database
    rotate_redis
    rotate_minio

    log_info "All secrets rotated"
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            jwt|database|redis|minio|all)
                SECRET_TYPE="$1"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    if [ -z "$SECRET_TYPE" ]; then
        log_error "Secret type is required"
        show_usage
        exit 1
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 <secret-type> [options]

Secret types:
  jwt          Rotate JWT signing key
  database     Rotate database password
  redis        Rotate Redis password
  minio        Rotate MinIO credentials
  all          Rotate all secrets

Options:
  --dry-run    Show what would be changed without making changes
  --force      Skip confirmation prompts
  --namespace  K8s namespace (default: one-data-system)
  -h, --help   Show this help message

Examples:
  $0 jwt --dry-run
  $0 database --force --namespace production
  $0 all
EOF
}

# Main
main() {
    parse_args "$@"
    check_prerequisites

    log_info "Namespace: $NAMESPACE"
    if [ "$DRY_RUN" = true ]; then
        log_warn "Running in DRY RUN mode - no changes will be made"
    fi

    case "$SECRET_TYPE" in
        jwt)
            rotate_jwt
            ;;
        database)
            rotate_database
            ;;
        redis)
            rotate_redis
            ;;
        minio)
            rotate_minio
            ;;
        all)
            rotate_all
            ;;
        *)
            log_error "Unknown secret type: $SECRET_TYPE"
            exit 1
            ;;
    esac
}

main "$@"
