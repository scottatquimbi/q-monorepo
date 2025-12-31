# Repository Audit & Cleanup Recommendations

**Date**: December 30, 2024
**Audit Scope**: All repositories in `/Users/scottallen/`
**Purpose**: Identify active repos, Railway deployments, and redundancies

---

## Executive Summary

**Total Repositories**: 15 git repositories
**Railway Connected**: 15 repositories (100%)
**Active (Updated in last 30 days)**: 5 repositories
**Redundant/Outdated**: 10 repositories

**Recommendation**: Consolidate and archive 7-8 outdated repos

---

## Repository Status Table

| Repository | Last Commit | Branch | Railway Project | Railway Service | Status |
|------------|-------------|--------|----------------|-----------------|---------|
| **q.ai-customer-support** | 2025-12-30 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ✅ **ACTIVE** |
| **quimbi-platform** | 2025-12-29 | clean-main | authentic-comfort | QuimbiBrainBEv1.0 | ✅ **ACTIVE** |
| **front-end_alpha_ecommerce** | 2025-12-11 | main | FE Customer Support --Alpha | front-end_alpha_ecommerce | ✅ **ACTIVE** |
| QuimbiDemoAsApp | 2025-12-03 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ⚠️ **REDUNDANT** |
| quimbi-backend | 2025-12-01 | main | QuimbiAI-GamingAlpha | skillful-nurturing | ⚠️ **OUTDATED** |
| unified-segmentation-ecommerce | 2025-12-01 | main | Ecommerce Backend -- Quimbi | None | ⚠️ **REDUNDANT** |
| ArbiterIO | 2025-11-26 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ⚠️ **EXTERNAL** |
| quimbi-support-backend | 2025-11-23 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ❌ **DUPLICATE** |
| quimbi-frontend | 2025-11-23 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ❌ **DUPLICATE** |
| unified-segmentation-system | 2025-10-15 | main | optimistic-nature | unified-segmentation | ❌ **OUTDATED** |
| backend-alpha | 2025-10-10 | main | Ecommerce Backend -- Quimbi | None | ❌ **OUTDATED** |
| quimbi-playground | 2025-10-05 | main | Q Playground | quimbi-playground | ⚠️ **TESTING** |
| backend-alpha-ecommerce | 2025-09-29 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ❌ **OUTDATED** |
| Quimbi-website | 2025-09-21 | main | Ecommerce Backend -- Quimbi | Ecommerce-backend | ❌ **OUTDATED** |
| PROD_ecommerce_quimbi | no commits | - | Ecommerce Backend -- Quimbi | Ecommerce-backend | ❌ **EMPTY** |

---

## Active Production Repositories (Keep)

### 1. ✅ **quimbi-platform** (Main Intelligence Backend)

**Location**: `/Users/scottallen/quimbi-platform`
**GitHub**: `https://github.com/scottatquimbi/q-monorepo`
**Railway**: `authentic-comfort` → `QuimbiBrainBEv1.0`
**Deployment**: `https://quimbibrainbev10-production.up.railway.app`
**Last Commit**: 2025-12-29
**Branch**: `clean-main`

**Purpose**: Core AI/ML intelligence engine
- 868 behavioral archetypes
- Fuzzy clustering mathematics
- Customer intelligence API
- Churn prediction & LTV forecasting

**Documentation**:
- `reference/BEHAVIORAL_MATH.md` (920 lines)
- `backend/ml/README.md` (464 lines)
- `docs/FCM_TEMPORAL_DRIFT_SYSTEM.md` (728 lines)

**Status**: **PRIMARY PRODUCTION SYSTEM** - Most up-to-date ML code

---

### 2. ✅ **q.ai-customer-support** (Customer Support Backend)

**Location**: `/Users/scottallen/q.ai-customer-support`
**GitHub**: `https://github.com/Quimbi-ai/q.ai-customer-support`
**Railway**: `Ecommerce Backend -- Quimbi` → `Ecommerce-backend`
**Deployment**: `https://beecommerce-production.up.railway.app`
**Last Commit**: 2025-12-30 (TODAY)
**Branch**: `main`

**Purpose**: Customer support automation
- Gorgias webhook processing
- Shopify fulfillment integration
- AI draft generation (calls quimbi-platform)
- Internal notes for agents

