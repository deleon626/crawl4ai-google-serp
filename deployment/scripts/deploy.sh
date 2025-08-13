#!/bin/bash

# Production Deployment Script
# Usage: ./deploy.sh [version] [environment]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERSION="${1:-latest}"
ENVIRONMENT="${2:-production}"
LOG_FILE="/var/log/company-extraction-api/deploy-$(date +%Y%m%d-%H%M%S).log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
    
    case $level in
        "ERROR")   echo -e "${RED}[ERROR]${NC} $message" ;;
        "WARN")    echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "INFO")    echo -e "${GREEN}[INFO]${NC} $message" ;;
        "DEBUG")   echo -e "${BLUE}[DEBUG]${NC} $message" ;;
    esac
}

# Error handler
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Cleanup function
cleanup() {
    log "INFO" "Performing cleanup..."
    # Remove temporary files
    rm -f /tmp/health_check_*
    # Stop any temporary containers
    docker stop deploy-test-container 2>/dev/null || true
    docker rm deploy-test-container 2>/dev/null || true
}

# Set up trap for cleanup
trap cleanup EXIT

# Pre-deployment checks
pre_deployment_checks() {
    log "INFO" "Running pre-deployment checks..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log "WARN" "Running as root. This is not recommended for production."
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed or not in PATH"
    fi
    
    if ! docker info &> /dev/null; then
        error_exit "Docker daemon is not running or user lacks permissions"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed or not in PATH"
    fi
    
    # Check available disk space (require at least 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=5242880  # 5GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        error_exit "Insufficient disk space. Required: 5GB, Available: $(($available_space/1024/1024))GB"
    fi
    
    # Check if environment file exists
    if [[ ! -f "$PROJECT_DIR/.env.$ENVIRONMENT" ]]; then
        error_exit "Environment file .env.$ENVIRONMENT not found"
    fi
    
    # Validate environment file
    if ! grep -q "BRIGHT_DATA_TOKEN" "$PROJECT_DIR/.env.$ENVIRONMENT"; then
        error_exit "BRIGHT_DATA_TOKEN not found in environment file"
    fi
    
    log "INFO" "Pre-deployment checks passed"
}

# Backup current state
backup_current_state() {
    log "INFO" "Backing up current state..."
    
    local backup_dir="/opt/backups/company-extraction-api"
    local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
    
    mkdir -p "$backup_dir"
    
    # Backup Redis data
    if docker ps | grep -q redis; then
        log "INFO" "Backing up Redis data..."
        docker exec redis redis-cli BGSAVE
        sleep 5
        docker cp redis:/data/dump.rdb "$backup_dir/$backup_name-redis.rdb"
    fi
    
    # Backup configuration
    log "INFO" "Backing up configuration..."
    tar -czf "$backup_dir/$backup_name-config.tar.gz" \
        -C "$PROJECT_DIR" \
        .env.production deployment/config/ 2>/dev/null || true
    
    # Backup logs
    if [[ -d "$PROJECT_DIR/logs" ]]; then
        log "INFO" "Backing up logs..."
        tar -czf "$backup_dir/$backup_name-logs.tar.gz" \
            -C "$PROJECT_DIR" logs/ 2>/dev/null || true
    fi
    
    log "INFO" "Backup completed: $backup_name"
    echo "$backup_name" > /tmp/current_backup_name
}

# Pull new images
pull_images() {
    log "INFO" "Pulling Docker images for version $VERSION..."
    
    cd "$PROJECT_DIR"
    
    # Set version in environment
    export VERSION="$VERSION"
    
    # Pull all images defined in docker-compose
    if ! docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" pull; then
        error_exit "Failed to pull Docker images"
    fi
    
    log "INFO" "Docker images pulled successfully"
}

# Health check function
health_check() {
    local url=$1
    local max_attempts=${2:-30}
    local interval=${3:-10}
    
    log "INFO" "Performing health check on $url..."
    
    for i in $(seq 1 $max_attempts); do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log "INFO" "Health check passed on attempt $i"
            return 0
        fi
        
        log "DEBUG" "Health check attempt $i/$max_attempts failed, waiting ${interval}s..."
        sleep $interval
    done
    
    error_exit "Health check failed after $max_attempts attempts"
}

