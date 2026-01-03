# L1/L2/L3 Archetype Methodology
## Three-Tier Behavioral Fingerprinting System

**Version**: 2.0 (Hierarchical Clustering)
**Date**: January 1, 2026
**Status**: Production-Ready

---

## Executive Summary

This document defines the **three-tier archetype system** that transforms raw behavioral clustering results into actionable customer archetypes at different granularity levels.

**The Three Tiers**:
- **L1 (Dominant)**: Single dominant segment per axis - Simple, interpretable, fast
- **L2 (Significant)**: Fuzzy memberships ≥10% - Captures hybrid personas
- **L3 (Complete)**: Full fuzzy thumbprint - Complete behavioral DNA

**Key Innovation**: Unlike the previous system (which suffered from mega-clusters at L1 and extreme fragmentation at L3), this methodology produces **balanced, statistically-valid archetypes** at all three levels.

---

## Table of Contents

1. [Methodology Overview](#methodology-overview)
2. [L1: Dominant Archetype](#l1-dominant-archetype)
3. [L2: Significant Archetype](#l2-significant-archetype)
4. [L3: Complete Thumbprint](#l3-complete-thumbprint)
5. [Archetype ID Generation](#archetype-id-generation)
6. [Sample Size Requirements](#sample-size-requirements)
7. [Production Deployment Process](#production-deployment-process)
8. [Use Cases by Tier](#use-cases-by-tier)
9. [Comparison to Previous System](#comparison-to-previous-system)

---

## 1. Methodology Overview

### Input: Hierarchical Clustering Results

The L1/L2/L3 system processes output from **9-axis hierarchical clustering**:

```
Axes (9):
├── Financial (3 axes)
│   ├── purchase_frequency → 14 segments
│   ├── purchase_value → 14 segments
│   └── price_sensitivity → 7 segments
├── Product (3 axes)
│   ├── category_exploration → 23 segments
│   ├── repurchase_behavior → 21 segments
│   └── return_behavior → 6 segments
├── Timing (2 axes)
│   ├── purchase_cadence → 8 segments
│   └── customer_maturity → 19 segments
└── Engagement (1 axis)
    └── loyalty_trajectory → 8 segments

Total: 120 balanced segments across 9 axes
```

### Customer Fuzzy Membership Vector

Each customer has fuzzy membership scores across all 120 segments:

```json
{
  "purchase_frequency": {
    "medium.1.2": 0.68,
    "medium.2.0": 0.32
  },
  "purchase_value": {
    "high.2": 0.75,
    "high.1": 0.25
  },
  "category_exploration": {
    "high.1.0": 0.71,
    "high.0.1": 0.29
  },
  ...
}
```

**Constraint**: Fuzzy memberships per axis sum to 1.0 (100%)

---

## 2. L1: Dominant Archetype

### Definition

**L1 extracts the single highest-scoring segment per axis**, ignoring all other memberships.

### Algorithm

```python
def generate_L1_archetype(customer_fuzzy_memberships):
    """
    Generate L1 archetype from fuzzy memberships.

    Returns: Dict with dominant segment per axis
    """
    l1_profile = {}

    for axis, segments in customer_fuzzy_memberships.items():
        # Extract segment with highest fuzzy score
        dominant_segment = max(segments.items(), key=lambda x: x[1])
        l1_profile[axis] = dominant_segment[0]  # Segment name only

    return l1_profile
```

### Example

**Input** (Customer #12345 fuzzy memberships):
```json
{
  "purchase_frequency": {"medium.1.2": 0.68, "medium.2.0": 0.32},
  "purchase_value": {"high.2": 0.75, "high.1": 0.25},
  "category_exploration": {"high.1.0": 0.71, "high.0.1": 0.29}
}
```

**Output** (L1 archetype):
```json
{
  "purchase_frequency": "medium.1.2",
  "purchase_value": "high.2",
  "category_exploration": "high.1.0"
}
```

**Archetype ID**: `arch_L1_452891` (hash of 9 dominant segments)

### Characteristics

- **Simplicity**: Easy to understand ("This customer is a high-value quilting specialist")
- **Performance**: Fast database queries (single segment per axis)
- **Interpretability**: Human-readable customer summaries
- **Loss**: Ignores 32% fuzzy membership in secondary segments

### Expected Distribution (94,686 customers)

```
Estimated unique L1 archetypes: 800-1,500
Average customers per archetype: 60-120
Largest archetype: ~5-8% of population (~5,000-7,500 customers)
```

**Why balanced**: Even though we're selecting dominant segments, the hierarchical clustering ensures no single segment dominates >65% of population.

---

## 3. L2: Significant Archetype

### Definition

**L2 includes all segments where fuzzy membership ≥ 10%**, filtering out noise while preserving hybrid personas.

### Algorithm

```python
def generate_L2_archetype(customer_fuzzy_memberships, threshold=0.10):
    """
    Generate L2 archetype from fuzzy memberships.

    Args:
        threshold: Minimum fuzzy score to include (default 0.10)

    Returns: Dict with significant segments per axis
    """
    l2_profile = {}

    for axis, segments in customer_fuzzy_memberships.items():
        # Filter segments >= threshold
        significant = {
            segment: score
            for segment, score in segments.items()
            if score >= threshold
        }

        # Normalize to sum to 1.0
        total = sum(significant.values())
        l2_profile[axis] = {
            segment: score / total
            for segment, score in significant.items()
        }

    return l2_profile
```

### Example

**Input** (Customer #12345 fuzzy memberships):
```json
{
  "purchase_frequency": {"medium.1.2": 0.68, "medium.2.0": 0.32},
  "purchase_value": {"high.2": 0.75, "high.1": 0.25},
  "category_exploration": {"high.1.0": 0.71, "high.0.1": 0.29},
  "repurchase_behavior": {"medium.0": 0.63, "medium.1": 0.32, "medium.2": 0.05}
}
```

**Output** (L2 archetype, threshold=0.10):
```json
{
  "purchase_frequency": {"medium.1.2": 0.68, "medium.2.0": 0.32},
  "purchase_value": {"high.2": 0.75, "high.1": 0.25},
  "category_exploration": {"high.1.0": 0.71, "high.0.1": 0.29},
  "repurchase_behavior": {"medium.0": 0.66, "medium.1": 0.34}
}
```

**Note**: `medium.2` (0.05) filtered out, remaining scores renormalized.

**Archetype ID**: `arch_L2_789234` (hash of significant membership structure)

### Characteristics

- **Hybrid Personas**: Captures transitioning customers (68% specialist, 32% explorer)
- **Behavioral Nuance**: Preserves secondary behaviors that matter
- **AI-Actionable**: Optimal for recommendation engines and personalization
- **Threshold**: 10% is configurable (environment variable `L2_THRESHOLD`)

### Expected Distribution (94,686 customers)

```
Estimated unique L2 archetypes: 5,000-15,000
Average customers per archetype: 6-20
Largest archetype: ~2-3% of population (~2,000-3,000 customers)
```

**Why more granular**: L2 captures nuanced differences in secondary memberships, creating more unique combinations.

---

## 4. L3: Complete Thumbprint

### Definition

**L3 stores the complete fuzzy membership vector**, including all segments with any non-zero membership.

### Algorithm

```python
def generate_L3_archetype(customer_fuzzy_memberships):
    """
    Generate L3 archetype (complete thumbprint).

    Returns: Complete fuzzy membership dict (no filtering)
    """
    # Return as-is, no transformation
    return customer_fuzzy_memberships
```

### Example

**Input & Output** (identical - no filtering):
```json
{
  "purchase_frequency": {"medium.1.2": 0.68, "medium.2.0": 0.30, "low.0": 0.02},
  "purchase_value": {"high.2": 0.75, "high.1": 0.24, "medium.3": 0.01},
  "category_exploration": {"high.1.0": 0.71, "high.0.1": 0.29},
  "repurchase_behavior": {"medium.0": 0.63, "medium.1": 0.32, "medium.2": 0.05},
  "return_behavior": {"medium.0": 0.95, "medium.1": 0.04, "low.0": 0.01},
  "purchase_cadence": {"medium.0": 0.77, "high": 0.23},
  "customer_maturity": {"high.1": 0.81, "high.2": 0.19},
  "loyalty_trajectory": {"medium.0": 0.72, "medium.2": 0.28},
  "price_sensitivity": {"medium.0": 0.82, "medium.1": 0.18}
}
```

**Archetype ID**: `arch_L3_123456` (hash of complete thumbprint)

### Characteristics

- **Complete Precision**: Full behavioral DNA, no information loss
- **Research-Grade**: Enables deep analysis and similarity matching
- **Anomaly Detection**: Identifies unusual fuzzy distributions
- **Storage**: ~2KB per customer (acceptable for modern databases)

### Expected Distribution (94,686 customers)

```
Estimated unique L3 archetypes: 30,000-60,000
Average customers per archetype: 1.5-3.0
```

**Why granular**: L3 captures every nuance, so most customers will have unique or near-unique thumbprints. This is **expected and desirable** for research/analysis.

---

## 5. Archetype ID Generation

### Hash-Based IDs (Like Current Production)

Archetype IDs follow the format: `arch_{level}_{hash}`

```python
import hashlib
import json

def generate_archetype_id(level, archetype_data):
    """
    Generate archetype ID from profile data.

    Args:
        level: 'L1', 'L2', or 'L3'
        archetype_data: Dict of segment memberships

    Returns: String like 'arch_L1_452891'
    """
    # Create deterministic string representation
    canonical = json.dumps(archetype_data, sort_keys=True)

    # Hash to 6-digit ID
    hash_obj = hashlib.md5(canonical.encode())
    hash_int = int(hash_obj.hexdigest(), 16) % 1000000

    return f"arch_{level}_{hash_int:06d}"
```

### Example IDs

```
L1: arch_L1_452891
L2: arch_L2_789234
L3: arch_L3_123456
```

### Database Schema

```sql
CREATE TABLE fact_customer_current (
    customer_id VARCHAR NOT NULL,
    store_id VARCHAR NOT NULL,

    -- Archetype IDs
    archetype_l1_id VARCHAR,  -- e.g., 'arch_L1_452891'
    archetype_l2_id VARCHAR,  -- e.g., 'arch_L2_789234'
    archetype_l3_id VARCHAR,  -- e.g., 'arch_L3_123456'

    -- Metrics
    lifetime_value FLOAT,
    total_orders INT,
    churn_risk_score FLOAT,

    -- Timestamps
    last_updated TIMESTAMP,
    created_at TIMESTAMP,

    PRIMARY KEY (customer_id, store_id)
);

-- Archetype metadata (optional)
CREATE TABLE archetype_definitions (
    archetype_id VARCHAR PRIMARY KEY,
    level VARCHAR,  -- 'L1', 'L2', or 'L3'
    profile_data JSONB,  -- Full archetype structure
    customer_count INT,  -- How many customers have this archetype
    avg_ltv FLOAT,
    avg_churn_risk FLOAT,
    created_at TIMESTAMP
);
```

---

## 6. Sample Size Requirements

### Production Statistics

```
Total Customers: 94,686
Total Orders: 1,288,058
Average Orders per Customer: 13.6
```

### Sample Size Analysis

**Statistical Requirements**:
- Confidence Level: 95%
- Margin of Error: ±1.5%
- **Required Sample**: 4,000 customers (4.2% of population)

**Why 4K is sufficient**:

| Sample Size | % of Population | Confidence | Margin of Error | Captures Segments ≥ |
|-------------|-----------------|------------|-----------------|---------------------|
| 1,000 | 1.1% | 95% | ±3.1% | 2% of population |
| 2,000 | 2.1% | 95% | ±2.2% | 1% of population |
| **4,000** | **4.2%** | **95%** | **±1.5%** | **0.75% (~710 customers)** |
| 10,000 | 10.6% | 95% | ±1.0% | 0.3% (~280 customers) |
| 94,686 (all) | 100% | 100% | 0% | All segments |

**Recommendation**: ✅ **Use 4,000 stratified random sample**

**Rationale**:
1. **Statistical Validity**: 95% confidence, captures all meaningful segments (>0.75%)
2. **Computational Efficiency**: ~12 minutes vs ~90 minutes for full population
3. **Actionability**: All discovered segments will have 700+ customers in production (statistically significant)
4. **Avoids Overfitting**: Won't create micro-segments for outliers

### Stratified Sampling Strategy

```python
def stratified_sample(population_size=94686, sample_size=4000):
    """
    Create stratified sample ensuring representation.

    Stratify by:
    - Lifetime Value Quartile (Q1/Q2/Q3/Q4)
    - Order Count Tier (1, 2-5, 6-10, 11-20, 21+)
    - Customer Tenure (0-3mo, 3-6mo, 6-12mo, 12-24mo, 24mo+)
    """
    strata = {
        'ltv_quartile': ['Q1', 'Q2', 'Q3', 'Q4'],
        'order_tier': ['1', '2-5', '6-10', '11-20', '21+'],
        'tenure': ['0-3mo', '3-6mo', '6-12mo', '12-24mo', '24mo+']
    }

    # Sample proportionally from each stratum
    # Ensures high/low value, new/established, frequent/occasional all represented
```

---

## 7. Production Deployment Process

### Step 1: Segment Discovery (on 4K sample)

```bash
# Run hierarchical clustering on stratified sample
python3 scripts/run_hierarchical_clustering.py \
  --sample-size 4000 \
  --stratified \
  --axes all \
  --enable-hierarchical

# Output: 120 balanced segments across 9 axes
# Time: ~12 minutes
```

### Step 2: Score All Customers (94,686)

```bash
# Assign fuzzy memberships to all customers
python3 scripts/score_all_customers.py \
  --segments-file discovered_segments.json \
  --output fuzzy_memberships.json

# Time: ~15 minutes
```

### Step 3: Generate L1/L2/L3 Archetypes

```bash
# Generate three-tier archetypes
python3 scripts/generate_archetypes.py \
  --fuzzy-memberships fuzzy_memberships.json \
  --l2-threshold 0.10 \
  --output archetypes_l1_l2_l3.json

# Time: ~5 minutes
```

### Step 4: Load to Database

```bash
# Update fact_customer_current table
python3 scripts/load_archetypes_to_db.py \
  --archetypes archetypes_l1_l2_l3.json \
  --table fact_customer_current

# Time: ~3 minutes
```

### Total Deployment Time

```
Segment Discovery (4K):     12 minutes
Score All (94.7K):          15 minutes
Generate Archetypes:         5 minutes
Load to Database:            3 minutes
─────────────────────────────────────
TOTAL:                      35 minutes
```

---

## 8. Use Cases by Tier

### L1: Dominant Archetype

**Best For**:
- ✅ **Executive Dashboards**: "We have 5,847 High-Value Quilting Specialists"
- ✅ **Basic Segmentation**: Email campaigns with simple targeting
- ✅ **Reporting**: Customer distribution across dominant behaviors
- ✅ **Performance**: Fast queries, minimal storage

**Example Queries**:
```sql
-- Count customers by dominant value tier
SELECT
    archetype_l1_id,
    COUNT(*) as customers,
    AVG(lifetime_value) as avg_ltv
FROM fact_customer_current
WHERE store_id = 'linda_quilting'
GROUP BY archetype_l1_id
ORDER BY customers DESC
LIMIT 10;
```

---

### L2: Significant Archetype

**Best For**:
- ✅ **AI Personalization**: Recommendation engines, content personalization
- ✅ **Hybrid Persona Detection**: Customers transitioning between segments
- ✅ **Behavioral Drift Tracking**: Monitor when secondary memberships rise/fall
- ✅ **Email Micro-Campaigns**: Target nuanced behavioral combinations

**Example Use Case**:
```
Target: Customers who are:
  - 70%+ quilting specialists
  - 25%+ exploring sewing
  - 60%+ high-value buyers

Message: "Expand your quilting skills into sewing with our beginner kits"
Reasoning: They're quilting-dominant but showing sewing interest
```

**Example Queries**:
```sql
-- Find hybrid personas (secondary membership ≥25%)
SELECT
    customer_id,
    archetype_l2_id
FROM fact_customer_current
WHERE archetype_l2_id LIKE '%explorer_0.25%'  -- Simplified example
LIMIT 100;
```

---

### L3: Complete Thumbprint

**Best For**:
- ✅ **Research/Analysis**: Data science, behavioral pattern discovery
- ✅ **Similarity Matching**: Find customers with nearly identical profiles
- ✅ **Anomaly Detection**: Identify unusual fuzzy distributions
- ✅ **Historical Tracking**: Precise drift analysis over time

**Example Use Case**:
```
Research Question: "Do customers with 5-10% return_behavior membership
have higher churn risk than those with 0-5%?"

Analysis: Query L3 thumbprints, extract return_behavior fuzzy scores,
correlate with churn outcomes.
```

**Example Queries**:
```sql
-- Find customers with similar L3 thumbprints (cosine similarity)
-- Requires custom function or application logic
SELECT
    customer_id,
    archetype_l3_id,
    cosine_similarity(
        get_l3_vector(customer_id),
        get_l3_vector('target_customer_id')
    ) as similarity
FROM fact_customer_current
WHERE similarity > 0.95
ORDER BY similarity DESC
LIMIT 20;
```

---

## 9. Comparison to Previous System

### Previous System Issues

| Level | Archetypes | Problem | Impact |
|-------|------------|---------|--------|
| **L1** | 71 | **Mega-clusters** (87.5% in top 10) | Mass marketing for 87% of customers |
| **L2** | 868 | **Dual distribution** (100 good, 768 overfitted) | Only 54% actionable |
| **L3** | 18,447 | **Extreme fragmentation** (69% single-customer) | Overfitting, no statistical validity |

### New System Improvements

| Level | Expected Archetypes | Distribution | Impact |
|-------|---------------------|--------------|--------|
| **L1** | 800-1,500 | **Balanced** (5-8% max) | ✅ Actionable summaries |
| **L2** | 5,000-15,000 | **Well-distributed** (2-3% max) | ✅ 90%+ customers actionable |
| **L3** | 30,000-60,000 | **Granular by design** (1.5-3 avg) | ✅ Research-grade precision |

### Key Differences

**Previous System**:
- L1 suffered from **mega-cluster problem** (same issue as baseline clustering)
- L2 had **uneven distribution** (100 concentrated + 768 overfitted)
- L3 had **no purpose** (overfitted noise, not actionable)

**New System**:
- L1 is **balanced** (no mega-clusters due to hierarchical subdivision)
- L2 is **optimal for AI** (captures hybrids, statistically valid)
- L3 is **research-grade** (intentionally granular for analysis)

---

## 10. Configuration Variables

### Environment Variables

```bash
# L2 Threshold (default: 0.10)
L2_THRESHOLD=0.10

# Sample size for discovery (default: 4000)
DISCOVERY_SAMPLE_SIZE=4000

# Enable stratified sampling (default: true)
STRATIFIED_SAMPLING=true

# Hierarchical clustering parameters
ENABLE_HIERARCHICAL_CLUSTERING=true
HIERARCHICAL_MAX_INTRA_VARIANCE=2.0
HIERARCHICAL_MAX_SEGMENT_PCT=60.0
HIERARCHICAL_MIN_SEGMENT_SIZE=100
HIERARCHICAL_MAX_DEPTH=3
```

### Tuning Recommendations

**L2_THRESHOLD**:
- **0.05**: More granular (includes weak secondary memberships)
- **0.10**: Recommended (filters noise, preserves signal)
- **0.15**: More conservative (only strong secondary memberships)
- **0.20**: Minimal (approaches L1 in most cases)

**Test different thresholds**:
```bash
# Generate L2 archetypes with different thresholds
for threshold in 0.05 0.10 0.15 0.20; do
  python3 scripts/generate_archetypes.py \
    --l2-threshold $threshold \
    --output archetypes_l2_${threshold}.json
done
```

---

## 11. Validation & Monitoring

### Quality Metrics

**L1 Quality Checks**:
```sql
-- Check for mega-clusters (no archetype should have >10% of customers)
SELECT
    archetype_l1_id,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_customer_current) as pct
FROM fact_customer_current
GROUP BY archetype_l1_id
HAVING COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_customer_current) > 10
ORDER BY pct DESC;

-- Expected: 0 rows (no mega-clusters)
```

**L2 Quality Checks**:
```sql
-- Check actionability (how many customers in archetypes with 30+ members)
SELECT
    SUM(CASE WHEN customer_count >= 30 THEN customer_count ELSE 0 END) * 100.0 /
    SUM(customer_count) as actionable_pct
FROM (
    SELECT archetype_l2_id, COUNT(*) as customer_count
    FROM fact_customer_current
    GROUP BY archetype_l2_id
) subq;

-- Expected: >90%
```

**L3 Quality Checks**:
```sql
-- Check granularity distribution
SELECT
    CASE
        WHEN customer_count = 1 THEN '1 customer'
        WHEN customer_count BETWEEN 2 AND 5 THEN '2-5 customers'
        WHEN customer_count BETWEEN 6 AND 10 THEN '6-10 customers'
        WHEN customer_count > 10 THEN '10+ customers'
    END as bucket,
    COUNT(*) as archetype_count,
    SUM(customer_count) as total_customers
FROM (
    SELECT archetype_l3_id, COUNT(*) as customer_count
    FROM fact_customer_current
    GROUP BY archetype_l3_id
) subq
GROUP BY bucket
ORDER BY MIN(customer_count);

-- Expected: Most archetypes have 1-5 customers (granular by design)
```

---

## 12. Future Enhancements

### Potential Additions

**1. L2.5 (Hybrid Tier)**:
- Threshold: 0.05-0.10 (between L2 and L3)
- Use case: Weak secondary signals for advanced ML

**2. Temporal L1/L2/L3**:
- Track archetype changes over time
- Detect transitions (e.g., L2 shows rising secondary membership → predict switch)

**3. Cross-Axis Archetypes**:
- Combine top-2 segments from multiple axes
- Example: "high_value × quilting_specialist × weekend_shopper" compound archetype

**4. Archetype Similarity Index**:
- Precompute similarity scores between L3 thumbprints
- Enable fast "find similar customers" queries

---

## Appendix: Algorithm Pseudocode

### Complete L1/L2/L3 Generation

```python
def generate_all_archetypes(fuzzy_memberships, l2_threshold=0.10):
    """
    Generate L1/L2/L3 archetypes for all customers.

    Args:
        fuzzy_memberships: Dict[customer_id -> Dict[axis -> Dict[segment -> score]]]
        l2_threshold: Minimum score for L2 inclusion

    Returns:
        Dict with L1/L2/L3 archetype assignments per customer
    """
    results = {}

    for customer_id, memberships in fuzzy_memberships.items():
        # L1: Extract dominant per axis
        l1_profile = {
            axis: max(segments.items(), key=lambda x: x[1])[0]
            for axis, segments in memberships.items()
        }

        # L2: Filter >= threshold, renormalize
        l2_profile = {}
        for axis, segments in memberships.items():
            significant = {
                seg: score
                for seg, score in segments.items()
                if score >= l2_threshold
            }
            total = sum(significant.values())
            l2_profile[axis] = {
                seg: score / total
                for seg, score in significant.items()
            }

        # L3: Keep complete (no transformation)
        l3_profile = memberships

        # Generate archetype IDs
        results[customer_id] = {
            'archetype_l1_id': generate_archetype_id('L1', l1_profile),
            'archetype_l2_id': generate_archetype_id('L2', l2_profile),
            'archetype_l3_id': generate_archetype_id('L3', l3_profile),
            'l1_profile': l1_profile,
            'l2_profile': l2_profile,
            'l3_profile': l3_profile
        }

    return results
```

---

**Document Version**: 2.0
**Last Updated**: January 1, 2026
**Author**: Quimbi Platform Team
**Status**: Production-Ready
