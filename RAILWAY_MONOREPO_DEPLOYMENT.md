# Railway Monorepo Deployment Guide

Guide for deploying q-monorepo to Railway's `authentic-comfort` project with staging/production environments.

## Current Architecture (Before Migration)

```
GitHub Repos (3 separate)              Railway Project: authentic-comfort
├── quimbibrain-repo        ──────────→ QuimbiBrainBEv1.0 (ML backend)
├── backend-support-repo    ──────────→ backend-support (business logic)
└── frontend-repo           ──────────→ frontend
```

## Target Architecture (After Migration)

```
GitHub Repo (1 monorepo)               Railway Project: authentic-comfort

scottatquimbi/q-monorepo              ┌─ Staging Environment ─┐
├── backend/                ──────────→│ quimbibrain-staging   │
├── backend-support/        ──────────→│ support-staging       │
└── frontend/               ──────────→│ frontend-staging      │
                                       └───────────────────────┘

                                       ┌─ Production Environment ─┐
                            ──────────→│ QuimbiBrainBEv1.0        │
                            ──────────→│ backend-support          │
                            ──────────→│ frontend                 │
                                       └──────────────────────────┘
```

## Migration Strategy: Staging First, Then Production

### Phase 1: Create Staging Environment (Risk-Free Testing)

1. Create new Railway environment: `staging`
2. Deploy all 3 services from q-monorepo to staging
3. Test thoroughly
4. Keep production running on old repos (no risk)

### Phase 2: Migrate Production (One Service at a Time)

Once staging is verified:
1. Migrate QuimbiBrainBEv1.0 → point to monorepo
2. Test production
3. Migrate backend-support → point to monorepo
4. Test production
5. Migrate frontend → point to monorepo
6. Test production
7. Archive old GitHub repos

---

## Step-by-Step Implementation

### Prerequisites

1. **Ensure q-monorepo is up to date on GitHub:**
   ```bash
   cd /Users/scottallen/quimbi-platform
   git status
   git push origin clean-main
   ```

2. **Directory structure in q-monorepo:**
   ```
   q-monorepo/
   ├── backend/              # QuimbiBrain ML backend
   │   ├── main.py
   │   ├── requirements.txt
   │   └── ...
   ├── backend-support/      # Business logic backend (if exists)
   │   └── ...
   ├── frontend/             # Frontend application
   │   └── ...
   └── scripts/              # Clustering scripts
   ```

---

## Phase 1: Create Staging Environment

### Step 1.1: Create Staging Environment in Railway

**Option A: Via Railway Dashboard (Recommended)**

1. Go to https://railway.app/project/authentic-comfort
2. Click "Environments" dropdown → "New Environment"
3. Name it: `staging`
4. Click "Create"

**Option B: Via Railway CLI**

```bash
cd /Users/scottallen/quimbi-platform
railway environment create staging
```

### Step 1.2: Deploy QuimbiBrain ML Backend to Staging

**Via Railway Dashboard:**

1. In `staging` environment, click "+ New"
2. Select "GitHub Repo"
3. Choose `scottatquimbi/q-monorepo`
4. Configure service:
   - **Name**: `quimbibrain-staging`
   - **Branch**: `clean-main`
   - **Root Directory**: `/` (monorepo root)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Healthcheck Path**: `/health`

5. Add environment variables (copy from production QuimbiBrainBEv1.0):
   ```
   DATABASE_URL
   ANTHROPIC_API_KEY
   SHOPIFY_ACCESS_TOKEN
   SHOPIFY_SHOP_NAME
   # ... all other variables from production
   ```

6. Click "Deploy"

**Via Railway CLI:**

```bash
cd /Users/scottallen/quimbi-platform

# Switch to staging environment
railway environment staging

# Create new service
railway service create quimbibrain-staging

# Link to monorepo
railway link --service quimbibrain-staging

# Deploy
railway up
```

### Step 1.3: Deploy Backend-Support to Staging (if applicable)

If you have a separate `backend-support` directory:

**Via Railway Dashboard:**

1. In `staging` environment, click "+ New"
2. Select "GitHub Repo"
3. Choose `scottatquimbi/q-monorepo`
4. Configure service:
   - **Name**: `support-staging`
   - **Branch**: `clean-main`
   - **Root Directory**: `/backend-support` (if separate directory)
   - Or adjust start command to point to correct module

5. Add environment variables
6. Click "Deploy"

### Step 1.4: Deploy Frontend to Staging

**Via Railway Dashboard:**

1. In `staging` environment, click "+ New"
2. Select "GitHub Repo"
3. Choose `scottatquimbi/q-monorepo`
4. Configure service:
   - **Name**: `frontend-staging`
   - **Branch**: `clean-main`
   - **Root Directory**: `/frontend`
   - Build/start commands depend on your frontend framework

5. Add environment variables
6. Click "Deploy"

### Step 1.5: Test Staging Environment

```bash
# Check staging services are running
railway status --environment staging

# Check logs
railway logs --service quimbibrain-staging --environment staging

# Test API endpoints
curl https://quimbibrain-staging-xxxxx.railway.app/health
```

**Verify:**
- ✅ All services deploy successfully
- ✅ Health checks pass
- ✅ Database connections work
- ✅ APIs respond correctly
- ✅ Frontend loads and functions
- ✅ Clustering scripts can be run from QuimbiBrain service

---

## Phase 2: Migrate Production (After Staging Verified)

### Option A: Point Existing Services to Monorepo (Recommended)

This keeps your existing service names and URLs.

#### Step 2.1: Migrate QuimbiBrainBEv1.0

**Via Railway Dashboard:**

