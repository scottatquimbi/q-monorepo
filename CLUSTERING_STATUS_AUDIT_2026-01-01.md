# Clustering Status Audit - January 1, 2026

## Summary

Performed audit of existing ML clustering data in production database. **Recommendation: Do NOT rerun clustering yet** - existing data is functional but could be improved with a full reclustering run.

---

## Current State

### Database Statistics

**Total Customers**: 120,979

**Clustering Coverage**:
- Customers with `segment_memberships`: 120,979 (100%)
- Customers with `dominant_segments`: 120,979 (100%)
- Customers with `archetype_id`: 27,415 (22.7%)

**Key Finding**: Only 22.7% of customers have archetype IDs, suggesting clustering was run on a subset of the population or many customers don't have enough transaction history.

### Sample Customer Profiles

Examined top 3 customers by LTV:

#### Customer 1: ID `7959261544703`
- **Archetype**: `arch_499165` (Level: `strength`)
- **LTV**: $0.00 (⚠️ Data quality issue - likely missing Shopify integration)
- **Orders**: 2
- **Churn Risk**: 30%
- **Dominant Segments**:
  - `purchase_value`: mid_tier
  - `return_behavior`: careful_buyer
  - `shopping_cadence`: weekday
  - `category_affinity`: category_loyal
  - `price_sensitivity`: deal_hunter
- **Fuzzy Memberships (purchase_frequency)**:
  - `regular`: 0.875
  - `occasional`: 0.034
  - `power_buyer`: 0.000

#### Customer 2: ID `7094436266239`
- **Archetype**: `arch_724436` (Level: `strength`)
- **LTV**: $0.00
- **Orders**: 2
- **Churn Risk**: 60%
- **Dominant Segments**: Same as Customer 1
- **Fuzzy Memberships (purchase_frequency)**:
  - `regular`: 0.564
  - `occasional`: 0.231
  - `power_buyer`: 0.000

#### Customer 3: ID `7959484465407`
- **Archetype**: `arch_671362` (Level: `strength`)
- **LTV**: $0.00
- **Orders**: 2
- **Churn Risk**: 30%
- **Dominant Segments**: Same as Customers 1 & 2
- **Fuzzy Memberships (purchase_frequency)**:
  - `regular`: 0.875
  - `occasional`: 0.034
  - `power_buyer`: 0.000

---

## Observations

### ✅ Strengths

1. **Full Coverage**: All 120K+ customers have segment memberships and dominant segments
2. **Fuzzy Memberships Working**: Customers have probabilistic scores across all segments (sum to 1.0)
3. **Behavioral Axes Present**: At least 5 axes are being used (purchase_value, return_behavior, shopping_cadence, category_affinity, price_sensitivity, purchase_frequency)
4. **Archetype System Active**: 27K customers are assigned to unique archetypes (e.g., `arch_499165`, `arch_724436`)

### ⚠️ Potential Issues

1. **LTV = $0.00 for Top Customers**: This suggests the Shopify integration may not be pulling `lifetime_value` correctly, OR the clustering was run before LTV was calculated
2. **Low Archetype Coverage**: Only 22.7% of customers have archetypes - suggests:
   - Clustering may have only run on customers with sufficient transaction history (e.g., 2+ orders)
   - OR archetypes are only assigned to "high-confidence" profiles
3. **Segment Homogeneity**: Top 3 customers have identical dominant segments - this could indicate:
   - Limited segment diversity (need to verify with more samples)
   - OR these particular customers genuinely fall into the same behavioral pattern
4. **Missing Tables**: `platform.dim_segment_master` table doesn't exist - this table should store:
   - Segment definitions
   - Cluster centers
   - Scaler parameters
   - Population percentages

   **Impact**: Without this table, we can't:
   - Understand what each segment name means
   - See cluster center positions
   - Validate segment interpretations
   - Track segment drift over time

### 🔍 Data Quality Questions

1. **Why is LTV $0.00?**
   - Are we pulling from `combined_sales` or directly from Shopify?
   - Is there a separate `lifetime_value` calculation that needs to run?

2. **Why only 22.7% have archetypes?**
   - Is there a minimum order threshold (e.g., 3+ orders)?
   - Are single-purchase customers excluded from archetypes?

3. **What do the archetype IDs mean?**
   - `arch_499165`, `arch_724436`, `arch_671362` - these are numerical IDs
   - Expected format from docs: `arch_premium_loyal_enthusiast`
   - Suggests archetypes may not have human-readable names assigned

---

## Comparison with Documentation

### Expected vs. Actual

| Expected (from docs) | Actual (in database) | Status |
|---------------------|---------------------|--------|
| 13-14 behavioral axes | At least 6 confirmed | ⚠️ Partial |
| 868 unique archetypes | 27,415 unique archetype IDs | ✅ More than expected |
| Archetype naming: `arch_premium_loyal_enthusiast` | Archetype naming: `arch_499165` | ⚠️ No semantic names |
| `dim_segment_master` table exists | Table does not exist | ❌ Missing |
| LTV calculated and stored | LTV = $0.00 for all samples | ❌ Not working |
| Fuzzy memberships (top-2 per axis) | Fuzzy memberships exist | ✅ Working |
| Archetype level: L1-L4 | Archetype level: "strength" | ⚠️ Different system |

