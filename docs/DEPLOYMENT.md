# TidyFrame Unified Deployment & Development Guide

## Overview
TidyFrame now uses a **unified control system** for both development and production.

**Control Script:** `tidyframe.sh` - Single script for all operations  
**Environment Files:** 
- `.env.development` - Local development settings
- `.env.production` - Production deployment settings  
**Key Scripts:** Only 5 essential scripts remain (reduced from 60+)

## Quick Start

### Local Development
```bash
# Start development environment
./tidyframe.sh dev

# View logs
./tidyframe.sh logs

# Stop services
./tidyframe.sh stop
```

### Production Deployment
```bash
# Copy to server
rsync -avz --exclude=node_modules --exclude=.git ./ root@YOUR_IP:/opt/tidyframe/

# SSH and deploy
ssh root@YOUR_IP
cd /opt/tidyframe
./tidyframe.sh deploy
```

## Environment Management

The system automatically selects the right environment:
- `./tidyframe.sh dev` → Uses `.env.development`
- `./tidyframe.sh prod` → Uses `.env.production`
- Script copies the selected env to `.env` for Docker

## Prerequisites

### 1. Digital Ocean Droplet
- **Size:** 8GB RAM minimum
- **OS:** Ubuntu 22.04 LTS
- **Region:** US (for legal compliance)

### 2. Domain Setup
- Point your domain's A records to droplet IP
- Create both @ and www records

### 3. Required API Keys
Before deployment, ensure `.env.production` has:
- `GEMINI_API_KEY` - Get from https://makersuite.google.com/app/apikey
- `STRIPE_SECRET_KEY` - From Stripe dashboard
- `RESEND_API_KEY` - From Resend dashboard
- `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET` - From Google Console

## Step 1: Prepare Environment

```bash
# On your local machine
cd tidyframe

# Update .env.production with your actual values
nano .env.production

# Critical variables to update:
# - GEMINI_API_KEY (MUST replace - current one is exposed)
# - STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY
# - RESEND_API_KEY
# - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# - ADMIN_PASSWORD (used for admin account)
```

## Step 2: Copy to Digital Ocean

```bash
# From local machine
rsync -avz --exclude=node_modules --exclude=__pycache__ \
  --exclude=.git --exclude=backups \
  ./ root@YOUR_DROPLET_IP:/opt/tidyframe/
```

## Step 3: Run Deployment

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Navigate to project
cd /opt/tidyframe

# Run deployment script
DOMAIN=tidyframe.com \
CERTBOT_EMAIL=admin@tidyframe.com \
./backend/scripts/deploy.sh
```

The script will:
1. Install Docker & dependencies
2. Build all containers
3. Run database migrations
4. Create admin user from ADMIN_PASSWORD
5. Setup SSL certificates
6. Start all services

## Step 4: Verify Deployment

### Check Services
```bash
docker ps
# Should show: postgres, redis, backend, celery-worker, celery-beat, nginx
```

### Check Admin Access
```bash
# Admin is created automatically using:
# Email: admin@tidyframe.com (or ADMIN_EMAIL if set)
# Password: from ADMIN_PASSWORD in .env.production
```

### Test Endpoints
```bash
# Health check
curl https://tidyframe.com/health

# API docs
curl https://tidyframe.com/api/docs
```

## Site Password

If `ENABLE_SITE_PASSWORD=true` in `.env.production`:
- Users will be prompted for site password on first visit
- Password is stored in `SITE_PASSWORD` environment variable
- Cookie persists for 30 days

## Monitoring

### View Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

### Check Resource Usage
```bash
docker stats
```

### Database Backup
```bash
docker exec tidyframe-postgres-prod pg_dumpall -U tidyframe > backup.sql
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs [service_name]

# Restart service
docker-compose -f docker-compose.prod.yml restart [service_name]
```

### SSL Issues
```bash
# Test with staging certificates first
docker-compose -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot --webroot-path=/var/www/certbot \
  --staging -d tidyframe.com -d www.tidyframe.com
```

### Database Connection Issues
```bash
# Check if postgres is running
docker exec tidyframe-postgres-prod pg_isready

# Check database exists
docker exec tidyframe-postgres-prod psql -U tidyframe -c "\l"
```

### Admin Access Issues
```bash
# Manually create/update admin
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/setup_admin.py
```

## Maintenance

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### SSL Renewal (Auto)
SSL certificates auto-renew via cron job. To manually renew:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot renew
```

### Backup Schedule
Add to crontab:
```bash
# Daily database backup at 2 AM
0 2 * * * docker exec tidyframe-postgres-prod pg_dumpall -U tidyframe > /backups/db-$(date +\%Y\%m\%d).sql
```

## Security Notes

1. **Never commit `.env.production`** - Contains secrets
2. **Rotate API keys regularly**
3. **Monitor rate limits** - Set in `RATE_LIMIT_PER_MINUTE`
4. **US-only access** enforced via middleware
5. **Admin bypass** - Admins skip subscription checks

## Simplified File Structure
```
/opt/tidyframe/
├── tidyframe.sh               # Main control script (NEW!)
├── .env.development           # Development config
├── .env.production            # Production secrets
├── docker-compose.yml         # Development compose
├── docker-compose.prod.yml    # Production compose
├── backend/
│   ├── scripts/
│   │   ├── deploy.sh          # Production deployment
│   │   ├── setup_admin.py     # Admin creation
│   │   ├── backup.sh          # Database backup
│   │   └── health-check.sh    # Health monitoring
│   └── app/
├── frontend/
└── DEPLOYMENT.md              # This file
```

**Removed:** 55+ redundant scripts, 3 duplicate .env files, 15+ test files

## Support

For issues:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Review this guide
3. Ensure all environment variables are set
4. Verify domain DNS is configured correctly