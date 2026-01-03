#!/usr/bin/env python3
"""
Complete L1/L2/L3 Archetype Generation - End to End

This script:
1. Runs 4K clustering to discover segments (with segment data export)
2. Loads all 94,686 customers from combined_sales
3. Extracts features and scores against discovered segments
4. Generates L1/L2/L3 archetypes
5. Saves to JSON files

Works directly with combined_sales schema.
"""

import os
import sys
import asyncio
import logging
import json
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
sys.path.insert(0, '/Users/scottallen/quimbi-platform')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_clustering_and_export_segments(store_id: str, max_customers: int = 4000) -> Dict:
    """
    Run hierarchical clustering on sample and return discovered segments with full data

    Returns: Dict[axis_name -> List[segment_dict_with_cluster_centers]]
    """
    logger.info("=" * 80)
    logger.info("PHASE 1: DISCOVER SEGMENTS (4K Sample Clustering)")
    logger.info("=" * 80)

    from backend.segmentation.ecommerce_clustering_engine import EcommerceClusteringEngine

    # Enable hierarchical subdivision
    os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "true"

    engine = EcommerceClusteringEngine(min_k=2, max_k=6, use_ai_naming=False)

    axes = [
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

    logger.info(f"Running clustering on {max_customers:,} customer sample...")
    logger.info(f"Axes: {', '.join(axes)}")

    discovered_segments = await engine.discover_multi_axis_segments(
        store_id=store_id,
        axes_to_cluster=axes,
        max_customers=max_customers
    )

    # Convert DiscoveredSegment objects to dicts with all needed data
    segments_export = {}

    for axis_name, segments in discovered_segments.items():
        segments_export[axis_name] = []

        for seg in segments:
            seg_dict = {
                'segment_id': seg.segment_id,
                'axis_name': seg.axis_name,
                'segment_name': seg.segment_name,
                'cluster_center': seg.cluster_center.tolist(),  # Convert numpy to list
                'feature_names': seg.feature_names,
                'scaler_params': seg.scaler_params,
                'population_percentage': seg.population_percentage,
                'customer_count': seg.customer_count,
                'interpretation': seg.interpretation
            }
            segments_export[axis_name].append(seg_dict)

    total_segments = sum(len(s) for s in segments_export.values())
    logger.info(f"✅ Discovered {total_segments} segments across {len(segments_export)} axes")

    for axis, segs in segments_export.items():
        logger.info(f"  {axis}: {len(segs)} segments")

    return segments_export


async def load_all_customer_data() -> pd.DataFrame:
    """Load all customer line items from combined_sales"""
    logger.info("=" * 80)
    logger.info("PHASE 2: LOAD CUSTOMER DATA")
    logger.info("=" * 80)

    import asyncpg

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")

    conn = await asyncpg.connect(db_url)

    try:
        logger.info("Loading all line items from combined_sales...")

        rows = await conn.fetch("""
            SELECT
                customer_id,
                order_id,
                order_date,
                order_total,
                line_item_sales,
                line_item_discount,
                line_item_refunds,
                quantity,
                category,
                product_type,
                product_id
            FROM combined_sales
            WHERE customer_id IS NOT NULL
            ORDER BY customer_id, order_date
        """)

        logger.info(f"✅ Loaded {len(rows):,} line items")

        # Convert to DataFrame
        df = pd.DataFrame([dict(r) for r in rows])
        df['order_date'] = pd.to_datetime(df['order_date'])

        num_customers = df['customer_id'].nunique()
        logger.info(f"✅ Found {num_customers:,} unique customers")

        return df

    finally:
        await conn.close()


def extract_customer_features(customer_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Extract behavioral features for one customer"""

    # Group by order
    orders = customer_df.groupby('order_id').agg({
        'order_date': 'first',
        'order_total': 'first',
        'line_item_sales': 'sum',
        'line_item_discount': 'sum',
        'line_item_refunds': 'sum',
        'quantity': 'sum'
    }).reset_index().sort_values('order_date')

    first_date = orders['order_date'].min()
    last_date = orders['order_date'].max()
    days_active = max((last_date - first_date).days, 1)
    days_since_last = (datetime.now() - last_date).days

    num_orders = len(orders)
    total_sales = orders['line_item_sales'].sum()
    total_discount = orders['line_item_discount'].sum()
    total_refunds = orders['line_item_refunds'].sum() if orders['line_item_refunds'].notna().any() else 0

    avg_order_value = total_sales / num_orders if num_orders > 0 else 0

    features = {}

    # Purchase frequency
    features['purchase_frequency'] = {
        'num_orders': float(num_orders),
        'days_active': float(days_active),
        'orders_per_month': float(num_orders / max(days_active / 30, 1)),
        'days_since_last_order': float(days_since_last)
    }

    # Purchase value
    features['purchase_value'] = {
        'total_sales': float(total_sales),
        'avg_order_value': float(avg_order_value),
        'max_order_value': float(orders['line_item_sales'].max()),
        'lifetime_value': float(total_sales)
    }

    # Price sensitivity
    features['price_sensitivity'] = {
        'total_discount': float(total_discount),
        'discount_rate': float(total_discount / total_sales if total_sales > 0 else 0),
        'orders_with_discount': float(sum(orders['line_item_discount'] > 0))
    }

    # Category exploration
    features['category_exploration'] = {
        'unique_categories': float(customer_df['category'].nunique()),
        'unique_product_types': float(customer_df['product_type'].nunique()),
        'unique_products': float(customer_df['product_id'].nunique()),
        'category_diversity': float(customer_df['category'].nunique() / max(num_orders, 1))
    }

    # Repurchase behavior
    total_items = len(customer_df)
    unique_skus = customer_df['product_id'].nunique()
    features['repurchase_behavior'] = {
        'total_items': float(total_items),
        'unique_skus': float(unique_skus),
        'repeat_purchase_rate': float(1 - (unique_skus / total_items) if total_items > 0 else 0),
        'avg_items_per_order': float(total_items / num_orders if num_orders > 0 else 0)
    }

    # Return behavior
    features['return_behavior'] = {
        'total_refunds': float(abs(total_refunds)),
        'return_rate': float(abs(total_refunds) / total_sales if total_sales > 0 else 0),
        'orders_with_returns': float(sum(orders['line_item_refunds'].fillna(0) > 0))
    }

    # Purchase cadence
    if num_orders > 1:
        order_gaps = orders['order_date'].diff().dt.days.dropna()
        avg_gap = order_gaps.mean() if len(order_gaps) > 0 else days_active
        std_gap = order_gaps.std() if len(order_gaps) > 1 else 0
    else:
        avg_gap = days_active
        std_gap = 0

    features['purchase_cadence'] = {
        'avg_days_between_orders': float(avg_gap),
        'std_days_between_orders': float(std_gap),
        'purchase_regularity': float(1 / (std_gap + 1))
    }

    # Customer maturity
    features['customer_maturity'] = {
        'days_since_first_order': float(days_active),
        'total_orders': float(num_orders),
        'orders_per_year': float(num_orders / max(days_active / 365, 0.1))
    }

    # Loyalty trajectory
    if num_orders >= 4:
        mid_point = num_orders // 2
        early_orders = orders.iloc[:mid_point]
        recent_orders = orders.iloc[mid_point:]

        early_days = (early_orders['order_date'].max() - early_orders['order_date'].min()).days
        recent_days = (recent_orders['order_date'].max() - recent_orders['order_date'].min()).days

        early_freq = len(early_orders) / max(early_days / 30, 1)
        recent_freq = len(recent_orders) / max(recent_days / 30, 1)

        freq_trend = recent_freq - early_freq
    else:
        freq_trend = 0

    features['loyalty_trajectory'] = {
        'frequency_trend': float(freq_trend),
        'days_since_last_order': float(days_since_last),
        'lifetime_value': float(total_sales)
    }

    return features


def calculate_fuzzy_membership(customer_features: Dict[str, float], segments: List[Dict]) -> Dict[str, float]:
    """Calculate fuzzy membership scores using inverse distance weighting"""

    if not segments:
        return {}

    feature_names = segments[0]['feature_names']
    customer_vector = np.array([customer_features.get(fname, 0.0) for fname in feature_names])
    customer_vector = np.nan_to_num(customer_vector, nan=0.0, posinf=1e10, neginf=-1e10)

    # Scale using population scaler
    scaler_params = segments[0]['scaler_params']
    scaler_type = scaler_params.get('type', 'standard')

    if scaler_type == 'robust':
        center = np.array(scaler_params['center'])
        scale = np.array(scaler_params['scale'])
        customer_vector_scaled = (customer_vector - center) / np.maximum(scale, 1e-10)
    else:
        mean = np.array(scaler_params.get('mean', scaler_params.get('center', [])))
        scale = np.array(scaler_params['scale'])
        customer_vector_scaled = (customer_vector - mean) / np.maximum(scale, 1e-10)

    # Calculate distances
    distances = []
    for segment in segments:
        center_scaled = np.array(segment['cluster_center'])
        dist = np.linalg.norm(customer_vector_scaled - center_scaled)
        distances.append(dist)

    # Convert to similarities (exponential decay)
    distances = np.array(distances)
    similarities = np.exp(-distances)

    # Normalize
    total = np.sum(similarities)
    memberships = similarities / total if total > 0 else np.ones(len(segments)) / len(segments)

    return {segments[i]['segment_name']: float(memberships[i]) for i in range(len(segments))}


async def main():
    """Complete end-to-end execution"""

    logger.info("=" * 80)
    logger.info("COMPLETE L1/L2/L3 ARCHETYPE GENERATION")
    logger.info("=" * 80)

    store_id = "linda_quilting"

    # Phase 1: Discover segments from 4K sample
    discovered_segments = await run_clustering_and_export_segments(store_id, max_customers=4000)

    # Save segments to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    segments_file = f"/tmp/discovered_segments_{timestamp}.json"
    with open(segments_file, 'w') as f:
        json.dump(discovered_segments, f, indent=2)
    logger.info(f"✅ Saved segments to: {segments_file}")

    # Phase 2: Load all customer data
    all_data = await load_all_customer_data()

    # Phase 3: Score all customers
    logger.info("=" * 80)
    logger.info("PHASE 3: SCORE ALL CUSTOMERS")
    logger.info("=" * 80)

    all_customer_ids = all_data['customer_id'].unique()
    total_customers = len(all_customer_ids)

    logger.info(f"Scoring {total_customers:,} customers against discovered segments...")

    all_fuzzy_memberships = {}

    for idx, customer_id in enumerate(all_customer_ids):
        customer_data = all_data[all_data['customer_id'] == customer_id]

        # Extract features
        try:
            features = extract_customer_features(customer_data)
        except Exception as e:
            logger.warning(f"Failed to extract features for customer {customer_id}: {e}")
            continue

        # Score against all axes
        fuzzy_memberships = {}
        for axis_name, segments in discovered_segments.items():
            if axis_name in features:
                memberships = calculate_fuzzy_membership(features[axis_name], segments)
                fuzzy_memberships[axis_name] = memberships

        all_fuzzy_memberships[str(customer_id)] = fuzzy_memberships

        # Progress logging
        if (idx + 1) % 1000 == 0 or (idx + 1) == total_customers:
            pct = ((idx + 1) / total_customers) * 100
            logger.info(f"  Progress: {idx + 1:,}/{total_customers:,} ({pct:.1f}%)")

    logger.info(f"✅ Scored {len(all_fuzzy_memberships):,} customers")

    # Phase 4: Generate L1/L2/L3 archetypes
    logger.info("=" * 80)
    logger.info("PHASE 4: GENERATE L1/L2/L3 ARCHETYPES")
    logger.info("=" * 80)

    from scripts.score_all_customers import generate_l1_archetype, generate_l2_archetype, generate_l3_archetype, generate_archetype_id

    all_archetypes = {}
    archetype_stats = {'L1': defaultdict(int), 'L2': defaultdict(int), 'L3': defaultdict(int)}

    for customer_id, fuzzy_memberships in all_fuzzy_memberships.items():
        l1_profile = generate_l1_archetype(fuzzy_memberships)
        l2_profile = generate_l2_archetype(fuzzy_memberships, threshold=0.10)
        l3_profile = generate_l3_archetype(fuzzy_memberships)

        l1_id = generate_archetype_id('L1', l1_profile)
        l2_id = generate_archetype_id('L2', l2_profile)
        l3_id = generate_archetype_id('L3', l3_profile)

        all_archetypes[customer_id] = {
            'archetype_l1_id': l1_id,
            'archetype_l2_id': l2_id,
            'archetype_l3_id': l3_id,
            'l1_profile': l1_profile,
            'l2_profile': l2_profile,
            'l3_profile': l3_profile
        }

        archetype_stats['L1'][l1_id] += 1
        archetype_stats['L2'][l2_id] += 1
        archetype_stats['L3'][l3_id] += 1

    logger.info(f"✅ Generated archetypes for {len(all_archetypes):,} customers")
    logger.info(f"  L1 unique archetypes: {len(archetype_stats['L1']):,}")
    logger.info(f"  L2 unique archetypes: {len(archetype_stats['L2']):,}")
    logger.info(f"  L3 unique archetypes: {len(archetype_stats['L3']):,}")

    # Phase 5: Save results
    logger.info("=" * 80)
    logger.info("PHASE 5: SAVE RESULTS")
    logger.info("=" * 80)

    output_file = f"/tmp/archetypes_l1_l2_l3_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(all_archetypes, f, indent=2)

    logger.info(f"✅ Saved archetypes to: {output_file}")
    logger.info(f"  File size: {os.path.getsize(output_file) / 1024 / 1024:.1f} MB")
    logger.info("=" * 80)
    logger.info("COMPLETE!")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
