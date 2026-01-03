# Hierarchical Customer Archetype System - Technical Documentation

## System Overview

The hierarchical customer archetype system segments customers across 9 behavioral axes using fuzzy c-means clustering with hierarchical refinement. It generates three tiers of archetypes (L1, L2, L3) providing increasing granularity from broad segments to near-unique customer fingerprints.

## Architecture

### Data Flow

```
Customer Data (PostgreSQL)
    ↓
Feature Engineering (9 behavioral axes)
    ↓
Fuzzy C-Means Clustering (per axis)
    ↓
Hierarchical Clustering (3 levels deep)
    ↓
Fuzzy Membership Calculation
    ↓
L1/L2/L3 Archetype Generation
    ↓
Database Storage (dimension + fact tables)
```

### Behavioral Axes

1. **purchase_frequency** - Customer purchase rate
2. **purchase_value** - Average order value
3. **price_sensitivity** - Response to discounts/pricing
4. **category_exploration** - Product category diversity
5. **repurchase_behavior** - Repeat purchase patterns
6. **return_behavior** - Product return frequency
7. **purchase_cadence** - Time between purchases
8. **customer_maturity** - Account lifecycle stage
9. **loyalty_trajectory** - Loyalty trend over time

### Archetype Tiers

**L1 (Dominant Segment)**
- **Method**: Single highest-scoring segment per axis
- **Count**: 296 unique archetypes
- **Avg customers/archetype**: 319.9
- **Use case**: Broad segmentation, campaign targeting, executive reporting
- **Calculation**: `argmax(fuzzy_membership_scores)`

**L2 (Filtered & Renormalized)**
- **Method**: All segments with membership ≥10%, renormalized to sum=1
- **Count**: 49,266 unique archetypes
- **Avg customers/archetype**: 1.9
- **Use case**: AI personalization, product recommendations, dynamic pricing
- **Calculation**: `filter(score ≥ 0.10) → renormalize()`

**L3 (Complete Fuzzy Vector)**
- **Method**: All fuzzy membership scores preserved
- **Count**: 51,612 unique archetypes
- **Avg customers/archetype**: 1.8
- **Use case**: Research analytics, lookalike modeling, precision targeting
- **Calculation**: `complete_fuzzy_memberships`

## Database Schema

### Dimension Tables

#### `platform.dim_archetype_l1`

```sql
CREATE TABLE platform.dim_archetype_l1 (
    archetype_id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
    dominant_segments JSONB NOT NULL,
    description TEXT,
    behavioral_traits TEXT[],
    member_count INTEGER NOT NULL,
    population_percentage DOUBLE PRECISION NOT NULL,
    avg_lifetime_value DOUBLE PRECISION,
    avg_order_frequency DOUBLE PRECISION,
    last_calculated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    tenant_id UUID
);
```

- **dominant_segments**: `{axis: segment_name}` mapping
- **behavioral_traits**: Array of `axis:segment` strings
- **member_count**: Count of customers with this archetype
- **population_percentage**: Percentage of total customer base

#### `platform.dim_archetype_l2`

```sql
CREATE TABLE platform.dim_archetype_l2 (
    archetype_id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
    dominant_segments JSONB NOT NULL,
    membership_strengths JSONB NOT NULL,
    description TEXT,
    behavioral_traits TEXT[],
    member_count INTEGER NOT NULL,
    population_percentage DOUBLE PRECISION NOT NULL,
    avg_lifetime_value DOUBLE PRECISION,
    avg_order_frequency DOUBLE PRECISION,
    last_calculated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    tenant_id UUID
);
```

- **membership_strengths**: `{axis: {segment: score}}` - filtered segments ≥10%
- **dominant_segments**: Highest-scoring segment per axis

#### `platform.dim_archetype_l3`

```sql
CREATE TABLE platform.dim_archetype_l3 (
    archetype_id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
    fuzzy_memberships JSONB NOT NULL,
    dominant_segments JSONB NOT NULL,
    description TEXT,
    behavioral_traits TEXT[],
    member_count INTEGER NOT NULL,
    population_percentage DOUBLE PRECISION NOT NULL,
    avg_lifetime_value DOUBLE PRECISION,
    avg_order_frequency DOUBLE PRECISION,
    last_calculated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    tenant_id UUID
);
```

- **fuzzy_memberships**: `{axis: {segment: score}}` - complete fuzzy vector
- All segments with non-zero membership preserved

### Customer Assignment Tables

#### `platform.customer_archetypes`

