# Deployment Guide

## Overview

This guide covers deployment options for the Video Proxy & Subclip Platform.

## Prerequisites

- Docker & Docker Compose installed
- (Optional) Docker Hub account for image registry
- (Optional) Cloud provider account (AWS, GCP, Azure)

## Local Development with Docker

### 1. Setup Environment Variables

```bash
# Copy example files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit .env files with your configuration
vim .env
```

### 2. Build and Start Services

```bash
# Build all containers
docker-compose build

# Start services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Access Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432

### 4. Stop Services

```bash
# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Production Deployment

### Option 1: Docker Compose (Simple)

**Best for**: Small deployments, single server

```bash
# On production server
git clone <repository>
cd man_subclip

# Configure production environment
cp .env.example .env
vim .env  # Update with production values

# Deploy
docker-compose -f docker-compose.yml up -d

# Setup automatic restarts
docker update --restart=unless-stopped $(docker ps -q)
```

### Option 2: Kubernetes (Scalable)

**Best for**: High availability, auto-scaling, multi-server

**Create Kubernetes manifests**:

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: video-platform

---
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: video-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/video-platform-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        volumeMounts:
        - name: nas-originals
          mountPath: /nas/originals
        - name: nas-proxy
          mountPath: /nas/proxy
        - name: nas-clips
          mountPath: /nas/clips
      volumes:
      - name: nas-originals
        persistentVolumeClaim:
          claimName: nas-originals-pvc
      - name: nas-proxy
        persistentVolumeClaim:
          claimName: nas-proxy-pvc
      - name: nas-clips
        persistentVolumeClaim:
          claimName: nas-clips-pvc
```

**Deploy to Kubernetes**:

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic db-credentials \
  --from-literal=url=postgresql://user:pass@db:5432/platform \
  -n video-platform

# Deploy services
kubectl apply -f k8s/
kubectl get pods -n video-platform

# Expose services
kubectl expose deployment backend --type=LoadBalancer --port=8000 -n video-platform
```

### Option 3: Cloud Platforms

#### AWS ECS (Elastic Container Service)

```bash
# Install AWS CLI and ECS CLI
pip install awscli
ecs-cli configure --cluster video-platform --region us-east-1

# Push images to ECR
aws ecr create-repository --repository-name video-platform-backend
docker tag video-platform-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/video-platform-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/video-platform-backend:latest

# Deploy with ECS
ecs-cli compose --file docker-compose.yml service up
```

#### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/backend backend/
gcloud builds submit --tag gcr.io/PROJECT_ID/frontend frontend/

# Deploy
gcloud run deploy backend \
  --image gcr.io/PROJECT_ID/backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

gcloud run deploy frontend \
  --image gcr.io/PROJECT_ID/frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances

```bash
# Login to Azure
az login

# Create resource group
az group create --name video-platform-rg --location eastus

# Push images to ACR
az acr create --resource-group video-platform-rg --name videoplatformacr --sku Basic
az acr build --registry videoplatformacr --image backend:latest backend/
az acr build --registry videoplatformacr --image frontend:latest frontend/

# Deploy
az container create \
  --resource-group video-platform-rg \
  --name backend \
  --image videoplatformacr.azurecr.io/backend:latest \
  --dns-name-label video-backend \
  --ports 8000
```

## CI/CD Pipeline

### GitHub Actions (Included)

Pipeline triggers on:
- **Push to main**: Runs tests, builds Docker images, pushes to registry
- **Pull request**: Runs tests and E2E tests

**Setup**:

1. Add Docker Hub credentials to GitHub Secrets:
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`

2. Pipeline automatically:
   - Runs backend pytest
   - Runs frontend Vitest
   - Builds Docker images
   - Pushes to Docker Hub
   - (Optional) Runs E2E tests with Playwright

## Database Migrations

### Initial Setup

```bash
# Access backend container
docker exec -it video-platform-backend bash

# Run migrations (using Alembic)
alembic upgrade head
```

### Creating Migrations

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Add new column"

# Review migration file
vim alembic/versions/XXXX_add_new_column.py

# Apply migration
alembic upgrade head
```

## Monitoring & Logging

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connection
docker exec video-platform-db pg_isready -U video_user
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# With tail
docker-compose logs -f --tail=100 backend
```

### Storage Cleanup

```bash
# Run storage cleanup script (dry-run)
docker exec video-platform-backend python scripts/storage_cleanup.py --dry-run

# Remove orphaned files
docker exec video-platform-backend python scripts/storage_cleanup.py

# Remove files older than 30 days
docker exec video-platform-backend python scripts/storage_cleanup.py --days 30
```

## Backup & Recovery

### Database Backup

```bash
# Backup database
docker exec video-platform-db pg_dump -U video_user video_platform > backup.sql

# Restore database
docker exec -i video-platform-db psql -U video_user video_platform < backup.sql
```

### NAS Storage Backup

```bash
# Backup volumes
docker run --rm -v video-platform_nas_originals:/source -v $(pwd)/backups:/backup alpine tar czf /backup/originals.tar.gz -C /source .
docker run --rm -v video-platform_nas_proxy:/source -v $(pwd)/backups:/backup alpine tar czf /backup/proxy.tar.gz -C /source .
docker run --rm -v video-platform_nas_clips:/source -v $(pwd)/backups:/backup alpine tar czf /backup/clips.tar.gz -C /source .

# Restore volumes
docker run --rm -v video-platform_nas_originals:/target -v $(pwd)/backups:/backup alpine tar xzf /backup/originals.tar.gz -C /target
```

## Security Checklist

- [ ] Change default passwords in .env
- [ ] Use HTTPS in production (setup reverse proxy like nginx or Traefik)
- [ ] Configure firewall rules (only expose ports 80, 443)
- [ ] Enable Docker security scanning
- [ ] Set up log monitoring and alerting
- [ ] Regular backups configured
- [ ] Database access restricted to backend only
- [ ] Environment variables never committed to git
- [ ] CORS origins properly configured
- [ ] Rate limiting enabled on API

## Performance Tuning

### Backend Optimization

```yaml
# docker-compose.yml - Add resource limits
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Database Optimization

```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_videos_proxy_status ON videos(proxy_status);
CREATE INDEX idx_videos_created_at ON videos(created_at);
CREATE INDEX idx_clips_video_id ON clips(video_id);
```

### NAS Storage

- Mount NAS volumes to dedicated SSD/NVMe drives for better I/O
- Configure storage cleanup cron job
- Monitor disk usage regularly

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs backend

# Check container status
docker ps -a

# Restart specific service
docker-compose restart backend
```

### Database connection issues

```bash
# Test database connectivity
docker exec video-platform-backend python -c "from src.database import engine; print(engine.connect())"

# Check PostgreSQL logs
docker-compose logs db
```

### High memory usage

```bash
# Check resource usage
docker stats

# Restart services to free memory
docker-compose restart
```

## Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3

  # Add load balancer
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - backend
```

### Vertical Scaling (More Resources)

- Increase Docker resource limits
- Upgrade server specifications
- Use faster storage (SSD/NVMe)

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review documentation: `docs/`
- GitHub Issues: Create an issue with logs and configuration details
