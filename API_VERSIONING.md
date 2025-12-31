# API Versioning Strategy

**Service**: Quimbi Platform API
**Current Version**: v1.0 (unversioned)
**Last Updated**: December 30, 2024

---

## Table of Contents

1. [Versioning Philosophy](#versioning-philosophy)
2. [Current State](#current-state)
3. [Versioning Approach](#versioning-approach)
4. [Breaking vs Non-Breaking Changes](#breaking-vs-non-breaking-changes)
5. [Migration Guide](#migration-guide)
6. [Deprecation Policy](#deprecation-policy)
7. [Version Support Timeline](#version-support-timeline)

---

## Versioning Philosophy

**Goals**:
- ✅ **Backwards compatibility**: Clients don't break on updates
- ✅ **Clear migration path**: Easy to upgrade between versions
- ✅ **Minimal versions**: Avoid version sprawl
- ✅ **Predictable lifecycle**: Known deprecation timeline

**Principles**:
1. **Semantic Versioning** for API releases (v1.0, v2.0, v2.1)
2. **URL-based versioning** for major versions (/v1/, /v2/)
3. **Header-based versioning** for minor versions (optional)
4. **Graceful deprecation** with 6-month notice

---

## Current State

### Unversioned API (MVP)

**Current Endpoints**:
```
GET  /health
GET  /api/intelligence/customer/{id}
POST /api/intelligence/generate-message
GET  /api/segments/{axis}/list
POST /webhooks/gorgias/ticket
```

**Issues**:
- ❌ No explicit version in URL
- ❌ Breaking changes would affect all clients immediately
- ❌ No deprecation path

**Migration Plan**: Add versioning in Q1 2025

---

## Versioning Approach

### URL-Based Versioning (Recommended)

**Format**: `/v{major}/resource`

**Example**:
```
# Version 1
GET /v1/intelligence/customer/{id}

# Version 2 (with breaking changes)
GET /v2/intelligence/customer/{id}
```

**Advantages**:
- ✅ Explicit and visible in URL
- ✅ Easy to route to different implementations
- ✅ Simple for clients to understand

**Disadvantages**:
- ⚠️ Verbose URLs
- ⚠️ Need to maintain multiple code paths

---

### Implementation Plan

**Phase 1: Add /v1/ prefix to all endpoints**

```python
# Current (unversioned)
@app.get("/api/intelligence/customer/{customer_id}")
async def get_customer_intelligence(customer_id: str):
    # ...

# New (versioned)
from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")

@v1_router.get("/intelligence/customer/{customer_id}")
async def get_customer_intelligence_v1(customer_id: str):
    # Same implementation
```

**Phase 2: Maintain backwards compatibility**

```python
# Keep old unversioned endpoints as aliases to /v1/
@app.get("/api/intelligence/customer/{customer_id}")
async def get_customer_intelligence_legacy(customer_id: str):
    """Legacy endpoint - redirects to /v1/"""
    # Log deprecation warning
    logger.warning(f"Legacy endpoint called: /api/intelligence/customer/{customer_id}")

    # Call v1 implementation
    return await get_customer_intelligence_v1(customer_id)
```

**Phase 3: Deprecation notice (6 months before removal)**

```python
from fastapi import Response

@app.get("/api/intelligence/customer/{customer_id}")
async def get_customer_intelligence_legacy(customer_id: str, response: Response):
    """DEPRECATED - Use /v1/intelligence/customer/{id} instead"""

    # Add deprecation header
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2025-07-01"  # 6 months from now
    response.headers["Link"] = '</v1/intelligence/customer/{id}>; rel="successor-version"'

    logger.warning(f"DEPRECATED endpoint called: /api/intelligence/customer/{customer_id}")

    return await get_customer_intelligence_v1(customer_id)
```

---

## Breaking vs Non-Breaking Changes

### Non-Breaking Changes (Patch/Minor Versions)

**Allowed without version bump**:
- ✅ Adding new endpoints
- ✅ Adding optional fields to request/response
- ✅ Adding new query parameters (optional)
- ✅ Bug fixes that don't change behavior
- ✅ Performance improvements

**Example**:
```json
// v1.0 response
{
  "customer_id": "12345",
  "archetype": "High-Value VIP"
}

// v1.1 response (added optional field - non-breaking)
{
  "customer_id": "12345",
  "archetype": "High-Value VIP",
  "confidence_score": 0.85  // NEW FIELD (optional)
}
```

---

### Breaking Changes (Major Version)

**Require new major version**:
- ❌ Removing endpoints
- ❌ Removing fields from response
- ❌ Changing field types
- ❌ Changing field names
- ❌ Adding required fields to request
- ❌ Changing authentication mechanism
- ❌ Changing error response format

**Example - Breaking Change**:
```json
// v1 response
{
  "customer_id": "12345",
  "archetype": "High-Value VIP"  // String format
}

// v2 response (breaking - changed archetype to object)
{
  "customer_id": "12345",
  "archetype": {  // NOW AN OBJECT (breaks v1 clients)
    "id": "arch_12345",
    "name": "High-Value VIP",
    "traits": ["quality_focused", "frequent_buyer"]
  }
}
```

---

## Migration Guide

### Migrating from Unversioned → v1

**Timeline**: Q1 2025

**Steps for Clients**:

1. **Update base URL** (immediate - backwards compatible):
   ```python
   # Old
   BASE_URL = "https://quimbibrainbev10-production.up.railway.app/api"

   # New
   BASE_URL = "https://quimbibrainbev10-production.up.railway.app/v1"
   ```

2. **Test endpoints** (verify same behavior):
   ```bash
   # Old (still works)
   curl https://quimbibrainbev10-production.up.railway.app/api/intelligence/customer/12345

   # New (same response)
   curl https://quimbibrainbev10-production.up.railway.app/v1/intelligence/customer/12345
   ```

3. **Monitor deprecation headers**:
   ```bash
   curl -I https://quimbibrainbev10-production.up.railway.app/api/intelligence/customer/12345
   # Check for:
   # Deprecation: true
   # Sunset: 2025-07-01
   ```

4. **Complete migration** before sunset date (2025-07-01)

---

### Migrating from v1 → v2 (Future)

**When v2 is released** (estimated Q3 2025):

**Breaking Changes** (example):
- Archetype response format changed to object
- Customer ID now includes store prefix (e.g., "lindas_12345")
- Authentication required (API key)

**Migration Steps**:

1. **Read migration guide**: `/v2/MIGRATION_GUIDE.md`

2. **Update client code**:
   ```python
   # v1 - archetype is string
   archetype = response["archetype"]

   # v2 - archetype is object
   archetype_name = response["archetype"]["name"]
   archetype_traits = response["archetype"]["traits"]
   ```

3. **Add API key authentication**:
   ```python
   headers = {"X-API-Key": "qk_live_abc123"}
   response = requests.get(url, headers=headers)
   ```

4. **Test in v2 sandbox**: `https://quimbibrainbev10-staging.up.railway.app/v2`

5. **Deploy to production** once validated

---

## Deprecation Policy

### Timeline

**6-month deprecation window**:
1. **Month 0**: Announce deprecation (blog post, email, API headers)
2. **Month 1-5**: Deprecation warnings in responses
3. **Month 6**: Remove deprecated endpoints

**Example Timeline**:
- Jan 1, 2025: Announce unversioned API deprecation
- Jan 1 - Jun 30, 2025: Deprecation warnings active
- Jul 1, 2025: Unversioned API removed

---

### Deprecation Headers

**Standard headers** (RFC 8594):

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Mon, 01 Jul 2025 00:00:00 GMT
Link: </v1/intelligence/customer/{id}>; rel="successor-version"
```

**Client should**:
- Check for `Deprecation: true` header
- Note `Sunset` date (when endpoint will be removed)
- Migrate to `Link` header URL (successor version)

---

### Communication Channels

**Deprecation announcements**:
1. **API response headers** (immediate feedback)
2. **Email to registered developers** (1 week notice)
3. **Blog post** (public announcement)
4. **Changelog** (in documentation)
5. **Slack notifications** (for enterprise customers)

---

## Version Support Timeline

### Support Matrix

| Version | Release Date | Sunset Date | Status |
|---------|-------------|-------------|--------|
| **Unversioned** | Nov 2024 | Jul 1, 2025 | 🟡 Deprecated |
| **v1.0** | Jan 1, 2025 | TBD (12+ months) | ✅ Supported |
| **v2.0** | Q3 2025 (planned) | TBD | 🔵 Planned |

**Support Policy**:
- **Current version**: Full support (bug fixes, features)
- **Previous version**: Security fixes only
- **Deprecated versions**: No support, sunset date announced

---

## Endpoint Inventory

### v1.0 Endpoints (Planned)

**Intelligence API**:
```
GET    /v1/intelligence/customer/{customer_id}
POST   /v1/intelligence/generate-message
GET    /v1/intelligence/customer/{customer_id}/history
```

**Segments API**:
```
GET    /v1/segments/axes
GET    /v1/segments/{axis}/list
GET    /v1/segments/{axis}/{segment_name}
```

**ML Models API**:
```
POST   /v1/ml/predict-churn
POST   /v1/ml/predict-ltv
GET    /v1/ml/model-status
```

**Webhooks** (unversioned, stable interface):
```
POST   /webhooks/gorgias/ticket
POST   /webhooks/shopify/order
```

**System**:
```
GET    /v1/health
GET    /v1/version
```

---

## Versioning Best Practices

### For API Developers

1. **Never break existing contracts** - Additive changes only in minor versions
2. **Document all changes** - Keep CHANGELOG.md updated
3. **Test backwards compatibility** - Regression tests for v1 endpoints
4. **Version OpenAPI spec** - Separate spec files for each version

### For API Clients

1. **Always specify version** - Don't rely on unversioned endpoints
2. **Handle deprecation gracefully** - Check Deprecation headers
3. **Test before migrating** - Use staging environment
4. **Pin to specific version** - Don't use "latest" in production

---

## Semantic Versioning

**Format**: `MAJOR.MINOR.PATCH`

**Version Bumps**:
- **MAJOR** (v1.0 → v2.0): Breaking changes
- **MINOR** (v1.0 → v1.1): New features, backwards compatible
- **PATCH** (v1.0.0 → v1.0.1): Bug fixes only

**Examples**:
- v1.0.0 → v1.0.1: Fixed churn prediction accuracy bug
- v1.0.0 → v1.1.0: Added confidence scores to responses
- v1.0.0 → v2.0.0: Changed archetype format from string to object

---

## Changelog Format

**Keep CHANGELOG.md** in repository root:

```markdown
# Changelog

All notable changes to Quimbi Platform API will be documented in this file.

## [Unreleased]

### Added
- Confidence scores to customer intelligence responses

## [1.1.0] - 2025-02-15

### Added
- New endpoint: GET /v1/intelligence/customer/{id}/history
- Confidence scores for churn predictions

### Fixed
- LTV prediction bug for customers with refunds

## [1.0.0] - 2025-01-01

### Added
- Initial v1 release with versioned endpoints
- Customer intelligence API
- Segmentation API
- ML prediction API

### Deprecated
- Unversioned endpoints (/api/*) - sunset date 2025-07-01
```

---

## Future Considerations

### GraphQL Alternative

**Consideration**: GraphQL avoids versioning issues

**Pros**:
- ✅ Clients request only needed fields
- ✅ Schema evolution without breaking changes
- ✅ Single endpoint (`/graphql`)

**Cons**:
- ⚠️ Higher complexity
- ⚠️ Caching more difficult
- ⚠️ Rate limiting more complex

**Decision**: Stick with REST + versioning for now, revisit in v3

---

### API Gateways

**Consideration**: Use Kong/AWS API Gateway for versioning

**Benefits**:
- ✅ Centralized versioning logic
- ✅ Easy A/B testing between versions
- ✅ Built-in rate limiting, analytics

**Decision**: Defer until multi-tenant deployment (Phase 3)

---

**Last Updated**: December 30, 2024
**Next Review**: March 30, 2025
**Owner**: Head of Engineering

🤖 Generated with [Claude Code](https://claude.com/claude-code)
