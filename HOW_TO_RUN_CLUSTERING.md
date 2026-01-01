# How to Run ML Clustering Algorithm

This guide shows how to rerun the behavioral segmentation clustering on customer data.

## Overview

The clustering system has **3 tiers**:

1. **Tier 1**: K-means clustering per axis → 40-60 segments across 13-14 axes
2. **Tier 2**: Archetype combinations → 100-200 unique behavioral archetypes
3. **Tier 3**: Individual fuzzy membership vectors → Every customer gets fuzzy scores (0-1) for ALL segments

---

## Quick Start

### Option 1: Run Full 3-Tier Pipeline (Recommended)

This runs the complete clustering pipeline on ALL customer data:

```bash
cd /Users/scottallen/quimbi-platform

# Run full pipeline (5-15 minutes)
python3 run_full_clustering.py
```

**What it does:**
- Loads ALL customers from `combined_sales` table
- Runs Tier 1: K-means clustering on 13 axes (2-8 clusters per axis)
- Runs Tier 2: Creates archetypes from segment combinations (filters to ≥10 customers)
- Runs Tier 3: Generates fuzzy membership vectors for each customer
- Saves results to `/tmp/clustering_results.json`

**Output:**
```
TIER 1 COMPLETE
  Axes clustered: 13
  Total segments: 52
  Avg segments/axis: 4.0

TIER 2 COMPLETE
  Unique archetypes: 180
  Avg customers/archetype: 152.3

TIER 3 COMPLETE
  Customer vectors generated: 27,415
```

---

### Option 2: Run Initial Clustering Only (Tier 1)

This runs just segment discovery without archetypes:

```bash
cd /Users/scottallen/quimbi-platform

# Run all 13 axes
python3 scripts/run_initial_clustering.py --store-id linda_quilting

# Run specific axes only
python3 scripts/run_initial_clustering.py \
  --store-id linda_quilting \
  --axes purchase_frequency,purchase_value,loyalty_trajectory

# Dry run (don't save to database)
python3 scripts/run_initial_clustering.py \
  --store-id linda_quilting \
  --dry-run

# Disable AI naming (faster, uses fallback names)
python3 scripts/run_initial_clustering.py \
  --store-id linda_quilting \
  --no-ai-naming
```

**Options:**
- `--store-id`: Store identifier (default: `linda_quilting`)
- `--axes`: Comma-separated list of axes (default: all 13)
- `--min-k`: Minimum clusters per axis (default: 2)
- `--max-k`: Maximum clusters per axis (default: 6)
- `--use-ai-naming`: Use Claude API for segment naming (default: True)
- `--no-ai-naming`: Disable AI naming, use fallback names
- `--dry-run`: Run clustering but don't save to database

---

## Core Clustering Files

### Main Engine Files

| File | Purpose |
|------|---------|
| [`backend/segmentation/multi_axis_clustering_engine.py`](backend/segmentation/multi_axis_clustering_engine.py) | **Main clustering engine** - Tier 1 & 3 implementation |
| [`backend/segmentation/fuzzy_cmeans_clustering.py`](backend/segmentation/fuzzy_cmeans_clustering.py) | **Fuzzy C-Means algorithm** - Custom implementation (m=2.0 fuzziness) |
| [`backend/segmentation/hierarchical_clustering.py`](backend/segmentation/hierarchical_clustering.py) | **Hierarchical clustering** - For creating cluster hierarchies |
| [`backend/segmentation/archetype_analyzer.py`](backend/segmentation/archetype_analyzer.py) | **Tier 2 archetype creation** - Combines segments into archetypes |
| [`backend/segmentation/ecommerce_feature_extraction.py`](backend/segmentation/ecommerce_feature_extraction.py) | **Feature engineering** - Extracts behavioral features from orders |

### Runner Scripts

| Script | Purpose |
|--------|---------|
| [`run_full_clustering.py`](run_full_clustering.py) | **Full 3-tier pipeline** - Runs Tier 1 + 2 + 3 on all customers |
| [`scripts/run_initial_clustering.py`](scripts/run_initial_clustering.py) | **Tier 1 only** - Discovers segments per axis with AI naming |
| [`scripts/load_clustering_results.py`](scripts/load_clustering_results.py) | Load saved clustering results into database |
| [`scripts/efficient_segmentation.py`](scripts/efficient_segmentation.py) | Efficient batch processing of customer profiles |

---

## The 13 Behavioral Axes

Each axis is clustered independently using K-means (2-8 clusters per axis):

