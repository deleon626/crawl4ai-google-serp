# Deployment Guide

This guide covers deployment strategies for the Company Information Extraction API in various environments from development to production scale.

## Quick Start Deployment

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd crawl4ai_GoogleSERP

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start services
./run.sh  # Unix/Linux/macOS
# OR
run.bat   # Windows
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Production Deployment Options

### 1. Docker Container Deployment

**Recommended for**: Small to medium scale deployments, cloud platforms

```bash
# Build production image
docker build -t company-extraction-api:latest .

# Run with production configuration
docker run -d \
  --name company-api \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e BRIGHT_DATA_TOKEN=your_token \
  -e REDIS_URL=redis://redis:6379/0 \
  --restart unless-stopped \
  company-extraction-api:latest
```

### 2. Kubernetes Deployment

**Recommended for**: Enterprise scale, high availability requirements

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/
```

### 3. Cloud Platform Deployment

**Recommended for**: Managed services, serverless scaling

- [AWS ECS/Fargate](./cloud/aws-deployment.md)
- [Google Cloud Run](./cloud/gcp-deployment.md)
- [Azure Container Instances](./cloud/azure-deployment.md)

## Infrastructure Requirements

### Minimum Requirements

| Resource | Development | Production |
|----------|-------------|------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB | 100 GB |
| Network | 10 Mbps | 100 Mbps |

### Recommended Requirements

| Resource | Small Scale | Medium Scale | Large Scale |
|----------|-------------|--------------|-------------|
| CPU | 4 cores | 8 cores | 16+ cores |
| RAM | 8 GB | 16 GB | 32+ GB |
| Storage | 100 GB | 500 GB | 1+ TB |
| Network | 100 Mbps | 1 Gbps | 10+ Gbps |

### External Dependencies

#### Required Services

1. **Redis** - Caching and session storage
   - Version: 6.0+
   - Memory: 2-8 GB depending on cache size
   - Persistence: Optional (RDB recommended)

2. **Internet Access** - For external API calls
   - Bright Data SERP API access
   - Web crawling capabilities
   - DNS resolution

#### Optional Services

1. **PostgreSQL** - For persistent storage (if enabled)
   - Version: 12+
   - Storage: 100+ GB

2. **Monitoring Stack**
   - Prometheus + Grafana
   - ELK Stack (Elasticsearch, Logstash, Kibana)

## Environment Configuration

### Environment Variables

```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# External APIs
BRIGHT_DATA_TOKEN=your_bright_data_token
BRIGHT_DATA_ZONE=serp_api1

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=100

# Performance Configuration
MAX_CONCURRENT_EXTRACTIONS=10
MAX_CONCURRENT_SEARCHES=15
MAX_CONCURRENT_CRAWLS=12
BATCH_PROCESSING_ENABLED=true

# Cache Configuration
CACHE_ENABLED=true
COMPANY_CACHE_TTL=86400
SERP_CACHE_TTL=21600

# Resource Limits
MAX_MEMORY_MB=1024
MAX_CPU_PERCENT=80.0
CONNECTION_POOL_SIZE=50

# Security (Production)
API_KEY_REQUIRED=true
RATE_LIMITING_ENABLED=true
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Monitoring
PERFORMANCE_MONITORING_ENABLED=true
METRICS_RETENTION_HOURS=168
LOG_LEVEL=INFO

# Health Checks
HEALTH_CHECK_TIMEOUT=30
EXTERNAL_SERVICE_TIMEOUT=10
```

### Configuration Validation

```bash
# Validate configuration
python -c "
from config.settings import Settings
settings = Settings()
print('Configuration valid!')
print(f'Environment: {settings.ENVIRONMENT}')
print(f'Redis URL: {settings.REDIS_URL}')
"
```

## Deployment Strategies

### 1. Blue-Green Deployment

**Benefits**: Zero downtime, easy rollback

```bash
# Deploy to green environment
docker-compose -f docker-compose.green.yml up -d

# Health check green environment
curl http://green.yourdomain.com/api/v1/health

# Switch traffic (update load balancer)
# Shutdown blue environment after validation
```

### 2. Rolling Deployment

**Benefits**: Resource efficient, gradual rollout

```bash
# Rolling update with Kubernetes
kubectl rollout restart deployment/company-extraction-api
kubectl rollout status deployment/company-extraction-api
```

### 3. Canary Deployment

**Benefits**: Risk mitigation, performance validation

```bash
# Deploy canary (10% traffic)
kubectl apply -f deployment/kubernetes/canary.yaml

# Monitor metrics and gradually increase traffic
# Full deployment after validation
```

## Load Balancing

### Nginx Configuration

```nginx
upstream company_api {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://company_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://company_api/api/v1/health;
    }
}
```

### HAProxy Configuration

```haproxy
global
    maxconn 4096
    log stdout local0
    
defaults
    mode http
    timeout connect 5000ms
    timeout client 300000ms
    timeout server 300000ms
    option httplog
    
frontend company_api_frontend
    bind *:80
    # Rate limiting (adjust as needed)
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request reject if { sc_http_req_rate(0) gt 20 }
    
    default_backend company_api_backend
    
