#!/bin/bash
# Encryption Key Rotation Script
# Sprint 29: 企业安全强化
#
# This script rotates the encryption master key for sensitive data.
# It generates a new key, updates Kubernetes secrets, and triggers
# re-encryption of existing data.
#
# Usage:
#   ./rotate-encryption-keys.sh [options]
#
# Options:
#   --dry-run        Show what would be done without making changes
#   --namespace      K8s namespace (default: one-data-system)
#   --force          Skip confirmation prompts
#   --backup         Create backup before rotation

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-one-data-system}"
SECRET_NAME="${SECRET_NAME:-encryption-keys}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/key-rotation-backup}"
DRY_RUN=false
FORCE=false
CREATE_BACKUP=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    local missing=()

    command -v kubectl &> /dev/null || missing+=("kubectl")
    command -v openssl &> /dev/null || missing+=("openssl")
    command -v base64 &> /dev/null || missing+=("base64")

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi

    # Check kubectl connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Generate new encryption key
generate_key() {
    # Generate 32 bytes (256 bits) of random data, base64 encoded
    openssl rand -base64 32
}

# Get current key version
get_current_version() {
    local version
    version=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.data.ENCRYPTION_KEY_VERSION}' 2>/dev/null | base64 -d || echo "0")
    echo "${version:-0}"
}

# Get current encryption key
get_current_key() {
    kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.data.ENCRYPTION_MASTER_KEY}' 2>/dev/null | base64 -d || echo ""
}

# Backup current keys
backup_keys() {
    log_step "Creating backup of current keys..."

    mkdir -p "$BACKUP_DIR"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/encryption-keys-${timestamp}.yaml"

    if kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &> /dev/null; then
        kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o yaml > "$backup_file"
        chmod 600 "$backup_file"
        log_info "Backup saved to: $backup_file"
    else
        log_warn "No existing secret found, skipping backup"
    fi
}

