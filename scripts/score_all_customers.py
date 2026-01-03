#!/usr/bin/env python3
"""
Score All Customers Against Discovered Segments - Works with combined_sales

This script:
1. Loads discovered segments from 4K clustering run
2. Loads customer data from combined_sales table (line-item level)
3. Extracts behavioral features for all 94,686 customers
4. Scores customers against discovered segments using fuzzy membership
5. Generates L1/L2/L3 archetypes
6. Saves results to JSON files

Compatible with combined_sales schema (no orders/order_items tables needed)
"""

import os
import sys
import asyncio
import logging
import json
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, '/Users/scottallen/quimbi-platform')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_customer_data_from_combined_sales() -> pd.DataFrame:
    """Load all customer line items from combined_sales table"""

    logger.info("Loading customer data from combined_sales...")

    import asyncpg

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")

    conn = await asyncpg.connect(db_url)

    try:
        # Load all line items
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
                product_id,
                sales_channel
            FROM combined_sales
            WHERE customer_id IS NOT NULL
            ORDER BY customer_id, order_date
        """)

        logger.info(f"Loaded {len(rows):,} line items from combined_sales")

        # Convert to DataFrame
        df = pd.DataFrame([dict(r) for r in rows])

        # Convert dates
        df['order_date'] = pd.to_datetime(df['order_date'])

        return df

    finally:
        await conn.close()


def extract_customer_features(customer_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Extract behavioral features for a single customer from their line items

    Returns: Dict[axis_name -> Dict[feature_name -> value]]
    """

    # Group by order to get order-level metrics
    orders = customer_df.groupby('order_id').agg({
        'order_date': 'first',
        'order_total': 'first',
        'line_item_sales': 'sum',
        'line_item_discount': 'sum',
        'line_item_refunds': 'sum',
        'quantity': 'sum'
    }).reset_index()

    orders = orders.sort_values('order_date')

    # Calculate date ranges
    first_order_date = orders['order_date'].min()
    last_order_date = orders['order_date'].max()
    days_active = (last_order_date - first_order_date).days
    days_since_last = (datetime.now() - last_order_date).days

    num_orders = len(orders)
    total_sales = orders['line_item_sales'].sum()
    total_discount = orders['line_item_discount'].sum()
    total_refunds = orders['line_item_refunds'].sum() if orders['line_item_refunds'].notna().any() else 0
    total_quantity = orders['quantity'].sum()

    features = {}

    # ==================== PURCHASE FREQUENCY ====================
    features['purchase_frequency'] = {
        'num_orders': float(num_orders),
        'days_active': float(max(days_active, 1)),
        'orders_per_month': float(num_orders / max(days_active / 30, 1)),
        'days_since_last_order': float(days_since_last)
    }

    # ==================== PURCHASE VALUE ====================
    avg_order_value = total_sales / num_orders if num_orders > 0 else 0
    features['purchase_value'] = {
        'total_sales': float(total_sales),
        'avg_order_value': float(avg_order_value),
        'max_order_value': float(orders['line_item_sales'].max()),
        'lifetime_value': float(total_sales)
    }

    # ==================== PRICE SENSITIVITY ====================
    discount_rate = total_discount / total_sales if total_sales > 0 else 0
    features['price_sensitivity'] = {
        'total_discount': float(total_discount),
        'discount_rate': float(discount_rate),
        'orders_with_discount': float(sum(orders['line_item_discount'] > 0))
    }

    # ==================== CATEGORY EXPLORATION ====================
    unique_categories = customer_df['category'].nunique()
    unique_product_types = customer_df['product_type'].nunique()
    unique_products = customer_df['product_id'].nunique()

    features['category_exploration'] = {
        'unique_categories': float(unique_categories),
        'unique_product_types': float(unique_product_types),
        'unique_products': float(unique_products),
        'category_diversity': float(unique_categories / max(num_orders, 1))
    }

    # ==================== REPURCHASE BEHAVIOR ====================
    total_items = len(customer_df)
    unique_skus = customer_df['product_id'].nunique()
    repeat_rate = 1 - (unique_skus / total_items) if total_items > 0 else 0

    features['repurchase_behavior'] = {
        'total_items': float(total_items),
        'unique_skus': float(unique_skus),
        'repeat_purchase_rate': float(repeat_rate),
        'avg_items_per_order': float(total_items / num_orders) if num_orders > 0 else 0
    }

    # ==================== RETURN BEHAVIOR ====================
    return_rate = abs(total_refunds) / total_sales if total_sales > 0 else 0
    orders_with_returns = sum(orders['line_item_refunds'].fillna(0) > 0)

    features['return_behavior'] = {
        'total_refunds': float(abs(total_refunds)),
        'return_rate': float(return_rate),
        'orders_with_returns': float(orders_with_returns)
    }

    # ==================== PURCHASE CADENCE ====================
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
        'purchase_regularity': float(1 / (std_gap + 1))  # Higher = more regular
    }

    # ==================== CUSTOMER MATURITY ====================
    features['customer_maturity'] = {
        'days_since_first_order': float(days_active),
        'total_orders': float(num_orders),
        'orders_per_year': float(num_orders / max(days_active / 365, 0.1))
    }

    # ==================== LOYALTY TRAJECTORY ====================
    # Calculate trend in order frequency (early vs recent)
    if num_orders >= 4:
        mid_point = num_orders // 2
        early_orders = orders.iloc[:mid_point]
        recent_orders = orders.iloc[mid_point:]

        early_days = (early_orders['order_date'].max() - early_orders['order_date'].min()).days
        recent_days = (recent_orders['order_date'].max() - recent_orders['order_date'].min()).days

        early_frequency = len(early_orders) / max(early_days / 30, 1)
        recent_frequency = len(recent_orders) / max(recent_days / 30, 1)

        frequency_trend = recent_frequency - early_frequency
    else:
        frequency_trend = 0

    features['loyalty_trajectory'] = {
        'frequency_trend': float(frequency_trend),
        'days_since_last_order': float(days_since_last),
        'lifetime_value': float(total_sales)
    }

    return features


