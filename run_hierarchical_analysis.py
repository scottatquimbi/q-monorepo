#!/usr/bin/env python3
"""
Comprehensive analysis comparing clustering results with and without hierarchical subdivision
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_clustering_comparison():
    """Run clustering with both configurations and compare results"""

    logger.info("=" * 80)
    logger.info("HIERARCHICAL CLUSTERING ANALYSIS")
    logger.info("=" * 80)

    from backend.segmentation.ecommerce_clustering_engine import EcommerceClusteringEngine

    results = {
        'baseline': {},
        'hierarchical': {},
        'comparison': {}
    }

    # Configuration
    store_id = "linda_quilting"
    axes = ["purchase_frequency", "purchase_value", "price_sensitivity"]
    max_customers = 5000  # Use 5k sample for faster analysis

    # ==================== BASELINE: K-Means Only ====================
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE: K-Means Clustering (No Hierarchical Subdivision)")
    logger.info("=" * 80)

    os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "false"

    engine_baseline = EcommerceClusteringEngine(
        min_k=2,
        max_k=6,
        use_ai_naming=False
    )

    logger.info("Running baseline clustering...")
    segments_baseline = await engine_baseline.discover_multi_axis_segments(
        store_id=store_id,
        axes_to_cluster=axes,
        max_customers=max_customers
    )

    # Analyze baseline results
    for axis_name, axis_segments in segments_baseline.items():
        results['baseline'][axis_name] = {
            'num_segments': len(axis_segments),
            'segments': []
        }

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

    # ==================== HIERARCHICAL: K-Means + Subdivision ====================
    logger.info("\n" + "=" * 80)
    logger.info("HIERARCHICAL: K-Means + Hierarchical Subdivision")
    logger.info("=" * 80)

    os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "true"

    engine_hierarchical = EcommerceClusteringEngine(
        min_k=2,
        max_k=6,
        use_ai_naming=False
    )

    logger.info("Running hierarchical clustering...")
    segments_hierarchical = await engine_hierarchical.discover_multi_axis_segments(
        store_id=store_id,
        axes_to_cluster=axes,
        max_customers=max_customers
    )

    # Analyze hierarchical results
    for axis_name, axis_segments in segments_hierarchical.items():
        results['hierarchical'][axis_name] = {
            'num_segments': len(axis_segments),
            'segments': []
        }

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

    # ==================== COMPARISON ====================
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON: Baseline vs Hierarchical")
    logger.info("=" * 80)

    for axis_name in axes:
        if axis_name not in segments_baseline or axis_name not in segments_hierarchical:
            continue

        baseline_segs = segments_baseline[axis_name]
        hierarchical_segs = segments_hierarchical[axis_name]

        logger.info(f"\n{axis_name}:")
        logger.info(f"  Baseline segments: {len(baseline_segs)}")
        logger.info(f"  Hierarchical segments: {len(hierarchical_segs)}")
        logger.info(f"  Improvement: +{len(hierarchical_segs) - len(baseline_segs)} segments")

        # Calculate balance metrics
        baseline_pcts = [s.population_percentage * 100 for s in baseline_segs]
        hierarchical_pcts = [s.population_percentage * 100 for s in hierarchical_segs]

        baseline_max = max(baseline_pcts)
        baseline_min = min(baseline_pcts)
        hierarchical_max = max(hierarchical_pcts)
        hierarchical_min = min(hierarchical_pcts)

        logger.info(f"  Baseline balance: {baseline_min:.1f}% - {baseline_max:.1f}% "
                   f"(spread: {baseline_max - baseline_min:.1f}%)")
        logger.info(f"  Hierarchical balance: {hierarchical_min:.1f}% - {hierarchical_max:.1f}% "
                   f"(spread: {hierarchical_max - hierarchical_min:.1f}%)")

        # Check if largest segment was subdivided
        if baseline_max > 60.0:
            logger.info(f"  ✅ Large segment ({baseline_max:.1f}%) was subdivided!")

        results['comparison'][axis_name] = {
            'baseline_count': len(baseline_segs),
            'hierarchical_count': len(hierarchical_segs),
            'improvement': len(hierarchical_segs) - len(baseline_segs),
            'baseline_balance': {
                'max': baseline_max,
                'min': baseline_min,
                'spread': baseline_max - baseline_min
            },
            'hierarchical_balance': {
                'max': hierarchical_max,
                'min': hierarchical_min,
                'spread': hierarchical_max - hierarchical_min
            }
        }

    # ==================== SAVE RESULTS ====================
    output_file = f"/tmp/hierarchical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\n✅ Analysis complete! Results saved to: {output_file}")

    # ==================== SUMMARY ====================
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)

    total_baseline = sum(len(segments_baseline.get(axis, [])) for axis in axes)
    total_hierarchical = sum(len(segments_hierarchical.get(axis, [])) for axis in axes)

    logger.info(f"Total segments (baseline): {total_baseline}")
    logger.info(f"Total segments (hierarchical): {total_hierarchical}")
    logger.info(f"Net improvement: +{total_hierarchical - total_baseline} segments "
               f"({((total_hierarchical - total_baseline) / total_baseline * 100):.1f}% increase)")

    # Check for large segments that were subdivided
    large_segments_fixed = 0
    for axis_name in axes:
        if axis_name in results['comparison']:
            baseline_max = results['comparison'][axis_name]['baseline_balance']['max']
            if baseline_max > 60.0:
                large_segments_fixed += 1

    logger.info(f"\n✅ Fixed {large_segments_fixed} overly-broad segments (>60% of population)")

    return results

if __name__ == "__main__":
    results = asyncio.run(run_clustering_comparison())
    sys.exit(0)
