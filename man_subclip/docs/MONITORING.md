# Monitoring & Logging Guide

## Logging System

### Backend Logging

**Configuration**: `backend/src/utils/logger.py`

```python
from src.utils.logger import logger

# Use in your code
logger.info("Video uploaded successfully")
logger.warning("Proxy rendering taking longer than expected")
logger.error("Failed to extract clip", exc_info=True)
```

**Log Levels**:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors requiring immediate attention

**Log Format**:
```
2025-01-18 15:30:45 - video_platform - INFO - Video uploaded: sample.mp4
```

### Storage Cleanup

**Script**: `backend/scripts/storage_cleanup.py`

```bash
# Dry run (show what would be deleted)
python backend/scripts/storage_cleanup.py --dry-run

# Remove orphaned files only
python backend/scripts/storage_cleanup.py

# Remove files older than 30 days
python backend/scripts/storage_cleanup.py --days 30

# Dry run with age filter
python backend/scripts/storage_cleanup.py --dry-run --days 60
```

**Cron job** for automated cleanup:

```bash
# Run cleanup every Sunday at 2 AM
0 2 * * 0 cd /app && python backend/scripts/storage_cleanup.py >> /var/log/storage_cleanup.log 2>&1
```

## Monitoring Metrics

### Backend Metrics

**Request Latency**:

```python
# backend/src/main.py
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response
```

**Database Connection Pool**:

```python
# Monitor connection pool usage
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("Database connection established")

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")
```

### Storage Metrics

**Disk Usage**:

```bash
# Check disk usage
df -h /nas

# Check directory sizes
du -sh /nas/originals/*
du -sh /nas/proxy/*
du -sh /nas/clips/*
```

**File Count**:

```bash
# Count files by type
find /nas/originals -type f | wc -l
find /nas/proxy -type f -name "*.m3u8" | wc -l
find /nas/clips -type f | wc -l
```

### Application Metrics

**Video Processing**:
- Total videos uploaded
- Proxy rendering success rate
- Average proxy rendering time
- Clip extraction count
- Storage usage by category

**API Performance**:
- Requests per second (RPS)
- Average response time
- 95th percentile latency
- Error rate

## Health Checks

**Endpoint**: `GET /health`

```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T15:30:45Z",
  "checks": {
    "database": "ok",
    "storage": "ok",
    "disk_space": "ok"
  }
}
```

**Enhanced health check**:

```python
# backend/src/api/health.py
from fastapi import APIRouter
from src.database import engine
from src.config import get_settings
import shutil

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    checks = {}

    # Database check
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Storage check
    settings = get_settings()
    storage_paths = [
        settings.nas_originals_path,
        settings.nas_proxy_path,
        settings.nas_clips_path
    ]

    for path in storage_paths:
        if Path(path).exists():
            checks[f"storage_{Path(path).name}"] = "ok"
        else:
            checks[f"storage_{Path(path).name}"] = "missing"

    # Disk space check
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    checks["disk_free_gb"] = free_gb

    if free_gb < 10:
        checks["disk_space"] = "warning"
    else:
        checks["disk_space"] = "ok"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": status,
        "checks": checks
    }
```

## Alerting

### Disk Space Alerts

```bash
#!/bin/bash
# scripts/check_disk_space.sh

THRESHOLD=90  # Alert at 90% usage

USAGE=$(df -h /nas | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    echo "WARNING: Disk usage at ${USAGE}%"
    # Send alert (e.g., email, Slack, etc.)
fi
```

### Failed Proxy Rendering Alerts

```python
# Check for failed proxy renders
failed_count = db.query(Video).filter(Video.proxy_status == "failed").count()

if failed_count > 10:
    logger.critical(f"High number of failed proxy renders: {failed_count}")
    # Send alert
```

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

**Logstash configuration**:

```conf
# logstash.conf
input {
  file {
    path => "/var/log/video_platform/*.log"
    type => "video_platform"
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} - %{DATA:logger} - %{LOGLEVEL:level} - %{GREEDYDATA:message}" }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "video-platform-%{+YYYY.MM.dd}"
  }
}
```

### Grafana Dashboards

**Example queries**:
- Video uploads per hour
- Proxy rendering success rate
- Average clip extraction time
- Storage usage trends

## Best Practices

1. **Log rotation**: Use `logrotate` to prevent log files from growing too large
2. **Structured logging**: Use JSON format for easier parsing
3. **Correlation IDs**: Add request IDs to trace requests across services
4. **Sampling**: Log only a sample of high-volume requests in production
5. **Security**: Never log sensitive data (passwords, API keys, personal info)

## Maintenance Schedule

- **Daily**: Check logs for errors
- **Weekly**: Run storage cleanup script
- **Monthly**: Review storage usage trends
- **Quarterly**: Audit logging configuration
