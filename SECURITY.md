# Security Documentation

**Service**: Quimbi Platform
**Classification**: Confidential
**Last Updated**: December 30, 2024
**Next Review**: March 30, 2025

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Encryption](#data-encryption)
4. [Secrets Management](#secrets-management)
5. [API Security](#api-security)
6. [Database Security](#database-security)
7. [Webhook Security](#webhook-security)
8. [Compliance](#compliance)
9. [Incident Response](#incident-response)
10. [Security Checklist](#security-checklist)

---

## Security Overview

### Threat Model

**Assets to Protect**:
- Customer PII (names, emails, phone numbers)
- Purchase history (orders, products, amounts)
- Behavioral profiles (868 archetypes, fuzzy memberships)
- ML models (churn, LTV prediction algorithms)
- API credentials (Shopify, Gorgias, Anthropic)

**Threat Actors**:
- External attackers (data theft, ransom)
- Malicious insiders (data exfiltration)
- Accidental exposure (misconfigured services)

**Security Controls**:
- ✅ Encryption at rest (database)
- ✅ Encryption in transit (HTTPS/TLS)
- ✅ HMAC signature validation (webhooks)
- ✅ Secret rotation (API keys)
- ⚠️ Access control (TODO: implement RBAC)
- ⚠️ Audit logging (TODO: implement comprehensive logging)

---

## Authentication & Authorization

### Current State: No Authentication (MVP)

**APIs are currently OPEN** with no authentication required.

**Risk Level**: 🔴 HIGH
**Justification**: Early development phase, single-tenant deployment
**Mitigation**: Railway network security, non-public URLs

---

### Planned: API Key Authentication (Phase 1)

**Implementation Date**: Q1 2025

```python
# Add to backend/api/middleware/auth.py

from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify API key against database."""
    # Check if API key exists and is active
    async with get_db_session() as session:
        result = await session.execute(
            "SELECT store_id, is_active FROM api_keys WHERE key_hash = crypt(%s, key_hash)",
            (api_key,)
        )
        key_record = result.fetchone()

    if not key_record or not key_record.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return key_record.store_id

# Apply to protected routes
@app.get("/api/intelligence/customer/{customer_id}")
async def get_customer_intelligence(
    customer_id: str,
    store_id: str = Depends(verify_api_key)  # Enforces auth
):
    # ...
```

**API Key Storage**:
```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL,
    key_hash TEXT NOT NULL,  -- bcrypt hash, never store plaintext
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    scope TEXT[]  -- ['read:customers', 'write:segments']
);

CREATE INDEX idx_api_keys_hash ON api_keys USING btree(key_hash);
```

**Key Generation**:
```python
import secrets
import bcrypt

def generate_api_key():
    """Generate secure API key."""
    # Format: qk_live_<32 random bytes>
    key = f"qk_live_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(key.encode(), bcrypt.gensalt())
    return key, key_hash.decode()
```

---

### Planned: OAuth 2.0 (Phase 2)

**Implementation Date**: Q2 2025

**Use Case**: Multi-tenant SaaS with per-user permissions

```python
# OAuth 2.0 with JWT tokens
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode JWT and return user."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        store_id = payload.get("store_id")
        return {"user_id": user_id, "store_id": store_id}
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Data Encryption

### Encryption at Rest

**Database**: PostgreSQL with full disk encryption (Railway managed)

```bash
# Verify encryption enabled
psql $DATABASE_URL -c "SHOW data_encryption;"
```

**Sensitive Fields**: Additional encryption for PII

```python
# Encrypt sensitive fields before storing
from cryptography.fernet import Fernet

class EncryptedField:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext to base64 ciphertext."""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext to plaintext."""
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Usage
cipher = EncryptedField(key=os.getenv("ENCRYPTION_KEY").encode())

# Before insert
encrypted_email = cipher.encrypt("customer@example.com")
await session.execute("INSERT INTO customers (email_encrypted) VALUES (%s)", (encrypted_email,))

# After select
encrypted_email = result.fetchone().email_encrypted
plaintext_email = cipher.decrypt(encrypted_email)
```

**Encryption Key Management**:
```bash
# Generate encryption key (store in Railway secrets)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Store in Railway
railway variables set ENCRYPTION_KEY="<generated-key>"
```

---

### Encryption in Transit

**HTTPS/TLS**: All API traffic encrypted with TLS 1.3

**Railway Configuration**:
- ✅ Automatic HTTPS for `*.up.railway.app` domains
- ✅ TLS 1.3 with strong cipher suites
- ✅ HTTP → HTTPS redirect enforced

**Verify TLS**:
```bash
# Check TLS version and cipher
curl -vI https://quimbibrainbev10-production.up.railway.app 2>&1 | grep -E "TLS|cipher"
```

---

## Secrets Management

### Current Approach: Environment Variables

**Storage**: Railway environment variables (encrypted at rest)

**Access**:
```python
import os

# Retrieve secrets
DATABASE_URL = os.getenv("DATABASE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

**Best Practices**:
- ✅ Never commit secrets to git (.env in .gitignore)
- ✅ Use different secrets for dev/staging/production
- ✅ Rotate secrets quarterly
- ⚠️ TODO: Implement secret rotation automation

---

### Planned: HashiCorp Vault (Future)

**Use Case**: Multi-tenant deployment with dynamic secrets

```python
import hvac

vault_client = hvac.Client(url='https://vault.quimbi.ai')

# Retrieve database credentials (auto-rotated)
secret = vault_client.secrets.database.generate_credentials(name='postgres-quimbi')
db_user = secret['data']['username']
db_pass = secret['data']['password']
```

---

### Secret Rotation Schedule

| Secret | Rotation Frequency | Last Rotated | Next Rotation |
|--------|-------------------|--------------|---------------|
| DATABASE_URL | Never (managed) | - | - |
| SHOPIFY_ACCESS_TOKEN | Annually | 2024-06-01 | 2025-06-01 |
| GORGIAS_API_KEY | Annually | 2024-11-01 | 2025-11-01 |
| ANTHROPIC_API_KEY | Quarterly | 2024-12-01 | 2025-03-01 |
| ENCRYPTION_KEY | Never (break existing data) | 2024-11-01 | - |

---

## API Security

### Rate Limiting

**Current State**: No rate limiting (MVP)

**Planned Implementation**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Global rate limit: 100 requests per minute
@app.get("/api/intelligence/customer/{customer_id}")
@limiter.limit("100/minute")
async def get_customer_intelligence(request: Request, customer_id: str):
    # ...
```

**Rate Limit Tiers**:
- Free tier: 100 req/min
- Paid tier: 1000 req/min
- Enterprise: Custom limits

---

### Input Validation

**Prevent Injection Attacks**:

```python
from pydantic import BaseModel, validator

class CustomerQuery(BaseModel):
    customer_id: str

    @validator('customer_id')
    def validate_customer_id(cls, v):
        # Only allow alphanumeric and underscore
        if not v.replace('_', '').isalnum():
            raise ValueError('Invalid customer ID format')
        return v
```

**SQL Injection Prevention**:
```python
# ❌ NEVER do this
query = f"SELECT * FROM customers WHERE id = '{customer_id}'"

# ✅ Always use parameterized queries
query = "SELECT * FROM customers WHERE id = %s"
result = await session.execute(query, (customer_id,))
```

---

### CORS Configuration

**Current State**: Permissive (allow all origins)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Too permissive
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Configuration**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dashboard.quimbi.ai",
        "https://app.quimbi.ai",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

## Database Security

### Access Control

**Current State**: Single admin user (Railway managed)

**Planned**: Principle of least privilege

```sql
-- Create read-only user for analytics
CREATE USER analytics_readonly WITH PASSWORD '<strong-password>';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_readonly;

-- Create app user with limited permissions
CREATE USER quimbi_app WITH PASSWORD '<strong-password>';
GRANT SELECT, INSERT, UPDATE ON combined_sales TO quimbi_app;
GRANT SELECT ON discovered_segments TO quimbi_app;
REVOKE DELETE ON ALL TABLES FROM quimbi_app;  -- Prevent accidental deletion
```

---

### SQL Injection Prevention

**Always use parameterized queries**:

```python
# ✅ SAFE: Parameterized query
async def get_customer_orders(customer_id: str):
    query = "SELECT * FROM orders WHERE customer_id = %s"
    result = await session.execute(query, (customer_id,))
    return result.fetchall()

# ❌ UNSAFE: String interpolation
async def get_customer_orders_unsafe(customer_id: str):
    query = f"SELECT * FROM orders WHERE customer_id = '{customer_id}'"  # NEVER DO THIS
    result = await session.execute(query)
    return result.fetchall()
```

---

### Database Backups

**Railway Automated Backups**:
- Daily snapshots (retained 7 days)
- Point-in-time recovery

**Manual Backup**:
```bash
# Export full database
pg_dump $DATABASE_URL > quimbi_backup_$(date +%Y%m%d).sql

# Compress
gzip quimbi_backup_$(date +%Y%m%d).sql

# Upload to S3 (encrypted)
aws s3 cp quimbi_backup_$(date +%Y%m%d).sql.gz \
  s3://quimbi-backups/ \
  --sse AES256
```

---

## Webhook Security

### HMAC Signature Validation

**Gorgias Webhooks**:

```python
import hmac
import hashlib

def verify_gorgias_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Gorgias."""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

# In webhook handler
@app.post("/webhooks/gorgias/ticket")
async def handle_gorgias_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Gorgias-Signature")

    if not verify_gorgias_signature(payload, signature, GORGIAS_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process webhook...
```

**Shopify Webhooks** (future):

```python
def verify_shopify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Shopify."""
    expected_signature = base64.b64encode(
        hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    ).decode()

    return hmac.compare_digest(signature, expected_signature)
```

---

### Replay Attack Prevention

**Add timestamp validation**:

```python
from datetime import datetime, timedelta

def is_webhook_fresh(timestamp: str, max_age_seconds: int = 300) -> bool:
    """Ensure webhook was sent within last 5 minutes."""
    webhook_time = datetime.fromisoformat(timestamp)
    age = datetime.utcnow() - webhook_time
    return age < timedelta(seconds=max_age_seconds)

@app.post("/webhooks/gorgias/ticket")
async def handle_gorgias_webhook(request: Request):
    payload_dict = await request.json()
    timestamp = payload_dict.get("timestamp")

    if not is_webhook_fresh(timestamp):
        raise HTTPException(status_code=400, detail="Webhook too old (replay attack?)")

    # Process webhook...
```

---

## Compliance

### GDPR (EU General Data Protection Regulation)

**Right to Access**:
```python
@app.get("/api/privacy/customer/{customer_id}/data")
async def export_customer_data(customer_id: str):
    """Export all customer data (GDPR Article 15)."""
    # Fetch from all tables
    orders = await fetch_customer_orders(customer_id)
    segments = await fetch_customer_segments(customer_id)
    profiles = await fetch_customer_profiles(customer_id)

    return {
        "customer_id": customer_id,
        "orders": orders,
        "segments": segments,
        "profiles": profiles,
        "exported_at": datetime.utcnow().isoformat()
    }
```

**Right to Erasure ("Right to be Forgotten")**:
```python
@app.delete("/api/privacy/customer/{customer_id}")
async def delete_customer_data(customer_id: str):
    """Delete all customer data (GDPR Article 17)."""
    async with get_db_session() as session:
        # Delete from all tables
        await session.execute("DELETE FROM orders WHERE customer_id = %s", (customer_id,))
        await session.execute("DELETE FROM customer_segments WHERE customer_id = %s", (customer_id,))
        await session.execute("DELETE FROM customer_profiles WHERE customer_id = %s", (customer_id,))
        await session.commit()

    return {"status": "deleted", "customer_id": customer_id}
```

**Data Retention Policy**:
- Customer data: Retained while active, deleted on request
- Logs: Retained 90 days
- Backups: Retained 30 days

---

### CCPA (California Consumer Privacy Act)

**Data Categories**:
- Personal Information: Name, email, phone
- Commercial Information: Purchase history, order values
- Inferences: Behavioral archetypes, churn predictions

**Consumer Rights**:
- Right to Know: What data we collect
- Right to Delete: Delete personal information
- Right to Opt-Out: Opt-out of data "sales" (N/A - we don't sell data)

---

### PCI DSS (Payment Card Industry)

**Status**: Not applicable - Quimbi does NOT store payment card data

**Shopify handles all payments** - we only receive:
- Order ID
- Order total (amount)
- Customer ID

We never see or store:
- Credit card numbers
- CVV codes
- Expiration dates

---

## Incident Response

### Security Incident Response Plan

**1. Detection**
- Monitor logs for anomalies
- Alert on failed authentication attempts (>10 in 1 minute)
- Alert on database query failures (possible SQL injection)

**2. Containment**
- Disable compromised API keys immediately
- Block malicious IP addresses
- Isolate affected services

**3. Investigation**
- Review access logs
- Identify scope of breach (data exfiltrated?)
- Preserve evidence for forensics

**4. Notification**
- Internal: Notify CTO, CEO within 1 hour
- Customers: Notify within 72 hours (GDPR requirement)
- Regulators: Notify within 72 hours if data breach

**5. Recovery**
- Restore from backups if data corrupted
- Rotate all compromised secrets
- Apply security patches

**6. Post-Mortem**
- Document incident timeline
- Identify root cause
- Implement preventive measures

---

### Contact Information

**Security Team**:
- Email: security@quimbi.ai
- Phone: [Emergency hotline]
- Slack: #security-incidents

**Escalation Path**:
1. On-call engineer (respond within 15 min)
2. CTO (respond within 30 min)
3. CEO (notify within 1 hour)

---

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in environment variables (not code)
- [ ] HTTPS enabled for all endpoints
- [ ] Database encryption at rest enabled
- [ ] Webhook HMAC signature validation implemented
- [ ] SQL parameterized queries used (no string interpolation)
- [ ] Input validation on all API endpoints
- [ ] CORS configured (not allow_origins=["*"])
- [ ] Rate limiting enabled
- [ ] Error messages don't leak sensitive info

### Production

- [ ] API key authentication enabled
- [ ] Database backups automated (daily)
- [ ] Security monitoring/alerting configured
- [ ] Secrets rotated quarterly
- [ ] Dependency vulnerabilities scanned weekly
- [ ] Access logs reviewed monthly
- [ ] GDPR/CCPA compliance verified

### Ongoing

- [ ] Quarterly security audit
- [ ] Annual penetration test
- [ ] Incident response plan tested annually
- [ ] Team security training (quarterly)

---

## Security Best Practices

### For Developers

1. **Never commit secrets** - Use .env files (git ignored)
2. **Use parameterized queries** - Prevent SQL injection
3. **Validate all inputs** - Never trust user input
4. **Fail securely** - Don't expose error details
5. **Principle of least privilege** - Grant minimum permissions
6. **Keep dependencies updated** - Run `pip-audit` weekly

### For Operators

1. **Rotate secrets quarterly** - API keys, passwords
2. **Monitor logs daily** - Look for anomalies
3. **Backup database daily** - Test restore monthly
4. **Review access logs** - Who accessed what
5. **Patch vulnerabilities** - Within 7 days of disclosure

---

## Tools & Resources

**Security Scanning**:
```bash
# Python dependency vulnerability scan
pip-audit

# SAST (Static Application Security Testing)
bandit -r backend/

# Secrets scanning
trufflehog --regex --entropy=True .
```

**Monitoring**:
```bash
# Check for exposed secrets in logs
railway logs | grep -i "password\|api_key\|secret"

# Monitor failed auth attempts
railway logs | grep "401 Unauthorized" | wc -l
```

---

**Last Updated**: December 30, 2024
**Next Review**: March 30, 2025
**Owner**: CTO

🤖 Generated with [Claude Code](https://claude.com/claude-code)