def calculate_fuzzy_membership(
    customer_features: Dict[str, float],
    segments: List[Dict],
    axis_name: str
) -> Dict[str, float]:
    """
    Calculate fuzzy membership scores for customer against segments in one axis

    Uses inverse distance weighting with exponential decay:
    membership_i = exp(-distance_i) / Σ exp(-distance_j)

    Returns: Dict[segment_name -> membership_score (0-1)]
    """

    if not segments:
        return {}

    # Get feature names from first segment
    feature_names = segments[0]['feature_names']

    # Build customer feature vector
    customer_vector = np.array([customer_features.get(fname, 0.0) for fname in feature_names])
    customer_vector = np.nan_to_num(customer_vector, nan=0.0, posinf=1e10, neginf=-1e10)

    # Scale customer vector using population scaler
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

    # Calculate distances to all segment centers
    distances = []
    for segment in segments:
        center_scaled = np.array(segment['cluster_center'])
        dist = np.linalg.norm(customer_vector_scaled - center_scaled)
        distances.append(dist)

    # Convert distances to similarities (exponential decay)
    distances = np.array(distances)
    similarities = np.exp(-distances)

    # Normalize to sum to 1.0 (probability distribution)
    total = np.sum(similarities)
    if total > 0:
        memberships = similarities / total
    else:
        memberships = np.ones(len(segments)) / len(segments)

    # Return as dict
    return {
        segments[i]['segment_name']: float(memberships[i])
        for i in range(len(segments))
    }


def generate_l1_archetype(fuzzy_memberships: Dict[str, Dict[str, float]]) -> Dict[str, str]:
    """Generate L1 archetype (dominant segment per axis)"""
    l1_profile = {}
    for axis, segments in fuzzy_memberships.items():
        if segments:
            dominant = max(segments.items(), key=lambda x: x[1])
            l1_profile[axis] = dominant[0]
    return l1_profile


def generate_l2_archetype(
    fuzzy_memberships: Dict[str, Dict[str, float]],
    threshold: float = 0.10
) -> Dict[str, Dict[str, float]]:
    """Generate L2 archetype (significant segments ≥ threshold, renormalized)"""
    l2_profile = {}
    for axis, segments in fuzzy_memberships.items():
        if not segments:
            continue

        # Filter significant segments
        significant = {seg: score for seg, score in segments.items() if score >= threshold}

        # If no segments meet threshold, keep dominant only
        if not significant:
            dominant = max(segments.items(), key=lambda x: x[1])
            significant = {dominant[0]: dominant[1]}

        # Renormalize to sum to 1.0
        total = sum(significant.values())
        if total > 0:
            l2_profile[axis] = {seg: score / total for seg, score in significant.items()}
        else:
            # Edge case: All scores are 0 (shouldn't happen, but defensive)
            # Assign equal probability to all significant segments
            uniform_score = 1.0 / len(significant) if significant else 1.0
            l2_profile[axis] = {seg: uniform_score for seg in significant.keys()}

    return l2_profile


def generate_l3_archetype(fuzzy_memberships: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Generate L3 archetype (complete thumbprint)"""
    return fuzzy_memberships


def generate_archetype_id(level: str, archetype_data: Dict) -> str:
    """Generate deterministic archetype ID from profile data"""
    canonical = json.dumps(archetype_data, sort_keys=True)
    hash_obj = hashlib.md5(canonical.encode())
    hash_int = int(hash_obj.hexdigest(), 16) % 1000000
    return f"arch_{level}_{hash_int:06d}"


async def main():
    """Main execution"""

    logger.info("=" * 80)
    logger.info("L1/L2/L3 ARCHETYPE GENERATION - COMBINED_SALES VERSION")
    logger.info("=" * 80)

    # Step 1: Load discovered segments from 4K clustering
    logger.info("Step 1: Loading discovered segments from 4K clustering...")

    # Find most recent comprehensive analysis file
    import glob
    analysis_files = glob.glob("/tmp/comprehensive_analysis_*.json")
    if not analysis_files:
        logger.error("No comprehensive analysis files found in /tmp/")
        logger.error("Please run clustering first: python3 run_comprehensive_analysis.py")
        return

    latest_file = max(analysis_files, key=os.path.getmtime)
    logger.info(f"Loading segments from: {latest_file}")

    # For now, we'll use the segments from the running clustering process
    # The actual segment data with cluster centers is stored in the clustering engine's output
    # We need to wait for the current clustering to finish or use pre-saved segments

    logger.info("")
    logger.info("NEXT: Need discovered segments with cluster centers to continue")
    logger.info("The clustering is discovering segments but we need the full segment data")
    logger.info("(cluster_center, scaler_params, feature_names) to score customers")
    logger.info("")
    logger.info("Recommendation: Let the current 4K clustering finish, then it will save")
    logger.info("the complete segment data that we can use for scoring all customers.")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
