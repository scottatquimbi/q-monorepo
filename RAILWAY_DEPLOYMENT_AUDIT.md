# Railway Deployment Audit - December 2024

## Summary

**Total Railway Projects**: 9
**Active Deployments**: 5
**Unused/Duplicate Projects**: 4
**Recommendation**: Clean up 4 unused projects

---

## Active Railway Deployments ✅

### 1. **Ecommerce Backend -- Quimbi** (patient-friendship)
- **Status**: ✅ ACTIVE
- **Environment**: staging
- **Domain**: `https://ecommerce-backend-staging-a14c.up.railway.app`
- **Local Repo**: `/Users/scottallen/backend-alpha/` & `/Users/scottallen/unified-segmentation-ecommerce/`
- **GitHub**: `https://github.com/Quimbi-ai/Ecommerce-backend.git`
- **Purpose**: Main e-commerce intelligence API (staging)
- **Service**: Ecommerce-backend
- **Keep**: ✅ YES - Active staging environment

---

### 2. **optimistic-nature**
- **Status**: ✅ ACTIVE
- **Environment**: staging
- **Domain**: `https://unified-segmentation-staging.up.railway.app`
- **Local Repo**: `/Users/scottallen/unified-segmentation-system/`
- **GitHub**: `https://github.com/scottatquimbi/unified-segmentation.git`
- **Purpose**: Unified segmentation system (staging)
- **Service**: unified-segmentation
- **Keep**: ✅ YES - Active staging environment

---

### 3. **FE Customer Support --Alpha** (selfless-beauty)
- **Status**: ✅ ACTIVE
- **Environment**: production
- **Domain**: `https://front-endalphaecommerce-production.up.railway.app`
- **Local Repo**: `/Users/scottallen/front-end_alpha_ecommerce/`
- **GitHub**: `https://github.com/Quimbi-ai/front-end_alpha_ecommerce.git`
- **Purpose**: Frontend for customer support (production)
- **Service**: front-end_alpha_ecommerce
- **Keep**: ✅ YES - Active production frontend

---

### 4. **authentic-comfort**
- **Status**: ✅ ACTIVE
- **Environment**: production
- **Domain**: `https://quimbibrainbev10-production.up.railway.app`
- **Local Repo**: `/Users/scottallen/quimbi-platform/packages/support-backend/`
- **GitHub**: `https://github.com/scottatquimbi/q-monorepo.git`
- **Purpose**: Support backend with AI capabilities (production)
- **Service**: QuimbiBrainBEv1.0
- **Keep**: ✅ YES - Active production support API

---

### 5. **QuimbiAI-GamingAlpha** (innovative-fascination)
- **Status**: ✅ ACTIVE
- **Environment**: production
- **Domain**: `https://skillful-nurturing-production.up.railway.app`
- **Local Repo**: `/Users/scottallen/quimbi-backend/`
- **GitHub**: `https://github.com/Quimbi-ai/CustomerSup_BE.git`
- **Purpose**: Gaming/Customer Support Backend (production)
- **Service**: skillful-nurturing
- **Keep**: ✅ YES - Active production service

---

## Unused/Candidate for Removal ❌

### 6. **empathetic-joy**
- **Status**: ❌ NOT FOUND LOCALLY
- **Issue**: No local repository linked to this project
- **Recommendation**: Check Railway dashboard - likely unused or orphaned
- **Action**: 🗑️ DELETE if not actively used

---

### 7. **Metabase Deployment**
- **Status**: ⚠️ UNKNOWN
- **Issue**: No local repository found
- **Purpose**: Analytics/BI tool deployment
- **Recommendation**: Check if Metabase is actively used
- **Action**:
  - ✅ KEEP if Metabase dashboards are in use
  - 🗑️ DELETE if unused

---

### 8. **Customer Support Ecl BE --Alpha**
- **Status**: ❌ NOT FOUND LOCALLY
- **Issue**: No local repository linked
- **Recommendation**: Possibly duplicate of other customer support backends
- **Action**: 🗑️ DELETE if duplicate/unused

---

### 9. **Q Playground** (caring-intuition)
- **Status**: ⚠️ DEVELOPMENT/TESTING
- **Environment**: production
- **Domain**: `https://quimbi-playground-production.up.railway.app`
- **Local Repo**: `/Users/scottallen/quimbi-playground/`
- **GitHub**: `https://github.com/scottatquimbi/quimbi-playground.git`
- **Purpose**: Development/testing playground
- **Service**: quimbi-playground
- **Recommendation**:
  - ✅ KEEP if actively used for testing
  - 🗑️ DELETE if no longer needed (can redeploy later)

---

## Duplicate/Overlapping Repositories

### Issue: Multiple repos for same project

**Ecommerce Backend has 3+ local repos:**
1. `/Users/scottallen/backend-alpha/` → `backend-alpha.git`
2. `/Users/scottallen/unified-segmentation-ecommerce/` → `Ecommerce-backend.git`
3. `/Users/scottallen/backend-alpha-ecommerce/` → `backend-alpha-ecommerce.git`
4. `/Users/scottallen/PROD_ecommerce_quimbi/` → `PROD_ecommerce_quimbi.git` (EMPTY)