1. Switch to `production` environment
2. Click on `QuimbiBrainBEv1.0` service
3. Go to **Settings** → **Source**
4. Click "Configure"
5. Change:
   - **Repository**: Keep `scottatquimbi/q-monorepo`
   - **Branch**: Change to `clean-main`
   - **Root Directory**: `/` (if needed)
6. Go to **Settings** → **Deploy**
7. Verify/update:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
8. Click "Redeploy"

**Via Railway CLI:**

```bash
cd /Users/scottallen/quimbi-platform

# Switch to production environment
railway environment production

# Link to the existing service
railway link --service QuimbiBrainBEv1.0

# Deploy from monorepo
railway up
```

#### Step 2.2: Verify QuimbiBrainBEv1.0 Works

```bash
# Check production service
railway logs --service QuimbiBrainBEv1.0 --environment production

# Test production endpoint
curl https://your-production-url.railway.app/health

# Test clustering scripts still work
# (they should now use the updated code from clean-main)
```

#### Step 2.3: Migrate backend-support

Repeat Step 2.1 for `backend-support` service:
- Change repo to monorepo
- Change branch to `clean-main`
- Update root directory if needed
- Redeploy

#### Step 2.4: Migrate frontend

Repeat Step 2.1 for `frontend` service:
- Change repo to monorepo
- Change branch to `clean-main`
- Update root directory to `/frontend`
- Redeploy

---

### Option B: Create New Services (Alternative)

If you want fresh service names:

1. Create new services in production (quimbibrain-v2, support-v2, frontend-v2)
2. Deploy from monorepo
3. Test new services
4. Update DNS/environment variables to point to new services
5. Remove old services

---

## Monorepo Configuration Files

### For QuimbiBrain (ML Backend)

Create `railway-quimbibrain.json` in repo root:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### For Backend-Support

Create `railway-support.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r backend-support/requirements.txt"
  },
  "deploy": {
    "startCommand": "python -m uvicorn backend_support.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### For Frontend

Create `railway-frontend.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

## Environment Variables

### Copy from Existing Services

For each service, copy environment variables from production:

```bash
# List variables from production service
railway variables --service QuimbiBrainBEv1.0 --environment production

# Copy to staging
# (Do this manually in Railway Dashboard or via CLI)
```

### Required Variables for QuimbiBrain

```bash
DATABASE_URL=${{turntable.DATABASE_URL}}
ANTHROPIC_API_KEY=<your-key>
SHOPIFY_ACCESS_TOKEN=<your-token>
SHOPIFY_SHOP_NAME=lindas-electric-quilters
# ... plus any other variables from your current setup
```

---

## Testing Checklist

### Staging Environment

- [ ] All 3 services deploy successfully
- [ ] Health checks pass
- [ ] Database connections work
- [ ] API endpoints respond
- [ ] Frontend loads
- [ ] Test clustering script execution
- [ ] Test Shopify integration
- [ ] Test all critical user flows

### Production Migration

For each migrated service:
- [ ] Service deploys successfully from monorepo
- [ ] No downtime during migration
- [ ] All environment variables preserved
- [ ] Database connections work
- [ ] URLs/endpoints unchanged (if using Option A)
- [ ] Monitor logs for errors
- [ ] Test all integrations

---

## Rollback Plan

### If Staging Fails

- Delete staging environment
- No impact on production
- Debug issues locally
- Try again

### If Production Migration Fails

**Option A (Recommended approach):**
- Service settings still exist
- Just change Source back to old repo
- Redeploy
- Production restored in ~2 minutes

**Option B (If new services):**
- Keep old services running during migration
- Update environment variables to point back to old services
- Remove new services

---

## Benefits of Monorepo Approach

1. **Single Source of Truth**: All code in one repo
2. **Atomic Updates**: Update all services together
3. **Shared Code**: backend, scripts, docs all in one place
4. **Easier CI/CD**: One repo, one pipeline
5. **Better Version Control**: All changes tracked together
6. **Simplified Clustering**: Scripts directly available to ML backend

---

## Post-Migration Cleanup

After successful migration to production:

1. **Archive Old GitHub Repos** (don't delete immediately):
   - Add README noting they're archived
   - Link to q-monorepo
   - Keep for 30-60 days before deleting

2. **Update Documentation**:
   - Update any deployment docs
   - Update team wiki/notes
   - Update CI/CD configs

3. **Remove Staging Environment** (optional):
   - Keep it for future testing
   - Or remove to save costs

---

## Troubleshooting

### "Service failed to deploy"

Check Railway logs:
```bash
railway logs --service <service-name> --environment <env>
```

Common issues:
- Wrong root directory
- Missing requirements.txt
- Wrong start command
- Missing environment variables

### "Health check failed"

- Verify healthcheck path exists (`/health`)
- Check timeout is sufficient (100s)
- Check service actually starts (view logs)

### "Module not found"

- Verify root directory is correct
- Check PYTHONPATH if needed
- Verify requirements.txt has all dependencies

### "Database connection failed"

- Verify DATABASE_URL is set correctly
- Check service has access to database
- Verify database is running in Railway

---

## Next Steps

1. **Review this guide**
2. **Push monorepo to GitHub** (if not already done)
3. **Create staging environment in Railway**
4. **Deploy to staging and test**
5. **Migrate production services one by one**
6. **Celebrate successful migration! 🎉**

---

## Support Resources

- [Railway Monorepo Docs](https://docs.railway.app/guides/monorepo)
- [Railway Environments Docs](https://docs.railway.app/develop/environments)
- [Railway CLI Reference](https://docs.railway.app/develop/cli)
