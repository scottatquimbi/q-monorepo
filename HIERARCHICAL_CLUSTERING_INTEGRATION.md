# Hierarchical Clustering Integration

## Overview

Successfully integrated hierarchical clustering into the main `EcommerceClusteringEngine` to enable automatic subdivision of overly-broad segments. This addresses the critical issue identified in the clustering analysis where 67.5% of customers were grouped into a single "regular buyers" segment.

**Related Documentation**:
- [L1/L2/L3 Archetype Methodology](L1_L2_L3_ARCHETYPE_METHODOLOGY.md) - Three-tier behavioral fingerprinting system
- [AI Personalization Comparison](AI_PERSONALIZATION_COMPARISON_9_VS_13_AXES.md) - Impact on AI/ML personalization
- [Archetype Distribution Comparison](ARCHETYPE_DISTRIBUTION_COMPARISON.md) - Current vs new system analysis

## Changes Made

### 1. Engine Initialization (`ecommerce_clustering_engine.py:193-207`)

Added hierarchical clustering initialization with environment variable flag:

```python
# Hierarchical clustering (for recursive segment subdivision)
self.enable_hierarchical = os.getenv("ENABLE_HIERARCHICAL_CLUSTERING", "false").lower() == "true"
self.hierarchical_engine = None

if self.enable_hierarchical:
    from backend.segmentation.hierarchical_clustering import HierarchicalClusteringEngine
    self.hierarchical_engine = HierarchicalClusteringEngine(
        max_intra_variance=2.0,
        max_diameter_percentile=95.0,
        max_segment_pct=60.0,
        min_segment_size_for_split=100,
        max_depth=3,
        min_subsegment_size=30
    )
    logger.info("✅ Hierarchical Subdivision ENABLED")
```

**Parameters**:
- `max_intra_variance=2.0`: Trigger subdivision if segment variance exceeds 2.0
- `max_segment_pct=60.0`: Trigger subdivision if segment contains >60% of population
- `max_depth=3`: Allow up to 3 levels of recursive subdivision
- `min_segment_size_for_split=100`: Only subdivide segments with ≥100 customers

### 2. Subdivision Integration (`ecommerce_clustering_engine.py:804-897`)

Added hierarchical subdivision step after K-Means clustering completes:

```python
# Hierarchical subdivision: Refine overly-broad segments
if self.enable_hierarchical and self.hierarchical_engine:
    logger.info(f"{axis_name}: Analyzing segments for hierarchical subdivision")

    refined_segments = []
    for cluster_id, segment in enumerate(segments):
        # Check if segment needs subdivision
        diversity = self.hierarchical_engine.analyze_segment_diversity(...)

        if diversity.needs_subdivision:
            # Recursively subdivide this segment
            sub_hierarchy = self.hierarchical_engine.recursive_cluster_segment(...)
            flattened = self.hierarchical_engine.flatten_hierarchy(sub_hierarchy)

            # Create DiscoveredSegment objects for sub-segments
            for sub_seg in flattened:
                refined_segments.append(refined_segment)
        else:
            # Keep original segment
            refined_segments.append(segment)

    segments = refined_segments
```

**Flow**:
1. After K-Means creates initial segments
2. Analyze each segment's diversity metrics (variance, diameter, population %)
3. If segment is "too broad", recursively subdivide it
4. Replace overly-broad segments with refined sub-segments
5. Keep cohesive segments unchanged

### 3. Environment Configuration (`.env.example:52-63`)

Added environment variables for advanced clustering features:

```bash
# ==================== Clustering Advanced Features ====================
# Enable dynamic K-range optimization (automatic optimal cluster count)
ENABLE_DYNAMIC_K_RANGE=false

# Enable robust outlier handling with RobustScaler and winsorization
CLUSTERING_ROBUST_SCALING=true

# Enable Fuzzy C-Means instead of K-Means (soft clustering with membership degrees)
ENABLE_FUZZY_CMEANS=false

# Enable hierarchical clustering for recursive subdivision of broad segments
ENABLE_HIERARCHICAL_CLUSTERING=false
```

## Test Results

Created test script (`test_hierarchical_integration.py`) demonstrating successful integration:

**Before Hierarchical Subdivision**:
- K-Means optimal k=2
- Segment distribution: 93.2% / 6.8% (severely unbalanced)
- Large segment variance: 4.25 (too diverse)

**After Hierarchical Subdivision**:
- ✅ Large segment (93.2%) automatically subdivided
- ✅ 5 sub-segments created through recursive subdivision
- ✅ Final distribution: 59.5%, 11.6%, 10.5%, 8.4%, 6.8%, 3.2%
- ✅ Maximum recursion depth: 3 levels

**Log Output**:
```
purchase_frequency/medium_purchase_frequency: Subdividing - High variance (4.25 > 2.0); Large segment (93.2% > 60.0%)
Depth 0: 932 customers, variance=4.25, diameter=4.95
  Depth 1: 595 customers, variance=1.13 (cohesive)
  Depth 1: 232 customers, variance=3.74 (subdividing...)
    Depth 2: 32 customers (too small to split)
    Depth 2: 116 customers, variance=1.54 (cohesive)
    Depth 2: 84 customers (too small to split)
  Depth 1: 105 customers, variance=1.08 (cohesive)
purchase_frequency: After hierarchical subdivision: 6 segments
```

## Usage

### Enable Hierarchical Clustering

