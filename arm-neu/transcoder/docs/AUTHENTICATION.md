# Authentication Guide

ARM Transcoder supports simple header-based authentication using API keys.

## Quick Start

### 1. Disable Authentication (Development)

```env
# .env
REQUIRE_API_AUTH=false
```

All endpoints are public. **Not recommended for production.**

### 2. Enable Authentication (Production)

```env
# .env
REQUIRE_API_AUTH=true
API_KEYS=admin:your-secret-key-here
WEBHOOK_SECRET=your-webhook-secret
```

## API Key Format

### Simple Keys (All Admin)

```env
API_KEYS=key1,key2,key3
```

All keys have admin access.

### Role-Based Keys

```env
API_KEYS=admin:abc123,readonly:def456
```

- **admin** - Full access (list, stats, retry, delete)
- **readonly** - Read-only access (list, stats only; cannot retry or delete)

## Using API Keys

### cURL Examples

```bash
# List jobs
curl -H "X-API-Key: abc123" http://localhost:5000/jobs

# Get stats
curl -H "X-API-Key: abc123" http://localhost:5000/stats

# Retry job (admin only)
curl -X POST -H "X-API-Key: abc123" http://localhost:5000/jobs/1/retry

# Delete job (admin only)
curl -X DELETE -H "X-API-Key: abc123" http://localhost:5000/jobs/1
```

### Python Example

```python
import requests

headers = {"X-API-Key": "abc123"}

# List jobs
response = requests.get("http://localhost:5000/jobs", headers=headers)
jobs = response.json()

# Get stats
stats = requests.get("http://localhost:5000/stats", headers=headers).json()
```

## Webhook Authentication

Webhooks from ARM use a separate secret:

```env
WEBHOOK_SECRET=your-webhook-secret
```

### Required: `X-Api-Version` header

As of v17.4.0 the webhook router enforces an API-version handshake.
Every `POST /webhook/arm` request **must** include:

```
X-Api-Version: 2
```

The strict-mode flag `ACCEPT_MISSING_VERSION_HEADER = False` lives in
`src/version.py`; missing-header requests are rejected with HTTP 400.
ARM clients on v16.0.0+ send the header automatically. If you operate a
custom ARM deployment or hand-craft webhook POSTs (curl, smoke scripts),
add the header explicitly or your webhook will 400 silently.

### Configure ARM

Update your ARM `arm.yaml`:

```yaml
TRANSCODER_URL: "http://transcoder-ip:5000/webhook/arm"
```

### Send Webhook with Secret

```bash
curl -X POST \
  -H "X-Webhook-Secret: your-webhook-secret" \
  -H "X-Api-Version: 2" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","body":"Rip of Movie (2024) complete","status":"success","job_id":1}' \
  http://localhost:5000/webhook/arm
```

If ARM supports custom headers in TRANSCODER_URL (check ARM documentation), you can include the secret in the webhook configuration.

## Endpoint Access Control

| Endpoint | Public (no auth) | Authenticated User | Admin Only |
|----------|------------------|-------------------|-----------|
| `GET /health` | ✅ Always | - | - |
| `GET /system/info` | ✅ Always | - | - |
| `GET /system/stats` | ✅ Always | - | - |
| `POST /webhook/arm` | ✅ With WEBHOOK_SECRET | - | - |
| `GET /jobs` | - | ✅ | ✅ |
| `GET /stats` | - | ✅ | ✅ |
| `GET /workers` | - | ✅ | ✅ |
| `GET /config` | - | ✅ | ✅ |
| `GET /logs` | - | ✅ | ✅ |
| `GET /logs/{file}` | - | ✅ | ✅ |
| `GET /logs/{file}/structured` | - | ✅ | ✅ |
| `PATCH /config` | - | - | ✅ |
| `POST /jobs/{id}/retry` | - | - | ✅ |
| `DELETE /jobs/{id}` | - | - | ✅ |
| `POST /system/restart` | - | - | ✅ |

## Security Best Practices

### 1. Use Strong Keys

```bash
# Generate random API key
openssl rand -hex 32

# Or
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Use Different Keys for Different Clients

```env
# Good
API_KEYS=admin:web-dashboard-key,admin:monitoring-key,admin:ci-cd-key

# Bad - reusing same key
API_KEYS=admin:same-key-for-everything
```

### 3. Rotate Keys Regularly

Update keys every 90 days, or immediately if compromised.

### 4. Use HTTPS in Production

API keys are sent in headers. Use TLS/HTTPS to encrypt traffic:

```nginx
# nginx reverse proxy with TLS
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://arm-transcoder:5000;
        proxy_set_header X-API-Key $http_x_api_key;
    }
}
```

### 5. Don't Log Keys

Keys are automatically sanitized in logs:

```
# Actual log output
INFO - Received request with key=abc1***
```

## Disabling Auth for Specific Endpoints

Currently all-or-nothing. To disable auth for health checks:

Edit `src/main.py` and remove `Depends(get_current_user)` from the endpoint.

## Troubleshooting

### Error: "API key required"

You forgot the header:

```bash
# Wrong
curl http://localhost:5000/jobs

# Right
curl -H "X-API-Key: your-key" http://localhost:5000/jobs
```

### Error: "Invalid API key"

Key doesn't match configuration:

1. Check `.env` file: `API_KEYS=...`
2. Restart service to load new keys
3. Verify key exactly matches (case-sensitive)

### Error: "Admin access required"

Using readonly key on admin endpoint:

```env
# .env
API_KEYS=readonly:abc123  # This key can't delete jobs
```

Use an admin key or change the role:

```env
API_KEYS=admin:abc123
```

### Webhook: "Webhook secret required"

ARM didn't send `X-Webhook-Secret` header:

1. Check ARM supports custom headers
2. Or disable webhook secret: `WEBHOOK_SECRET=` (empty)

## Migration from No Auth

If upgrading from unauthenticated deployment:

**Option A: Gradual Rollout**

1. Deploy with `REQUIRE_API_AUTH=false`
2. Add API keys to clients
3. Enable `REQUIRE_API_AUTH=true`

**Option B: Immediate**

1. Set `REQUIRE_API_AUTH=true` and `API_KEYS=...`
2. Update all clients with keys before deploying

## Future Enhancements

Planned features:

- [ ] Per-key rate limiting
- [ ] Key expiration dates
- [ ] Audit log of API key usage
- [ ] JWT tokens instead of static keys
- [ ] OAuth2 support

## Questions?

See:
- [IMPLEMENTATION_SPEC.md](IMPLEMENTATION_SPEC.md) - Full improvement roadmap
- [README.md](../README.md) - General setup
