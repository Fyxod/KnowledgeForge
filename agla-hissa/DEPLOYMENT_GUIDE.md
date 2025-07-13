# Deployment Guide - Enterprise Knowledge Synthesis Platform

This guide provides step-by-step instructions for deploying the Multi-Modal Enterprise Knowledge Synthesis Platform to production.

## Pre-Deployment Checklist

### Code Quality Verification
- [ ] All tests passing (see TESTING_CHECKLIST.md)
- [ ] No compilation errors
- [ ] No ESLint warnings
- [ ] All documentation updated
- [ ] Security vulnerabilities addressed

### Environment Preparation
- [ ] Production server configured
- [ ] SSL certificates obtained
- [ ] Database ready
- [ ] Backup strategy in place
- [ ] Monitoring tools configured

## Frontend Deployment

### Build for Production

1. **Install Dependencies**
```bash
cd agla-hissa
npm install
```

2. **Build Production Bundle**
```bash
npm run build
```

3. **Verify Build Output**
```bash
# Check dist/ directory
ls -la dist/
# Verify all assets are generated
```

### Environment Configuration

#### Production Environment Variables
Create `.env.production` file:
```env
VITE_API_BASE_URL=https://your-backend-domain.com
VITE_APP_NAME=Enterprise Knowledge Synthesis Platform
VITE_APP_VERSION=1.0.0
```

#### Update API Configuration
In `src/services/api.js`:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

### Hosting Options

#### Option 1: Static Hosting (Recommended)

**Netlify Deployment:**
1. Connect repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Configure environment variables
5. Enable automatic deployments

**Vercel Deployment:**
1. Import project to Vercel
2. Configure build settings
3. Set environment variables
4. Deploy

**AWS S3 + CloudFront:**
1. Create S3 bucket
2. Enable static website hosting
3. Upload dist/ contents
4. Configure CloudFront distribution
5. Set up custom domain

#### Option 2: Self-Hosted

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    root /var/www/knowledge-platform;
    index index.html;
    
    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://backend-server:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Apache Configuration:**
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    Redirect permanent / https://your-domain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName your-domain.com
    DocumentRoot /var/www/knowledge-platform
    
    SSLEngine on
    SSLCertificateFile /path/to/certificate.crt
    SSLCertificateKeyFile /path/to/private.key
    
    # Handle client-side routing
    RewriteEngine On
    RewriteRule ^(?!.*\.).*$ /index.html [L]
    
    # API proxy
    ProxyPass /api/ http://backend-server:8000/
    ProxyPassReverse /api/ http://backend-server:8000/
    
    # Static assets caching
    <LocationMatch "\.(css|js|png|jpg|jpeg|gif|ico|svg)$">
        ExpiresActive On
        ExpiresDefault "access plus 1 year"
    </LocationMatch>
</VirtualHost>
```

## Backend Deployment

### Production Configuration

#### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:password@host:port/dbname
MONGODB_URL=mongodb://user:password@host:port/dbname

# Security
JWT_SECRET=your-super-secure-jwt-secret
CORS_ORIGINS=https://your-frontend-domain.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# File Storage
UPLOAD_DIRECTORY=/app/uploads
MAX_FILE_SIZE=50MB

# External Services
OPENAI_API_KEY=your-openai-key
```

#### Docker Deployment
```dockerfile
# Dockerfile for backend
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - database
      
  database:
    image: postgres:14
    environment:
      POSTGRES_DB: knowledge_platform
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
volumes:
  postgres_data:
```

## Database Setup

### PostgreSQL Production Setup
```sql
-- Create database
CREATE DATABASE knowledge_platform;

-- Create user
CREATE USER app_user WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE knowledge_platform TO app_user;

-- Run migrations
-- (Run your migration scripts here)
```

### MongoDB Production Setup
```javascript
// Create database and collections
use knowledge_platform;

// Create user
db.createUser({
  user: "app_user",
  pwd: "secure_password",
  roles: [
    { role: "readWrite", db: "knowledge_platform" }
  ]
});

// Create indexes for performance
db.threads.createIndex({ "user_id": 1 });
db.messages.createIndex({ "thread_id": 1 });
db.users.createIndex({ "email": 1 }, { unique: true });
```

## Security Configuration

