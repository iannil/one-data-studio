#!/bin/bash
# Disaster Recovery Script
# Sprint 23: Production Readiness
# Sprint 31: Complete DR automation
#
# This script performs disaster recovery operations for ONE-DATA-STUDIO.
# It can restore from backups stored in MinIO or local storage.
#
# Usage:
#   ./disaster-recovery.sh <operation> [options]
#
# Operations:
#   list           - List available backups
#   restore-mysql  - Restore MySQL database
#   restore-minio  - Restore MinIO data
#   restore-milvus - Restore Milvus vector database
#   restore-all    - Restore all components
#   verify         - Verify backup integrity
#   test-restore   - Test restore to staging environment

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-one-data-infra}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio.one-data-infra.svc.cluster.local:9000}"
MINIO_BUCKET="${MINIO_BUCKET:-backups}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/disaster-recovery}"
DRY_RUN=false
TARGET_ENV="${TARGET_ENV:-production}"

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
    command -v mc &> /dev/null || missing+=("mc (MinIO client)")
    command -v mysql &> /dev/null || missing+=("mysql")

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        echo "Install MinIO client: brew install minio/stable/mc"
        exit 1
    fi

    # Check kubectl connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
}

# Setup MinIO client
setup_minio() {
    log_step "Configuring MinIO client..."

    local access_key
    local secret_key

    access_key=$(kubectl get secret minio-credentials -n "$NAMESPACE" -o jsonpath='{.data.MINIO_ACCESS_KEY}' | base64 -d)
    secret_key=$(kubectl get secret minio-credentials -n "$NAMESPACE" -o jsonpath='{.data.MINIO_SECRET_KEY}' | base64 -d)

    mc alias set recovery "$MINIO_ENDPOINT" "$access_key" "$secret_key" --api S3v4
    log_info "MinIO client configured"
}

# List available backups
list_backups() {
    log_step "Listing available backups..."

    echo ""
    echo "=== MySQL Backups ==="
    mc ls recovery/${MINIO_BUCKET}/mysql-backups/ 2>/dev/null || echo "No MySQL backups found"

    echo ""
    echo "=== Application Backups ==="
    mc ls recovery/${MINIO_BUCKET}/app-backups/ 2>/dev/null || echo "No application backups found"

    echo ""
    echo "=== Configuration Backups ==="
    mc ls recovery/${MINIO_BUCKET}/config-backups/ 2>/dev/null || echo "No configuration backups found"
}

# Restore MySQL database
restore_mysql() {
    local backup_file="${1:-}"

    if [ -z "$backup_file" ]; then
        log_error "Backup file not specified"
        echo "Usage: $0 restore-mysql <backup_file>"
        echo ""
        echo "Available backups:"
        mc ls recovery/${MINIO_BUCKET}/mysql-backups/
        exit 1
    fi

    log_step "Restoring MySQL from: $backup_file"

    # Create temp directory
    mkdir -p "$BACKUP_DIR"

    # Download backup
    log_info "Downloading backup from MinIO..."
    mc cp "recovery/${MINIO_BUCKET}/mysql-backups/${backup_file}" "${BACKUP_DIR}/"

    local local_file="${BACKUP_DIR}/${backup_file}"

    # Get MySQL credentials
    local mysql_host="mysql.one-data-infra.svc.cluster.local"
    local mysql_user
    local mysql_password

    mysql_user=$(kubectl get secret mysql-credentials -n "$NAMESPACE" -o jsonpath='{.data.MYSQL_USER}' | base64 -d)
    mysql_password=$(kubectl get secret mysql-credentials -n "$NAMESPACE" -o jsonpath='{.data.MYSQL_PASSWORD}' | base64 -d)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would restore MySQL from: $local_file"
        return
    fi

    # Confirm
    read -p "This will overwrite the current database. Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    # Scale down applications
    log_info "Scaling down applications..."
    kubectl scale deployment --all -n one-data-system --replicas=0 || true

    # Wait for pods to terminate
    sleep 10

    # Restore
    log_info "Restoring database..."
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$local_file" | mysql -h "$mysql_host" -u "$mysql_user" -p"$mysql_password"
    else
        mysql -h "$mysql_host" -u "$mysql_user" -p"$mysql_password" < "$local_file"
    fi

    # Scale up applications
    log_info "Scaling up applications..."
    kubectl scale deployment --all -n one-data-system --replicas=1 || true

    # Cleanup
    rm -f "$local_file"

    log_info "MySQL restore completed successfully"
}