**Recommendation**:
- ✅ Keep: `/Users/scottallen/backend-alpha/` (main development)
- ⚠️ Archive: `/Users/scottallen/backend-alpha-ecommerce/` (old version)
- 🗑️ Delete: `/Users/scottallen/PROD_ecommerce_quimbi/` (empty repo)

---

## Railway Config Issues

### Missing Railway Links
The following Railway projects are NOT linked to any local directory:

1. **empathetic-joy** - No local repo
2. **Metabase Deployment** - No local repo
3. **Customer Support Ecl BE --Alpha** - No local repo

### Stale Config Entry
- `/Users/scottallen/backend-alpha/unified-segmentation-deployment` - **Path doesn't exist**
  - Linked to: optimistic-nature project
  - Issue: Directory was moved/deleted
  - Fix: Re-link from correct directory

---

## Cleanup Recommendations

### Immediate Actions:

1. **Delete unused Railway projects** (saves $$$):
   ```bash
   # Via Railway dashboard, delete:
   - empathetic-joy (if confirmed unused)
   - Customer Support Ecl BE --Alpha (if duplicate)
   ```

2. **Evaluate Metabase**:
   - If not used → delete
   - If used → document and keep

3. **Q Playground**:
   - If just for testing → delete (can redeploy anytime)
   - If actively used → keep

4. **Clean up local repos**:
   ```bash
   # Delete empty repo
   rm -rf /Users/scottallen/PROD_ecommerce_quimbi

   # Archive old version (optional)
   mv /Users/scottallen/backend-alpha-ecommerce ~/archive/
   ```

5. **Re-link Railway configs**:
   ```bash
   cd /Users/scottallen/backend-alpha
   railway link  # Re-link to correct project
   ```

---

## Production Deployment Status

### Missing Production Environment ⚠️

**patient-friendship** (Ecommerce Backend) has:
- ✅ Staging: `ecommerce-backend-staging-a14c.up.railway.app`
- ❌ Production: **NOT FOUND**

**Questions**:
1. Is there a production deployment for the ecommerce backend?
2. Is `beecommerce-production.up.railway.app` the production version?
3. Should we create a production environment?

---

## Cost Optimization

### Potential Savings

Assuming $5-20/month per Railway project:

- **Delete empathetic-joy**: ~$5-20/month
- **Delete Customer Support Ecl BE --Alpha**: ~$5-20/month
- **Delete Q Playground** (if unused): ~$5-20/month

**Total Potential Savings**: $15-60/month

---

## Action Plan

### Priority 1: Identify & Delete Unused Projects
1. Log into Railway dashboard
2. Check last deployment date for:
   - empathetic-joy
   - Customer Support Ecl BE --Alpha
   - Metabase Deployment
3. Delete projects with no activity in 30+ days

### Priority 2: Consolidate Repos
1. Delete `/Users/scottallen/PROD_ecommerce_quimbi` (empty)
2. Archive `/Users/scottallen/backend-alpha-ecommerce` (old)
3. Document which repo is canonical for each project

### Priority 3: Create Production Environment
1. Decide if production ecommerce backend is needed
2. If yes, create production environment in Railway
3. Update documentation with production URLs

### Priority 4: Update Documentation
1. Update [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) with findings
2. Document which Railway project maps to which GitHub repo
3. Create runbook for Railway project management

---

## Railway Project Mapping Table

| Railway Project | Environment | Domain | GitHub Repo | Local Path | Status |
|----------------|-------------|---------|-------------|------------|--------|
| **Ecommerce Backend -- Quimbi** | staging | ecommerce-backend-staging-a14c | Ecommerce-backend.git | backend-alpha/ | ✅ ACTIVE |
| **optimistic-nature** | staging | unified-segmentation-staging | unified-segmentation.git | unified-segmentation-system/ | ✅ ACTIVE |
| **FE Customer Support --Alpha** | production | front-endalphaecommerce-production | front-end_alpha_ecommerce.git | front-end_alpha_ecommerce/ | ✅ ACTIVE |
| **authentic-comfort** | production | quimbibrainbev10-production | q-monorepo.git | quimbi-platform/packages/support-backend/ | ✅ ACTIVE |
| **QuimbiAI-GamingAlpha** | production | skillful-nurturing-production | CustomerSup_BE.git | quimbi-backend/ | ✅ ACTIVE |
| **empathetic-joy** | ? | ? | ? | NONE | ❌ ORPHANED |
| **Metabase Deployment** | ? | ? | ? | NONE | ⚠️ UNKNOWN |
| **Customer Support Ecl BE --Alpha** | ? | ? | ? | NONE | ❌ ORPHANED |
| **Q Playground** | production | quimbi-playground-production | quimbi-playground.git | quimbi-playground/ | ⚠️ DEV/TEST |

---

## Next Steps

1. ✅ Review this audit
2. 🔍 Check Railway dashboard for orphaned projects
3. 🗑️ Delete confirmed unused projects
4. 📋 Update documentation
5. 💰 Monitor cost savings

**Estimated Time**: 1-2 hours
**Estimated Savings**: $15-60/month