### Marketing Axes (1-8)

1. **purchase_frequency** - How often they buy
   - Features: `orders_per_month`, `avg_gap`, `consistency`
   - Segments: `power_buyer`, `regular`, `occasional`, `first_time`

2. **purchase_value** - How much they spend
   - Features: `lifetime_value`, `AOV`, `value_trend`
   - Segments: `premium`, `mid_tier`, `value`, `budget`

3. **price_sensitivity** - Discount dependency
   - Features: `discount_rate`, `full_price_ratio`
   - Segments: `deal_hunter`, `strategic`, `quality_focused`, `premium_buyer`

4. **shopping_maturity** - Lifecycle stage
   - Features: `tenure`, `maturity_score`, `acceleration`
   - Segments: `new`, `beginner`, `established`, `experienced`, `expert`

5. **product_diversity** - Product variety seeking
   - Features: `unique_categories`, `diversity`, `exploration_breadth`
   - Segments: `single_item`, `single_category`, `multi_category`, `explorer`

6. **brand_loyalty** - Loyalty patterns
   - Features: `repeat_rate`, `loyalty_index`
   - Segments: `exploring`, `switcher`, `moderately_loyal`, `highly_loyal`, `exclusive`

7. **seasonal_behavior** - When they buy
   - Features: `weekend_ratio`, `business_hours`, `timing`
   - Segments: `holiday_only`, `seasonal_spikes`, `year_round`, `non_seasonal`

8. **return_behavior** - Refund patterns
   - Features: `refund_rate`, `items_returned_pct`
   - Segments: `no_history`, `rarely_returns`, `occasional_returner`, `frequent_returner`

### Support Axes (9-13)

9. **cart_behavior** - Cart building patterns
   - Features: `items_per_order`, `basket_size`
   - Segments: `decisive`, `thoughtful`, `basket_builder`, `bulk_buyer`

10. **channel_preference** - Device/platform
    - Features: `primary_channel`, `preferred_time`
    - Segments: `mobile_app`, `mobile_web`, `desktop`, `mixed`

11. **weekend_affinity** - Shopping timing
    - Features: `weekend_ratio`
    - Segments: `weekday_shopper`, `weekend_shopper`, `no_preference`

12. **promotional_responsiveness** - Promotion engagement
    - Features: `discount_hunt_score`, `brand_driven`
    - Segments: `coupon_seeker`, `sale_driven`, `brand_driven`, `promotion_resistant`

13. **cart_abandonment** - Cart abandonment patterns
    - Features: `abandonment_rate`
    - Segments: `low_abandoner`, `moderate_abandoner`, `high_abandoner`

---

## Fuzzy C-Means Algorithm

### Implementation Details

**Location**: [`backend/segmentation/fuzzy_cmeans_clustering.py`](backend/segmentation/fuzzy_cmeans_clustering.py)

**Key Parameters:**
- `m = 2.0` - Fuzziness parameter (controls overlap between clusters)
- `max_iter = 150` - Maximum iterations
- `error = 1e-5` - Convergence threshold

**Algorithm:**
```python
# 1. Initialize cluster centers randomly
centers = random_sample(n_clusters, n_features)

# 2. Iteratively update memberships and centers
for iteration in range(max_iter):
    # Calculate fuzzy memberships
    distances = euclidean_distance(X, centers)
    memberships = 1 / sum((dist_i / dist_j) ^ (2/(m-1)))

    # Update cluster centers
    centers = sum(membership^m * data_point) / sum(membership^m)

    # Check convergence
    if change < error:
        break

# 3. Return memberships matrix (n_customers x n_clusters)
```

**Key Property**: Every customer gets a membership score (0-1) for EVERY cluster, summing to 1.0

**Example:**
```python
# Customer fuzzy memberships for "purchase_frequency" axis
{
    'power_buyer': 0.786,      # Strong membership
    'regular': 0.175,          # Weak membership
    'occasional': 0.039        # Very weak membership
}
# Sum = 1.000 ✓
```

---

## Customer Thumbprint (Top-2 Fuzzy Memberships)

Each customer's "thumbprint" consists of their **top-2 fuzzy memberships per axis**:

```python
customer_thumbprint = {
    'price_sensitivity': [
        ('deal_hunter', 0.82),
        ('strategic', 0.71)
    ],
    'shopping_maturity': [
        ('established', 0.87),
        ('experienced', 0.62)
    ],
    'purchase_value': [
        ('mid_tier', 0.79),
        ('value', 0.68)
    ],
    # ... 13 axes total
}
```