```sql
CREATE TABLE platform.customer_archetypes (
    customer_id VARCHAR(255) PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
    archetype_l1_id VARCHAR(50) NOT NULL,
    archetype_l2_id VARCHAR(50) NOT NULL,
    archetype_l3_id VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    tenant_id UUID,

    CONSTRAINT fk_customer_archetype_l1
        FOREIGN KEY (archetype_l1_id)
        REFERENCES platform.dim_archetype_l1(archetype_id),
    CONSTRAINT fk_customer_archetype_l2
        FOREIGN KEY (archetype_l2_id)
        REFERENCES platform.dim_archetype_l2(archetype_id),
    CONSTRAINT fk_customer_archetype_l3
        FOREIGN KEY (archetype_l3_id)
        REFERENCES platform.dim_archetype_l3(archetype_id)
);

CREATE INDEX idx_customer_archetypes_l1 ON platform.customer_archetypes(archetype_l1_id);
CREATE INDEX idx_customer_archetypes_l2 ON platform.customer_archetypes(archetype_l2_id);
CREATE INDEX idx_customer_archetypes_l3 ON platform.customer_archetypes(archetype_l3_id);
CREATE INDEX idx_customer_archetypes_store ON platform.customer_archetypes(store_id);
```

**Purpose**: Master table for all customer archetype assignments (94,686 customers)

#### `public.fact_customer_current`

Updated with archetype_l1_id, archetype_l2_id, archetype_l3_id columns linking to dimension tables via foreign keys.

**Purpose**: Fact table for customers with purchase history (27,415 customers)

## Clustering Algorithm

### Fuzzy C-Means Clustering

```python
from sklearn_extra.cluster import FuzzyKMeans

# Per-axis clustering
for axis in behavioral_axes:
    features = extract_features(customers, axis)
    scaled_features = RobustScaler().fit_transform(features)

    model = FuzzyKMeans(
        n_clusters=optimal_k,
        m=2.0,  # Fuzziness parameter
        max_iter=300,
        random_state=42
    )

    fuzzy_memberships = model.fit_predict(scaled_features)
    cluster_centers = model.cluster_centers_
```

### Hierarchical Refinement

```python
def hierarchical_clustering(segment, depth=0, max_depth=3):
    if depth >= max_depth or len(segment.customers) < 100:
        return [segment]

    # Calculate diversity metrics
    diversity = calculate_diversity(segment)

    if not should_subdivide(diversity):
        return [segment]

    # Subdivide using fuzzy c-means
    subsegments = fuzzy_cluster(segment.customers, k=2)

    # Recursively refine
    refined = []
    for subseg in subsegments:
        refined.extend(
            hierarchical_clustering(subseg, depth+1, max_depth)
        )

    return refined
```

### Archetype ID Generation

```python
def generate_archetype_id(profile, tier):
    """
    Generate deterministic archetype ID from profile

    L1: Hash of dominant segments
    L2: Hash of filtered segment set + scores
    L3: Hash of complete fuzzy vector
    """
    profile_str = json.dumps(profile, sort_keys=True)
    hash_val = hashlib.md5(profile_str.encode()).hexdigest()[:6]
    return f"arch_{tier}_{hash_val}"
```

## Critical Implementation Details

### Cluster Center Export Fix

**Issue**: Hierarchical segments were using parent cluster centers instead of their own.

**Impact**: Caused uniform fuzzy membership scores, severely limiting archetype diversity.

