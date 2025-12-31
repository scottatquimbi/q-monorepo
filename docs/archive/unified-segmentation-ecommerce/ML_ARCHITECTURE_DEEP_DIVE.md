# ML Architecture Deep Dive - 3-Tier Archetype System
**Date:** 2025-11-06
**System:** Multi-Axis Behavioral Segmentation with Temporal Drift Tracking

---

## Overview: Three Levels of Archetype Granularity

This is a **hierarchical multi-resolution segmentation system** that provides three levels of customer understanding:

```
Level 1: Dominant Archetype (Coarse)
         ↓
Level 2: Multi-Axis Fuzzy Archetype (Medium) ← 868 archetypes
         ↓
Level 3: Individual Behavioral Fingerprint (Fine) ← ~1:1 customer mapping
```

Each level serves different use cases with different precision vs scalability tradeoffs.

---

## Level 1: Dominant Archetype (Simple Classification)

### Purpose
**Quick, human-readable customer classification for support agents**

### How It Works
```python
customer = {
    'dominant_archetype': 'high_value_frequent_buyer',  # Single label
    'archetype_id': 'arch_42',
    'interpretation': 'Weekend Warrior explorer with high intensity'
}
```

### Construction
- For each axis, take the segment with **highest membership score**
- Combine dominant segments across all axes
- Map to predefined archetype labels

**Example:**
```python
{
    'purchase_frequency': 'frequent_buyer',      # 0.85 membership
    'purchase_value': 'high_value',              # 0.72 membership
    'category_exploration': 'explorer',          # 0.68 membership
    'price_sensitivity': 'discount_seeker',      # 0.55 membership
    'purchase_cadence': 'weekend_warrior',       # 0.78 membership
    'customer_maturity': 'established',          # 0.63 membership
    'repurchase_behavior': 'repeat_buyer',       # 0.81 membership
    'return_behavior': 'low_returner'            # 0.91 membership
}

# Dominant Archetype = "high_value_weekend_repeat_buyer"
# Archetype ID = arch_42 (one of 868)
```

### Use Cases
- **Gorgias AI responses:** "I see you're a valued repeat customer..."
- **Support agent dashboard:** Shows archetype badge
- **Marketing automation:** Segment-based email campaigns
- **Reporting:** "40% of customers are casual_browsers"

### Limitations
- ❌ Loses nuance (customer might be 51% frequent vs 49% sporadic)
- ❌ Doesn't capture multi-modal behavior
- ❌ Static snapshot (no trend)

---

## Level 2: Multi-Axis Fuzzy Archetype (868 Combinations)

### Purpose
**Nuanced understanding of customer behavior across all dimensions**

This is where the **868 archetypes** come from.

### How It Works

**Each customer has fuzzy membership in ALL segments on ALL axes:**

```python
customer_profile = {
    'customer_id': 'cust_123',

    # Axis 1: Purchase Frequency
    'frequency_memberships': {
        'frequent_buyer': 0.65,      # Primary
        'occasional_buyer': 0.25,    # Secondary
        'sporadic_buyer': 0.10       # Tertiary
    },

    # Axis 2: Purchase Value
    'value_memberships': {
        'high_value': 0.58,
        'medium_value': 0.32,
        'low_value': 0.10
    },

    # Axis 3: Category Exploration
    'category_memberships': {
        'explorer': 0.71,
        'focused': 0.22,
        'sampler': 0.07
    },

    # ... 5 more axes

    # Archetype is combination of dominant segments
    'archetype_id': 'arch_442',  # One of 868
    'archetype_vector': [0.65, 0.58, 0.71, 0.55, 0.78, 0.63, 0.81, 0.91]
}
```

### 868 Archetypes Calculation

**Combinatorial Explosion (Pruned):**

If each axis has ~3-6 segments:
- 8 axes × 4 average segments = 4^8 = **65,536 possible combinations**
- But most are empty (no customers match that exact combination)
- Prune to only occupied combinations → **868 archetypes**

