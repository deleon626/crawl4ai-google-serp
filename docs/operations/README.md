# Operations Guide

This guide provides comprehensive operational procedures for monitoring, maintaining, and troubleshooting the Company Information Extraction API in production environments.

## Overview

The operations guide covers:
- **Monitoring**: Health checks, metrics, alerting, and performance tracking
- **Security**: Authentication, authorization, threat protection, and compliance
- **Maintenance**: Updates, backups, disaster recovery, and capacity planning
- **Troubleshooting**: Issue diagnosis, resolution procedures, and escalation paths

## Quick Reference

### System Health Dashboard
```bash
# Check overall system health
curl http://localhost:8000/api/v1/health/detailed

# Check specific service health
curl http://localhost:8000/api/v1/company/health

# Check batch processing statistics
curl http://localhost:8000/api/v1/company/batch/stats
```

### Emergency Procedures
1. **Service Down**: [Restart procedures](./troubleshooting.md#service-restart)
2. **High Error Rate**: [Error investigation](./troubleshooting.md#error-investigation)
3. **Performance Issues**: [Performance troubleshooting](./troubleshooting.md#performance-issues)
4. **Security Incident**: [Security response](./security.md#incident-response)

### Key Metrics to Monitor
- API response times (< 30s for standard extraction)
- Error rates (< 1% for all endpoints)
- Cache hit rates (> 70% for optimal performance)
- Resource utilization (CPU < 80%, Memory < 90%)
- External API success rates (> 95%)

## Monitoring and Alerting

### Health Check Endpoints

The API provides comprehensive health check endpoints:

#### Basic Health Check
```bash
GET /api/v1/health
```
Returns basic application health status.

#### Detailed Health Check
```bash
GET /api/v1/company/health
```
Returns comprehensive health information including:
- Service status
- Dependency health (Redis, external APIs)
- Resource utilization
- Performance metrics
- Recent error rates

#### Batch Processing Stats
```bash
GET /api/v1/company/batch/stats
```
Returns batch processing performance metrics and system utilization.

### Monitoring Stack Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'company-extraction-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Alert Rules
```yaml
# alert_rules.yml
groups:
  - name: company-extraction-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API response time is slow"
          description: "95th percentile response time is {{ $value }} seconds"
      
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis instance is not responding"
      
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90%"
      
      - alert: ExternalAPIFailure
        expr: external_api_success_rate < 0.95
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "External API success rate low"
          description: "Success rate is {{ $value }}"
```

#### Grafana Dashboards

Import the provided dashboard configurations:
- [System Overview Dashboard](./monitoring/grafana-system-dashboard.json)
- [API Performance Dashboard](./monitoring/grafana-api-dashboard.json)
- [Business Metrics Dashboard](./monitoring/grafana-business-dashboard.json)

### Log Management

#### Structured Logging Configuration
```python
# logging_config.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        },
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/application.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "INFO",
            "formatter": "json"
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "ERROR",
            "formatter": "json"
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        },
        "httpx": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False
        }
    }
}
```

#### ELK Stack Configuration
```yaml
# docker-compose.elk.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
  
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./config/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch
  
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## Security Operations

### Authentication and Authorization

#### API Key Management
```python
# api_key_management.py
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class APIKeyManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "api_key:"
    
    def generate_api_key(self, user_id: str, permissions: List[str] = None, 
                        expires_in_days: int = 365) -> str:
        """Generate a new API key for a user."""
        
        # Generate random key
        api_key = secrets.token_urlsafe(32)
        
        # Create key metadata
        key_data = {
            "user_id": user_id,
            "permissions": permissions or ["read", "extract"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat(),
            "active": True,
            "usage_count": 0,
            "last_used": None
        }
        
        # Store in Redis
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.redis.hset(f"{self.key_prefix}{key_hash}", mapping=key_data)
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate an API key and return user permissions."""
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_data = self.redis.hgetall(f"{self.key_prefix}{key_hash}")
        
        if not key_data:
            return None
        
        # Check if key is active
        if not key_data.get("active", "").lower() == "true":
            return None
        
        # Check expiration
        expires_at = datetime.fromisoformat(key_data.get("expires_at", ""))
        if datetime.utcnow() > expires_at:
            return None
        
        # Update usage statistics
        self.redis.hset(f"{self.key_prefix}{key_hash}", "last_used", 
                       datetime.utcnow().isoformat())
        self.redis.hincrby(f"{self.key_prefix}{key_hash}", "usage_count", 1)
        
        return {
            "user_id": key_data.get("user_id"),
            "permissions": key_data.get("permissions", "").split(","),
            "usage_count": int(key_data.get("usage_count", 0)) + 1
        }
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return self.redis.hset(f"{self.key_prefix}{key_hash}", "active", "false")
    
    def list_user_keys(self, user_id: str) -> List[Dict]:
        """List all API keys for a user."""
        
        keys = []
        for key in self.redis.scan_iter(match=f"{self.key_prefix}*"):
            key_data = self.redis.hgetall(key)
            if key_data.get("user_id") == user_id:
                keys.append({
                    "key_hash": key.decode().split(":")[-1],
                    "created_at": key_data.get("created_at"),
                    "expires_at": key_data.get("expires_at"),
                    "active": key_data.get("active"),
                    "usage_count": key_data.get("usage_count"),
                    "last_used": key_data.get("last_used")
                })
        
        return keys
```

#### Rate Limiting Implementation
```python
# rate_limiting.py
import time
from typing import Dict, Tuple
import redis
from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

class AdvancedRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, Dict]:
        """
        Check rate limit using sliding window algorithm.
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        
        now = time.time()
        pipeline = self.redis.pipeline()
        
        # Remove old entries
        pipeline.zremrangebyscore(key, 0, now - window)
        
        # Count current requests
        pipeline.zcard(key)
        
        # Add current request
        pipeline.zadd(key, {str(now): now})
        
        # Set expiration
        pipeline.expire(key, window)
        
        results = pipeline.execute()
        current_requests = results[1]
        
        # Check if limit exceeded
        if current_requests >= limit:
            # Remove the request we just added
            self.redis.zrem(key, str(now))
            
            # Calculate reset time
            oldest_request = self.redis.zrange(key, 0, 0, withscores=True)
            reset_time = oldest_request[0][1] + window if oldest_request else now + window
            
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": int(reset_time),
                "retry_after": int(reset_time - now)
            }
        
        return True, {
            "limit": limit,
            "remaining": limit - current_requests - 1,
            "reset": int(now + window)
        }

# FastAPI integration
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enhanced rate limiting decorator
def enhanced_rate_limit(rate: str, per_user: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request') or args[0]
            
            # Determine rate limit key
            if per_user and hasattr(request.state, 'user_id'):
                key = f"user:{request.state.user_id}"
            else:
                key = f"ip:{get_remote_address(request)}"
            
            # Parse rate string (e.g., "100/minute")
            limit, period = rate.split("/")
            limit = int(limit)
            window = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[period]
            
            # Check rate limit
            allowed, info = rate_limiter.check_rate_limit(key, limit, window)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset"]),
                        "Retry-After": str(info["retry_after"])
                    }
                )
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(info["reset"])
            
            return response
        
        return wrapper
    return decorator
```

### Security Monitoring

#### Security Event Detection
```python
# security_monitoring.py
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import geoip2.database
import re

class SecurityMonitor:
    def __init__(self, redis_client, geoip_db_path: str):
        self.redis = redis_client
        self.geoip_reader = geoip2.database.Reader(geoip_db_path)
        self.logger = logging.getLogger("security")
    
    def log_security_event(self, event_type: str, request_data: Dict, 
                          severity: str = "info"):
        """Log security events for monitoring and analysis."""
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "ip_address": request_data.get("ip"),
            "user_agent": request_data.get("user_agent"),
            "endpoint": request_data.get("endpoint"),
            "method": request_data.get("method"),
            "status_code": request_data.get("status_code"),
            "response_time": request_data.get("response_time"),
            "user_id": request_data.get("user_id"),
            "api_key_hash": request_data.get("api_key_hash")
        }
        
        # Add geolocation data
        try:
            if request_data.get("ip"):
                response = self.geoip_reader.city(request_data["ip"])
                event["country"] = response.country.name
                event["city"] = response.city.name
                event["coordinates"] = {
                    "lat": float(response.location.latitude or 0),
                    "lon": float(response.location.longitude or 0)
                }
        except Exception:
            pass  # Ignore geolocation errors
        
        # Store event
        self.redis.lpush("security_events", json.dumps(event))
        self.redis.ltrim("security_events", 0, 10000)  # Keep last 10k events
        
        # Log based on severity
        if severity == "critical":
            self.logger.critical(f"SECURITY ALERT: {event_type}", extra=event)
        elif severity == "warning":
            self.logger.warning(f"Security event: {event_type}", extra=event)
        else:
            self.logger.info(f"Security event: {event_type}", extra=event)
    
    def detect_suspicious_activity(self, ip_address: str) -> List[str]:
        """Detect suspicious activity patterns."""
        
        alerts = []
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        # Check for high request rate from single IP
        request_count = self.redis.zcount(f"requests:{ip_address}", 
                                         hour_ago.timestamp(), now.timestamp())
        if request_count > 1000:  # More than 1000 requests per hour
            alerts.append("HIGH_REQUEST_RATE")
        
        # Check for multiple failed authentications
        failed_auth_count = self.redis.get(f"failed_auth:{ip_address}") or 0
        if int(failed_auth_count) > 10:
            alerts.append("MULTIPLE_AUTH_FAILURES")
        
        # Check for suspicious user agents
        user_agents = self.redis.smembers(f"user_agents:{ip_address}")
        suspicious_patterns = [
            r"sqlmap", r"nmap", r"nikto", r"dirb", r"gobuster",
            r"python-requests/\d+\.\d+\.\d+$",  # Raw requests without custom UA
            r"curl/\d+\.\d+\.\d+$"  # Raw curl without custom UA
        ]
        
        for ua in user_agents:
            ua_str = ua.decode() if isinstance(ua, bytes) else ua
            for pattern in suspicious_patterns:
                if re.search(pattern, ua_str, re.IGNORECASE):
                    alerts.append("SUSPICIOUS_USER_AGENT")
                    break
        
        # Check for error rate
        error_count = self.redis.get(f"errors:{ip_address}") or 0
        total_requests = self.redis.get(f"total_requests:{ip_address}") or 1
        error_rate = int(error_count) / int(total_requests)
        if error_rate > 0.5:  # More than 50% error rate
            alerts.append("HIGH_ERROR_RATE")
        
        return list(set(alerts))  # Remove duplicates
    
    def block_ip(self, ip_address: str, duration_hours: int = 24, reason: str = None):
        """Block an IP address for a specified duration."""
        
        block_data = {
            "blocked_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat(),
            "reason": reason or "Suspicious activity detected",
            "blocked_by": "system"
        }
        
        self.redis.hset(f"blocked_ip:{ip_address}", mapping=block_data)
        self.redis.expire(f"blocked_ip:{ip_address}", duration_hours * 3600)
        
        self.log_security_event("IP_BLOCKED", {
            "ip": ip_address,
            "reason": reason,
            "duration_hours": duration_hours
        }, severity="warning")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is currently blocked."""
        
        block_data = self.redis.hgetall(f"blocked_ip:{ip_address}")
        if not block_data:
            return False
        
        expires_at = datetime.fromisoformat(block_data.get("expires_at", ""))
        return datetime.utcnow() < expires_at
```

## Maintenance Operations

### Update Procedures

#### Rolling Update Strategy
```bash
#!/bin/bash
# rolling_update.sh

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Starting rolling update to version $VERSION"

# Pull new image
docker pull company-extraction-api:$VERSION

# Update instances one by one
INSTANCES=("api-1" "api-2" "api-3")

for instance in "${INSTANCES[@]}"; do
    echo "Updating $instance..."
    
    # Take instance out of load balancer
    curl -X POST http://load-balancer/admin/disable/$instance
    
    # Wait for existing requests to complete
    sleep 30
    
    # Stop old container
    docker stop $instance
    docker rm $instance
    
    # Start new container
    docker run -d \
        --name $instance \
        --network company-api-network \
        -e ENVIRONMENT=production \
        --env-file .env.production \
        company-extraction-api:$VERSION
    
    # Health check
    for i in {1..30}; do
        if curl -f http://$instance:8000/api/v1/health; then
            echo "$instance is healthy"
            break
        fi
        
        if [ $i -eq 30 ]; then
            echo "$instance failed health check"
            exit 1
        fi
        
        sleep 5
    done
    
    # Add back to load balancer
    curl -X POST http://load-balancer/admin/enable/$instance
    
    echo "$instance updated successfully"
    sleep 10
done

echo "Rolling update completed successfully"
```

#### Database Migration
```python
# migration_manager.py
import asyncio
import redis
import json
from datetime import datetime
from typing import Dict, List

class MigrationManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.migration_key = "migrations:applied"
    
    async def apply_migration(self, migration_id: str, migration_func, rollback_func=None):
        """Apply a data migration with rollback capability."""
        
        # Check if migration already applied
        if self.is_migration_applied(migration_id):
            print(f"Migration {migration_id} already applied")
            return
        
        # Create migration record
        migration_record = {
            "id": migration_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running"
        }
        
        self.redis.hset(f"migration:{migration_id}", mapping=migration_record)
        
        try:
            # Run migration
            await migration_func()
            
            # Mark as completed
            self.redis.hset(f"migration:{migration_id}", "status", "completed")
            self.redis.hset(f"migration:{migration_id}", "completed_at", 
                           datetime.utcnow().isoformat())
            self.redis.sadd(self.migration_key, migration_id)
            
            print(f"Migration {migration_id} completed successfully")
            
        except Exception as e:
            # Mark as failed
            self.redis.hset(f"migration:{migration_id}", "status", "failed")
            self.redis.hset(f"migration:{migration_id}", "error", str(e))
            
            # Attempt rollback if provided
            if rollback_func:
                try:
                    await rollback_func()
                    print(f"Migration {migration_id} rolled back successfully")
                except Exception as rollback_error:
                    print(f"Rollback failed for {migration_id}: {rollback_error}")
            
            raise e
    
    def is_migration_applied(self, migration_id: str) -> bool:
        """Check if a migration has been applied."""
        return self.redis.sismember(self.migration_key, migration_id)
    
    def list_migrations(self) -> List[Dict]:
        """List all migration records."""
        migrations = []
        for key in self.redis.scan_iter(match="migration:*"):
            migration_data = self.redis.hgetall(key)
            migration_data["key"] = key.decode()
            migrations.append(migration_data)
        
        return sorted(migrations, key=lambda x: x.get("started_at", ""))

# Example migration
async def migrate_cache_keys_v2():
    """Example migration to update cache key format."""
    
    redis_client = redis.Redis.from_url("redis://localhost:6379/0")
    migration_manager = MigrationManager(redis_client)
    
    async def migration_func():
        # Find all old format cache keys
        old_keys = []
        for key in redis_client.scan_iter(match="company:*"):
            old_keys.append(key)
        
        print(f"Found {len(old_keys)} keys to migrate")
        
        # Migrate each key
        for old_key in old_keys:
            old_key_str = old_key.decode()
            company_name = old_key_str.split(":", 1)[1]
            
            # Create new key format
            new_key = f"company_v2:{company_name}"
            
            # Copy data
            data = redis_client.get(old_key)
            if data:
                redis_client.setex(new_key, 86400, data)  # 24 hour TTL
                
            # Delete old key
            redis_client.delete(old_key)
            
        print("Cache key migration completed")
    
    async def rollback_func():
        # Rollback logic if needed
        print("Rolling back cache key migration...")
        # Implementation depends on specific requirements
    
    await migration_manager.apply_migration(
        "migrate_cache_keys_v2", 
        migration_func, 
        rollback_func
    )

# Run migration
# asyncio.run(migrate_cache_keys_v2())
```

### Backup and Disaster Recovery

#### Automated Backup System
```bash
#!/bin/bash
# backup_system.sh

set -e

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR/daily/$DATE"

echo "Starting backup at $(date)"

# Backup Redis data
echo "Backing up Redis data..."
docker exec redis redis-cli BGSAVE
sleep 10  # Wait for background save to complete

docker cp redis:/data/dump.rdb "$BACKUP_DIR/daily/$DATE/redis_dump.rdb"
echo "Redis backup completed"

# Backup application configuration
echo "Backing up application configuration..."
tar -czf "$BACKUP_DIR/daily/$DATE/app_config.tar.gz" \
    .env.production \
    config/ \
    deployment/ \
    --exclude='*.log'

echo "Configuration backup completed"

# Backup application logs
echo "Backing up logs..."
tar -czf "$BACKUP_DIR/daily/$DATE/logs.tar.gz" logs/ --exclude='*.tmp'
echo "Log backup completed"

# Create backup manifest
cat > "$BACKUP_DIR/daily/$DATE/manifest.json" << EOF
{
  "backup_date": "$(date -Iseconds)",
  "backup_type": "daily",
  "components": [
    "redis_data",
    "app_config",
    "logs"
  ],
  "size": "$(du -sh $BACKUP_DIR/daily/$DATE | cut -f1)",
  "hostname": "$(hostname)",
  "version": "$(docker inspect company-extraction-api:latest --format='{{.Id}}')"
}
EOF

# Compress entire backup
echo "Compressing backup..."
cd "$BACKUP_DIR/daily"
tar -czf "${DATE}.tar.gz" "$DATE/"
rm -rf "$DATE/"

echo "Backup compressed: $BACKUP_DIR/daily/${DATE}.tar.gz"

# Upload to remote storage (example: S3)
if [ -n "$AWS_S3_BACKUP_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_DIR/daily/${DATE}.tar.gz" \
        "s3://$AWS_S3_BACKUP_BUCKET/daily/${DATE}.tar.gz" \
        --storage-class STANDARD_IA
    echo "S3 upload completed"
fi

# Clean old backups
echo "Cleaning old backups..."
find "$BACKUP_DIR/daily" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo "Old backups cleaned"

echo "Backup completed successfully at $(date)"

# Send notification (example: Slack)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"✅ Daily backup completed successfully for $(hostname) at $(date)\"}" \
        "$SLACK_WEBHOOK_URL"
fi
```

#### Disaster Recovery Procedures
```bash
#!/bin/bash
# disaster_recovery.sh

set -e

BACKUP_FILE=$1
RECOVERY_TYPE=${2:-"full"}  # full, redis-only, config-only

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file> [recovery_type]"
    echo "Recovery types: full, redis-only, config-only"
    exit 1
fi

echo "Starting disaster recovery from $BACKUP_FILE"
echo "Recovery type: $RECOVERY_TYPE"

# Create temporary recovery directory
RECOVERY_DIR="/tmp/recovery_$(date +%s)"
mkdir -p "$RECOVERY_DIR"

# Extract backup
echo "Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$RECOVERY_DIR"

# Find backup directory
BACKUP_DIR=$(find "$RECOVERY_DIR" -type d -name "*_*" | head -1)
if [ -z "$BACKUP_DIR" ]; then
    echo "Error: Could not find backup directory in archive"
    exit 1
fi

# Validate backup manifest
if [ -f "$BACKUP_DIR/manifest.json" ]; then
    echo "Backup manifest found:"
    cat "$BACKUP_DIR/manifest.json"
else
    echo "Warning: No backup manifest found"
fi

# Stop services for full recovery
if [ "$RECOVERY_TYPE" = "full" ]; then
    echo "Stopping services..."
    docker-compose down
fi

# Recovery based on type
case $RECOVERY_TYPE in
    "full"|"redis-only")
        if [ -f "$BACKUP_DIR/redis_dump.rdb" ]; then
            echo "Restoring Redis data..."
            
            # Stop Redis if running
            docker stop redis 2>/dev/null || true
            
            # Remove old data
            docker volume rm redis_data 2>/dev/null || true
            
            # Create new volume and restore data
            docker volume create redis_data
            docker run --rm \
                -v redis_data:/data \
                -v "$BACKUP_DIR:/backup" \
                alpine \
                cp /backup/redis_dump.rdb /data/dump.rdb
            
            echo "Redis data restored"
        else
            echo "Warning: Redis backup not found"
        fi
        ;;&  # Continue to next case
    
    "full"|"config-only")
        if [ -f "$BACKUP_DIR/app_config.tar.gz" ]; then
            echo "Restoring configuration..."
            
            # Backup current config
            tar -czf "/tmp/config_backup_$(date +%s).tar.gz" \
                .env.production config/ deployment/ 2>/dev/null || true
            
            # Restore configuration
            tar -xzf "$BACKUP_DIR/app_config.tar.gz" -C .
            
            echo "Configuration restored"
        else
            echo "Warning: Configuration backup not found"
        fi
        ;;
esac

# Restore logs if requested and available
if [ "$RECOVERY_TYPE" = "full" ] && [ -f "$BACKUP_DIR/logs.tar.gz" ]; then
    echo "Restoring logs..."
    tar -xzf "$BACKUP_DIR/logs.tar.gz" -C .
    echo "Logs restored"
fi

# Start services
if [ "$RECOVERY_TYPE" = "full" ]; then
    echo "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    echo "Waiting for services to start..."
    sleep 30
    
    # Health check
    for i in {1..12}; do  # Try for 2 minutes
        if curl -f http://localhost:8000/api/v1/health; then
            echo "✅ Services are healthy"
            break
        fi
        
        if [ $i -eq 12 ]; then
            echo "❌ Services failed to start properly"
            echo "Check logs: docker-compose logs"
            exit 1
        fi
        
        echo "Waiting for services... ($i/12)"
        sleep 10
    done
fi

# Cleanup
echo "Cleaning up temporary files..."
rm -rf "$RECOVERY_DIR"

echo "✅ Disaster recovery completed successfully"

# Send notification
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🔄 Disaster recovery completed successfully for $(hostname) using backup: $BACKUP_FILE\"}" \
        "$SLACK_WEBHOOK_URL"
fi
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

1. **API Response Times**
   - Target: < 30s for standard extraction
   - Alert: > 60s for 95th percentile

2. **Throughput**
   - Target: > 100 extractions per hour
   - Alert: < 50 extractions per hour

3. **Error Rates**
   - Target: < 1% overall error rate
   - Alert: > 5% error rate over 10 minutes

4. **Cache Performance**
   - Target: > 70% cache hit rate
   - Alert: < 50% cache hit rate

5. **Resource Utilization**
   - CPU: Alert at > 80% sustained usage
   - Memory: Alert at > 90% usage
   - Disk: Alert at > 85% usage

### Performance Optimization Playbook

#### High Response Time Resolution
1. Check external API latency
2. Verify database/cache performance
3. Analyze request patterns
4. Check resource utilization
5. Scale horizontally if needed

#### High Error Rate Resolution
1. Check external service status
2. Review recent deployments
3. Analyze error patterns
4. Check resource constraints
5. Implement circuit breakers

#### Low Cache Hit Rate Resolution
1. Analyze cache key patterns
2. Check cache expiration settings
3. Verify cache size limits
4. Review request patterns
5. Optimize cache strategy

## Next Steps

1. **Implement Monitoring**: Set up Prometheus, Grafana, and log aggregation
2. **Configure Alerting**: Create alert rules and notification channels
3. **Security Hardening**: Implement authentication, rate limiting, and monitoring
4. **Backup Strategy**: Set up automated backups and test disaster recovery
5. **Performance Baseline**: Establish performance baselines and optimization targets
6. **Incident Response**: Create incident response procedures and escalation paths

## Related Documentation

- [Monitoring Setup Guide](./monitoring.md)
- [Security Implementation Guide](./security.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Backup and Recovery Guide](./backup-recovery.md)