### SSL/TLS Setup
1. Obtain SSL certificates (Let's Encrypt recommended)
2. Configure web server for HTTPS
3. Set up automatic certificate renewal
4. Enforce HTTPS redirects

### Security Headers
```nginx
# Add to Nginx configuration
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

### Environment Secrets
- Use environment variables for all sensitive data
- Never commit secrets to version control
- Use secret management services (AWS Secrets Manager, etc.)
- Rotate secrets regularly

## Monitoring and Logging

### Frontend Monitoring
```javascript
// Error tracking setup
if (import.meta.env.PROD) {
  // Initialize error tracking service (Sentry, etc.)
  Sentry.init({
    dsn: "your-sentry-dsn",
    environment: "production"
  });
}

// Performance monitoring
if ('performance' in window) {
  window.addEventListener('load', () => {
    const timing = performance.timing;
    const loadTime = timing.loadEventEnd - timing.navigationStart;
    // Send metrics to monitoring service
  });
}
```

### Backend Monitoring
```python
# Logging configuration
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/app/app.log'),
        logging.StreamHandler()
    ]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }
```

### Monitoring Stack
- **Application Performance**: New Relic, DataDog, or Sentry
- **Infrastructure**: Prometheus + Grafana
- **Logs**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Uptime**: UptimeRobot or similar

## Backup Strategy

### Database Backups
```bash
# PostgreSQL backup
pg_dump -h host -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql

# MongoDB backup
mongodump --host host --db database --out backup_$(date +%Y%m%d_%H%M%S)
```

### File Storage Backups
```bash
# Sync uploads to backup location
rsync -av --delete /app/uploads/ /backup/uploads/

# AWS S3 sync
aws s3 sync /app/uploads/ s3://backup-bucket/uploads/
```

### Automated Backup Script
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/$DATE"

mkdir -p $BACKUP_DIR

# Database backup
pg_dump $DATABASE_URL > $BACKUP_DIR/database.sql

# Files backup
tar -czf $BACKUP_DIR/uploads.tar.gz /app/uploads/

# Upload to cloud storage
aws s3 cp $BACKUP_DIR s3://backup-bucket/$DATE/ --recursive

# Cleanup old backups (keep 30 days)
find /backup -type d -mtime +30 -exec rm -rf {} +
```

## Performance Optimization

### Frontend Optimization
```json
// vite.config.js optimizations
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom']
        }
      }
    }
  }
});
```

### Backend Optimization
```python
# Async database connections
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)

# Caching
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

FastAPICache.init(
    RedisBackend(host="redis", port=6379),
    prefix="cache"
)
```

### CDN Configuration
- Configure CDN for static assets
- Set appropriate cache headers
- Use compression (gzip/brotli)
- Optimize images and fonts

## Deployment Automation

### CI/CD Pipeline Example (GitHub Actions)
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Install dependencies
        run: |
          cd agla-hissa
          npm ci
          
      - name: Run tests
        run: |
          cd agla-hissa
          npm test
          
      - name: Build
        run: |
          cd agla-hissa
          npm run build
          
      - name: Deploy to Production
        run: |
          # Deploy to your hosting service
          # This depends on your chosen platform
```

## Post-Deployment Verification

### Verification Checklist
- [ ] Frontend loads correctly
- [ ] User registration works
- [ ] User login works
- [ ] File upload functions
- [ ] Chat functionality works
- [ ] All API endpoints accessible
- [ ] SSL certificate valid
- [ ] Database connections stable
- [ ] Monitoring systems active
- [ ] Backup systems running

### Performance Testing
```bash
# Load testing with Apache Bench
ab -n 1000 -c 10 https://your-domain.com/

# API endpoint testing
ab -n 100 -c 5 -H "Authorization: Bearer token" https://your-domain.com/api/threads
```

## Maintenance and Updates

### Regular Maintenance Tasks
1. **Security Updates**: Keep all dependencies updated
2. **Database Maintenance**: Regular vacuum/optimize operations
3. **Log Rotation**: Implement log rotation to prevent disk space issues
4. **Backup Verification**: Regularly test backup restoration
5. **Performance Monitoring**: Review performance metrics weekly

### Update Deployment Process
1. Test updates in staging environment
2. Create database backup before deployment
3. Deploy during low-traffic periods
4. Monitor system health post-deployment
5. Have rollback plan ready

---

**Support Contact**: Contact your system administrator for deployment assistance and troubleshooting.
