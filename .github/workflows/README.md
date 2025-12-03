# TidyFrame CI/CD Documentation

This document explains the Continuous Integration and Continuous Deployment (CI/CD) pipeline for TidyFrame.

## Overview

TidyFrame uses GitHub Actions for automated testing, security scanning, and deployment. The pipeline ensures code quality, security, and zero-downtime deployments to production.

### Pipeline Architecture

```
┌─────────────┐
│   Git Push  │
│  to main/   │
│   develop   │
└──────┬──────┘
       │
       ├────────────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌──────────────┐
│   CI Tests  │  │   Security   │
│             │  │   Scanning   │
└──────┬──────┘  └──────────────┘
       │
       ▼
┌─────────────┐
│   CI Pass?  │
└──────┬──────┘
       │ Yes
       ▼
┌─────────────┐
│   Deploy    │
│ Production  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Health    │
│   Checks    │
└──────┬──────┘
       │
       ├─────── Success ────────────┐
       │                            │
       ▼                            │
┌─────────────┐                     │
│  Monitoring │                     │
│  (Every 15m)│                     │
└─────────────┘                     │
                                    │
       ├─────── Failure ────────────┘
       │
       ▼
┌─────────────┐
│  Automatic  │
│  Rollback   │
└─────────────┘
```

## Workflows

### 1. Continuous Integration (ci.yml)

**Trigger:** Push to `main` or `develop`, Pull Requests to `main`

**Jobs:**
- **Frontend Checks**
  - ESLint (strict mode)
  - TypeScript type checking
  - Build verification
  - Bundle size analysis

- **Backend Checks**
  - Black (code formatting)
  - isort (import sorting)
  - Flake8 (linting)
  - Mypy (type checking)
  - pytest (unit tests with coverage)

- **Security Scans**
  - Frontend: npm audit
  - Backend: Safety check, Bandit

- **Docker Validation**
  - Build backend/frontend images
  - Trivy vulnerability scanning

- **Database Validation**
  - Alembic migration testing
  - Migration rollback testing

- **Quality Gate**
  - All checks must pass before deployment

**Failure Handling:** Pull requests cannot be merged if CI fails.

### 2. Continuous Deployment (cd.yml)

**Trigger:**
- Automatic: After CI passes on `main` branch
- Manual: workflow_dispatch with options

**Process:**
1. **Pre-deployment Validation**
   - Verify environment variables
   - Auto-fix FRONTEND_URL if needed
   - Create database backup

2. **Zero-Downtime Deployment**
   - Pull latest code
   - Build new Docker images
   - Recreate containers (backend, celery-worker, celery-beat)
   - Keep postgres/redis running to avoid downtime

3. **Health Checks**
   - Check health endpoint (10 attempts, 10s intervals)
   - Verify API responds
   - Confirm frontend loads

4. **Container Verification**
   - Verify all services are running
   - Check container health status

5. **Rollback on Failure**
   - Automatically triggered if deployment fails
   - Restores previous code version
   - Rebuilds and restarts services

**Environment URL:** https://tidyframe.com

#### 🚨 Troubleshooting: If CD Doesn't Auto-Deploy

The `workflow_run` trigger (used to chain CI → CD) has **known reliability issues** in GitHub Actions. If CI passes but CD doesn't automatically trigger within 2-3 minutes, use one of these manual deployment options:

**Option 1: GitHub CLI (Fastest)**
```bash
gh workflow run cd.yml
```