**Documentation**:
- `SYSTEM_ARCHITECTURE.md` - Service architecture
- `QUIMBI_ECOSYSTEM_OVERVIEW.md` - Ecosystem map
- `GORGIAS_POSTING_IMPLEMENTATION.md` - Features

**Status**: **ACTIVE PRODUCTION** - Most recently updated (today!)

---

### 3. ✅ **front-end_alpha_ecommerce** (Frontend Dashboard)

**Location**: `/Users/scottallen/front-end_alpha_ecommerce`
**GitHub**: `https://github.com/Quimbi-ai/front-end_alpha_ecommerce`
**Railway**: `FE Customer Support --Alpha` → `front-end_alpha_ecommerce`
**Last Commit**: 2025-12-11
**Branch**: `main`

**Purpose**: Agent dashboard and customer intelligence UI
- Support agent dashboard
- Customer archetype visualization
- Natural language queries (Claude-powered)

**Status**: **ACTIVE PRODUCTION** - Frontend for support system

---

## Redundant/Duplicate Repositories (Consider Archiving)

### ❌ **quimbi-support-backend** (DUPLICATE of q.ai-customer-support)

**Location**: `/Users/scottallen/quimbi-support-backend`
**GitHub**: `https://github.com/Quimbi-ai/q.ai-customer-support` (SAME AS #2!)
**Last Commit**: 2025-11-23 (37 days ago)
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: This is a DUPLICATE clone of `q.ai-customer-support` pointing to the same GitHub repo.

**Recommendation**: ❌ **DELETE LOCAL DIRECTORY** - Use `q.ai-customer-support` instead

---

### ❌ **quimbi-frontend** (DUPLICATE?)

**Location**: `/Users/scottallen/quimbi-frontend`
**GitHub**: `https://github.com/Quimbi-ai/MinimalAI_FE`
**Last Commit**: 2025-11-23 (37 days ago)
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: Likely duplicate/old version of `front-end_alpha_ecommerce`

**Recommendation**: ❌ **ARCHIVE** - Use `front-end_alpha_ecommerce` as primary frontend

---

### ❌ **PROD_ecommerce_quimbi** (EMPTY)

**Location**: `/Users/scottallen/PROD_ecommerce_quimbi`
**GitHub**: `https://github.com/Quimbi-ai/PROD_ecommerce_quimbi`
**Last Commit**: None (empty repo)
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: Empty repository with no commits

**Recommendation**: ❌ **DELETE LOCAL DIRECTORY** - Completely empty

---

### ❌ **unified-segmentation-ecommerce** (OUTDATED)

**Location**: `/Users/scottallen/unified-segmentation-ecommerce`
**GitHub**: `https://github.com/Quimbi-ai/Ecommerce-backend`
**Last Commit**: 2025-12-01 (29 days ago)
**Railway**: Ecommerce Backend -- Quimbi (Service: None)

**Issue**: Contains ML documentation (ML_ARCHITECTURE_DEEP_DIVE.md) but code is outdated. Documentation has been superseded by `quimbi-platform/reference/BEHAVIORAL_MATH.md`

**Recommendation**: ⚠️ **EXTRACT DOCS → ARCHIVE**
- Copy unique documentation to `quimbi-platform/docs/archive/`
- Archive the repo

---

### ❌ **unified-segmentation-system** (OUTDATED)

**Location**: `/Users/scottallen/unified-segmentation-system`
**GitHub**: `https://github.com/scottatquimbi/unified-segmentation`
**Last Commit**: 2025-10-15 (76 days ago)
**Railway**: optimistic-nature → unified-segmentation

**Issue**: Old version of segmentation system, superseded by `quimbi-platform`

**Recommendation**: ❌ **ARCHIVE** - Code is outdated

---

### ❌ **backend-alpha** (OUTDATED)

**Location**: `/Users/scottallen/backend-alpha`
**GitHub**: `https://github.com/Quimbi-ai/backend-alpha`
**Last Commit**: 2025-10-10 (81 days ago)
**Railway**: Ecommerce Backend -- Quimbi (Service: None)

**Issue**: Old alpha version, no Railway service assigned

**Recommendation**: ❌ **ARCHIVE**

---

### ❌ **backend-alpha-ecommerce** (OUTDATED)

**Location**: `/Users/scottallen/backend-alpha-ecommerce`
**GitHub**: `https://github.com/scottatquimbi/backend-alpha-ecommerce`
**Last Commit**: 2025-09-29 (92 days ago)
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: Another old alpha version

**Recommendation**: ❌ **ARCHIVE**

---

### ❌ **Quimbi-website** (OUTDATED)

**Location**: `/Users/scottallen/Quimbi-website`
**GitHub**: `https://github.com/scottatquimbi/Quimbi-website`
**Last Commit**: 2025-09-21 (100 days ago)
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: Website repo hasn't been updated in 3+ months

**Recommendation**: ⚠️ **CHECK IF STILL USED** - Archive if not public-facing

---

## Special Case Repositories

### ⚠️ **quimbi-backend** (Gaming Alpha?)

**Location**: `/Users/scottallen/quimbi-backend`
**GitHub**: `https://github.com/Quimbi-ai/CustomerSup_BE`
**Last Commit**: 2025-12-01
**Railway**: QuimbiAI-GamingAlpha → skillful-nurturing

**Issue**: Connected to "Gaming Alpha" project - unclear purpose

**Recommendation**: ⚠️ **INVESTIGATE** - Is this still active? Different product line?

---

### ⚠️ **QuimbiDemoAsApp** (Demo/Testing)

**Location**: `/Users/scottallen/QuimbiDemoAsApp`
**GitHub**: `https://github.com/scottatquimbi/QuimbiDemoAsApp`
**Last Commit**: 2025-12-03
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: Demo application - unclear if still needed

**Recommendation**: ⚠️ **KEEP FOR DEMOS** or archive if no longer used

---

### ⚠️ **quimbi-playground** (Testing)

**Location**: `/Users/scottallen/quimbi-playground`
**GitHub**: `https://github.com/scottatquimbi/quimbi-playground`
**Last Commit**: 2025-10-05
**Railway**: Q Playground → quimbi-playground

**Issue**: Playground/testing environment

**Recommendation**: ⚠️ **KEEP FOR TESTING** - Useful for experiments

---

### ⚠️ **ArbiterIO** (External Project)

**Location**: `/Users/scottallen/ArbiterIO`
**GitHub**: `https://github.com/greenteasamurai/arbiter`
**Last Commit**: 2025-11-26
**Railway**: Ecommerce Backend -- Quimbi

**Issue**: External project (greenteasamurai org) connected to Quimbi Railway

**Recommendation**: ⚠️ **INVESTIGATE** - Why is this connected to Quimbi Railway?

---

## Railway Project Consolidation Issues

### Problem: Many Repos Point to Same Railway Service

**Ecommerce Backend -- Quimbi** (12 repos connected!):
- q.ai-customer-support ✅ (CORRECT - production)
- QuimbiDemoAsApp
- unified-segmentation-ecommerce
- ArbiterIO
- quimbi-support-backend (duplicate)
- quimbi-frontend
- backend-alpha
- quimbi-playground
- backend-alpha-ecommerce
- Quimbi-website
- PROD_ecommerce_quimbi (empty)

**Issue**: Multiple local repos are linked to the same Railway project/service, but only ONE should be the source of truth.

**Expected State**:
```
authentic-comfort → QuimbiBrainBEv1.0 → quimbi-platform ✅
Ecommerce Backend -- Quimbi → beecommerce-production → q.ai-customer-support ✅
FE Customer Support --Alpha → front-end_alpha_ecommerce → front-end_alpha_ecommerce ✅
```

---

## Cleanup Action Plan

### Phase 1: Immediate (Do Now)

1. ❌ **Delete Empty Repo**:
   ```bash
   rm -rf /Users/scottallen/PROD_ecommerce_quimbi
   ```

2. ❌ **Delete Duplicate**:
   ```bash
   rm -rf /Users/scottallen/quimbi-support-backend
   # (This is the same as q.ai-customer-support)
   ```

3. ⚠️ **Extract & Archive Documentation**:
   ```bash
   # Copy unique docs from unified-segmentation-ecommerce
   cp /Users/scottallen/unified-segmentation-ecommerce/ML_ARCHITECTURE_DEEP_DIVE.md \
      /Users/scottallen/quimbi-platform/docs/archive/

   cp /Users/scottallen/unified-segmentation-ecommerce/ML_CHURN_LTV_SCOPE.md \
      /Users/scottallen/quimbi-platform/docs/archive/

   # Then archive the repo
   mkdir -p ~/Archive/old-repos-2024-12-30
   mv /Users/scottallen/unified-segmentation-ecommerce ~/Archive/old-repos-2024-12-30/
   ```

### Phase 2: Archive Outdated (This Week)

4. ❌ **Archive Old Backends**:
   ```bash
   mkdir -p ~/Archive/old-repos-2024-12-30
   mv /Users/scottallen/backend-alpha ~/Archive/old-repos-2024-12-30/
   mv /Users/scottallen/backend-alpha-ecommerce ~/Archive/old-repos-2024-12-30/
   mv /Users/scottallen/unified-segmentation-system ~/Archive/old-repos-2024-12-30/
   ```

5. ⚠️ **Check Before Archiving**:
   - `quimbi-frontend` - Confirm `front-end_alpha_ecommerce` is the production frontend
   - `Quimbi-website` - Check if website is still public-facing
   - `QuimbiDemoAsApp` - Confirm not needed for demos

### Phase 3: Investigate (Next Week)

6. ⚠️ **Investigate Special Cases**:
   - `quimbi-backend` (Gaming Alpha project)
   - `ArbiterIO` (External project)

---

## Recommended Final State

**Active Production Repos** (3):
```
/Users/scottallen/
├── quimbi-platform/              ← Main AI/ML backend
├── q.ai-customer-support/        ← Customer support backend
└── front-end_alpha_ecommerce/    ← Frontend dashboard
```

**Testing/Development** (2):
```
├── quimbi-playground/            ← Testing environment
└── QuimbiDemoAsApp/              ← Demo application (if needed)
```

**Archived** (~/Archive/old-repos-2024-12-30/):
```
├── unified-segmentation-ecommerce/
├── unified-segmentation-system/
├── backend-alpha/
├── backend-alpha-ecommerce/
├── quimbi-frontend/              (if confirmed duplicate)
├── Quimbi-website/               (if not public)
└── quimbi-support-backend/
```

**Total Reduction**: 15 repos → 5 active repos (67% reduction)

---

## Railway Project Mapping

**Correct Mapping**:

| Railway Project | Service | Repository | Deployment URL |
|----------------|---------|------------|----------------|
| **authentic-comfort** | QuimbiBrainBEv1.0 | quimbi-platform | quimbibrainbev10-production.up.railway.app |
| **authentic-comfort** | beecommerce-production | q.ai-customer-support | beecommerce-production.up.railway.app |
| **FE Customer Support --Alpha** | front-end_alpha_ecommerce | front-end_alpha_ecommerce | TBD |
| Q Playground | quimbi-playground | quimbi-playground | TBD |

**Action**: Disconnect archived repos from Railway to avoid confusion

---

## Documentation Consolidation

**Primary Documentation Location**: `/Users/scottallen/quimbi-platform/docs/`

**Move to quimbi-platform**:
- `unified-segmentation-ecommerce/ML_ARCHITECTURE_DEEP_DIVE.md` → `docs/archive/ML_ARCHITECTURE_DEEP_DIVE.md`
- `unified-segmentation-ecommerce/ML_CHURN_LTV_SCOPE.md` → `docs/archive/ML_CHURN_LTV_SCOPE.md`
- Any unique docs from other repos

**Result**: Single source of truth for all ML/AI documentation

---

## Benefits of Cleanup

✅ **Clarity**: Clear which repos are active vs archived
✅ **Performance**: Fewer Railway connections to manage
✅ **Maintenance**: Easier to know where to make changes
✅ **Onboarding**: New developers see only active code
✅ **Cost**: Reduce Railway project count if possible

---

## Next Steps

1. ✅ Review this audit
2. ⚠️ Confirm repos to archive
3. ⚠️ Extract unique documentation
4. ⚠️ Execute Phase 1 cleanup
5. ⚠️ Update QUIMBI_ECOSYSTEM_OVERVIEW.md with final state
6. ⚠️ Document in CHANGELOG

---

**Generated**: December 30, 2024
**Author**: Repository Audit Script
**Review Required**: Yes - Confirm before deleting repos

🤖 Generated with [Claude Code](https://claude.com/claude-code)
