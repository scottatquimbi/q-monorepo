#!/usr/bin/env python3
"""
Test script to verify hierarchical clustering integration
"""

import os
import sys
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variables
os.environ["ENABLE_HIERARCHICAL_CLUSTERING"] = "true"
os.environ["CLUSTERING_ROBUST_SCALING"] = "true"
os.environ["ENABLE_FUZZY_CMEANS"] = "false"

async def test_hierarchical_clustering():
    """Test hierarchical clustering integration"""
    logger.info("=" * 80)
    logger.info("HIERARCHICAL CLUSTERING INTEGRATION TEST")
    logger.info("=" * 80)

    # Import engine
    from backend.segmentation.ecommerce_clustering_engine import EcommerceClusteringEngine

    # Create engine
    logger.info("Initializing clustering engine with hierarchical subdivision...")
    engine = EcommerceClusteringEngine(
        min_k=2,
        max_k=5,
        use_ai_naming=False  # Faster testing
    )

    # Check that hierarchical is enabled
    if not engine.enable_hierarchical:
        logger.error("❌ Hierarchical clustering NOT enabled!")
        return False

    if not engine.hierarchical_engine:
        logger.error("❌ Hierarchical engine NOT initialized!")
        return False

    logger.info("✅ Hierarchical clustering properly initialized")
    logger.info(f"   - Max intra variance: {engine.hierarchical_engine.max_intra_variance}")
    logger.info(f"   - Max segment %: {engine.hierarchical_engine.max_segment_pct}%")
    logger.info(f"   - Max depth: {engine.hierarchical_engine.max_depth}")

    # Run discovery on single axis (faster)
    logger.info("\nRunning segmentation on purchase_frequency axis...")
    try:
        segments = await engine.discover_multi_axis_segments(
            store_id="linda_quilting",
            axes_to_cluster=["purchase_frequency"],
            max_customers=1000  # Small sample for speed
        )

        if "purchase_frequency" in segments:
            axis_segments = segments["purchase_frequency"]
            logger.info(f"\n✅ Successfully discovered {len(axis_segments)} segments")

            for seg in axis_segments:
                logger.info(f"   - {seg.segment_name}: {seg.customer_count} customers ({seg.population_percentage*100:.1f}%)")

            return True
        else:
            logger.warning("⚠️  No segments discovered for purchase_frequency")
            return False

    except Exception as e:
        logger.error(f"❌ Error during segmentation: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_hierarchical_clustering())
    sys.exit(0 if success else 1)
