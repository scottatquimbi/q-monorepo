# Comprehensive Clustering Analysis - Expanded Scope

## Context

The initial hierarchical clustering analysis (HIERARCHICAL_CLUSTERING_RESULTS_2026-01-01.md) tested only 3 financial/transactional axes:
- purchase_frequency
- purchase_value
- price_sensitivity

While these showed excellent results (600% segment improvement), they only capture **transactional behavior**, not **product preferences** or **engagement patterns**.

## Expanded Analysis Scope

The comprehensive analysis now includes **9 behavioral axes** across 4 categories:

### 1. Financial/Transactional (3 axes)
Already tested - baseline for comparison

**purchase_frequency**
- How often customers purchase
- Segments: first-time, occasional, regular, power buyers
- Personalization: Reactivation campaigns, loyalty rewards

**purchase_value**
- Average order value and total spending
- Segments: budget, mid-tier, high-value, VIP
- Personalization: Product recommendations, tier-based offers

**price_sensitivity**
- Response to discounts and promotions
- Segments: price-agnostic, moderate, deal-hunter, bargain-seeker
- Personalization: Timing of promotional emails, discount depth

---

### 2. Product Behavior (3 axes) - NEW
Addresses feedback about product-level insights

**category_exploration**
- **What**: Diversity of product categories purchased
- **Why**: Identifies specialists vs generalists
- **Segments**:
  - Specialists: Buy only from 1-2 categories (e.g., "fabric only")
  - Focused: 3-4 categories (e.g., "quilting essentials")
  - Explorers: 5+ categories (e.g., "multi-craft enthusiasts")
- **Personalization**:
  - Specialists: Deep dives into their category
  - Explorers: Cross-category bundles, new product discovery

**repurchase_behavior**
- **What**: How often customers buy the same products repeatedly
- **Why**: Distinguishes consumables buyers from project-based buyers
- **Segments**:
  - Loyal repurchasers: Same products every time (e.g., thread, backing)
  - Mix of repeat & new: Core supplies + project materials
  - Always new: Never repeat purchase (one-time projects)
- **Personalization**:
  - Repurchasers: Subscribe & save, stock alerts
  - Mix: Suggest complementary products to favorites
  - Project buyers: Inspiration for next project

**return_behavior**
- **What**: Return/refund frequency and patterns
- **Why**: Indicates fit issues, buyer's remorse, or quality expectations
- **Segments**:
  - No returns: Confident buyers, good fit
  - Occasional returns: Normal experimentation
  - Frequent returns: Fit issues or high standards
- **Personalization**:
  - No returns: Upsell higher-end products
  - Occasional: Better product descriptions, size guides
  - Frequent: Satisfaction surveys, personalized recommendations

---

### 3. Timing/Cadence Behavior (2 axes) - NEW
Captures when and how purchasing patterns evolve

**purchase_cadence**
- **What**: Temporal purchasing patterns
- **Why**: Identifies seasonal shoppers, weekend browsers, planners
- **Segments**:
  - Weekend shoppers: Browse/buy on Saturdays
  - Weekday buyers: Purchase during work hours
  - Seasonal: Spike around specific times (holidays, events)
  - Always-on: Consistent across days/weeks
- **Personalization**:
  - Weekend: Email campaigns Friday afternoon
  - Weekday: Lunchtime promotions
  - Seasonal: Early access to seasonal collections

**customer_maturity**
- **What**: How long they've been a customer, purchase evolution
- **Why**: New vs established customers have different needs
- **Segments**:
  - Brand new: First 30 days, onboarding phase
  - Growing: 30-180 days, expanding purchases
  - Established: 180+ days, stable patterns
  - Lapsed: Had pattern, now dormant
- **Personalization**:
  - New: Welcome series, education content
  - Growing: Loyalty program enrollment
  - Established: VIP treatment, early access
  - Lapsed: Win-back campaigns

---

### 4. Engagement/Loyalty (1 axis) - NEW
Captures overall relationship trajectory

**loyalty_trajectory**
- **What**: Direction of customer relationship over time
- **Why**: Predicts churn, identifies growth opportunities
- **Segments**:
  - Rising stars: Increasing engagement/spend
  - Stable loyalists: Consistent engagement
  - Declining: Decreasing activity (churn risk)
  - Reactivated: Returned after dormancy
- **Personalization**:
  - Rising: Accelerate with incentives
  - Stable: Maintain with recognition
  - Declining: Intervention campaigns
  - Reactivated: Welcome back offers

---

## What This Enables

### Before (3 financial axes only)
Limited to transactional insights:
- "You spend $X per order"
- "You purchase Y times per year"
- "You respond to discounts"