This creates **868 unique behavioral archetypes** based on dominant segment combinations.

---

## Example Clustering Output

### Tier 1: Segments Discovered

```
PURCHASE_FREQUENCY (3 segments):
  - power_buyer
    Population: 2,841 customers (10.4%)
    Customers who purchase 3+ times per month with consistent patterns

  - regular
    Population: 18,492 customers (67.5%)
    Moderate purchase frequency with 30-60 day gaps

  - first_time
    Population: 6,082 customers (22.2%)
    Single purchase or very infrequent buyers

LOYALTY_TRAJECTORY (4 segments):
  - accelerating
    Population: 3,205 customers (11.7%)
    Increasing frequency and value, low churn risk

  - stable
    Population: 15,384 customers (56.1%)
    Consistent ordering pattern

  - declining
    Population: 4,116 customers (15.0%)
    Decreasing engagement, HIGH CHURN RISK

  - seasonal
    Population: 4,710 customers (17.2%)
    Predictable seasonal purchasing
```

### Tier 2: Archetypes Created

```
Top 10 archetypes by population:

1. 4,215 customers (15.4%)
   Signature: (regular, mid_tier, established, deal_hunter, ...)

2. 3,892 customers (14.2%)
   Signature: (power_buyer, premium, expert, quality_focused, ...)

3. 2,764 customers (10.1%)
   Signature: (first_time, budget, new, deal_hunter, ...)

4. 2,103 customers (7.7%)
   Signature: (occasional, value, beginner, strategic, ...)

... 176 more archetypes
```

### Tier 3: Customer Fuzzy Vectors

```
Customer ID: 7845123456

Archetype: (power_buyer, premium, expert, quality_focused, highly_loyal, ...)

Fuzzy Memberships:
  purchase_frequency:
    - power_buyer: 0.786
    - regular: 0.175
    - first_time: 0.039

  purchase_value:
    - premium: 0.912
    - mid_tier: 0.073
    - value: 0.015

  price_sensitivity:
    - quality_focused: 0.891
    - premium_buyer: 0.087
    - deal_hunter: 0.022

  ... 13 axes total
```

---

## Environment Setup

### Required Environment Variables

```bash
# PostgreSQL database connection
export DATABASE_URL="postgresql://user:password@host:port/database"

# Optional: Claude API for AI segment naming (Tier 1)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Database Requirements

**Input Tables:**
- `combined_sales` - Customer orders with full transaction history
- `order_items` - Line items with product, category, price, refunds

**Output Tables:**
- `platform.customer_profiles` - Customer behavioral profiles (JSONB columns)
- `platform.dim_segment_master` - Segment definitions and cluster centers
- `platform.archetype_definitions` - Tier 2 archetype signatures

---

## Performance Benchmarks

### Full 3-Tier Pipeline (27,415 customers)

| Phase | Time | Details |
|-------|------|---------|
| **Tier 1: Segment Discovery** | 10-15 min | K-means on 13 axes, AI naming |
| **Tier 2: Archetype Creation** | 3-5 min | Profile all customers, create archetypes |
| **Tier 3: Fuzzy Vectors** | 1-2 min | Generate membership vectors |
| **Total** | **15-20 min** | End-to-end pipeline |

### Single Customer Profile Calculation

| Operation | Time |
|-----------|------|
| Calculate profile (with cache) | ~100-200ms |
| Calculate profile (no cache) | ~500ms-1s |
| Batch (1000 customers) | ~30-60s |

---

## Programmatic Usage

### Calculate Customer Profile

```python
import asyncio
from backend.segmentation import MultiAxisClusteringEngine

async def get_customer_intelligence(customer_id: str):
    # Initialize engine
    engine = MultiAxisClusteringEngine(
        min_k=2,
        max_k=6,
        use_ai_naming=False  # Use existing segments
    )

    # Calculate customer profile
    # This loads discovered segments from database
    profile = await engine.calculate_customer_profile(
        customer_id=customer_id,
        store_id='linda_quilting',
        store_profile=True  # Save to database
    )

    # Access fuzzy memberships
    print("Fuzzy Memberships:")
    for axis, memberships in profile.fuzzy_memberships.items():
        print(f"\n{axis}:")
        for segment, score in sorted(memberships.items(), key=lambda x: -x[1])[:2]:
            print(f"  {segment}: {score:.3f}")

    # Access dominant segments
    print("\nDominant Segments:")
    for axis, segment in profile.dominant_segments.items():
        strength = profile.membership_strength[axis]
        print(f"  {axis}: {segment} ({strength})")

    # Access archetype
    print(f"\nArchetype: {profile.archetype_id}")
    print(f"Level: {profile.archetype_level}")

    return profile

