# Docker Deployment Guide

Complete guide for deploying the Company Information Extraction API using Docker and Docker Compose in various environments.

## Overview

Docker deployment provides:
- ✅ Consistent runtime environment across all platforms
- ✅ Easy scaling and resource management
- ✅ Simplified dependency management
- ✅ Production-ready configuration options
- ✅ Built-in service discovery and networking

## Quick Start

### 1. Prerequisites

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2. Basic Deployment

```bash
# Clone repository
git clone <repository-url>
cd crawl4ai_GoogleSERP

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start services
docker-compose up -d
```

### 3. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test API
curl http://localhost:8000/api/v1/health
```

## Docker Images

### Application Image

The main application image is built from the provided `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-stage Production Image

For optimized production deployment:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Docker Compose Configurations

### Development Configuration

`docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  company-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - .:/app
      - /app/__pycache__
    depends_on:
      - redis
    restart: unless-stopped
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis_data:
```

### Production Configuration

`docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  company-api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - REDIS_URL=redis://redis:6379/0
      - MAX_WORKERS=4
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.2'
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - company-api
    restart: unless-stopped

volumes:
  redis_data:
    driver: local
```

### High Availability Configuration

`docker-compose.ha.yml`:

```yaml
version: '3.8'

services:
  company-api-1:
    build: .
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis-master:6379/0
    env_file:
      - .env
    depends_on:
      - redis-master
    restart: unless-stopped
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  company-api-2:
    build: .
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis-master:6379/0
    env_file:
      - .env
    depends_on:
      - redis-master
    restart: unless-stopped
    deploy:
      replicas: 2

  redis-master:
    image: redis:7-alpine
    volumes:
      - redis_master_data:/data
      - ./config/redis-master.conf:/etc/redis/redis.conf
    command: redis-server /etc/redis/redis.conf
    restart: unless-stopped
    ports:
      - "6379:6379"

  redis-replica:
    image: redis:7-alpine
    volumes:
      - redis_replica_data:/data
      - ./config/redis-replica.conf:/etc/redis/redis.conf
    command: redis-server /etc/redis/redis.conf
    depends_on:
      - redis-master
    restart: unless-stopped

  haproxy:
    image: haproxy:2.4-alpine
    ports:
      - "80:80"
      - "443:443"
      - "8404:8404"  # Stats page
    volumes:
      - ./config/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg
      - ./ssl:/etc/ssl/certs
    depends_on:
      - company-api-1
      - company-api-2
    restart: unless-stopped

volumes:
  redis_master_data:
  redis_replica_data:
```

## Environment Configuration

### Environment Files

`.env.production`:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=4

# External APIs
BRIGHT_DATA_TOKEN=your_production_token
BRIGHT_DATA_ZONE=serp_api1

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=100
REDIS_PASSWORD=secure_redis_password

# Performance
MAX_CONCURRENT_EXTRACTIONS=10
MAX_CONCURRENT_SEARCHES=15
MAX_CONCURRENT_CRAWLS=12
BATCH_PROCESSING_ENABLED=true

# Caching
CACHE_ENABLED=true
COMPANY_CACHE_TTL=86400
SERP_CACHE_TTL=21600

# Security
API_KEY_REQUIRED=true
RATE_LIMITING_ENABLED=true
CORS_ORIGINS=https://yourdomain.com

# Monitoring
PERFORMANCE_MONITORING_ENABLED=true
LOG_LEVEL=INFO
METRICS_RETENTION_HOURS=168

# Resource Limits
MAX_MEMORY_MB=2048
MAX_CPU_PERCENT=80.0
CONNECTION_POOL_SIZE=50
```

### Docker Environment Variables

```bash
# Pass environment variables to containers
docker run -d \
  --name company-api \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e BRIGHT_DATA_TOKEN=${BRIGHT_DATA_TOKEN} \
  -e REDIS_URL=redis://redis:6379/0 \
  --env-file .env.production \
  company-extraction-api:latest
```

## Service Configuration

### Redis Configuration

`config/redis.conf`:

```redis
# Basic settings
port 6379
bind 0.0.0.0
timeout 300
tcp-keepalive 300

# Memory management
maxmemory 1gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_secure_redis_password
rename-command FLUSHDB ""
rename-command FLUSHALL ""

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Append only file
appendonly yes
appendfsync everysec
```

### Nginx Configuration

`config/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream company_api {
        least_conn;
        server company-api-1:8000 max_fails=3 fail_timeout=30s;
        server company-api-2:8000 max_fails=3 fail_timeout=30s;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    server {
        listen 80;
        server_name api.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;
        
        # SSL configuration
        ssl_certificate /etc/nginx/ssl/certificate.crt;
        ssl_certificate_key /etc/nginx/ssl/private.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        location / {
            proxy_pass http://company_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts for long-running extractions
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }
        
        location /health {
            access_log off;
            proxy_pass http://company_api/api/v1/health;
        }
    }
}
```

## Deployment Commands

### Development Deployment

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Rebuild after code changes
docker-compose -f docker-compose.dev.yml up --build -d
```

### Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Scale API instances
docker-compose -f docker-compose.prod.yml up --scale company-api=3 -d

# Rolling updates
docker-compose -f docker-compose.prod.yml up -d --no-deps company-api
```

### High Availability Deployment

```bash
# Deploy HA stack
docker-compose -f docker-compose.ha.yml up -d

# Check service status
docker-compose -f docker-compose.ha.yml ps

# View HAProxy stats
open http://localhost:8404/stats
```

## Monitoring and Logging

### Container Monitoring

```bash
# Resource usage
docker stats

# Service health
docker-compose ps

# Individual service logs
docker-compose logs company-api
docker-compose logs redis
docker-compose logs nginx
```

### Log Management

`docker-compose.logging.yml`:

```yaml
version: '3.8'

services:
  company-api:
    # ... other configuration
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=company-api"

  redis:
    # ... other configuration
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  log-aggregator:
    image: fluent/fluent-bit:latest
    volumes:
      - /var/log:/var/log:ro
      - ./config/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf
    ports:
      - "24224:24224"
```

### Metrics Collection

Add Prometheus monitoring:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana:/etc/grafana/provisioning

volumes:
  prometheus_data:
  grafana_data:
```

## Security Considerations

### Container Security

```bash
# Run containers as non-root user
USER 1001:1001

# Use minimal base images
FROM python:3.11-alpine

# Scan images for vulnerabilities
docker scan company-extraction-api:latest

# Use Docker secrets for sensitive data
docker secret create bright_data_token ./bright_data_token.txt
```

### Network Security

```yaml
services:
  company-api:
    networks:
      - internal
      - web
    
  redis:
    networks:
      - internal
    # Redis not exposed to external network

networks:
  internal:
    driver: bridge
    internal: true
  web:
    driver: bridge
```

### Resource Limits

```yaml
services:
  company-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
          pids: 1000
        reservations:
          cpus: '1.0'
          memory: 2G
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
```

## Backup and Recovery

### Automated Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup Redis data
docker exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb $BACKUP_DIR/redis_dump.rdb

# Backup application configuration
docker cp company-api:/app/.env $BACKUP_DIR/app_config.env

# Backup logs
docker logs company-api > $BACKUP_DIR/app_logs.txt

# Compress backup
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Clean old backups (keep last 7 days)
find /opt/backups -name "*.tar.gz" -mtime +7 -delete
```

### Recovery Process

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
RESTORE_DIR="/tmp/restore"

# Extract backup
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# Stop services
docker-compose down

# Restore Redis data
docker run --rm -v redis_data:/data -v $RESTORE_DIR:/backup alpine \
    cp /backup/redis_dump.rdb /data/dump.rdb

# Restore configuration
cp $RESTORE_DIR/app_config.env ./.env

# Start services
docker-compose up -d

# Verify recovery
sleep 30
curl http://localhost:8000/api/v1/health
```

## Troubleshooting

### Common Issues

1. **Container Won't Start**
   ```bash
   # Check logs
   docker-compose logs company-api
   
   # Check resource limits
   docker system df
   docker system prune
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connectivity
   docker exec company-api ping redis
   docker exec redis redis-cli ping
   
   # Check Redis logs
   docker logs redis
   ```

3. **Performance Issues**
   ```bash
   # Monitor resource usage
   docker stats
   
   # Check external API connectivity
   docker exec company-api curl -I https://api.brightdata.com
   ```

### Debug Commands

```bash
# Enter container for debugging
docker exec -it company-api bash

# Check environment variables
docker exec company-api env | grep BRIGHT_DATA

# Test API endpoints
docker exec company-api curl http://localhost:8000/api/v1/health

# View real-time logs
docker-compose logs -f --tail=50
```

## Best Practices

### Image Optimization

1. **Use Multi-stage Builds**: Reduce final image size
2. **Minimize Layers**: Combine RUN commands where possible
3. **Use .dockerignore**: Exclude unnecessary files
4. **Pin Base Image Versions**: Ensure reproducible builds

### Configuration Management

1. **Use Environment Variables**: For configuration
2. **Separate Configs by Environment**: dev/staging/prod
3. **Use Docker Secrets**: For sensitive data
4. **Volume Management**: Persist important data

### Operational Excellence

1. **Health Checks**: Implement comprehensive health checks
2. **Resource Limits**: Set appropriate CPU/memory limits
3. **Logging Strategy**: Structured logging with log rotation
4. **Monitoring**: Comprehensive monitoring and alerting

## Next Steps

1. Set up [Kubernetes deployment](./kubernetes-deployment.md) for enterprise scale
2. Configure [cloud deployment](./cloud/) for managed services
3. Implement [CI/CD pipelines](./cicd/) for automated deployment
4. Set up [monitoring and alerting](../operations/monitoring.md)
5. Review [security hardening](../operations/security.md) guidelines