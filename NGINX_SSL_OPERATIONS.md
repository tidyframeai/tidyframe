# TidyFrame Nginx & SSL Operations Guide

## Table of Contents
- [Quick Reference](#quick-reference)
- [Architecture Overview](#architecture-overview)
- [Common Operations](#common-operations)
- [SSL Certificate Management](#ssl-certificate-management)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## Quick Reference

### Health Check
```bash
cd /opt/tidyframe
./backend/scripts/test-nginx-config.sh
```

### Restart Nginx
```bash
cd /opt/tidyframe
docker-compose -f docker-compose.prod.yml restart nginx
```

### Test Config Before Applying
```bash
docker exec tidyframe_nginx_1 nginx -t
```

### Regenerate SSL Certificate
```bash
cd /opt/tidyframe
./backend/scripts/regenerate-ssl-cert.sh tidyframe.com tidyframeai@gmail.com
```

### Check SSL Certificate Expiry
```bash
openssl x509 -enddate -noout -in /opt/tidyframe/certbot/conf/live/tidyframe.com/fullchain.pem
```

---

## Architecture Overview

### Nginx Configuration Files

**Active Configuration:**
```
nginx/conf.d/tidyframe-production-ssl.conf  ← SINGLE ACTIVE CONFIG
```

**Disabled/Backup Configurations:**
```
nginx/conf.d/tidyframe-production.conf.disabled
nginx/conf.d/tidyframe-ssl.conf.disabled
nginx/conf.d/tidyframe-local.conf.disabled
```

**⚠️ IMPORTANT:** Only ONE `.conf` file should be active in `nginx/conf.d/`. Multiple active configs will cause duplicate upstream errors.

### SSL/TLS Configuration

- **Certificate Provider:** Let's Encrypt
- **Certificate Location:** `certbot/conf/live/tidyframe.com/`
- **Auto-Renewal:** Certbot container runs every 12 hours
- **Renewal Window:** 30 days before expiration
- **Protocols:** TLSv1.2, TLSv1.3
- **HTTP/2:** Enabled (modern syntax)

### Security Features

✅ HSTS with preload
✅ Content Security Policy (CSP)
✅ XSS Protection headers
✅ Frame Options (clickjacking protection)
✅ MIME sniffing protection
✅ OCSP stapling
✅ WebSocket support with secure headers

---

## Common Operations

### 1. Checking Nginx Status

```bash
# Check container status
docker ps | grep nginx

# Check container health
docker inspect --format='{{.State.Health.Status}}' tidyframe_nginx_1

# View logs
docker logs tidyframe_nginx_1 --tail 50

# Follow logs in real-time
docker logs -f tidyframe_nginx_1
```

### 2. Testing Configuration Changes

**ALWAYS test before applying changes:**

```bash
# Test syntax
docker exec tidyframe_nginx_1 nginx -t

# Test with dry-run
docker-compose -f docker-compose.prod.yml config

# Run full health check
./backend/scripts/test-nginx-config.sh
```

### 3. Applying Configuration Changes

```bash
# 1. Edit configuration file
nano nginx/conf.d/tidyframe-production-ssl.conf

# 2. Test configuration
docker exec tidyframe_nginx_1 nginx -t

# 3. Reload nginx (zero-downtime)
docker exec tidyframe_nginx_1 nginx -s reload

# OR restart container (brief downtime)
docker-compose -f docker-compose.prod.yml restart nginx
```

### 4. Viewing Access Logs

```bash
# Real-time access logs
docker exec tidyframe_nginx_1 tail -f /var/log/nginx/access.log

# Error logs
docker exec tidyframe_nginx_1 tail -f /var/log/nginx/error.log

# Search logs for specific IP
docker exec tidyframe_nginx_1 grep "192.168.1.1" /var/log/nginx/access.log
```

---

## SSL Certificate Management

### Certificate Status

```bash
# Check certificate expiration
openssl x509 -enddate -noout -in certbot/conf/live/tidyframe.com/fullchain.pem

# View full certificate details
openssl x509 -in certbot/conf/live/tidyframe.com/fullchain.pem -text -noout

# Check certificate chain
openssl s_client -connect tidyframe.com:443 -showcerts
```

### Auto-Renewal Status

```bash
# Check certbot container
docker ps | grep certbot

# View certbot logs
docker logs tidyframe_certbot_1 --tail 50

# Test renewal (dry-run)
docker-compose -f docker-compose.prod.yml run --rm --entrypoint 'certbot' certbot renew --dry-run
```

### Manual Certificate Renewal

**Option 1: Force Renewal Script (Recommended)**
```bash
cd /opt/tidyframe
./backend/scripts/regenerate-ssl-cert.sh tidyframe.com tidyframeai@gmail.com
```

**Option 2: Manual Certbot Command**
```bash
cd /opt/tidyframe

# Stop certbot container
docker-compose -f docker-compose.prod.yml stop certbot

# Force renewal
docker-compose -f docker-compose.prod.yml run --rm --entrypoint 'certbot' certbot renew \
  --force-renewal \
  --email tidyframeai@gmail.com \
  --agree-tos \
  --no-eff-email

# Restart nginx to load new certificate
docker-compose -f docker-compose.prod.yml restart nginx

# Restart certbot container
docker-compose -f docker-compose.prod.yml up -d certbot
```

### Initial SSL Setup (New Domain)

```bash
cd /opt/tidyframe
./backend/scripts/setup-ssl.sh tidyframe.com tidyframeai@gmail.com production
```

---

## Troubleshooting

### Problem: Nginx Won't Start

**Symptoms:**
- Container keeps restarting
- `docker ps` shows status as "Restarting"

**Diagnosis:**
```bash
# Check logs
docker logs tidyframe_nginx_1 --tail 100

# Common errors:
# - "duplicate upstream" → Multiple .conf files active
# - "SSL certificate not found" → Certificate path wrong
# - "bind() failed" → Port already in use
```

**Solutions:**

**Duplicate Upstream Error:**
```bash
cd /opt/tidyframe/nginx/conf.d

# List active configs
ls -la *.conf

# Should only see tidyframe-production-ssl.conf
# Disable any others:
mv tidyframe-XXXX.conf tidyframe-XXXX.conf.disabled
```

**SSL Certificate Not Found:**
```bash
# Check certificate exists
ls -la certbot/conf/live/tidyframe.com/

# If missing, regenerate:
./backend/scripts/regenerate-ssl-cert.sh tidyframe.com tidyframeai@gmail.com
```

**Port Conflict:**
```bash
# Check what's using port 80/443
sudo netstat -tlnp | grep :443
sudo lsof -i :443

# Stop conflicting service or use different ports
```

### Problem: SSL Certificate Expired

**Symptoms:**
- Browser shows "Your connection is not private"
- Certificate error in logs

**Solution:**
```bash
cd /opt/tidyframe

# Check expiry
openssl x509 -enddate -noout -in certbot/conf/live/tidyframe.com/fullchain.pem

# Force renewal
./backend/scripts/regenerate-ssl-cert.sh tidyframe.com tidyframeai@gmail.com
```

### Problem: HTTP Not Redirecting to HTTPS

**Diagnosis:**
```bash
# Test redirect
curl -I http://tidyframe.com/

# Should return:
# HTTP/1.1 301 Moved Permanently
# Location: https://tidyframe.com/
```

**Solution:**
Check nginx configuration has HTTP server block with redirect:
```nginx
server {
    listen 80;
    location / {
        return 301 https://$host$request_uri;
    }
}
```

### Problem: Certbot Auto-Renewal Failing

**Symptoms:**
- Certificate close to expiry
- Certbot logs show errors

**Common Causes:**
1. Port 80 not accessible (firewall)
2. DNS not pointing to server
3. `.well-known/acme-challenge` location misconfigured

**Diagnosis:**
```bash
# Test ACME challenge endpoint
curl -I http://tidyframe.com/.well-known/acme-challenge/test

# Should return 404 or 403 (but not 301 redirect to HTTPS)

# Check firewall
sudo ufw status
sudo iptables -L -n | grep 80

# Test renewal
docker-compose -f docker-compose.prod.yml run --rm --entrypoint 'certbot' certbot renew --dry-run
```

**Solution:**
Ensure nginx allows HTTP for ACME challenges:
```nginx
location /.well-known/acme-challenge/ {
    root /var/www/certbot;
    allow all;
}
```

### Problem: Security Headers Missing

**Diagnosis:**
```bash
# Check headers
curl -I https://tidyframe.com/docs | grep -i "strict-transport\|x-frame\|content-security"
```

**Expected Headers:**
```
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
content-security-policy: default-src 'self'; ...
```

**Solution:**
Headers are defined in `nginx/conf.d/tidyframe-production-ssl.conf`. Ensure they're in the `server` block with `always` flag.

---

## Emergency Procedures

### Emergency Rollback to HTTP

If SSL is completely broken and you need to restore HTTP access:

```bash
cd /opt/tidyframe/nginx/conf.d

# 1. Disable SSL config
mv tidyframe-production-ssl.conf tidyframe-production-ssl.conf.disabled

# 2. Create emergency HTTP-only config
cat > emergency-http.conf << 'EOF'
upstream backend_servers {
    server backend:8000;
}

server {
    listen 80;
    server_name tidyframe.com www.tidyframe.com;

    location / {
        proxy_pass http://backend_servers/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# 3. Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx

# 4. Fix SSL, then restore HTTPS
mv emergency-http.conf emergency-http.conf.disabled
mv tidyframe-production-ssl.conf.disabled tidyframe-production-ssl.conf
docker-compose -f docker-compose.prod.yml restart nginx
```

### Emergency Certificate Regeneration

If certificate is corrupted:

```bash
cd /opt/tidyframe

# 1. Backup old certificate
sudo mv certbot/conf/live/tidyframe.com certbot/conf/live/tidyframe.com.bak

# 2. Generate new certificate
./backend/scripts/setup-ssl.sh tidyframe.com tidyframeai@gmail.com production

# 3. Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Complete Nginx Reset

If nginx is completely broken:

```bash
cd /opt/tidyframe

# 1. Stop and remove nginx container
docker-compose -f docker-compose.prod.yml stop nginx
docker-compose -f docker-compose.prod.yml rm -f nginx

# 2. Verify only one .conf file is active
ls nginx/conf.d/*.conf
# Should ONLY see tidyframe-production-ssl.conf

# 3. Test config syntax (in a temporary container)
docker run --rm -v $(pwd)/nginx:/etc/nginx:ro nginx:alpine nginx -t

# 4. Recreate nginx container
docker-compose -f docker-compose.prod.yml up -d nginx

# 5. Check status
docker ps | grep nginx
docker logs tidyframe_nginx_1
```

---

## Best Practices

### Configuration Management

✅ **DO:**
- Always test config changes with `nginx -t` before applying
- Keep only ONE active `.conf` file in `nginx/conf.d/`
- Use `.disabled` extension for backup configs
- Document changes in commit messages
- Run health check after changes

❌ **DON'T:**
- Edit configs directly in production without backup
- Have multiple `.conf` files active simultaneously
- Modify files while nginx is reading them
- Skip testing step before applying changes

### SSL/TLS Management

✅ **DO:**
- Monitor certificate expiry (30+ days before expiration)
- Test auto-renewal monthly with `--dry-run`
- Keep certbot container running
- Ensure port 80 accessible for ACME challenges
- Use modern TLS protocols (1.2, 1.3)

❌ **DON'T:**
- Let certificates expire
- Block port 80 (needed for renewal)
- Modify certificate files manually
- Use self-signed certs in production

### Monitoring

Set up monitoring for:
- Certificate expiry (alert at 30 days)
- Nginx uptime/health
- HTTP→HTTPS redirect working
- Security headers present
- Port 80/443 accessibility

---

## Scripts Reference

### test-nginx-config.sh

**Location:** `backend/scripts/test-nginx-config.sh`

**Purpose:** Comprehensive health check for nginx and SSL

**Usage:**
```bash
./backend/scripts/test-nginx-config.sh
```

**Checks:**
1. Nginx container status
2. Configuration syntax
3. SSL certificate validity
4. Certbot status
5. HTTP→HTTPS redirect
6. HTTPS connectivity & HTTP/2
7. Security headers
8. Active config files (should be 1)
9. ACME challenge endpoint
10. Backend API connectivity

### regenerate-ssl-cert.sh

**Location:** `backend/scripts/regenerate-ssl-cert.sh`

**Purpose:** Force SSL certificate renewal

**Usage:**
```bash
./backend/scripts/regenerate-ssl-cert.sh [domain] [email]
# Example:
./backend/scripts/regenerate-ssl-cert.sh tidyframe.com tidyframeai@gmail.com
```

**Process:**
1. Checks current certificate status
2. Ensures nginx running for ACME challenge
3. Tests domain reachability
4. Forces certificate renewal
5. Restarts nginx with new certificate
6. Tests HTTPS connectivity

### setup-ssl.sh

**Location:** `backend/scripts/setup-ssl.sh`

**Purpose:** Initial SSL setup for new domains

**Usage:**
```bash
./backend/scripts/setup-ssl.sh <domain> <email> [environment]
# Example:
./backend/scripts/setup-ssl.sh tidyframe.com tidyframeai@gmail.com production
```

**Process:**
1. Creates certbot directories
2. Starts nginx with HTTP for ACME challenge
3. Generates SSL certificates
4. Creates unified nginx configuration
5. Disables conflicting configs
6. Restarts nginx with HTTPS
7. Tests HTTPS connectivity

---

## Support

For issues not covered in this guide:

1. Check nginx logs: `docker logs tidyframe_nginx_1`
2. Run health check: `./backend/scripts/test-nginx-config.sh`
3. Review nginx config: `nginx/conf.d/tidyframe-production-ssl.conf`
4. Test config syntax: `docker exec tidyframe_nginx_1 nginx -t`

---

**Last Updated:** December 3, 2025
**Nginx Version:** nginx/1.25+ (Alpine)
**Certbot Version:** Latest (Docker image)
**TLS Protocols:** TLSv1.2, TLSv1.3