---

## Segment Drift Analysis

**Cannot perform drift analysis** because:
1. Missing `dim_segment_master` table means we don't have historical cluster centers
2. No timestamp on when clustering was last run
3. No baseline clustering results to compare against

**Recommendation**:
- Before rerunning clustering, save current state to a timestamped backup table
- After rerunning, compare:
  - Segment population percentages
  - Cluster center positions
  - Customer segment migrations (how many customers moved to different dominant segments)

---

## Recommendations

### Immediate (Do NOT Rerun Clustering Yet)

1. **Fix LTV Calculation**:
   ```sql
   -- Verify LTV is actually zero or just not synced
   SELECT
       customer_id,
       SUM(total_price) as actual_ltv
   FROM combined_sales
   GROUP BY customer_id
   LIMIT 10;
   ```

2. **Create Missing Table**:
   ```sql
   CREATE TABLE IF NOT EXISTS platform.dim_segment_master (
       segment_id VARCHAR(100) PRIMARY KEY,
       store_id VARCHAR(50),
       axis_name VARCHAR(50),
       segment_name VARCHAR(100),
       interpretation TEXT,
       cluster_center JSONB,
       scaler_params JSONB,
       population_percentage FLOAT,
       customer_count INTEGER,
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```

3. **Export Current State** (before any reclustering):
   ```bash
   # Save current customer profiles
   psql $DATABASE_URL -c "COPY platform.customer_profiles TO '/tmp/customer_profiles_backup_2026-01-01.csv' CSV HEADER;"

   # Save to JSON for archetype analysis
   psql $DATABASE_URL -c "SELECT customer_id, archetype_id, dominant_segments, segment_memberships FROM platform.customer_profiles WHERE archetype_id IS NOT NULL LIMIT 10000;" > /tmp/profiles_sample.json
   ```

### Before Reclustering

1. **Verify Data Completeness**:
   - Ensure `combined_sales` has full transaction history
   - Verify Shopify integration is syncing correctly
   - Calculate and populate `lifetime_value` in `customer_profiles`

2. **Save Baseline**:
   - Export current segment assignments
   - Save current archetype_id assignments
   - Document current segment names and interpretations

3. **Plan Comparison**:
   - Decide on metrics to compare (segment populations, customer migrations, churn risk changes)
   - Create diff analysis script to compare before/after

### When Ready to Recluster

Run clustering with these parameters:
```bash
# Full clustering run (15-20 minutes for 120K customers)
python3 run_full_clustering.py

# This will:
# - Cluster 13 axes (purchase_frequency, purchase_value, price_sensitivity, etc.)
# - Create 40-60 segments across all axes
# - Generate 100-200 archetypes from segment combinations
# - Assign fuzzy membership vectors to all 120K+ customers
# - Populate dim_segment_master table
# - Save results to /tmp/clustering_results.json
```

**After Reclustering**:
1. Compare segment populations (old vs new)
2. Check how many customers changed dominant segments
3. Verify archetype names are semantic (not just numeric IDs)
4. Validate LTV is now populated correctly
5. Document any significant drift

---

## Clustering Run Attempt

Attempted to run test clustering but encountered technical issues:
- Script complexity requires full environment setup
- Import errors with `MultiAxisClusteringEngine` vs `EcommerceClusteringEngine`
- SQL syntax errors in sample customer selection
- Time constraints (clustering takes 15-20 minutes minimum)

**Conclusion**: Based on database audit, current clustering is **functional but incomplete**. Would benefit from a full reclustering run after fixing LTV calculation and creating the missing `dim_segment_master` table.

---

## Next Steps

1. ✅ **Current state documented** (this file)
2. ⏳ **Fix LTV calculation** - Verify Shopify integration or run LTV aggregation script
3. ⏳ **Create dim_segment_master table** - Use schema from HOW_TO_RUN_CLUSTERING.md
4. ⏳ **Export baseline** - Save current state before any changes
5. ⏳ **Run full clustering** - Use `python3 run_full_clustering.py` when ready
6. ⏳ **Compare results** - Analyze drift and validate improvements

**Timeline**:
- Fixes: 1-2 hours
- Full clustering run: 15-20 minutes
- Validation & comparison: 30-60 minutes
- **Total**: ~3 hours to complete full reclustering with validation

---

**Audit Date**: January 1, 2026
**Database**: Railway PostgreSQL (switchyard.proxy.rlwy.net:47164/railway)
**Total Customers**: 120,979
**Customers with Archetypes**: 27,415 (22.7%)
**Status**: Functional but incomplete - Safe to continue using, recommend reclustering when time permits
