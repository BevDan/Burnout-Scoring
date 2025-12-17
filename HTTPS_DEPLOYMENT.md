# HTTPS and Rate Limiting Deployment Guide

## What Was Added:

1. **HTTPS Support** - Nginx configured for SSL/TLS encryption
2. **Rate Limiting** - Backend protected against brute force and spam
3. **Security Headers** - Additional HTTP security headers

## Deployment Steps on Rock 3A:

### Step 1: Update Nginx Configuration

```bash
# SSH into Rock 3A
ssh burnouts@your-rock-ip

# Backup current config
sudo cp /etc/nginx/sites-available/burnout /etc/nginx/sites-available/burnout.backup

# Edit nginx config
sudo nano /etc/nginx/sites-available/burnout
```

**Replace entire content with the config from `nginx_burnout_https.conf`**

**IMPORTANT:** Change this line to match YOUR domain:
```nginx
# Line 18-19: Replace 'yourname.no-ip.org' with your actual No-IP domain
ssl_certificate /etc/letsencrypt/live/yourname.no-ip.org/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourname.no-ip.org/privkey.pem;

# Line 31: Also update this line
ssl_trusted_certificate /etc/letsencrypt/live/yourname.no-ip.org/chain.pem;
```

Save (Ctrl+O, Enter, Ctrl+X)

### Step 2: Test Nginx Configuration

```bash
# Test config for errors
sudo nginx -t

# Should see:
# nginx: configuration file /etc/nginx/conf.d/nginx.conf test is successful

# If error about certificate paths, verify your domain:
sudo ls /etc/letsencrypt/live/
# Use the folder name you see there
```

### Step 3: Reload Nginx

```bash
# Reload nginx with new HTTPS config
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

### Step 4: Update Backend with Rate Limiting

```bash
cd /home/burnouts/burnout-scoring

# Pull latest changes from GitHub
git pull

# Update backend dependencies
cd backend
source venv/bin/activate
pip install slowapi
deactivate

# Restart backend
sudo systemctl restart burnout-backend

# Check status
sudo systemctl status burnout-backend
```

### Step 5: Update Router Port Forwarding

**On your router admin page:**

**Old setup:**
- External port 12480 → Internal port 80

**New setup:**
- External port 12480 → Internal port 443 (HTTPS)
- Optional: External port 80 → Internal port 80 (for HTTP redirect)

### Step 6: Test Everything

```bash
# Test HTTPS locally
curl -k https://localhost/

# Test rate limiting (should block after 5 attempts)
for i in {1..6}; do
  echo "Attempt $i:"
  curl -X POST https://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}' \
    -k
  echo ""
done

# 6th attempt should return: 429 Too Many Requests

# Check all services
sudo systemctl status burnout-backend nginx
docker ps | grep mongodb
```

### Step 7: Test from External Network

From your phone or another network:
```
https://yourname.no-ip.org:12480
```

Should see:
- 🔒 Secure padlock in browser
- No certificate warnings
- Login page loads

## Rate Limiting Rules Applied:

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/api/auth/login` | 5/minute | Prevent brute force password attacks |
| `/api/judge/scores` | 10/minute | Prevent score spam |
| `/api/admin/competitors/bulk` | 2/minute | Prevent system overload from CSV imports |

## Security Headers Added:

- `Strict-Transport-Security` - Forces HTTPS for 1 year
- `X-Frame-Options` - Prevents clickjacking
- `X-Content-Type-Options` - Prevents MIME sniffing
- `X-XSS-Protection` - Enables XSS filter

## Certificate Auto-Renewal:

Certbot automatically creates a renewal timer:

```bash
# Check renewal timer
sudo systemctl status certbot.timer

# Test renewal (dry run)
sudo certbot renew --dry-run

# Certificates auto-renew every 90 days
```

## Troubleshooting:

### "Certificate not found" error:

```bash
# List your certificates
sudo certbot certificates

# Use the correct domain name shown there
```

### Port 443 connection refused:

```bash
# Check nginx is listening on 443
sudo ss -tlnp | grep :443

# Should show nginx process
```

### Rate limit not working:

```bash
# Check backend logs
sudo journalctl -u burnout-backend -n 50 | grep -i "rate\|limit"

# Verify slowapi installed
cd /home/burnouts/burnout-scoring/backend
source venv/bin/activate
pip list | grep slowapi
deactivate
```

### HTTP redirect not working:

```bash
# Test HTTP redirect
curl -I http://yourname.no-ip.org:12480

# Should return: 301 Moved Permanently
# Location: https://yourname.no-ip.org:12480
```

## Reverting to HTTP Only (if needed):

```bash
# Restore backup
sudo cp /etc/nginx/sites-available/burnout.backup /etc/nginx/sites-available/burnout

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

# Change port forwarding back: External 12480 → Internal 80
```

## What Users Will See:

**Before (HTTP):**
- ⚠️ "Not Secure" warning in browser
- Passwords sent in plain text
- Vulnerable to interception

**After (HTTPS):**
- 🔒 Secure padlock icon
- Encrypted traffic
- Login credentials protected
- Professional appearance

## Security Checklist:

- ✅ Strong JWT_SECRET (you have this)
- ✅ HTTPS enabled (after this deployment)
- ✅ Rate limiting active
- ✅ Security headers configured
- ✅ Admin password changed
- ✅ MongoDB not exposed to internet
- ⚠️ Consider: IP whitelist or VPN for production

## Next Steps After Deployment:

1. Test login from external network
2. Verify HTTPS certificate shows green padlock
3. Test rate limiting (try 6 failed logins)
4. Share HTTPS URL with judges
5. Close port forwarding after competition if desired

## Support:

If you encounter issues:
1. Check nginx error logs: `sudo tail -f /var/log/nginx/error.log`
2. Check backend logs: `sudo journalctl -u burnout-backend -f`
3. Verify certificate: `sudo certbot certificates`
4. Test config: `sudo nginx -t`