backend company_api_backend
    balance roundrobin
    option httpchk GET /api/v1/health
    
    server api1 api1:8000 check inter 30s
    server api2 api2:8000 check inter 30s
    server api3 api3:8000 check inter 30s
```

## Database Configuration

### Redis Configuration

```redis
# redis.conf for production

# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password
rename-command FLUSHDB ""
rename-command FLUSHALL ""

# Performance
tcp-keepalive 300
timeout 300
```

### PostgreSQL Configuration (Optional)

```sql
-- Create database and user
CREATE DATABASE company_extraction;
CREATE USER company_api WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE company_extraction TO company_api;

-- Performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

## Security Configuration

### SSL/TLS Setup

```bash
# Generate SSL certificate (Let's Encrypt)
certbot --nginx -d api.yourdomain.com

# Or use existing certificates
cp /path/to/certificate.crt /etc/nginx/ssl/
cp /path/to/private.key /etc/nginx/ssl/
```

### Firewall Configuration

```bash
# UFW (Ubuntu Firewall)
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow from 10.0.0.0/8 to any port 6379  # Redis (internal network only)
ufw enable

# iptables alternative
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 6379 -s 10.0.0.0/8 -j ACCEPT
```

### API Security

```python
# Enable API key authentication
API_KEY_REQUIRED=true
API_KEY_HEADER=X-API-Key

# Configure CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_CREDENTIALS=true

# Rate limiting
RATE_LIMITING_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
```

## Monitoring and Observability

### Health Checks

```bash
# Application health check
curl http://localhost:8000/api/v1/health

# Detailed health check with dependencies
curl http://localhost:8000/api/v1/health/detailed

# Company service health
curl http://localhost:8000/api/v1/company/health
```

### Metrics Collection

```python
# Prometheus metrics endpoint
GET /metrics

# Key metrics to monitor:
# - Request rate and latency
# - Error rates by endpoint
# - Cache hit/miss ratios
# - Resource utilization
# - External API response times
```

### Log Management

```yaml
# docker-compose.yml logging configuration
services:
  company-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Backup and Disaster Recovery

### Redis Backup

```bash
# Automated Redis backup
#!/bin/bash
BACKUP_DIR="/opt/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/dump_$DATE.rdb

# Compress and clean old backups
gzip $BACKUP_DIR/dump_$DATE.rdb
find $BACKUP_DIR -name "*.rdb.gz" -mtime +7 -delete
```

### Application Backup

```bash
# Backup configuration and logs
tar -czf app_backup_$(date +%Y%m%d).tar.gz \
    .env \
    logs/ \
    deployment/
```

### Disaster Recovery Plan

1. **Service Failure**: Automatic restart with health checks
2. **Data Loss**: Restore from Redis backup
3. **Complete System Failure**: Deploy from infrastructure as code
4. **Regional Outage**: Failover to secondary region

## Performance Tuning

### Application Tuning

```python
# Optimize concurrent processing
MAX_CONCURRENT_EXTRACTIONS=8  # Based on CPU cores
MAX_CONCURRENT_SEARCHES=12     # Higher for I/O bound operations
MAX_CONCURRENT_CRAWLS=10       # Balance between speed and resources

# Cache optimization
COMPANY_CACHE_TTL=86400        # 24 hours
SERP_CACHE_TTL=21600          # 6 hours
CACHE_MAX_MEMORY=512          # MB

# Connection pooling
CONNECTION_POOL_SIZE=50        # Adjust based on concurrent load
HTTP_TIMEOUT=30               # Seconds
```

### System Tuning

```bash
# Linux system optimizations
echo 'net.core.somaxconn = 1024' >> /etc/sysctl.conf
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 1024' >> /etc/sysctl.conf
echo 'fs.file-max = 65536' >> /etc/sysctl.conf

# Apply changes
sysctl -p
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check Redis memory usage: `redis-cli INFO memory`
   - Monitor application memory: `ps aux | grep python`
   - Adjust cache TTL and max memory settings

2. **Slow Response Times**
   - Check external API latency
   - Monitor database query performance
   - Verify network connectivity

3. **Service Unavailable**
   - Check health endpoints
   - Verify external dependencies
   - Review application logs

### Debug Commands

```bash
# Container logs
docker logs company-extraction-api

# Resource usage
docker stats

# Network connectivity
docker exec company-extraction-api ping bright-data-api.com

# Redis connectivity
docker exec redis redis-cli ping
```

## Scaling Strategies

### Horizontal Scaling

```bash
# Scale with Docker Compose
docker-compose up --scale company-api=3

# Scale with Kubernetes
kubectl scale deployment company-extraction-api --replicas=5
```

### Vertical Scaling

```yaml
# Docker resource limits
services:
  company-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Auto-scaling

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: company-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: company-extraction-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Next Steps

1. Review [infrastructure-specific deployment guides](./cloud/)
2. Set up [monitoring and alerting](../operations/monitoring.md)
3. Configure [security measures](../operations/security.md)
4. Plan [backup and disaster recovery](../operations/backup-recovery.md)
5. Implement [CI/CD pipelines](./cicd/)

## Support

For deployment issues:
- Check [troubleshooting guide](../operations/troubleshooting.md)
- Review [system requirements](./requirements.md)
- Contact technical support with deployment logs