# Rolling deployment
rolling_deployment() {
    log "INFO" "Starting rolling deployment..."
    
    cd "$PROJECT_DIR"
    export VERSION="$VERSION"
    
    # Get list of services to update
    local services=$(docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" config --services | grep -E '^company-api')
    
    # Check if we have multiple instances for rolling update
    local instance_count=$(docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" ps -q company-api | wc -l)
    
    if [[ $instance_count -gt 1 ]]; then
        log "INFO" "Performing rolling update on $instance_count instances"
        
        # Update instances one by one
        for i in $(seq 1 $instance_count); do
            local instance_name="company-api-$i"
            
            log "INFO" "Updating instance $instance_name..."
            
            # Stop instance
            docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" stop "$instance_name" || true
            
            # Remove old container
            docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" rm -f "$instance_name" || true
            
            # Start new instance
            docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" up -d "$instance_name"
            
            # Wait for health check
            sleep 30
            health_check "http://localhost:8000/api/v1/health"
            
            log "INFO" "Instance $instance_name updated successfully"
            sleep 10  # Brief pause between instances
        done
    else
        log "INFO" "Single instance deployment"
        
        # Standard deployment
        docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" up -d
        
        # Wait for services to start
        sleep 60
        health_check "http://localhost:8000/api/v1/health"
    fi
    
    log "INFO" "Rolling deployment completed"
}

# Update supporting services
update_supporting_services() {
    log "INFO" "Updating supporting services..."
    
    cd "$PROJECT_DIR"
    export VERSION="$VERSION"
    
    # Update monitoring services
    local monitoring_services="prometheus grafana alertmanager"
    
    for service in $monitoring_services; do
        if docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" ps -q "$service" > /dev/null 2>&1; then
            log "INFO" "Updating $service..."
            docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" up -d "$service"
        fi
    done
    
    # Update log management services
    local logging_services="elasticsearch logstash kibana filebeat"
    
    for service in $logging_services; do
        if docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" ps -q "$service" > /dev/null 2>&1; then
            log "INFO" "Updating $service..."
            docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" up -d "$service"
        fi
    done
    
    log "INFO" "Supporting services updated"
}

# Post-deployment verification
post_deployment_verification() {
    log "INFO" "Running post-deployment verification..."
    
    # Extended health checks
    health_check "http://localhost:8000/api/v1/health" 30 5
    health_check "http://localhost:8000/api/v1/health/detailed" 10 5
    health_check "http://localhost:8000/api/v1/company/health" 10 5
    
    # Test basic functionality
    log "INFO" "Testing basic API functionality..."
    
    local test_response=$(curl -s -w "%{http_code}" -o /tmp/health_check_response \
        "http://localhost:8000/api/v1/health")
    
    if [[ "$test_response" != "200" ]]; then
        error_exit "API health check returned status: $test_response"
    fi
    
    # Check if response contains expected fields
    if ! grep -q "status.*healthy" /tmp/health_check_response; then
        error_exit "API health check response does not contain healthy status"
    fi
    
    # Test company extraction endpoint (basic smoke test)
    log "INFO" "Testing company extraction endpoint..."
    
    local extract_test=$(curl -s -w "%{http_code}" -o /tmp/extract_response \
        -H "Content-Type: application/json" \
        -d '{"company_name": "Test Company", "extraction_mode": "basic"}' \
        "http://localhost:8000/api/v1/company/extract" || echo "000")
    
    # We expect this to either succeed (200) or fail gracefully (4xx, 5xx)
    if [[ "$extract_test" == "000" ]]; then
        error_exit "Company extraction endpoint is not responding"
    fi
    
    log "INFO" "API functionality tests passed"
    
    # Check service dependencies
    log "INFO" "Verifying service dependencies..."
    
    # Check Redis
    if ! docker exec redis redis-cli ping | grep -q PONG; then
        error_exit "Redis is not responding"
    fi
    
    # Check if monitoring is working
    if curl -f -s "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
        log "INFO" "Prometheus is healthy"
    else
        log "WARN" "Prometheus health check failed"
    fi
    
    # Check Grafana
    if curl -f -s "http://localhost:3000/api/health" > /dev/null 2>&1; then
        log "INFO" "Grafana is healthy"
    else
        log "WARN" "Grafana health check failed"
    fi
    
    log "INFO" "Post-deployment verification completed"
}

# Database migration (if needed)
run_migrations() {
    log "INFO" "Checking for database migrations..."
    
    # Check if there are any pending migrations
    if [[ -f "$PROJECT_DIR/migrations/pending.txt" ]]; then
        log "INFO" "Running database migrations..."
        
        # Run migration container
        docker run --rm \
            --network company-api-network \
            -e REDIS_URL=redis://redis:6379/0 \
            -v "$PROJECT_DIR/migrations:/migrations" \
            "company-extraction-api:$VERSION" \
            python -m migrations.run
        
        log "INFO" "Database migrations completed"
    else
        log "INFO" "No pending migrations found"
    fi
}

# Rollback function
rollback() {
    log "WARN" "Initiating rollback..."
    
    if [[ -f /tmp/current_backup_name ]]; then
        local backup_name=$(cat /tmp/current_backup_name)
        log "INFO" "Rolling back to backup: $backup_name"
        
        # Restore configuration
        if [[ -f "/opt/backups/company-extraction-api/$backup_name-config.tar.gz" ]]; then
            tar -xzf "/opt/backups/company-extraction-api/$backup_name-config.tar.gz" \
                -C "$PROJECT_DIR"
        fi
        
        # Restart with previous configuration
        cd "$PROJECT_DIR"
        docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" down
        docker-compose -f "deployment/docker-compose.$ENVIRONMENT.yml" up -d
        
        log "INFO" "Rollback completed"
    else
        log "ERROR" "No backup found for rollback"
        exit 1
    fi
}

# Notification functions
send_notification() {
    local status=$1
    local message=$2
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local emoji="📋"
        [[ "$status" == "success" ]] && emoji="✅"
        [[ "$status" == "error" ]] && emoji="❌"
        [[ "$status" == "warning" ]] && emoji="⚠️"
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$emoji Company Extraction API Deployment: $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
    
    # Email notification (if configured)
    if command -v mail &> /dev/null && [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        echo "$message" | mail -s "Company Extraction API Deployment $status" "$NOTIFICATION_EMAIL" || true
    fi
}

# Main deployment function
main() {
    log "INFO" "Starting deployment of Company Extraction API version $VERSION to $ENVIRONMENT"
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Source environment-specific configuration
    if [[ -f "$PROJECT_DIR/.env.$ENVIRONMENT" ]]; then
        set -a
        source "$PROJECT_DIR/.env.$ENVIRONMENT"
        set +a
    fi
    
    send_notification "info" "Starting deployment of version $VERSION to $ENVIRONMENT"
    
    # Run deployment steps
    pre_deployment_checks
    backup_current_state
    pull_images
    run_migrations
    rolling_deployment
    update_supporting_services
    post_deployment_verification
    
    # Cleanup old images and containers
    log "INFO" "Cleaning up old images..."
    docker system prune -f || true
    
    log "INFO" "Deployment completed successfully!"
    send_notification "success" "Version $VERSION deployed successfully to $ENVIRONMENT"
    
    # Display deployment summary
    cat << EOF

====================================
 Deployment Summary
====================================
Version:     $VERSION
Environment: $ENVIRONMENT
Started:     $(head -1 "$LOG_FILE" | cut -d' ' -f1-2)
Completed:   $(date '+%Y-%m-%d %H:%M:%S')
Log File:    $LOG_FILE

Service Status:
$(docker-compose -f "$PROJECT_DIR/deployment/docker-compose.$ENVIRONMENT.yml" ps)

====================================

EOF
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Check arguments
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <version> [environment]"
        echo "Example: $0 v1.2.3 production"
        exit 1
    fi
    
    # Run main function with error handling
    if ! main "$@"; then
        log "ERROR" "Deployment failed!"
        send_notification "error" "Deployment of version $VERSION to $ENVIRONMENT failed"
        
        # Ask for rollback
        echo -n "Do you want to rollback? (y/N): "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rollback
        fi
        
        exit 1
    fi
fi