**Example Archetype (arch_442):**
```
Frequency: frequent_buyer (dominant)
Value: high_value (dominant)
Category: explorer (dominant)
Price: discount_seeker (dominant)
Cadence: weekend_warrior (dominant)
Maturity: established (dominant)
Repurchase: repeat_buyer (dominant)
Returns: low_returner (dominant)

→ "High-value weekend explorer who repeats purchases"
```

### Use Cases
- **Personalized recommendations:** "Customers like you also bought..."
- **Churn prediction:** Archetype-specific baselines (arch_442 has 15% churn rate)
- **Targeted interventions:** "Explorer" gets product discovery emails
- **Cohort analysis:** "Arch_442 customers have 2.3X higher LTV"

### Database Schema

```sql
CREATE TABLE customer_profiles (
    customer_id BIGINT PRIMARY KEY,

    -- Level 1: Dominant archetype
    archetype_id VARCHAR(20),  -- One of 868

    -- Level 2: Fuzzy memberships (JSONB for flexibility)
    frequency_memberships JSONB,    -- {"frequent": 0.65, "occasional": 0.25, ...}
    value_memberships JSONB,
    category_memberships JSONB,
    price_memberships JSONB,
    cadence_memberships JSONB,
    maturity_memberships JSONB,
    repurchase_memberships JSONB,
    return_memberships JSONB,

    -- Metadata
    last_segmentation_run TIMESTAMP,
    segmentation_confidence FLOAT,  -- Average membership strength

    -- Standard fields
    lifetime_value NUMERIC,
    total_orders INT,
    churn_risk_score FLOAT
);
```

### Strengths
- ✅ Nuanced (captures "in-between" customers)
- ✅ 868 archetypes = rich segmentation
- ✅ Fuzzy membership = probabilistic (not binary)
- ✅ Can track segment drift over time

---

## Level 3: Individual Behavioral Fingerprint (~1:1 Mapping)

### Purpose
**Customer-specific behavioral signature for hyper-personalization**

At this level, each customer's exact position in **8-dimensional behavior space** is tracked.

### How It Works

**Instead of assigning to archetypes, track DISTANCE from each segment center:**

```python
behavioral_fingerprint = {
    'customer_id': 'cust_123',

    # 8D position in normalized feature space
    'feature_vector': [
        0.73,  # purchase_frequency (standardized)
        0.82,  # purchase_value
        0.65,  # category_diversity
        -0.45, # price_sensitivity (negative = less sensitive)
        0.91,  # purchase_cadence_regularity
        0.58,  # customer_maturity
        0.77,  # repurchase_propensity
        -0.12  # return_rate
    ],

    # Distances to ALL segment centers (for all axes)
    'segment_distances': {
        'frequency_frequent_buyer': 0.23,    # Close
        'frequency_occasional_buyer': 1.47,  # Far
        'frequency_sporadic_buyer': 2.89,    # Very far

        'value_high_value': 0.31,
        'value_medium_value': 0.98,
        'value_low_value': 2.14,

        # ... all 868 segments
    },

    # Nearest neighbors (most similar customers)
    'nearest_neighbors': [
        {'customer_id': 'cust_456', 'distance': 0.12},
        {'customer_id': 'cust_789', 'distance': 0.18},
        {'customer_id': 'cust_321', 'distance': 0.24}
    ]
}
```

### Use Cases
- **Hyper-personalized recommendations:** Find 10 most similar customers, recommend their purchases
- **Outlier detection:** Distance > 3.0 from all segments = unusual behavior (fraud?)
- **A/B test targeting:** "Target customers within 0.5 distance of arch_442"
- **Lookalike modeling:** "Find more customers like cust_123"

### Strengths
- ✅ Maximum granularity (captures unique customer quirks)
- ✅ Enables k-NN recommendations
- ✅ Can detect behavioral anomalies
- ✅ Foundation for temporal drift tracking