**Missing**: What do they buy? Why? When? How is it changing?

### After (9 comprehensive axes)
Holistic behavioral understanding:

**Financial + Product + Timing + Engagement**
- "You're a specialist fabric buyer who purchases every 6 weeks on weekends"
- "You repurchase the same backing materials - want to subscribe?"
- "You're exploring new categories - here are complementary tools"
- "Your engagement is growing - join our VIP program early"

### Example Customer Profiles

**Profile 1: "The Quilting Enthusiast"**
- purchase_frequency: power_buyer (top 10%)
- purchase_value: high_value
- price_sensitivity: quality_focused (low sensitivity)
- **category_exploration: specialist (quilting only)**
- **repurchase_behavior: mix (core supplies + new fabrics)**
- **return_behavior: no_returns (knows what they want)**
- **purchase_cadence: weekend_planner**
- **customer_maturity: established (2+ years)**
- **loyalty_trajectory: stable_loyalist**

**Personalization**:
- Friday afternoon: "New fabric collection arrives this weekend"
- Suggest: Pre-orders for popular fabrics
- Offer: Early access to limited editions
- Incentive: VIP quilting workshop invitations

**Profile 2: "The Multi-Craft Explorer"**
- purchase_frequency: occasional
- purchase_value: mid_tier
- price_sensitivity: deal_hunter
- **category_exploration: explorer (5+ categories)**
- **repurchase_behavior: always_new (project-based)**
- **return_behavior: occasional (experimenting)**
- **purchase_cadence: seasonal (spring/fall)**
- **customer_maturity: growing (6 months)**
- **loyalty_trajectory: rising_star**

**Personalization**:
- March/September: "Spring/Fall project inspiration"
- Suggest: Cross-craft bundle deals
- Offer: "Complete your project" kits
- Incentive: Loyalty points for category diversity

---

## Technical Impact

### Computation
- 3 axes: ~1-2 minutes
- 9 axes: **~4-6 minutes** (estimated)
- Acceptable for overnight batch processing

### Storage
- 3 axes: 42 segments → ~7KB JSON
- 9 axes: **~126 segments** (estimated) → ~20KB JSON
- Minimal database impact

### Archetype Combinations
- 3 axes: 42 segments → 42³ possible combinations (too many)
- **Smart archetype selection**: Top-2 per axis → 2⁹ = 512 meaningful archetypes
- Realistic: ~200-300 actual archetype patterns in data

---

## Expected Results

Based on 3-axis results (600% improvement), projecting to 9 axes:

| Axis Category | Baseline Segments | Expected Hierarchical | Improvement |
|---------------|-------------------|----------------------|-------------|
| Financial (3 axes) | 6 | 42 | **+600%** |
| Product (3 axes) | 6 | **~35-45** | **~500-650%** |
| Timing (2 axes) | 4 | **~20-30** | **~400-650%** |
| Engagement (1 axis) | 2 | **~8-15** | **~300-650%** |
| **TOTAL (9 axes)** | **18** | **~105-132** | **~480-630%** |

### Why Product Axes Will Show High Improvement

1. **category_exploration**: Expect very unbalanced baseline
   - Most customers likely buy from 1-2 categories (90%+ in one segment)
   - Hierarchical will subdivide into specialists by category type
   - Expected: 2 → 12-18 segments

2. **repurchase_behavior**: Natural bimodal distribution
   - Consumables buyers vs project buyers
   - Hierarchical will refine within each mode
   - Expected: 2 → 8-12 segments

3. **return_behavior**: Likely highly skewed (most have no returns)
   - Large "no returns" segment will be subdivided by reason
   - Expected: 2 → 6-10 segments

---

## Success Criteria

✅ **Baseline metrics** (achieved in 3-axis test):
- Segment count increase: >400%
- Balance improvement: >50% reduction in spread
- Automatic subdivision: No manual tuning

✅ **Product-level insights** (new):
- Category specialization discovered
- Repurchase patterns identified
- Return behavior segmented

✅ **Actionable personalization** (new):
- Product recommendations driven by category_exploration
- Subscribe & save offers for repurchasers
- Quality improvements for frequent returners

---

## Analysis in Progress

Currently running comprehensive analysis on:
- **Sample size**: 3,000 customers
- **Axes**: 9 behavioral dimensions
- **Comparison**: Baseline K-Means vs Hierarchical subdivision
- **Output**: Detailed results by axis category

Results will show whether hierarchical subdivision delivers similar improvements for product-level axes as it did for financial axes.

---

**Status**: Comprehensive analysis running
**ETA**: ~10-15 minutes
**Next**: Document product-level insights and personalization opportunities