**Fix** ([hierarchical_clustering.py:263](../backend/segmentation/hierarchical_clustering.py#L263)):

```python
return [{
    'segment_id': parent_id,
    'depth': current_depth,
    'customer_count': diversity.customer_count,
    'diversity': diversity,
    'cluster_center': cluster_center,  # CRITICAL: Export actual center
    'is_leaf': True,
    'subsegments': None
}]
```

### Cluster Center Scaling Fix

**Issue**: Fuzzy membership calculation requires scaled cluster centers to match scaled customer features.

**Fix** ([ecommerce_clustering_engine.py:911-925](../backend/segmentation/ecommerce_clustering_engine.py#L911-L925)):

```python
# Use actual cluster center from hierarchical segment
subseg_center_raw = sub_seg.get('cluster_center')

if subseg_center_raw is None:
    logger.warning(f"No cluster_center found for {sub_seg_id}")
    subseg_center_scaled = segment.cluster_center
else:
    # Scale the center using the same scaler that was used for population
    if 'center' in scaler_params:
        # RobustScaler
        subseg_center_scaled = (subseg_center_raw - center) / scale
    else:
        # StandardScaler
        subseg_center_scaled = (subseg_center_raw - mean) / scale

refined_segment = DiscoveredSegment(
    ...
    cluster_center=subseg_center_scaled,  # Use ACTUAL segment center (scaled)
    ...
)
```

## Production Pipeline

### Prerequisites

```bash
# Required environment variables
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
export PYTHONPATH="/path/to/quimbi-platform"

# Required Python packages
pip install asyncpg scikit-learn scikit-learn-extra numpy pandas
```

### Execution Steps

#### 1. Generate Archetype Assignments

```bash
cd /path/to/quimbi-platform
python3 scripts/generate_l1_l2_l3_archetypes.py
```

**Output**: `/tmp/archetypes_l1_l2_l3_YYYYMMDD_HHMMSS.json`

**Duration**: ~15-20 minutes for 94,686 customers

**Memory**: ~2-4 GB peak

#### 2. Create/Update Dimension Tables

```bash
python3 scripts/create_platform_dimension_tables.py \
    /tmp/archetypes_l1_l2_l3_YYYYMMDD_HHMMSS.json
```

**Actions**:
- Drops and recreates platform.dim_archetype_l1/l2/l3
- Aggregates customer statistics per archetype
- Populates dimension tables
- Re-enables foreign key constraints

**Duration**: ~2-3 minutes

#### 3. Load Customer Assignments

```bash
python3 scripts/create_customer_archetype_table.py \
    /tmp/archetypes_l1_l2_l3_YYYYMMDD_HHMMSS.json
```

**Actions**:
- Drops and recreates platform.customer_archetypes
- Loads all 94,686 customer assignments
- Creates indexes

**Duration**: ~30 seconds

### Cron Job Configuration

```bash
# Daily archetype regeneration at 2 AM
0 2 * * * cd /path/to/quimbi-platform && \
    export DATABASE_URL="..." && \
    export PYTHONPATH="/path/to/quimbi-platform" && \
    python3 scripts/generate_l1_l2_l3_archetypes.py 2>&1 | \
    tee /var/log/archetypes/generation_$(date +\%Y\%m\%d).log && \
    python3 scripts/create_platform_dimension_tables.py \
    /tmp/archetypes_l1_l2_l3_*.json 2>&1 | \
    tee /var/log/archetypes/dimension_$(date +\%Y\%m\%d).log && \
    python3 scripts/create_customer_archetype_table.py \
    /tmp/archetypes_l1_l2_l3_*.json 2>&1 | \
    tee /var/log/archetypes/customer_$(date +\%Y\%m\%d).log
```

### Error Handling

All scripts include:
- Database connection retry logic
- Transaction rollback on failure
- Detailed error logging
- Exit codes (0=success, 1=failure)

## Performance Characteristics

### Generation Performance

| Component | Duration | Memory | CPU |
|-----------|----------|--------|-----|
| Feature extraction | 2-3 min | 1 GB | 1 core |
| Clustering (9 axes) | 8-10 min | 2 GB | 4 cores |
| Hierarchical refinement | 3-5 min | 1 GB | 2 cores |
| Archetype generation | 1-2 min | 500 MB | 1 core |
| **Total** | **15-20 min** | **2-4 GB** | **4 cores** |

### Database Load Performance

| Operation | Records | Duration |
|-----------|---------|----------|
| Dimension L1 insert | 296 | <1 sec |
| Dimension L2 insert | 49,266 | 10-15 sec |
| Dimension L3 insert | 51,612 | 25-30 sec |
| Customer assignments | 94,686 | 20-25 sec |
| **Total** | **195,860** | **60-70 sec** |

### Query Performance

| Query Type | Typical Duration |
|------------|------------------|
| Single customer lookup | 15-25 ms |
| Archetype analytics | 30-50 ms |
| Segment aggregation | 25-40 ms |
| Complex joins (fact+dim) | 50-100 ms |

## Monitoring & Validation

### Health Checks

```bash
# Verify schema
python3 /tmp/verify_database_schema.py

# Expected output:
# ✅ All checks passed! Database schema is complete.
```

### Data Quality Checks

```python
# Verify archetype coverage
SELECT
    COUNT(*) as total,
    COUNT(archetype_l1_id) as with_l1,
    COUNT(archetype_l2_id) as with_l2,
    COUNT(archetype_l3_id) as with_l3
FROM platform.customer_archetypes;

# Expected: 100% coverage for all tiers
```

### Diversity Metrics

```python
# Check archetype diversity
SELECT
    'L1' as tier,
    COUNT(DISTINCT archetype_l1_id) as unique_archetypes,
    AVG(member_count) as avg_members_per_archetype
FROM platform.dim_archetype_l1

UNION ALL

SELECT
    'L2' as tier,
    COUNT(DISTINCT archetype_l2_id),
    AVG(member_count)
FROM platform.dim_archetype_l2

UNION ALL

SELECT
    'L3' as tier,
    COUNT(DISTINCT archetype_l3_id),
    AVG(member_count)
FROM platform.dim_archetype_l3;
```

Expected results:
- L1: ~300 archetypes, ~300 customers/archetype
- L2: ~50,000 archetypes, ~2 customers/archetype
- L3: ~50,000 archetypes, ~2 customers/archetype

## Troubleshooting

### Common Issues

**1. "No cluster_center found" warnings**

Cause: Hierarchical segment missing cluster center export

Fix: Ensure [hierarchical_clustering.py:263](../backend/segmentation/hierarchical_clustering.py#L263) exports `cluster_center`

**2. Uniform fuzzy membership scores**

Cause: Using parent cluster centers instead of child centers

Fix: Verify [ecommerce_clustering_engine.py:911-925](../backend/segmentation/ecommerce_clustering_engine.py#L911-L925) uses actual segment centers

**3. Foreign key violations during load**

Cause: Dimension tables not populated before customer assignments

Fix: Run scripts in order:
1. create_platform_dimension_tables.py
2. create_customer_archetype_table.py

**4. Memory errors during generation**

Cause: Insufficient RAM for 94k+ customers

Fix: Increase system memory or reduce customer batch size in clustering loops

## API Usage Examples

### Retrieve Customer Archetype

```python
import asyncpg

async def get_customer_archetype(customer_id: str):
    conn = await asyncpg.connect(DATABASE_URL)

    result = await conn.fetchrow("""
        SELECT
            ca.archetype_l1_id,
            ca.archetype_l2_id,
            ca.archetype_l3_id,
            l1.dominant_segments as l1_profile,
            l2.membership_strengths as l2_profile,
            l3.fuzzy_memberships as l3_profile
        FROM platform.customer_archetypes ca
        LEFT JOIN platform.dim_archetype_l1 l1
            ON ca.archetype_l1_id = l1.archetype_id
        LEFT JOIN platform.dim_archetype_l2 l2
            ON ca.archetype_l2_id = l2.archetype_id
        LEFT JOIN platform.dim_archetype_l3 l3
            ON ca.archetype_l3_id = l3.archetype_id
        WHERE ca.customer_id = $1
    """, customer_id)

    await conn.close()
    return dict(result) if result else None
```

### Find Similar Customers (L2)

```python
async def find_similar_customers(customer_id: str, limit: int = 10):
    conn = await asyncpg.connect(DATABASE_URL)

    results = await conn.fetch("""
        WITH target AS (
            SELECT archetype_l2_id
            FROM platform.customer_archetypes
            WHERE customer_id = $1
        )
        SELECT
            ca.customer_id,
            f.lifetime_value,
            f.total_orders
        FROM platform.customer_archetypes ca
        JOIN target t ON ca.archetype_l2_id = t.archetype_l2_id
        LEFT JOIN public.fact_customer_current f
            ON ca.customer_id = f.customer_id
        WHERE ca.customer_id != $1
        ORDER BY f.lifetime_value DESC NULLS LAST
        LIMIT $2
    """, customer_id, limit)

    await conn.close()
    return [dict(r) for r in results]
```

### Segment by Behavioral Trait

```python
async def get_customers_by_trait(trait: str, limit: int = 1000):
    """
    trait format: "axis:segment"
    example: "purchase_frequency:purchase_frequency_high"
    """
    conn = await asyncpg.connect(DATABASE_URL)

    results = await conn.fetch("""
        SELECT
            ca.customer_id,
            l1.member_count,
            l1.avg_lifetime_value
        FROM platform.customer_archetypes ca
        JOIN platform.dim_archetype_l1 l1
            ON ca.archetype_l1_id = l1.archetype_id
        WHERE $1 = ANY(l1.behavioral_traits)
        LIMIT $2
    """, trait, limit)

    await conn.close()
    return [dict(r) for r in results]
```

## Version History

- **2026-01-02**: Production deployment with 94,686 customers
  - Fixed cluster center export bug
  - Implemented L1/L2/L3 tier system
  - Created dimension + fact table schema
  - Added foreign key constraints

## References

- Fuzzy C-Means: Bezdek, J.C. (1981). Pattern Recognition with Fuzzy Objective Function Algorithms
- Hierarchical Clustering: Ward, J.H. (1963). Hierarchical Grouping to Optimize an Objective Function
- Inverse Distance Weighting: Shepard, D. (1968). A two-dimensional interpolation function for irregularly-spaced data