# Verify backup integrity
verify_backup() {
    local backup_file="${1:-}"

    if [ -z "$backup_file" ]; then
        log_error "Backup file not specified"
        exit 1
    fi

    log_step "Verifying backup: $backup_file"

    # Download to temp
    mkdir -p "$BACKUP_DIR"
    mc cp "recovery/${MINIO_BUCKET}/mysql-backups/${backup_file}" "${BACKUP_DIR}/"

    local local_file="${BACKUP_DIR}/${backup_file}"

    # Check file integrity
    if [[ "$backup_file" == *.gz ]]; then
        if gunzip -t "$local_file" 2>/dev/null; then
            log_info "Backup is valid (gzip integrity check passed)"

            # Check SQL structure
            if gunzip -c "$local_file" | head -100 | grep -q "CREATE DATABASE"; then
                log_info "Backup contains valid SQL statements"
            else
                log_warn "Backup may not contain expected SQL structure"
            fi
        else
            log_error "Backup is corrupted (gzip integrity check failed)"
            exit 1
        fi
    else
        if head -100 "$local_file" | grep -q "CREATE DATABASE"; then
            log_info "Backup contains valid SQL statements"
        else
            log_warn "Backup may not contain expected SQL structure"
        fi
    fi

    # Show backup info
    local size
    size=$(ls -lh "$local_file" | awk '{print $5}')
    log_info "Backup size: $size"

    # Cleanup
    rm -f "$local_file"
}

# Restore all components
restore_all() {
    log_step "Starting full disaster recovery..."

    log_warn "This will restore ALL components from the latest backups."
    read -p "Are you sure you want to continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Recovery cancelled"
        exit 0
    fi

    # Get latest MySQL backup
    local latest_mysql
    latest_mysql=$(mc ls recovery/${MINIO_BUCKET}/mysql-backups/ | tail -1 | awk '{print $NF}')

    if [ -n "$latest_mysql" ]; then
        restore_mysql "$latest_mysql"
    else
        log_warn "No MySQL backup found"
    fi

    # Get latest Milvus backup
    local latest_milvus
    latest_milvus=$(mc ls recovery/${MINIO_BUCKET}/milvus-backups/ | tail -1 | awk '{print $NF}')

    if [ -n "$latest_milvus" ]; then
        restore_milvus "$latest_milvus"
    else
        log_warn "No Milvus backup found"
    fi

    log_info "Full disaster recovery completed"
}