# Run
customer = asyncio.run(get_customer_intelligence("8234567890"))
```

### Run Clustering from Code

```python
import asyncio
from backend.segmentation import MultiAxisClusteringEngine

async def run_clustering():
    # Initialize engine
    engine = MultiAxisClusteringEngine(
        min_k=2,
        max_k=6,
        use_ai_naming=True,
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
    )

    # Discover segments (Tier 1)
    segments = await engine.discover_multi_axis_segments(
        store_id='linda_quilting',
        axes_to_cluster=None  # All 13 axes
    )

    print(f"Discovered {sum(len(s) for s in segments.values())} segments")

    # Calculate profiles for all customers (Tier 3)
    customer_ids = ["123", "456", "789"]  # Your customer IDs

    for customer_id in customer_ids:
        profile = await engine.calculate_customer_profile(
            customer_id=customer_id,
            store_id='linda_quilting',
            segments_dict=segments  # Pass discovered segments
        )
        print(f"Customer {customer_id}: {profile.archetype_id}")

asyncio.run(run_clustering())
```

---

## Troubleshooting

### Issue: "Insufficient population"

**Cause**: Less than 100 customers in database

**Solution**:
- Check `combined_sales` table has data
- Adjust `--min-population` parameter
- Verify `customer_id` is not NULL

### Issue: "Poor clustering quality"

**Cause**: Silhouette score < 0.25

**Solution**:
- Check for NaN values in features
- Reduce `--max-k` to force fewer clusters
- Verify order data has sufficient history (90+ days recommended)

### Issue: "AI naming failed"

**Cause**: ANTHROPIC_API_KEY not set or invalid

**Solution**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Or use --no-ai-naming flag
python3 scripts/run_initial_clustering.py --no-ai-naming
```

### Issue: "No segments discovered"

**Cause**: Database connection or data issues

**Solution**:
```bash
# Verify database connection
export DATABASE_URL="postgresql://..."

# Check combined_sales table
psql $DATABASE_URL -c "SELECT COUNT(*) FROM combined_sales WHERE customer_id IS NOT NULL;"

# Run dry run to see errors
python3 scripts/run_initial_clustering.py --dry-run
```

---

## Output Files

### Clustering Results

**Location**: `/tmp/clustering_results.json`

**Format**:
```json
{
  "timestamp": "2024-12-30T15:23:45",
  "tier1": {
    "axes": 13,
    "total_segments": 52,
    "segments_by_axis": {
      "purchase_frequency": [
        {
          "name": "power_buyer",
          "population": 2841,
          "percentage": 0.104,
          "interpretation": "Customers who purchase 3+ times per month"
        }
      ]
    }
  },
  "tier2": {
    "total_archetypes": 180,
    "top_archetypes": [...]
  },
  "tier3": {
    "total_customers": 27415,
    "sample_vectors": {...}
  }
}
```

---

## Next Steps

After running clustering:

1. **Load results to database**:
   ```bash
   python3 scripts/load_clustering_results.py
   ```

2. **Verify customer profiles**:
   ```bash
   # Check customer_profiles table
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM platform.customer_profiles WHERE segment_memberships IS NOT NULL;"
   ```

3. **Test API endpoints**:
   ```bash
   # Get customer intelligence
   curl http://localhost:8000/api/mcp/customer/8234567890
   ```

4. **Integrate with Gorgias**:
   - Customer intelligence automatically flows to Gorgias webhooks
   - See [GORGIAS_INTEGRATION_TEST_SCENARIOS.md](../q.ai-customer-support/GORGIAS_INTEGRATION_TEST_SCENARIOS.md)

---

## References

- [backend/segmentation/README.md](backend/segmentation/README.md) - Detailed architecture documentation
- [BEHAVIORAL_MATH.md](reference/BEHAVIORAL_MATH.md) - Complete mathematical documentation
- [ML_ARCHITECTURE_VERIFICATION.md](ML_ARCHITECTURE_VERIFICATION.md) - ML implementation audit
- [GORGIAS_INTEGRATION_TEST_SCENARIOS.md](../q.ai-customer-support/GORGIAS_INTEGRATION_TEST_SCENARIOS.md) - Integration testing guide

---

**Last Updated**: 2024-12-30
**Status**: ✅ Fully implemented and production-ready
