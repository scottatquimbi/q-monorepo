# Troubleshooting Guide

**Service**: Quimbi Platform (QuimbiBrain + Customer Support Backend)
**Last Updated**: December 30, 2024

---

## Table of Contents

1. [Common API Errors](#common-api-errors)
2. [Database Issues](#database-issues)
3. [Integration Problems](#integration-problems)
4. [ML Model Issues](#ml-model-issues)
5. [Performance Issues](#performance-issues)
6. [Deployment Issues](#deployment-issues)
7. [Debugging Tips](#debugging-tips)

---

## Common API Errors

### Error: 503 Service Unavailable - "No customers loaded"

**Symptom**:
```json
{
  "status": "unhealthy",
  "error": "No customers loaded in database"
}
```

**Cause**: Database is empty or segmentation hasn't run

**Solution**:
```bash
# 1. Check if data exists
psql $DATABASE_URL -c "SELECT COUNT(*) FROM combined_sales;"

# 2. If empty, load data from Shopify
python -m backend.integrations.shopify_sync --store-id=lindas

# 3. Run segmentation
python -m backend.segmentation.discover_segments --store-id=lindas
```

**Prevention**: Set up cron job for daily Shopify sync

---

### Error: 404 Not Found - Customer not found

**Symptom**:
```json
{
  "detail": "Customer 12345 not found in database"
}
```

**Cause**: Customer ID doesn't exist or hasn't synced from Shopify

**Solution**:
```bash
# 1. Check if customer exists in Shopify
curl https://lindas.myshopify.com/admin/api/2024-01/customers/12345.json \
  -H "X-Shopify-Access-Token: $SHOPIFY_ACCESS_TOKEN"

# 2. If exists in Shopify, trigger sync
python -m backend.integrations.shopify_sync --customer-id=12345

# 3. If doesn't exist, customer may have been deleted
# Check deleted_customers table
```

---

### Error: 500 Internal Server Error - "Scaler parameters not found"

**Symptom**:
```
KeyError: 'mean' in scaler_params
```

**Cause**: Segments discovered without scaler params (old version)

**Solution**:
```bash
# Re-discover segments with updated clustering engine
python -m backend.segmentation.discover_segments \
  --store-id=lindas \
  --force-rediscover
```

**Root Cause**: Segments table schema changed in v3.0.0

---

### Error: 422 Unprocessable Entity - Invalid axis name

**Symptom**:
```json
{
  "detail": "Axis 'purchase_behavior' not recognized"
}
```

**Cause**: Using old axis name (renamed in v3.0.0)

**Solution**: Use updated axis names

**Axis Name Changes**:
- `purchase_behavior` → `purchase_frequency`
- `spending_level` → `purchase_value`
- `category_preference` → `category_exploration`

**Check Valid Axes**:
```bash
curl https://quimbibrainbev10-production.up.railway.app/api/segments/axes
```

---

## Database Issues

### Issue: Connection pool exhausted

**Symptom**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached
```

**Cause**: Too many concurrent connections

**Solution**:
```python
# Update database.py connection pool settings
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Increase from 10
    max_overflow=30,     # Increase from 10
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**Prevention**: Use connection pooling with context managers

---

### Issue: Slow queries on customer lookup

**Symptom**: `/api/intelligence/customer/{id}` takes >5 seconds

**Cause**: Missing index on customer_id

**Solution**:
```sql
-- Add index on combined_sales.customer_id
CREATE INDEX CONCURRENTLY idx_combined_sales_customer_id
ON combined_sales(customer_id);

-- Add index on customer_segments.customer_id
CREATE INDEX CONCURRENTLY idx_customer_segments_customer_id
ON customer_segments(customer_id);
```

**Check Query Performance**:
```sql
EXPLAIN ANALYZE
SELECT * FROM combined_sales WHERE customer_id = 12345;
```

---

### Issue: Database migrations failed

**Symptom**:
```
alembic.util.exc.CommandError: Target database is not up to date
```

**Solution**:
```bash
# 1. Check current migration version
alembic current

# 2. Check pending migrations
alembic history

# 3. Upgrade to latest
alembic upgrade head

# 4. If errors, rollback one version
alembic downgrade -1

# 5. Re-apply
alembic upgrade head
```

---

## Integration Problems

### Gorgias Webhook: 400 Bad Request

**Symptom**: Gorgias webhook returns 400, ticket not processed

**Common Causes**:

**1. Missing HMAC signature validation**
```python
# Check logs for signature mismatch
# Fix: Update GORGIAS_WEBHOOK_SECRET in .env
```

**2. Invalid event type**
```python
# Supported: ticket.created, message.created
# Unsupported: ticket.updated, ticket.deleted
```

**3. Missing ticket ID**
```python
# Check webhook payload structure
# ticket.created: payload["ticket"]["id"]
# message.created: payload["message"]["ticket_id"]
```

**Solution**:
```bash
# Test webhook locally with ngrok
ngrok http 8000

# Update Gorgias webhook URL to ngrok URL
# Send test webhook from Gorgias
# Check logs: tail -f logs/quimbi.log
```

---

### Shopify GraphQL: Rate limit exceeded

**Symptom**:
```
shopify.errors.RateLimitError: Exceeded 1000 points per second
```

**Solution**:
```python
# Implement exponential backoff
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
async def fetch_with_retry(query):
    return await shopify_client.execute(query)
```

**Prevention**: Batch queries, use cursor-based pagination

---

### QuimbiBrain API: Timeout

**Symptom**: Customer support backend times out calling QuimbiBrain

**Cause**: ML inference takes >30 seconds for large customers

**Solution**:
```python
# Increase timeout in quimbi_client.py
async with httpx.AsyncClient(timeout=60.0) as client:  # Increase from 30.0
    response = await client.get(url)
```

**Long-term Fix**: Cache customer profiles in Redis

---

## ML Model Issues

### Issue: Churn model predictions are all 0.5

**Symptom**: Every customer has 50% churn probability

**Cause**: Model not trained or failed to load

**Solution**:
```bash
# 1. Check if model file exists
ls -lh models/churn/v1/model.pkl

# 2. If missing, train model
python -m backend.ml.train_churn_model \
  --start-date 2024-01-01 \
  --end-date 2025-01-01 \
  --model-dir models/churn/v1

# 3. Verify model loaded
curl https://quimbibrainbev10-production.up.railway.app/api/ml/model-status
```

---

### Issue: LTV predictions are negative

**Symptom**: Customer LTV = -$50.00

**Cause**: Gamma regression doesn't handle negative values, likely refund-heavy customer

**Solution**:
```python
# Update LTV prediction to handle edge cases
def predict_ltv(customer_id):
    ltv = model.predict(features)

    # Clamp to realistic range
    if ltv < 0:
        ltv = 0  # Can't have negative LTV
    if ltv > 10000:
        ltv = 10000  # Cap at $10k (sanity check)

    return ltv
```

---

### Issue: Segmentation discovers only 2 clusters per axis

**Symptom**: Expected 3-5 segments, getting only 2

**Cause**: Silhouette score optimization stuck at k=2

**Solution**:
```python
# Force min_k=3 in clustering config
engine = MultiAxisClusteringEngine(
    min_k=3,  # Force at least 3 clusters
    max_k=6,
    min_silhouette=0.25  # Lower threshold if needed
)
```

**Check Silhouette Scores**:
```python
# Run discovery with debug logging
python -m backend.segmentation.discover_segments \
  --store-id=lindas \
  --log-level=DEBUG
```

---

## Performance Issues

### Issue: API response time >1 second

**Symptom**: `/api/intelligence/customer/{id}` takes 2-5 seconds

**Diagnosis**:
```bash
# Check slow query log
tail -f logs/quimbi.log | grep "SLOW QUERY"

# Profile API endpoint
curl -w "@curl-format.txt" \
  https://quimbibrainbev10-production.up.railway.app/api/intelligence/customer/12345
```

**Common Fixes**:

**1. Add database indexes** (see Database Issues)

**2. Cache customer profiles**:
```python
# Add Redis caching
from redis import asyncio as aioredis

@cache(expire=3600)  # Cache for 1 hour
async def get_customer_profile(customer_id):
    # ...
```

**3. Optimize fuzzy membership calculation**:
```python
# Vectorize distance calculations
distances = cdist(customer_vector, segment_centers, metric='euclidean')
memberships = np.exp(-distances) / np.sum(np.exp(-distances))
```

---

### Issue: Memory leak, crashes after 24 hours

**Symptom**: Railway restarts service daily due to OOM

**Diagnosis**:
```bash
# Check memory usage
railway run python -m memory_profiler backend/api/main.py

# Monitor memory over time
watch -n 5 'railway status | grep Memory'
```

**Common Causes**:

**1. Database connections not closed**:
```python
# Always use context managers
async with get_db_session() as session:
    # ...
# Session auto-closed
```

**2. Large numpy arrays not freed**:
```python
# Explicitly delete large arrays
import gc
del large_array
gc.collect()
```

**3. Asyncio tasks not cleaned up**:
```python
# Cancel background tasks on shutdown
@app.on_event("shutdown")
async def shutdown():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Deployment Issues

### Issue: Railway deployment failed

**Symptom**: Build succeeds but app crashes on startup

**Check Logs**:
```bash
railway logs --service QuimbiBrainBEv1.0
```

**Common Causes**:

**1. Missing environment variables**:
```bash
# List all env vars
railway variables

# Add missing variable
railway variables set DATABASE_URL="postgresql://..."
```

**2. Database migration not run**:
```bash
# Run migrations on Railway
railway run alembic upgrade head
```

**3. Port binding issue**:
```python
# Ensure binding to 0.0.0.0, not localhost
uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

---

### Issue: Gorgias webhooks not reaching Railway

**Symptom**: Webhooks work locally, not in production

**Diagnosis**:
```bash
# Test webhook endpoint
curl -X POST https://beecommerce-production.up.railway.app/webhooks/gorgias/ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket": {"id": 123, "customer": {...}}}'
```

**Common Causes**:

**1. HTTPS required by Gorgias**:
```
# Railway provides HTTPS by default
# Ensure webhook URL uses https://
```

**2. IP whitelist blocking**:
```
# Railway IPs change, can't whitelist
# Solution: Use HMAC signature validation instead
```

**3. Request timeout (Gorgias waits max 10s)**:
```python
# Ensure webhook handler returns quickly
@app.post("/webhooks/gorgias/ticket")
async def handle_webhook(background_tasks: BackgroundTasks):
    # Validate and return immediately
    background_tasks.add_task(process_ticket_async, ticket_data)
    return {"status": "accepted"}
```

---

## Debugging Tips

### Enable Debug Logging

```python
# In main.py or config.py
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

### Inspect Database Directly

```bash
# Connect to production database
railway run psql $DATABASE_URL

# Check customer count
SELECT COUNT(DISTINCT customer_id) FROM combined_sales;

# Check segment count
SELECT axis_name, COUNT(*) as segment_count
FROM discovered_segments
GROUP BY axis_name;

# Find customers with no archetype
SELECT customer_id FROM combined_sales
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM customer_segments);
```

---

### Test API Endpoints Locally

```bash
# Start local server
uvicorn backend.api.main:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/health

# Test customer intelligence
curl http://localhost:8000/api/intelligence/customer/12345
```

---

### Profile ML Performance

```python
# Time fuzzy membership calculation
import time

start = time.time()
memberships = _calculate_fuzzy_membership(features, segments)
elapsed = time.time() - start

logger.info(f"Fuzzy membership took {elapsed:.2f}s")
```

---

### Check Railway Metrics

```bash
# View deployment logs
railway logs --tail 100

# View service status
railway status

# View environment variables
railway variables

# View build logs
railway logs --deployment
```

---

## FAQ

### Q: How often should segmentation be re-run?

**A**: Weekly for most stores. Daily if customer behavior is highly dynamic (e.g., flash sales, seasonal products).

### Q: What's the minimum customer count for meaningful segments?

**A**: 100 customers minimum. Below this, segments may not be statistically significant.

### Q: Can I use Quimbi with multiple Shopify stores?

**A**: Yes, use `store_id` parameter in all API calls. Each store has independent segments.

### Q: How do I migrate from v2.0 to v3.0 segmentation?

**A**: Run `python -m backend.segmentation.discover_segments --force-rediscover` to regenerate all segments with new algorithm.

### Q: What happens if Shopify sync fails?

**A**: API continues serving cached data. Sync errors are logged. Set up alerts on sync failures.

### Q: How do I delete customer data (GDPR compliance)?

**A**:
```bash
python -m backend.integrations.delete_customer_data --customer-id=12345
```

---

## Getting Help

### 1. Check Logs

```bash
# Railway production logs
railway logs --service QuimbiBrainBEv1.0 --tail 500

# Local development logs
tail -f logs/quimbi.log
```

### 2. Search Documentation

- [BEHAVIORAL_MATH.md](reference/BEHAVIORAL_MATH.md) - Mathematical details
- [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) - API reference
- [SYSTEM_ARCHITECTURE.md](../q.ai-customer-support/SYSTEM_ARCHITECTURE.md) - Architecture

### 3. Contact Support

**Email**: support@quimbi.ai
**Slack**: #quimbi-support (internal)
**GitHub Issues**: https://github.com/scottatquimbi/q-monorepo/issues

---

**Last Updated**: December 30, 2024
**Next Review**: January 30, 2025

🤖 Generated with [Claude Code](https://claude.com/claude-code)