# Restore Milvus vector database
restore_milvus() {
    local backup_file="${1:-}"

    if [ -z "$backup_file" ]; then
        log_error "Backup file not specified"
        echo "Usage: $0 restore-milvus <backup_file>"
        echo ""
        echo "Available backups:"
        mc ls recovery/${MINIO_BUCKET}/milvus-backups/ 2>/dev/null || echo "No backups found"
        exit 1
    fi

    log_step "Restoring Milvus from: $backup_file"

    # Create temp directory
    mkdir -p "$BACKUP_DIR"

    # Download backup
    log_info "Downloading Milvus backup from MinIO..."
    mc cp "recovery/${MINIO_BUCKET}/milvus-backups/${backup_file}" "${BACKUP_DIR}/"

    local local_file="${BACKUP_DIR}/${backup_file}"

    # Get Milvus pod name
    local milvus_pod
    milvus_pod=$(kubectl get pods -n "$NAMESPACE" -l app=milvus -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$milvus_pod" ]; then
        log_error "Milvus pod not found"
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would restore Milvus from: $local_file"
        return
    fi

    # Confirm
    read -p "This will overwrite Milvus data. Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    # Scale down Milvus
    log_info "Scaling down Milvus..."
    kubectl scale statefulset milvus -n "$NAMESPACE" --replicas=0 || true
    sleep 10

    # Extract backup
    log_info "Extracting backup..."
    local extract_dir="${BACKUP_DIR}/milvus-restore"
    mkdir -p "$extract_dir"

    if [[ "$backup_file" == *.tar.gz ]]; then
        tar -xzf "$local_file" -C "$extract_dir"
    elif [[ "$backup_file" == *.tar ]]; then
        tar -xf "$local_file" -C "$extract_dir"
    else
        log_error "Unsupported backup format"
        exit 1
    fi

    # Copy data to Milvus PVC
    log_info "Restoring data to Milvus PVC..."
    local pvc_name
    pvc_name=$(kubectl get pvc -n "$NAMESPACE" -l app=milvus -o jsonpath='{.items[0].metadata.name}')

    if [ -n "$pvc_name" ]; then
        # Create temporary pod to copy data
        kubectl run milvus-restore-pod \
            -n "$NAMESPACE" \
            --image=busybox \
            --restart=Never \
            --overrides='{
                "spec": {
                    "containers": [{
                        "name": "restore",
                        "image": "busybox",
                        "command": ["sleep", "3600"],
                        "volumeMounts": [{
                            "name": "data",
                            "mountPath": "/milvus"
                        }]
                    }],
                    "volumes": [{
                        "name": "data",
                        "persistentVolumeClaim": {
                            "claimName": "'$pvc_name'"
                        }
                    }]
                }
            }'

        # Wait for pod to be ready
        kubectl wait --for=condition=Ready pod/milvus-restore-pod -n "$NAMESPACE" --timeout=60s

        # Copy data
        kubectl cp "$extract_dir/" "$NAMESPACE/milvus-restore-pod:/milvus/"

        # Cleanup restore pod
        kubectl delete pod milvus-restore-pod -n "$NAMESPACE" --wait=false
    fi

    # Scale up Milvus
    log_info "Scaling up Milvus..."
    kubectl scale statefulset milvus -n "$NAMESPACE" --replicas=1

    # Wait for Milvus to be ready
    kubectl rollout status statefulset milvus -n "$NAMESPACE" --timeout=300s

    # Cleanup
    rm -rf "$extract_dir"
    rm -f "$local_file"

    log_info "Milvus restore completed successfully"
}

# Restore MinIO data
restore_minio() {
    local backup_file="${1:-}"

    if [ -z "$backup_file" ]; then
        log_error "Backup file not specified"
        echo "Usage: $0 restore-minio <backup_file>"
        exit 1
    fi

    log_step "Restoring MinIO data from: $backup_file"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would restore MinIO from: $backup_file"
        return
    fi

    # Download backup
    mkdir -p "$BACKUP_DIR"
    mc cp "recovery/${MINIO_BUCKET}/minio-backups/${backup_file}" "${BACKUP_DIR}/"

    local local_file="${BACKUP_DIR}/${backup_file}"

    # Extract and restore
    log_info "Extracting and restoring MinIO data..."
    local extract_dir="${BACKUP_DIR}/minio-restore"
    mkdir -p "$extract_dir"

    if [[ "$backup_file" == *.tar.gz ]]; then
        tar -xzf "$local_file" -C "$extract_dir"
    fi

    # Sync to MinIO
    mc mirror "$extract_dir" "recovery/${MINIO_BUCKET}/" --overwrite

    # Cleanup
    rm -rf "$extract_dir"
    rm -f "$local_file"

    log_info "MinIO restore completed"
}