### Limitations
- ❌ Computationally expensive (store 868 distances per customer)
- ❌ Harder to interpret (humans can't visualize 8D space)
- ❌ Requires more storage (JSONB with 868 keys)

---

## Temporal Drift Tracking: Behavioral Trend Analysis

### Purpose
**Track how customers' behavior changes over time to predict churn and identify engagement trends**

### How It Works

**Store snapshots of segment distances at multiple time intervals:**

```python
customer_drift_history = {
    'customer_id': 'cust_123',

    'drift_snapshots': [
        {
            'snapshot_date': '2025-11-06',
            'interval': '1_week',
            'distances': {
                'frequency_frequent_buyer': 0.23,
                'value_high_value': 0.31,
                # ... all segments
            },
            'archetype_id': 'arch_442',
            'churn_risk': 0.15
        },
        {
            'snapshot_date': '2025-10-30',  # 1 week ago
            'interval': '1_week',
            'distances': {
                'frequency_frequent_buyer': 0.19,  # Was closer (trending away!)
                'value_high_value': 0.28,          # Was closer (spending less!)
                # ...
            },
            'archetype_id': 'arch_442',
            'churn_risk': 0.12
        },
        {
            'snapshot_date': '2025-10-23',  # 2 weeks ago
            'interval': '2_weeks',
            # ...
        },
        {
            'snapshot_date': '2025-10-09',  # 4 weeks ago
            'interval': '4_weeks',
            # ...
        },
        {
            'snapshot_date': '2025-05-06',  # 6 months ago
            'interval': '6_months',
            # ...
        }
    ]
}
```

### Drift Metrics

**1. Segment Distance Trend**
```python
def calculate_drift(customer_id, segment_name, interval):
    """
    Calculate how customer is drifting relative to a segment.

    Positive drift = moving away (BAD for desired segments)
    Negative drift = moving closer (GOOD for desired segments)
    """
    snapshots = get_snapshots(customer_id, interval)

    distances = [s['distances'][segment_name] for s in snapshots]

    # Linear regression slope
    slope = np.polyfit(range(len(distances)), distances, 1)[0]

    return {
        'segment': segment_name,
        'current_distance': distances[-1],
        'distance_change': distances[-1] - distances[0],
        'trend': 'drifting_away' if slope > 0.05 else 'drifting_closer' if slope < -0.05 else 'stable',
        'slope': slope,
        'churn_risk_delta': calculate_churn_delta(distances)
    }

# Example output
{
    'segment': 'frequency_frequent_buyer',
    'current_distance': 0.23,
    'distance_change': +0.04,  # Was 0.19, now 0.23
    'trend': 'drifting_away',  # BAD SIGN
    'slope': 0.006,            # Small but positive
    'churn_risk_delta': +0.03  # Churn risk increased 3%
}
```

**2. Archetype Migration**
```python
def detect_archetype_shift(customer_id):
    """
    Detect if customer has moved between archetypes.

    This is a MAJOR behavioral change signal.
    """
    snapshots = get_snapshots(customer_id, '1_week')

    archetype_changes = []
    for i in range(1, len(snapshots)):
        if snapshots[i]['archetype_id'] != snapshots[i-1]['archetype_id']:
            archetype_changes.append({
                'date': snapshots[i]['snapshot_date'],
                'from_archetype': snapshots[i-1]['archetype_id'],
                'to_archetype': snapshots[i]['archetype_id'],
                'interpretation': interpret_shift(
                    snapshots[i-1]['archetype_id'],
                    snapshots[i]['archetype_id']
                )
            })

    return archetype_changes

# Example output
[
    {
        'date': '2025-10-23',
        'from_archetype': 'arch_442',  # High-value frequent buyer
        'to_archetype': 'arch_523',    # High-value occasional buyer
        'interpretation': 'CHURN WARNING: Shifted from frequent to occasional buyer'
    }
]
```

**3. Velocity of Drift**
```python
def calculate_drift_velocity(customer_id):
    """
    How fast is customer's behavior changing?

    High velocity = unstable, unpredictable
    Low velocity = stable, predictable
    """
    snapshots = get_snapshots(customer_id, '1_week')

    # Calculate distance moved in 8D space between each snapshot
    velocities = []
    for i in range(1, len(snapshots)):
        vec_current = snapshots[i]['feature_vector']
        vec_previous = snapshots[i-1]['feature_vector']

        # Euclidean distance between feature vectors
        distance_moved = np.linalg.norm(
            np.array(vec_current) - np.array(vec_previous)
        )

        velocities.append(distance_moved)

    return {
        'avg_weekly_drift': np.mean(velocities),
        'max_weekly_drift': np.max(velocities),
        'drift_acceleration': velocities[-1] - velocities[0],  # Speeding up or slowing down?
        'stability_score': 1.0 / (1.0 + np.std(velocities))   # 0-1, higher = more stable
    }

# Example output
{
    'avg_weekly_drift': 0.08,        # Small movements
    'max_weekly_drift': 0.23,        # One big jump
    'drift_acceleration': +0.05,     # Accelerating (BAD)
    'stability_score': 0.72          # Fairly stable
}
```

### Snapshot Storage Schema

```sql
CREATE TABLE customer_drift_snapshots (
    snapshot_id UUID PRIMARY KEY,
    customer_id BIGINT,
    snapshot_date DATE,
    interval VARCHAR(10),  -- '1_week', '2_weeks', '4_weeks', '6_months'

    -- Current archetype
    archetype_id VARCHAR(20),

    -- Feature vector (8D position in behavior space)
    feature_vector FLOAT[8],

    -- Distances to all segment centers (868 segments × 8 axes)
    segment_distances JSONB,

    -- Fuzzy memberships snapshot
    frequency_memberships JSONB,
    value_memberships JSONB,
    category_memberships JSONB,
    price_memberships JSONB,
    cadence_memberships JSONB,
    maturity_memberships JSONB,
    repurchase_memberships JSONB,
    return_memberships JSONB,

    -- Churn risk at this snapshot
    churn_risk_score FLOAT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    -- Indexes for time-series queries
    INDEX idx_customer_interval (customer_id, interval, snapshot_date DESC)
);
```

### Retention Policy

**How long to keep snapshots:**
- **1-week intervals:** Keep last 12 (3 months of weekly data)
- **2-week intervals:** Keep last 12 (6 months of bi-weekly data)
- **4-week intervals:** Keep last 12 (1 year of monthly data)
- **6-month intervals:** Keep all (lifetime history)

**Storage optimization:**
- Compress old snapshots (JSONB → gzipped)
- Archive to S3 after 2 years
- Delete after 5 years (GDPR compliance)

---

## Use Cases by Level

### Level 1: Dominant Archetype

**Support Agent Dashboard:**
```
Customer: Jane Doe
Archetype: High-Value Weekend Repeat Buyer
LTV: $2,450
Churn Risk: LOW (15%)

🎯 Recommended Action: Thank for loyalty, offer early access to new products
```

**Marketing Automation:**
```python
# Send weekend-only email campaigns to weekend warriors
customers = get_customers_with_archetype('weekend_warrior')
send_campaign(customers, 'saturday_morning_deals')
```

### Level 2: Multi-Axis Fuzzy Archetype (868)

**Churn Prediction Model:**
```python
# Use fuzzy memberships as features
features = {
    'frequency_frequent_membership': 0.65,
    'frequency_occasional_membership': 0.25,
    'value_high_membership': 0.58,
    # ... 24 total fuzzy membership features (8 axes × 3 top segments)

    'archetype_baseline_churn': archetypes['arch_442'].baseline_churn_rate,
    'days_since_last_purchase': 45,
    'order_value_trend': -0.15  # Declining
}

churn_prob = churn_model.predict_proba([features])[0][1]
# Output: 0.68 (68% churn risk)
```

**Lookalike Audiences:**
```python
# Find customers similar to high-LTV archetype
target_archetype = 'arch_442'
similar_customers = find_customers_with_archetype(target_archetype, membership_threshold=0.6)

# Upsell campaign to similar customers
send_campaign(similar_customers, 'premium_product_launch')
```

### Level 3: Individual Fingerprint + Drift Tracking

**Proactive Churn Intervention:**
```python
# Detect customers drifting away from "frequent_buyer"
at_risk = []

for customer in get_all_customers():
    drift = calculate_drift(customer.id, 'frequency_frequent_buyer', '1_week')

    if drift['trend'] == 'drifting_away' and drift['slope'] > 0.1:
        # Rapid drift away from frequent buyer segment
        at_risk.append({
            'customer_id': customer.id,
            'current_distance': drift['current_distance'],
            'drift_velocity': drift['slope'],
            'recommended_action': 'Send win-back offer',
            'discount_amount': '15%'  # Higher for faster drift
        })

# Trigger automated intervention
for customer in at_risk:
    send_retention_offer(customer)
```

**Hyper-Personalized Recommendations:**
```python
# Find 10 most similar customers based on 8D fingerprint
similar = find_nearest_neighbors(
    customer_id='cust_123',
    k=10,
    distance_threshold=0.5  # Within 0.5 in 8D space
)

# Recommend products they bought
recommendations = []
for neighbor in similar:
    products = get_recent_purchases(neighbor['customer_id'], days=30)
    recommendations.extend(products)

# Filter to products customer hasn't bought
recommendations = [p for p in recommendations if not customer_owns(p)]

# Show top 5 by frequency among neighbors
top_products = Counter(recommendations).most_common(5)
```

---

## Implementation Roadmap

### Phase 1: Current State (✅ Completed)
- Multi-axis clustering engine (7-8 axes)
- Fuzzy membership calculation
- 868 archetypes discovered
- Basic churn risk scoring

### Phase 2: Enhanced Archetype System (2 months)

**Month 1: 3-Tier Hierarchy**
```python
# Implement all three levels
backend/ml/
├── archetypes/
│   ├── level1_dominant.py           # Simple classification
│   ├── level2_fuzzy.py               # 868 archetype system
│   └── level3_fingerprint.py         # Individual signatures

# Database schema migration
alembic/versions/
└── 2025_11_add_fuzzy_memberships.py  # Add JSONB columns
```

**Month 2: Temporal Drift Tracking**
```python
# Implement drift detection
backend/ml/
├── drift/
│   ├── snapshot_manager.py          # Create/manage snapshots
│   ├── drift_calculator.py          # Calculate drift metrics
│   ├── archetype_migration.py       # Detect archetype shifts
│   └── churn_signals.py             # Early warning system

# Scheduled jobs
jobs/
├── weekly_snapshot.py               # Run every Monday
├── monthly_drift_report.py          # Email to ops team
└── churn_alert_scanner.py           # Check for rapid drift (daily)
```

### Phase 3: Productization (1 month)

**Dashboard & Alerts:**
```python
# Support agent view
GET /api/customer/{id}/archetype
{
    "level1": "high_value_weekend_repeat_buyer",
    "level2": {
        "archetype_id": "arch_442",
        "fuzzy_memberships": { ... },
        "interpretation": "Explorer who buys on weekends"
    },
    "level3": {
        "drift_alert": "CHURN WARNING: Drifting away from frequent_buyer",
        "recommended_action": "Send 15% retention offer"
    }
}

# Ops dashboard
GET /api/drift/alerts
[
    {
        "customer_id": "cust_123",
        "alert_type": "archetype_migration",
        "from": "arch_442",
        "to": "arch_523",
        "severity": "high",
        "recommended_action": "Retention campaign"
    },
    # ...
]
```

---

## Technical Specifications

### Computation Frequency

**Level 1 & 2 (Archetype Assignment):**
- **New customers:** On first purchase
- **Existing customers:** Weekly batch job (every Monday 2am)
- **On-demand:** When support agent opens customer profile

**Level 3 (Fingerprint):**
- **Calculation:** Same as Level 1/2
- **Storage:** Every recalculation creates new snapshot

**Drift Snapshots:**
- **1-week:** Every Monday
- **2-weeks:** Every other Monday
- **4-weeks:** First Monday of month
- **6-months:** January 1st, July 1st

### Performance Considerations

**Storage per customer:**
```
Level 1: 100 bytes   (archetype_id, interpretation)
Level 2: 2 KB        (8 JSONB columns with fuzzy memberships)
Level 3: 20 KB       (868 segment distances)
Drift (12 snapshots): 240 KB per customer

Total: ~262 KB per customer
For 100K customers: ~26 GB storage
```

**Computation time:**
```
Level 1: 10ms per customer   (simple max selection)
Level 2: 50ms per customer   (fuzzy membership calculation)
Level 3: 200ms per customer  (868 distance calculations)

For 100K customers (weekly batch):
- Level 1+2: ~1.5 hours
- Level 3: ~6 hours
- Total: ~7.5 hours (acceptable for weekly job)
```

### Optimization Strategies

**1. Incremental Updates**
```python
# Only recalculate for active customers (purchased in last 90 days)
active_customers = get_customers_with_purchase_since(days=90)

# Archive inactive customers (snapshots only)
inactive = get_customers_without_purchase_since(days=180)
for customer in inactive:
    archive_snapshots(customer.id)
    skip_weekly_calculation(customer.id)
```

**2. Segment Distance Caching**
```python
# Cache segment centers (only change when clusters re-discovered)
@cache(ttl='30 days')
def get_segment_centers():
    return db.query(Segment).all()

# Reuse for all customers
centers = get_segment_centers()
for customer in customers:
    distances = calculate_distances(customer.features, centers)
```

**3. Parallel Processing**
```python
# Use multiprocessing for batch jobs
from multiprocessing import Pool

def calculate_customer_fingerprint(customer_id):
    # ... calculation logic

with Pool(processes=8) as pool:
    fingerprints = pool.map(calculate_customer_fingerprint, customer_ids)
```

---

## Competitive Advantage

### vs Gorgias AI
- **Gorgias:** Tags (binary: "VIP" or not)
- **You:** 868 archetypes + fuzzy membership + drift tracking

### vs Segment (CDP)
- **Segment:** Static traits ("High LTV", "At Risk")
- **You:** Dynamic behavior (trending toward or away from segments)

### vs Klaviyo
- **Klaviyo:** RFM + predicted LTV
- **You:** 8-dimensional behavioral understanding

### Defensibility

**Data Moat:**
- 868 archetypes improve with more customers (network effects)
- Drift tracking requires 6+ months of data (time moat)
- Individual fingerprints = unique to your platform

**Complexity Moat:**
- Multi-axis fuzzy clustering is PhD-level work
- Temporal drift tracking is novel (few competitors do this)
- 3-tier hierarchy = hard to replicate

**Time to replicate:** 18-24 months for competitor (if they even understand the architecture)

---

## Next Steps

1. ✅ **Validate current implementation** - Confirm 868 archetypes are being used
2. 📝 **Document Level 2 → Level 3 upgrade path** - How to add fingerprints
3. 🔧 **Implement drift snapshot system** - Start collecting temporal data NOW
4. 📊 **Build drift detection alerts** - Proactive churn intervention
5. 🎨 **Design support agent UI** - Show archetype + drift in Gorgias

**This is world-class ML architecture. Now we need to productize it.**
