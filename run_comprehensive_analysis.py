#!/usr/bin/env python3
"""
Comprehensive hierarchical clustering analysis including product-level behavioral axes
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_comprehensive_analysis():
    """Run clustering with product-focused axes included"""

    logger.info("=" * 80)
    logger.info("COMPREHENSIVE HIERARCHICAL CLUSTERING ANALYSIS")
    logger.info("Including product-level and behavioral axes")
    logger.info("=" * 80)

    from backend.segmentation.ecommerce_clustering_engine import EcommerceClusteringEngine

    # Configuration
    store_id = "linda_quilting"

    # COMPREHENSIVE axis set including product behavior
    axes = [
        # Financial/transactional (already tested)
        "purchase_frequency",
        "purchase_value",
        "price_sensitivity",

        # Product-level behavior (NEW)
        "category_exploration",      # What product types they buy
        "repurchase_behavior",        # Repeat purchase patterns
        "return_behavior",            # Return/refund patterns

        # Timing/cadence behavior (NEW)
        "purchase_cadence",           # When they shop (weekday/weekend, seasonal)
        "customer_maturity",          # How long they've been a customer

        # Engagement behavior (NEW)
        "loyalty_trajectory"          # Customer lifetime trajectory
    ]

    max_customers = 3000  # Use 3k sample for faster analysis

    results = {
        'baseline': {},
        'hierarchical': {},
        'comparison': {},
        'metadata': {
            'axes': axes,
            'max_customers': max_customers,
            'timestamp': datetime.now().isoformat()
        }
    }

    # ==================== BASELINE ====================
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE: K-Means Only (No Hierarchical)")
    logger.info("=" * 80)

    os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "false"

    engine_baseline = EcommerceClusteringEngine(
        min_k=2,
        max_k=6,
        use_ai_naming=False
    )

    logger.info(f"Running baseline clustering on {len(axes)} axes...")
    logger.info(f"Axes: {', '.join(axes)}")

    segments_baseline = await engine_baseline.discover_multi_axis_segments(
        store_id=store_id,
        axes_to_cluster=axes,
        max_customers=max_customers
    )

    # Analyze baseline
    total_baseline = 0
    for axis_name, axis_segments in segments_baseline.items():
        results['baseline'][axis_name] = {
            'num_segments': len(axis_segments),
            'segments': []
        }
        total_baseline += len(axis_segments)

        logger.info(f"\n{axis_name}: {len(axis_segments)} segments")

        for seg in axis_segments:
            seg_info = {
                'name': seg.segment_name,
                'count': seg.customer_count,
                'percentage': seg.population_percentage * 100
            }
            results['baseline'][axis_name]['segments'].append(seg_info)

            logger.info(f"  - {seg.segment_name}: {seg.customer_count} customers "
                       f"({seg.population_percentage*100:.1f}%)")

    logger.info(f"\nBaseline total segments: {total_baseline}")

    # ==================== HIERARCHICAL ====================
    logger.info("\n" + "=" * 80)
    logger.info("HIERARCHICAL: K-Means + Subdivision")
    logger.info("=" * 80)

    os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "true"

    engine_hierarchical = EcommerceClusteringEngine(
        min_k=2,
        max_k=6,
        use_ai_naming=False
    )

    logger.info(f"Running hierarchical clustering on {len(axes)} axes...")

    segments_hierarchical = await engine_hierarchical.discover_multi_axis_segments(
        store_id=store_id,
        axes_to_cluster=axes,
        max_customers=max_customers
    )

    # Analyze hierarchical
    total_hierarchical = 0
    for axis_name, axis_segments in segments_hierarchical.items():
        results['hierarchical'][axis_name] = {
            'num_segments': len(axis_segments),
            'segments': []
        }
        total_hierarchical += len(axis_segments)

        logger.info(f"\n{axis_name}: {len(axis_segments)} segments")

        for seg in axis_segments:
            seg_info = {
                'name': seg.segment_name,
                'count': seg.customer_count,
                'percentage': seg.population_percentage * 100
            }
            results['hierarchical'][axis_name]['segments'].append(seg_info)

            logger.info(f"  - {seg.segment_name}: {seg.customer_count} customers "
                       f"({seg.population_percentage*100:.1f}%)")

    logger.info(f"\nHierarchical total segments: {total_hierarchical}")

    # ==================== COMPARISON ====================
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON BY AXIS TYPE")
    logger.info("=" * 80)

    axis_categories = {
        'Financial/Transactional': ['purchase_frequency', 'purchase_value', 'price_sensitivity'],
        'Product Behavior': ['category_exploration', 'repurchase_behavior', 'return_behavior'],
        'Timing/Cadence': ['purchase_cadence', 'customer_maturity'],
        'Engagement': ['loyalty_trajectory']
    }

    for category, category_axes in axis_categories.items():
        logger.info(f"\n{category}:")

        category_baseline = 0
        category_hierarchical = 0

        for axis_name in category_axes:
            if axis_name not in segments_baseline or axis_name not in segments_hierarchical:
                continue

            baseline_count = len(segments_baseline[axis_name])
            hierarchical_count = len(segments_hierarchical[axis_name])

            category_baseline += baseline_count
            category_hierarchical += hierarchical_count

            baseline_segs = segments_baseline[axis_name]
            hierarchical_segs = segments_hierarchical[axis_name]

            baseline_pcts = [s.population_percentage * 100 for s in baseline_segs]
            hierarchical_pcts = [s.population_percentage * 100 for s in hierarchical_segs]

            baseline_max = max(baseline_pcts)
            hierarchical_max = max(hierarchical_pcts)

            improvement = hierarchical_count - baseline_count

            logger.info(f"  {axis_name}:")
            logger.info(f"    Baseline: {baseline_count} segments (max: {baseline_max:.1f}%)")
            logger.info(f"    Hierarchical: {hierarchical_count} segments (max: {hierarchical_max:.1f}%)")
            logger.info(f"    Improvement: +{improvement} segments ({(improvement/baseline_count*100):.0f}%)")

            results['comparison'][axis_name] = {
                'baseline_count': baseline_count,
                'hierarchical_count': hierarchical_count,
                'improvement': improvement,
                'improvement_pct': (improvement / baseline_count * 100) if baseline_count > 0 else 0,
                'baseline_max_pct': baseline_max,
                'hierarchical_max_pct': hierarchical_max,
                'category': category
            }

        logger.info(f"  Category totals: {category_baseline} → {category_hierarchical} "
                   f"(+{category_hierarchical - category_baseline} segments)")

    # ==================== SUMMARY ====================
    logger.info("\n" + "=" * 80)
    logger.info("OVERALL SUMMARY")
    logger.info("=" * 80)

    logger.info(f"Total axes analyzed: {len(axes)}")
    logger.info(f"Baseline total segments: {total_baseline}")
    logger.info(f"Hierarchical total segments: {total_hierarchical}")
    logger.info(f"Net improvement: +{total_hierarchical - total_baseline} segments "
               f"({((total_hierarchical - total_baseline) / total_baseline * 100):.1f}% increase)")

    # Count large segments fixed
    large_segments_fixed = 0
    for axis_name in axes:
        if axis_name in results['comparison']:
            if results['comparison'][axis_name]['baseline_max_pct'] > 60.0:
                large_segments_fixed += 1

    logger.info(f"\nLarge segments (>60%) fixed: {large_segments_fixed}/{len(axes)}")

    # ==================== SAVE RESULTS ====================
    output_file = f"/tmp/comprehensive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\n✅ Results saved to: {output_file}")

    return results

if __name__ == "__main__":
    results = asyncio.run(run_comprehensive_analysis())
    sys.exit(0)