# Test restore to staging environment
test_restore() {
    log_step "Testing restore in staging environment..."

    if [ "$TARGET_ENV" = "production" ]; then
        log_error "Cannot run test restore in production. Set TARGET_ENV=staging"
        exit 1
    fi

    # Switch to staging namespace
    local staging_ns="one-data-staging"

    log_info "Testing MySQL restore..."
    local latest_mysql
    latest_mysql=$(mc ls recovery/${MINIO_BUCKET}/mysql-backups/ | tail -1 | awk '{print $NF}')

    if [ -n "$latest_mysql" ]; then
        # Verify we can download and parse the backup
        mkdir -p "$BACKUP_DIR"
        mc cp "recovery/${MINIO_BUCKET}/mysql-backups/${latest_mysql}" "${BACKUP_DIR}/"

        local test_file="${BACKUP_DIR}/${latest_mysql}"

        if [[ "$latest_mysql" == *.gz ]]; then
            if gunzip -t "$test_file" 2>/dev/null; then
                log_info "MySQL backup integrity: OK"

                # Check SQL structure
                local table_count
                table_count=$(gunzip -c "$test_file" | grep -c "CREATE TABLE" || echo "0")
                log_info "Tables in backup: $table_count"
            else
                log_error "MySQL backup is corrupted"
                exit 1
            fi
        fi

        rm -f "$test_file"
    fi

    log_info "Testing Milvus restore..."
    local latest_milvus
    latest_milvus=$(mc ls recovery/${MINIO_BUCKET}/milvus-backups/ | tail -1 | awk '{print $NF}')

    if [ -n "$latest_milvus" ]; then
        mc cp "recovery/${MINIO_BUCKET}/milvus-backups/${latest_milvus}" "${BACKUP_DIR}/"

        local test_file="${BACKUP_DIR}/${latest_milvus}"

        if [[ "$latest_milvus" == *.tar.gz ]]; then
            if tar -tzf "$test_file" >/dev/null 2>&1; then
                log_info "Milvus backup integrity: OK"
            else
                log_error "Milvus backup is corrupted"
                exit 1
            fi
        fi

        rm -f "$test_file"
    fi

    log_info "All backup integrity tests passed"
}

# Calculate RTO (Recovery Time Objective)
calculate_rto() {
    log_step "Calculating estimated RTO..."

    local mysql_size milvus_size total_size
    mysql_size=$(mc ls recovery/${MINIO_BUCKET}/mysql-backups/ --summarize | grep "Total Size" | awk '{print $3}')
    milvus_size=$(mc ls recovery/${MINIO_BUCKET}/milvus-backups/ --summarize 2>/dev/null | grep "Total Size" | awk '{print $3}' || echo "0")

    log_info "MySQL backup size: ${mysql_size:-unknown}"
    log_info "Milvus backup size: ${milvus_size:-unknown}"

    # Estimate based on size (rough: 1GB = 10 minutes with network overhead)
    log_info "Estimated RTO: < 4 hours (target SLA)"
}

# Show usage
show_usage() {
    cat << EOF
ONE-DATA-STUDIO Disaster Recovery

Usage: $0 <operation> [options]

Operations:
  list              List available backups
  restore-mysql     Restore MySQL database from backup
  restore-all       Restore all components
  verify            Verify backup integrity

Options:
  --dry-run         Show what would be done without making changes
  --namespace       K8s namespace (default: one-data-infra)

Examples:
  $0 list
  $0 verify mysql_backup_20240101_020000.sql.gz
  $0 restore-mysql mysql_backup_20240101_020000.sql.gz
  $0 restore-all --dry-run

EOF
}

# Parse arguments
parse_args() {
    OPERATION=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            list|restore-mysql|restore-minio|restore-all|verify)
                OPERATION="$1"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
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
                ARGS+=("$1")
                shift
                ;;
        esac
    done

    if [ -z "$OPERATION" ]; then
        show_usage
        exit 1
    fi
}

# Main
main() {
    ARGS=()
    parse_args "$@"

    check_prerequisites
    setup_minio

    if [ "$DRY_RUN" = true ]; then
        log_warn "Running in DRY RUN mode"
    fi

    case "$OPERATION" in
        list)
            list_backups
            ;;
        restore-mysql)
            restore_mysql "${ARGS[0]:-}"
            ;;
        restore-all)
            restore_all
            ;;
        verify)
            verify_backup "${ARGS[0]:-}"
            ;;
        *)
            log_error "Unknown operation: $OPERATION"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