**Option 2: GitHub Web UI**
1. Go to [Actions → Continuous Deployment](https://github.com/tidyframeai/tidyframe/actions/workflows/cd.yml)
2. Click "Run workflow" dropdown
3. Select branch: `main`
4. Click "Run workflow" button

**Option 3: Direct SSH Deployment**
```bash
# Full manual deployment via SSH
ssh root@24.199.122.244
cd /opt/tidyframe
git pull origin main

# Build frontend
cd frontend && npm ci && npm run build
rm -rf ../backend/app/static/* && cp -r dist/* ../backend/app/static/
cd ..

# Deploy
bash backend/scripts/zero-downtime-deploy.sh docker-compose.prod.yml backend celery-worker celery-beat

# Restart nginx (prevents 502 errors)
docker compose -f docker-compose.prod.yml restart nginx
```

**Why This Happens:**
- `workflow_run` events can be delayed or missed entirely (GitHub Actions limitation)
- Branch filters sometimes don't work correctly
- Conclusion field can be null/empty causing skips
- Token permission issues can block trigger propagation

**Prevention:**
- CD workflow now includes `conclusion == 'success'` check (safer)
- Debug logging added to diagnose issues
- Nginx restart step prevents 502 errors
- Consider upgrading to multi-job workflow (Phase 2) for 99.9% reliability

### 3. Manual Deployment (manual-deploy.yml)

**Trigger:** Manual (workflow_dispatch only)

**Use Cases:**
- Hotfixes that bypass CI
- Deploying specific commits/branches
- Emergency deployments
- Testing deployment process

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `environment` | Target environment (production/staging) | production |
| `git_ref` | Branch, tag, or commit SHA to deploy | main |
| `services` | Comma-separated list of services | backend,celery-worker,celery-beat |
| `skip_backup` | Skip database backup (risky) | false |
| `skip_health_checks` | Skip health validation (emergency) | false |
| `force_rebuild` | Force Docker rebuild (--no-cache) | true |
| `run_migrations` | Run Alembic migrations before deploy | false |

**How to Run:**
1. Go to Actions tab → Manual Deployment
2. Click "Run workflow"
3. Select options
4. Click "Run workflow" button

**Warning:** Deploying non-main branches to production will show warnings.

### 4. Security Scanning (security-scan.yml)

**Trigger:**
- Push to `main` or `develop`
- Pull requests
- Daily at 2 AM UTC (cron)
- Manual dispatch

**Scans:**

| Scan Type | Tool | Purpose |
|-----------|------|---------|
| Secret Detection | TruffleHog, GitLeaks | Find leaked secrets |
| Dependencies | npm audit, Safety, Snyk* | Vulnerability scanning |
| Containers | Trivy, Grype | Image vulnerabilities |
| Code Quality | SonarCloud*, CodeQL, Semgrep | Security issues in code |
| Infrastructure | Checkov, Hadolint | Docker/compose security |

\* *Optional - requires external tokens*

**Optional Secrets:**
- `SNYK_TOKEN` - For Snyk scanning (optional)
- `SONAR_TOKEN` - For SonarCloud analysis (optional)
- `SECURITY_SLACK_WEBHOOK_URL` - For alerts (optional)

**Note:** Scans will continue even if optional tokens are not configured.

### 5. Health Monitoring (health-monitor.yml)

**Trigger:**
- Every 15 minutes (cron)
- Manual dispatch

**Checks:**
- Website accessibility (200 status code)
- Response time
- Health endpoint (/health)
- API endpoints (/api/health)
- SSL certificate expiry
- Container status (detailed mode)
- Disk space usage (detailed mode)

**Alerting:**
- Creates GitHub issue on failure
- Updates existing issue if still failing
- Automatically closes issue when resolved

**Manual Detailed Check:**
1. Go to Actions → Production Health Monitor
2. Click "Run workflow"
3. Enable "Run detailed health checks"
4. Click "Run workflow"

## Scripts

### 1. validate-env.sh

**Purpose:** Validate environment variables before deployment

**Usage:**
```bash
./backend/scripts/validate-env.sh [env_file] [environment]

# Examples:
./backend/scripts/validate-env.sh .env production
./backend/scripts/validate-env.sh backend/.env.example development
```

**Checks:**
- Required variables exist
- No placeholder values (your-*, example, etc.)
- SECRET_KEY length (min 32 characters)
- FRONTEND_URL format (https:// in production)
- DEBUG disabled in production
- Database/Redis URL format
- Password strength
- Email configuration

**Exit Codes:**
- 0: All checks passed
- 1: Validation failed

### 2. zero-downtime-deploy.sh

**Purpose:** Perform rolling deployment without downtime

**Usage:**
```bash
./backend/scripts/zero-downtime-deploy.sh [compose_file] [services...]

# Examples:
./backend/scripts/zero-downtime-deploy.sh docker-compose.prod.yml backend celery-worker
./backend/scripts/zero-downtime-deploy.sh docker-compose.prod.yml backend celery-worker celery-beat
```

**Process:**
1. Store current deployment state
2. Build new Docker images
3. Recreate specified containers (--force-recreate --no-deps)
4. Wait for containers to start
5. Run health checks
6. Verify deployment success

**Environment Variables:**
- `BUILD_NO_CACHE` - Force rebuild without cache (default: true)
- `HEALTH_ENDPOINT` - URL for health checks (default: https://tidyframe.com/health)
- `MAX_HEALTH_CHECKS` - Max attempts (default: 10)
- `HEALTH_CHECK_INTERVAL` - Seconds between checks (default: 10)

### 3. backup.sh

**Purpose:** Create comprehensive backups

**Usage:**
```bash
./backend/scripts/backup.sh
```

**Backs Up:**
- PostgreSQL database (compressed)
- Application data
- Configuration files
- SSL certificates
- Docker volumes (optional)

**Features:**
- Compression
- Integrity verification
- Retention management (default: 30 days)
- Detailed logging

## Required GitHub Secrets

### Essential (Required for CD)

| Secret | Description | How to Obtain |
|--------|-------------|---------------|
| `PROD_SERVER_HOST` | Production server IP/hostname | Your server IP (e.g., 24.199.122.244) |
| `PROD_SERVER_USER` | SSH username | Usually `root` or your user |
| `PROD_SSH_KEY` | SSH private key | Generate with `ssh-keygen -t ed25519` |

### Optional (Enhanced Features)

| Secret | Description | Used By |
|--------|-------------|---------|
| `SNYK_TOKEN` | Snyk API token | security-scan.yml |
| `SONAR_TOKEN` | SonarCloud token | security-scan.yml |
| `SECURITY_SLACK_WEBHOOK_URL` | Slack webhook for alerts | security-scan.yml |

**How to Add Secrets:**
1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Enter name and value
4. Click "Add secret"

## Server Requirements

### Required System Packages

The production server requires these packages:

| Package | Purpose | Auto-Installed | Manual Install |
|---------|---------|----------------|----------------|
| `docker` | Container runtime | ❌ Manual | [Docker Install Guide](https://docs.docker.com/engine/install/) |
| `docker compose` | Orchestration | ❌ Manual | Included with Docker or install plugin |
| `git` | Version control | ✅ Auto | `apt-get install -y git` |
| `curl` | Health checks | ✅ Auto | `apt-get install -y curl` |
| `jq` | JSON parsing | ✅ Auto | `apt-get install -y jq` |
| `python3` | Fallback parsing | ⚠️ Usually pre-installed | `apt-get install -y python3` |

**Note**: The CD workflow automatically installs `git`, `curl`, and `jq` if missing. Docker must be installed manually.

### Server Setup Checklist

When provisioning a new production server:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Install system packages (auto-installed by CD, but good to have)
apt-get update
apt-get install -y git curl jq python3

# 3. Clone repository
git clone https://github.com/tidyframeai/tidyframe.git /opt/tidyframe
cd /opt/tidyframe

# 4. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with production values

# 5. Test deployment
bash backend/scripts/zero-downtime-deploy.sh docker-compose.prod.yml backend celery-worker celery-beat
```

### Troubleshooting Deployment Failures

**Symptom: "status: unknown" in deployment logs**
```
⚠️  backend status: unknown
❌ backend is not running (status: unknown)
```
- **Cause**: Missing `jq` package (older deployments)
- **Fix**: CD workflow now auto-installs jq, re-run deployment
- **Manual fix**: `apt-get install -y jq`

**Symptom: "Missing critical dependencies"**
- **Cause**: Docker, git, or curl not installed
- **Fix**: Install missing package, re-run deployment
- **Prevention**: Use server setup checklist above

## Common Operations

### Deploy to Production

**Automatic (Recommended):**
1. Merge PR to `main` branch
2. CI runs automatically
3. If CI passes, CD deploys to production
4. Monitor health checks

**Manual:**
1. Go to Actions → Manual Deployment
2. Click "Run workflow"
3. Configure options (use defaults for standard deploy)
4. Click "Run workflow"

### Rollback Production

**Automatic:**
- Happens automatically if deployment health checks fail

**Manual:**
1. Go to Actions → Manual Deployment
2. Set `git_ref` to previous commit SHA or tag
3. Keep other options as default
4. Click "Run workflow"

**Via SSH:**
```bash
ssh root@<server>
cd /opt/tidyframe

# Find previous commit
git log --oneline -10

# Rollback to specific commit
git reset --hard <commit-sha>
bash backend/scripts/zero-downtime-deploy.sh docker-compose.prod.yml backend celery-worker celery-beat
```

### View Logs

**GitHub Actions Logs:**
1. Go to Actions tab
2. Click on workflow run
3. Click on job
4. Expand steps to see logs

**Production Server Logs:**
```bash
ssh root@<server>
cd /opt/tidyframe

# View all logs
docker compose -f docker-compose.prod.yml logs

# Follow logs (live)
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs backend

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Run Database Migrations

**During Deployment:**
1. Use Manual Deployment workflow
2. Enable "Run database migrations before deployment"

**Direct on Server:**
```bash
ssh root@<server>
cd /opt/tidyframe

# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Rollback one migration
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

### Check Health Status

**Via Workflow:**
1. Go to Actions → Production Health Monitor
2. Click "Run workflow"
3. Enable detailed checks
4. View results

**Manual:**
```bash
# Check website
curl https://tidyframe.com/

# Check health endpoint
curl https://tidyframe.com/health

# Check API
curl https://tidyframe.com/api/health

# Check SSL
echo | openssl s_client -servername tidyframe.com -connect tidyframe.com:443 2>/dev/null | openssl x509 -noout -dates
```

## Troubleshooting

### Deployment Fails

**Symptoms:** CD workflow fails, services don't start

**Diagnosis:**
```bash
ssh root@<server>
cd /opt/tidyframe

# Check container status
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs --tail=100 backend

# Check for errors
docker compose -f docker-compose.prod.yml logs backend | grep -i error
```

**Common Causes:**
1. Environment variable issues → Run `validate-env.sh`
2. Database migration failure → Check migration logs
3. Port conflicts → Check `docker compose ps`
4. Resource exhaustion → Check `df -h` and `free -m`

**Fix:**
1. Fix the issue
2. Run manual deployment or push fix to main

### Health Checks Fail

**Symptoms:** GitHub issue created by health monitor

**Quick Check:**
```bash
# Test locally
curl -v https://tidyframe.com/health

# Check if site loads
curl -I https://tidyframe.com/
```

**Investigation:**
1. Check container logs
2. Verify all services running
3. Check recent deployments
4. Review error logs

### CI Tests Fail

**Backend Tests:**
```bash
# Run locally
cd backend
pip install -r requirements.txt
black --check app/
isort --check app/
flake8 app/
mypy app/
pytest tests/
```

**Frontend Tests:**
```bash
# Run locally
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

### Security Scan Issues

**Vulnerabilities Found:**
1. Review the security report
2. Update dependencies: `npm audit fix` or `pip install --upgrade`
3. Create PR with fixes
4. Re-run security scan

**Scan Timeout:**
- Normal for comprehensive scans
- Results will be partial
- Re-run manually if needed

## Best Practices

### Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes and test locally**
   ```bash
   # Frontend
   cd frontend && npm run lint && npm run typecheck

   # Backend
   cd backend && black app/ && isort app/ && pytest tests/
   ```

3. **Push and create PR**
   ```bash
   git push origin feature/your-feature
   ```

4. **CI runs automatically** - fix any failures

5. **Get code review**

6. **Merge to main** - automatic deployment

### Emergency Hotfix

1. **Create hotfix branch**
   ```bash
   git checkout -b hotfix/critical-fix main
   ```

2. **Make minimal fix**

3. **Option A: Go through CI (recommended)**
   - Push and create PR
   - Wait for CI
   - Merge to main

4. **Option B: Manual deployment (emergency)**
   - Push hotfix branch
   - Use Manual Deployment workflow
   - Set `git_ref` to hotfix branch
   - Monitor closely

### Deployment Safety

✅ **DO:**
- Let CI complete before deploying
- Create database backups (enabled by default)
- Monitor health checks after deployment
- Deploy during low-traffic hours
- Test in development first
- Keep rollback commit ready

❌ **DON'T:**
- Skip health checks (unless emergency)
- Deploy without backup (unless testing)
- Deploy untested code to production
- Deploy during peak hours
- Ignore warning signs in logs

## Monitoring

### Key Metrics

**Availability:**
- Target: 99.9% uptime
- Monitor: health-monitor.yml (every 15min)

**Response Time:**
- Target: < 500ms for health endpoint
- Monitor: health-monitor.yml

**Deployment Success Rate:**
- Target: 95%+ automatic deployments succeed
- Monitor: CD workflow history

**Security:**
- Target: No critical vulnerabilities
- Monitor: security-scan.yml (daily)

### Alerts

**GitHub Issues Created For:**
- Production health check failures
- Critical security vulnerabilities (via Slack if configured)

**Manual Monitoring:**
- Check Actions tab for workflow failures
- Review security scan reports
- Monitor production logs

## Maintenance

### Weekly

- [ ] Review security scan results
- [ ] Check for failed deployments
- [ ] Review health monitor issues
- [ ] Update dependencies if needed

### Monthly

- [ ] Review and clean old backups
- [ ] Audit GitHub secrets still valid
- [ ] Check SSL certificate expiry
- [ ] Review CI/CD performance metrics
- [ ] Update documentation if workflows changed

### Quarterly

- [ ] Security audit
- [ ] Performance review
- [ ] Disaster recovery drill
- [ ] Update CI/CD dependencies (Actions versions)

## Version History

- **v1.2.2** (2025-10-16) - Comprehensive CI/CD overhaul
  - Enhanced CD pipeline with zero-downtime deployments
  - Added backend Python checks (black, isort, flake8, mypy, pytest)
  - Created environment validation script
  - Fixed security scan issues
  - Added manual deployment workflow
  - Implemented health monitoring workflow
  - Created comprehensive documentation

## Support

**Issues:** https://github.com/anthropics/tidyframe/issues

**Emergency Contact:** Check deployment.state on production server for last known good commit

**Runbook Location:** This file (`.github/workflows/README.md`)
