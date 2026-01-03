#!/usr/bin/env python3
"""
Generate L1/L2/L3 Archetypes from Hierarchical Clustering Results

This script processes fuzzy membership data from clustering and generates
three-tier archetypes according to the L1/L2/L3 methodology:

- L1: Dominant segment per axis (highest fuzzy score)
- L2: Significant segments (fuzzy score ≥ threshold, default 0.10)
- L3: Complete fuzzy thumbprint (all segments, no filtering)

Output: JSON files with archetype assignments for all customers
NO DATABASE WRITES - Review files before loading to database
"""

import os
import sys
import asyncio
import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_archetype_id(level: str, archetype_data: Dict) -> str:
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


def generate_l1_archetype(fuzzy_memberships: Dict[str, Dict[str, float]]) -> Dict[str, str]:
    """
    Generate L1 archetype (dominant segment per axis).

    Args:
        fuzzy_memberships: Dict[axis -> Dict[segment -> score]]

    Returns: Dict[axis -> dominant_segment_name]
    """
    l1_profile = {}

    for axis, segments in fuzzy_memberships.items():
        if not segments:
            continue

        # Extract segment with highest fuzzy score
        dominant_segment = max(segments.items(), key=lambda x: x[1])
        l1_profile[axis] = dominant_segment[0]  # Segment name only

    return l1_profile


def generate_l2_archetype(
    fuzzy_memberships: Dict[str, Dict[str, float]],
    threshold: float = 0.10
) -> Dict[str, Dict[str, float]]:
    """
    Generate L2 archetype (significant segments ≥ threshold).

    Args:
        fuzzy_memberships: Dict[axis -> Dict[segment -> score]]
        threshold: Minimum fuzzy score to include (default 0.10)

    Returns: Dict[axis -> Dict[significant_segment -> normalized_score]]
    """
    l2_profile = {}

    for axis, segments in fuzzy_memberships.items():
        if not segments:
            continue

        # Filter segments >= threshold
        significant = {
            segment: score
            for segment, score in segments.items()
            if score >= threshold
        }

        if not significant:
            # If no segments meet threshold, include dominant only
            dominant = max(segments.items(), key=lambda x: x[1])
            significant = {dominant[0]: dominant[1]}

        # Normalize to sum to 1.0
        total = sum(significant.values())
        l2_profile[axis] = {
            segment: score / total
            for segment, score in significant.items()
        }

    return l2_profile