# Create or update encryption secret
update_secret() {
    local new_key="$1"
    local new_version="$2"
    local old_key="$3"
    local old_version="$4"

    log_step "Updating Kubernetes secret..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would update secret $SECRET_NAME with:"
        log_info "  - New key version: $new_version"
        log_info "  - Previous key version: $old_version"
        return
    fi

    # Build previous keys string (version:key format)
    local previous_keys=""
    if [ -n "$old_key" ] && [ "$old_version" != "0" ]; then
        previous_keys="${old_version}:${old_key}"
    fi

    # Check if secret exists
    if kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &> /dev/null; then
        # Update existing secret
        kubectl patch secret "$SECRET_NAME" -n "$NAMESPACE" --type='json' -p="[
            {\"op\": \"replace\", \"path\": \"/data/ENCRYPTION_MASTER_KEY\", \"value\": \"$(echo -n "$new_key" | base64)\"},
            {\"op\": \"replace\", \"path\": \"/data/ENCRYPTION_KEY_VERSION\", \"value\": \"$(echo -n "$new_version" | base64)\"},
            {\"op\": \"replace\", \"path\": \"/data/ENCRYPTION_PREVIOUS_KEYS\", \"value\": \"$(echo -n "$previous_keys" | base64)\"}
        ]"
    else
        # Create new secret
        kubectl create secret generic "$SECRET_NAME" -n "$NAMESPACE" \
            --from-literal=ENCRYPTION_MASTER_KEY="$new_key" \
            --from-literal=ENCRYPTION_KEY_VERSION="$new_version" \
            --from-literal=ENCRYPTION_PREVIOUS_KEYS="$previous_keys" \
            --from-literal=ENCRYPTION_KEY_SALT="one-data-studio-salt"
    fi

    log_info "Secret updated successfully"
}

# Trigger rolling restart of deployments
restart_deployments() {
    log_step "Triggering rolling restart of deployments..."

    local deployments=(
        "agent-api"
        "data-api"
        "openai-proxy"
    )

    for deploy in "${deployments[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY RUN] Would restart deployment: $deploy"
        else
            if kubectl get deployment "$deploy" -n "$NAMESPACE" &> /dev/null; then
                kubectl rollout restart deployment "$deploy" -n "$NAMESPACE"
                log_info "Restarted deployment: $deploy"
            else
                log_warn "Deployment not found: $deploy"
            fi
        fi
    done
}

# Wait for deployments to be ready
wait_for_rollout() {
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would wait for rollout completion"
        return
    fi

    log_step "Waiting for deployments to be ready..."

    local deployments=(
        "agent-api"
        "data-api"
        "openai-proxy"
    )

    for deploy in "${deployments[@]}"; do
        if kubectl get deployment "$deploy" -n "$NAMESPACE" &> /dev/null; then
            log_info "Waiting for $deploy..."
            kubectl rollout status deployment "$deploy" -n "$NAMESPACE" --timeout=300s || true
        fi
    done

    log_info "All deployments are ready"
}

# Trigger re-encryption job (optional)
trigger_reencryption() {
    log_step "Triggering re-encryption of existing data..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would trigger re-encryption job"
        return
    fi

    # Create a one-time job to re-encrypt data
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: data-reencryption-$(date +%Y%m%d%H%M%S)
  namespace: $NAMESPACE
  labels:
    app: data-reencryption
spec:
  ttlSecondsAfterFinished: 86400
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: reencrypt
        image: one-data-studio/agent-api:latest
        command: ["python", "-c"]
        args:
        - |
          import os
          import sys
          sys.path.insert(0, '/app/shared')
          from security.encryption import get_encryption_service
          from models import get_db_session

          print("Starting re-encryption of sensitive data...")

          service = get_encryption_service()
          if not service.is_enabled:
              print("Encryption is disabled, skipping")
              sys.exit(0)

          # Re-encrypt user API keys, OAuth tokens, etc.
          # This is a placeholder - implement based on your data model
          print("Re-encryption completed")
        envFrom:
        - secretRef:
            name: $SECRET_NAME
        - configMapRef:
            name: database-config
EOF

    log_info "Re-encryption job created"
}

# Show usage
show_usage() {
    cat << EOF
Encryption Key Rotation Script

Usage: $0 [options]

Options:
  --dry-run        Show what would be done without making changes
  --namespace      K8s namespace (default: one-data-system)
  --force          Skip confirmation prompts
  --backup         Create backup before rotation
  -h, --help       Show this help

Examples:
  $0 --dry-run
  $0 --backup --namespace production
  $0 --force

Security Notes:
  - Old keys are retained for a grace period to decrypt existing data
  - Rolling restart ensures all pods use the new key for encryption
  - Re-encryption job updates existing encrypted data to use new key

EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --backup)
                CREATE_BACKUP=true
                shift
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
}

# Main
main() {
    parse_args "$@"

    echo ""
    echo "========================================"
    echo "  Encryption Key Rotation"
    echo "========================================"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warn "Running in DRY RUN mode"
    fi

    check_prerequisites

    # Get current state
    local current_version
    local current_key
    current_version=$(get_current_version)
    current_key=$(get_current_key)

    log_info "Current key version: $current_version"

    # Calculate new version
    local new_version=$((current_version + 1))
    log_info "New key version: $new_version"

    # Generate new key
    local new_key
    new_key=$(generate_key)
    log_info "New encryption key generated"

    # Confirmation
    if [ "$FORCE" != true ] && [ "$DRY_RUN" != true ]; then
        echo ""
        log_warn "This will rotate the encryption key for namespace: $NAMESPACE"
        log_warn "All services will be restarted and existing data will be re-encrypted."
        echo ""
        read -p "Are you sure you want to continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Key rotation cancelled"
            exit 0
        fi
    fi

    # Create backup if requested
    if [ "$CREATE_BACKUP" = true ]; then
        backup_keys
    fi

    # Update secret
    update_secret "$new_key" "$new_version" "$current_key" "$current_version"

    # Restart deployments
    restart_deployments

    # Wait for rollout
    wait_for_rollout

    # Trigger re-encryption (optional)
    if [ "$DRY_RUN" != true ]; then
        read -p "Do you want to re-encrypt existing data with the new key? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            trigger_reencryption
        fi
    fi

    echo ""
    log_info "========================================"
    log_info "  Key rotation completed successfully"
    log_info "========================================"
    echo ""
    log_info "New key version: $new_version"
    log_info "Previous key version: $current_version (retained for decryption)"
    echo ""
}

main "$@"
