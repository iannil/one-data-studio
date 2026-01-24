#!/bin/bash
#
# Secrets Validation Script
# Validates that K8s secrets files don't contain placeholder values
#
# Usage:
#   ./validate-secrets.sh [secrets-file]
#
# Example:
#   ./validate-secrets.sh k8s/base/secrets.yaml
#   ./validate-secrets.sh  # validates all yaml files in k8s/

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Placeholder patterns to detect
PLACEHOLDER_PATTERNS=(
    "REPLACE_WITH"
    "CHANGEME"
    "TODO:"
    "PLACEHOLDER"
    "YOUR_.*_HERE"
    "xxx"
    "changeme"
)

# Function to check a file for placeholders
check_file() {
    local file=$1
    local has_error=0

    echo -e "${YELLOW}Checking: ${file}${NC}"

    for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
        if grep -qiE "$pattern" "$file" 2>/dev/null; then
            echo -e "${RED}  ERROR: Found placeholder pattern '$pattern' in $file${NC}"
            grep -niE "$pattern" "$file" | head -5 | while read line; do
                echo -e "${RED}    $line${NC}"
            done
            has_error=1
        fi
    done

    # Check for empty values in YAML
    if grep -qE "^[^#]*:\s*['\"]?\s*['\"]?\s*$" "$file" 2>/dev/null; then
        echo -e "${YELLOW}  WARNING: Found potentially empty values in $file${NC}"
        grep -nE "^[^#]*:\s*['\"]?\s*['\"]?\s*$" "$file" | head -5 | while read line; do
            echo -e "${YELLOW}    $line${NC}"
        done
    fi

    if [ $has_error -eq 0 ]; then
        echo -e "${GREEN}  OK: No placeholder patterns found${NC}"
    fi

    return $has_error
}

# Main logic
main() {
    local target="${1:-}"
    local exit_code=0

    echo "====================================="
    echo "ONE-DATA-STUDIO Secrets Validator"
    echo "====================================="
    echo ""

    if [ -n "$target" ]; then
        # Check single file
        if [ -f "$target" ]; then
            check_file "$target" || exit_code=1
        else
            echo -e "${RED}ERROR: File not found: $target${NC}"
            exit 1
        fi
    else
        # Check all yaml files in k8s directories
        echo "Scanning K8s manifests for placeholder values..."
        echo ""

        # Find all secrets-related yaml files
        for file in $(find . -path "*/k8s/*" -name "*.yaml" -o -name "*.yml" | grep -E "(secret|credential)" || true); do
            check_file "$file" || exit_code=1
        done

        # Also check any file with 'secret' in content
        for file in $(grep -rl "kind: Secret" . --include="*.yaml" --include="*.yml" 2>/dev/null | head -20); do
            if [ -f "$file" ]; then
                check_file "$file" || exit_code=1
            fi
        done
    fi

    echo ""
    echo "====================================="
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}PASSED: No placeholder values detected${NC}"
    else
        echo -e "${RED}FAILED: Placeholder values found!${NC}"
        echo ""
        echo "Please replace all placeholder values with actual secrets."
        echo "For production deployments, use:"
        echo "  - Kubernetes Secrets from environment"
        echo "  - HashiCorp Vault"
        echo "  - AWS Secrets Manager"
        echo "  - Azure Key Vault"
        echo ""
        echo "Never commit real secrets to the repository!"
    fi
    echo "====================================="

    exit $exit_code
}

main "$@"