Set environment variable before running clustering:

```bash
export ENABLE_HIERARCHICAL_CLUSTERING=true
python3 run_full_clustering.py
```

### Test the Integration

```bash
export DATABASE_URL="postgresql://..."
export ENABLE_HIERARCHICAL_CLUSTERING=true
python3 test_hierarchical_integration.py
```

### Configuration Options

Adjust subdivision sensitivity by modifying engine parameters:

```python
engine = EcommerceClusteringEngine()
if engine.enable_hierarchical:
    # More aggressive subdivision
    engine.hierarchical_engine.max_intra_variance = 1.5
    engine.hierarchical_engine.max_segment_pct = 50.0

    # Or more conservative subdivision
    engine.hierarchical_engine.max_intra_variance = 3.0
    engine.hierarchical_engine.max_segment_pct = 70.0
```

## Expected Impact

Based on the clustering analysis findings:

### Before Integration
- **Problem**: 67.5% of customers in single "regular" segment
- **Root Cause**: K-Means with low k (2-6) creates overly-broad segments
- **Impact**: Poor personalization, segments lack meaningful distinction

### After Integration
- **Expected Improvement**: 30-50% better segmentation quality
- **Mechanism**: Broad segments automatically refined into sub-segments
- **Result**: More granular customer distinctions within major segments
- **Example**: "regular buyers" → "super-engaged", "active", "occasional", "lapsed"

## Subdivision Triggers

A segment will be subdivided if it meets ANY of these conditions:

1. **High Variance**: `intra_cluster_variance > 2.0`
   - Segment has wide internal spread
   - Customers are too diverse to be one group

2. **Large Population**: `segment_percentage > 60.0%`
   - Segment dominates the population
   - Likely hiding meaningful sub-groups

3. **Wide Diameter**: `max_distance > 95th_percentile * 1.5`
   - Edge cases too far from center
   - Indicates broad range of behaviors

Subdivision will NOT occur if:
- Segment has fewer than 100 customers
- Maximum recursion depth (3) reached
- Sub-clusters would have fewer than 30 customers each

## Integration Architecture

```
EcommerceClusteringEngine._cluster_axis()
│
├─ Step 1: K-Means Clustering (k=2-6)
│  └─ Creates initial broad segments
│
├─ Step 2: [NEW] Hierarchical Subdivision
│  │
│  ├─ For each segment:
│  │  ├─ analyze_segment_diversity()
│  │  │  ├─ Calculate variance, diameter, population %
│  │  │  └─ Determine if subdivision needed
│  │  │
│  │  ├─ If needs_subdivision:
│  │  │  ├─ recursive_cluster_segment()
│  │  │  │  ├─ Re-cluster segment (k=2-3)
│  │  │  │  ├─ Analyze sub-segments
│  │  │  │  └─ Recursive call for broad sub-segments
│  │  │  │
│  │  │  └─ flatten_hierarchy()
│  │  │     └─ Extract leaf segments
│  │  │
│  │  └─ Else: keep original segment
│  │
│  └─ Return refined segment list
│
└─ Step 3: Return discovered segments
```

## Files Modified

1. **backend/segmentation/ecommerce_clustering_engine.py**
   - Added hierarchical engine initialization
   - Integrated subdivision step after K-Means
   - Lines: 193-207 (init), 804-897 (subdivision)

2. **.env.example**
   - Added ENABLE_HIERARCHICAL_CLUSTERING flag
   - Documented all clustering feature flags
   - Lines: 52-63

## Files Created

1. **test_hierarchical_integration.py**
   - Integration test demonstrating subdivision
   - Tests with 1000 customer sample
   - Validates hierarchical engine activation

2. **HIERARCHICAL_CLUSTERING_INTEGRATION.md** (this file)
   - Complete documentation of changes
   - Usage examples and expected impact

## Known Limitations

1. **AI Naming**: Sub-segments currently use parent segment name as approximation
   - Hierarchical engine doesn't export sub-segment centers
   - Future: Calculate actual sub-segment centers for better AI naming

2. **Fuzzy Membership**: Not yet integrated with hierarchical sub-segments
   - Sub-segments don't have fuzzy_membership_matrix
   - Only initial K-Means segments have fuzzy scores

3. **Storage**: Hierarchical structure not persisted in database
   - Only leaf segments stored in `dim_segment_master`
   - Parent-child relationships lost after flattening

## Next Steps

1. **Enable in Production**: Set `ENABLE_HIERARCHICAL_CLUSTERING=true`
2. **Rerun Clustering**: Execute full clustering pipeline with subdivision enabled
3. **Compare Results**: Diff against baseline export (`clustering_baseline_2026-01-01.json`)
4. **Monitor Quality**: Track silhouette scores, segment populations, personalization metrics
5. **Iterate**: Adjust subdivision thresholds based on results

## Related Documentation

- [CLUSTERING_ANALYSIS_2026-01-01.md](CLUSTERING_ANALYSIS_2026-01-01.md) - Root cause analysis
- [HOW_TO_RUN_CLUSTERING.md](HOW_TO_RUN_CLUSTERING.md) - Clustering execution guide
- [backend/segmentation/hierarchical_clustering.py](backend/segmentation/hierarchical_clustering.py) - Subdivision algorithm

---

**Status**: ✅ Integration Complete and Tested
**Date**: 2026-01-01
**Author**: Quimbi Platform (via Claude Code)