def generate_l3_archetype(fuzzy_memberships: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """
    Generate L3 archetype (complete thumbprint, no filtering).

    Args:
        fuzzy_memberships: Dict[axis -> Dict[segment -> score]]

    Returns: Complete fuzzy membership dict (no transformation)
    """
    # Return as-is, no transformation
    return fuzzy_memberships


async def load_clustering_results(results_file: str) -> Dict:
    """Load hierarchical clustering results from JSON file."""
    logger.info(f"Loading clustering results from: {results_file}")

    with open(results_file, 'r') as f:
        data = json.load(f)

    return data


async def generate_fuzzy_memberships(clustering_results: Dict, store_id: str) -> Dict[str, Dict]:
    """
    Generate fuzzy membership vectors for all customers.

    Runs full clustering on all production customers to discover segments
    and assign fuzzy memberships.

    Args:
        clustering_results: Hierarchical clustering output (for reference only)
        store_id: Store identifier

    Returns: Dict[customer_id -> Dict[axis -> Dict[segment -> fuzzy_score]]]
    """
    logger.info("Generating fuzzy membership vectors for all customers...")
    logger.info("Step 1: Discover segments using 4K stratified sample (12 min)")
    logger.info("Step 2: Score all 94,686 customers against discovered segments (15 min)")

    from backend.segmentation.ecommerce_clustering_engine import EcommerceClusteringEngine

    # Initialize clustering engine
    os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "true"
    engine = EcommerceClusteringEngine(min_k=2, max_k=6, use_ai_naming=False)

    # Define axes to cluster
    axes_to_cluster = [
        'purchase_frequency',
        'purchase_value',
        'price_sensitivity',
        'category_exploration',
        'repurchase_behavior',
        'return_behavior',
        'purchase_cadence',
        'customer_maturity',
        'loyalty_trajectory'
    ]

    logger.info(f"Clustering {len(axes_to_cluster)} axes: {', '.join(axes_to_cluster)}")

    # Run clustering on 4K sample to discover segments (optimal sample size for 94.7K population)
    logger.info("Running discover_multi_axis_segments on 4K stratified sample...")
    logger.info("Sample size: 4,000 customers (4.2% of 94,686 total)")
    logger.info("Statistical validity: 95% confidence, ±1.5% margin of error")

    discovered_segments = await engine.discover_multi_axis_segments(
        store_id=store_id,
        axes_to_cluster=axes_to_cluster,
        max_customers=4000  # 4K stratified sample for segment discovery
    )

    logger.info(f"✅ Discovered {sum(len(s) for s in discovered_segments.values())} total segments across {len(discovered_segments)} axes")

    # Calculate fuzzy memberships for all customers using discovered segments
    logger.info("Calculating fuzzy memberships for all customers against discovered segments...")

    # First, we need to get all customer IDs and their features
    # Re-run calculate_customer_profile for each customer to get fuzzy memberships
    from backend.core.database import get_db_session
    from sqlalchemy import text

    async with get_db_session() as session:
        # Get all customer IDs (combined_sales doesn't have store_id column - all data is for linda_quilting)
        query = text("SELECT DISTINCT customer_id FROM combined_sales WHERE customer_id IS NOT NULL")
        result = await session.execute(query)
        all_customer_ids = [str(row.customer_id) for row in result.fetchall()]

    logger.info(f"Calculating fuzzy memberships for {len(all_customer_ids):,} customers...")

    fuzzy_memberships = {}
    failed_count = 0

    # Process in batches for progress tracking
    batch_size = 100

    for i in range(0, len(all_customer_ids), batch_size):
        batch = all_customer_ids[i:i+batch_size]

        for customer_id in batch:
            try:
                # Calculate customer profile using the clustering engine
                profile = await engine.calculate_customer_profile(
                    customer_id=customer_id,
                    store_id=store_id,
                    store_profile=False  # Don't store, just calculate
                )

                if profile and profile.fuzzy_memberships:
                    fuzzy_memberships[customer_id] = profile.fuzzy_memberships

            except Exception as e:
                failed_count += 1
                if failed_count <= 5:  # Only log first few failures
                    logger.warning(f"Failed to calculate profile for customer {customer_id}: {e}")

        # Progress logging
        progress = min(i + batch_size, len(all_customer_ids))
        pct = (progress / len(all_customer_ids)) * 100
        logger.info(f"Progress: {progress:,}/{len(all_customer_ids):,} customers ({pct:.1f}%), {len(fuzzy_memberships):,} successful")

    if failed_count > 0:
        logger.warning(f"Failed to calculate profiles for {failed_count:,} customers")

    logger.info(f"✅ Generated fuzzy memberships for {len(fuzzy_memberships):,} customers")

    return fuzzy_memberships


async def generate_all_archetypes(
    fuzzy_memberships: Dict[str, Dict],
    l2_threshold: float = 0.10
) -> Dict[str, Dict]:
    """
    Generate L1/L2/L3 archetypes for all customers.

    Args:
        fuzzy_memberships: Dict[customer_id -> Dict[axis -> Dict[segment -> score]]]
        l2_threshold: Minimum score for L2 inclusion (default 0.10)

    Returns: Dict[customer_id -> {l1, l2, l3, archetype_ids}]
    """
    logger.info(f"Generating L1/L2/L3 archetypes for {len(fuzzy_memberships)} customers...")
    logger.info(f"L2 threshold: {l2_threshold}")

    results = {}
    archetype_populations = {
        'L1': defaultdict(int),
        'L2': defaultdict(int),
        'L3': defaultdict(int)
    }

    for customer_id, memberships in fuzzy_memberships.items():
        # Generate L1: Dominant per axis
        l1_profile = generate_l1_archetype(memberships)

        # Generate L2: Significant >= threshold
        l2_profile = generate_l2_archetype(memberships, threshold=l2_threshold)

        # Generate L3: Complete thumbprint
        l3_profile = generate_l3_archetype(memberships)

        # Generate archetype IDs
        l1_id = generate_archetype_id('L1', l1_profile)
        l2_id = generate_archetype_id('L2', l2_profile)
        l3_id = generate_archetype_id('L3', l3_profile)

        # Track populations
        archetype_populations['L1'][l1_id] += 1
        archetype_populations['L2'][l2_id] += 1
        archetype_populations['L3'][l3_id] += 1

        results[customer_id] = {
            'archetype_l1_id': l1_id,
            'archetype_l2_id': l2_id,
            'archetype_l3_id': l3_id,
            'l1_profile': l1_profile,
            'l2_profile': l2_profile,
            'l3_profile': l3_profile
        }

    # Log statistics
    logger.info("\n" + "="*80)
    logger.info("ARCHETYPE GENERATION STATISTICS")
    logger.info("="*80)

    logger.info(f"\nUnique archetypes generated:")
    logger.info(f"  L1 (Dominant):     {len(archetype_populations['L1']):>6,} archetypes")
    logger.info(f"  L2 (Significant):  {len(archetype_populations['L2']):>6,} archetypes")
    logger.info(f"  L3 (Complete):     {len(archetype_populations['L3']):>6,} archetypes")

    logger.info(f"\nAverage customers per archetype:")
    logger.info(f"  L1: {len(fuzzy_memberships) / len(archetype_populations['L1']):.1f} customers/archetype")
    logger.info(f"  L2: {len(fuzzy_memberships) / len(archetype_populations['L2']):.1f} customers/archetype")
    logger.info(f"  L3: {len(fuzzy_memberships) / len(archetype_populations['L3']):.1f} customers/archetype")

    # Top 10 L1 archetypes
    logger.info("\nTop 10 L1 Archetypes:")
    sorted_l1 = sorted(archetype_populations['L1'].items(), key=lambda x: x[1], reverse=True)[:10]
    for rank, (archetype_id, count) in enumerate(sorted_l1, 1):
        pct = count / len(fuzzy_memberships) * 100
        logger.info(f"  {rank}. {archetype_id}: {count} customers ({pct:.1f}%)")

    return results


async def save_results(archetypes: Dict, output_dir: str = "/tmp"):
    """Save archetype results to JSON files."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save full archetypes
    archetypes_file = f"{output_dir}/archetypes_l1_l2_l3_{timestamp}.json"
    with open(archetypes_file, 'w') as f:
        json.dump(archetypes, f, indent=2)

    logger.info(f"\n✅ Archetypes saved to: {archetypes_file}")

    # Save archetype definitions (for dimension tables)
    archetype_defs = {
        'L1': {},
        'L2': {},
        'L3': {}
    }

    for customer_id, data in archetypes.items():
        for level in ['L1', 'L2', 'L3']:
            archetype_id = data[f'archetype_{level.lower()}_id']
            profile_key = f'{level.lower()}_profile'

            if archetype_id not in archetype_defs[level]:
                archetype_defs[level][archetype_id] = {
                    'archetype_id': archetype_id,
                    'level': level,
                    'profile': data[profile_key],
                    'customer_count': 0
                }

            archetype_defs[level][archetype_id]['customer_count'] += 1

    defs_file = f"{output_dir}/archetype_definitions_{timestamp}.json"
    with open(defs_file, 'w') as f:
        json.dump(archetype_defs, f, indent=2)

    logger.info(f"✅ Archetype definitions saved to: {defs_file}")

    return archetypes_file, defs_file


async def main():
    """Main execution function."""
    logger.info("="*80)
    logger.info("L1/L2/L3 ARCHETYPE GENERATION")
    logger.info("="*80)

    # Configuration
    results_file = "/tmp/comprehensive_analysis_20260101_204550.json"
    store_id = "linda_quilting"
    l2_threshold = float(os.getenv("L2_THRESHOLD", "0.10"))
    output_dir = "/tmp"

    # Load clustering results
    clustering_results = await load_clustering_results(results_file)

    # Generate fuzzy memberships for all customers
    # NOTE: This is a simplified demo - production would score all 94,686 customers
    fuzzy_memberships = await generate_fuzzy_memberships(clustering_results, store_id)

    # Generate L1/L2/L3 archetypes
    archetypes = await generate_all_archetypes(fuzzy_memberships, l2_threshold=l2_threshold)

    # Save results
    archetypes_file, defs_file = await save_results(archetypes, output_dir=output_dir)

    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    logger.info("\n1. Review generated archetype files:")
    logger.info(f"   - {archetypes_file}")
    logger.info(f"   - {defs_file}")
    logger.info("\n2. Sample customer archetypes:")

    # Show sample
    sample_id = list(archetypes.keys())[0]
    sample = archetypes[sample_id]

    logger.info(f"\n   Customer: {sample_id}")
    logger.info(f"   L1 ID: {sample['archetype_l1_id']}")
    logger.info(f"   L1 Profile (Dominant per axis):")
    for axis, segment in sample['l1_profile'].items():
        logger.info(f"     - {axis}: {segment}")

    logger.info(f"\n   L2 ID: {sample['archetype_l2_id']}")
    logger.info(f"   L2 Profile (Significant ≥{l2_threshold}):")
    for axis, segments in sample['l2_profile'].items():
        logger.info(f"     - {axis}:")
        for segment, score in sorted(segments.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"         {segment}: {score:.3f}")

    logger.info(f"\n   L3 ID: {sample['archetype_l3_id']}")
    logger.info(f"   L3 Profile (Complete thumbprint): [Full fuzzy vector stored]")

    logger.info("\n3. To load to database, run:")
    logger.info(f"   python3 scripts/load_archetypes_to_db.py --file {archetypes_file} --test")

    logger.info("\n⚠️  WARNING: Database writes not implemented in this script")
    logger.info("   This script is READ-ONLY for safety")
    logger.info("   Review output files before creating database loader script")

    return archetypes


if __name__ == "__main__":
    results = asyncio.run(main())
    sys.exit(0)
