#!/usr/bin/env python3
"""
Finalize archetype integration by:
1. Cleaning up orphaned archetype IDs from old system
2. Re-enabling foreign key constraints
3. Verifying complete integration
"""

import asyncio
import asyncpg
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def cleanup_orphaned_archetypes(conn: asyncpg.Connection):
    """Remove archetype IDs that don't exist in dimension tables"""
    logger.info("=" * 80)
    logger.info("CLEANING UP ORPHANED ARCHETYPE IDS")
    logger.info("=" * 80)

    # Find orphaned L1 archetypes
    l1_orphans = await conn.fetch("""
        SELECT archetype_l1_id, COUNT(*) as customer_count
        FROM public.fact_customer_current
        WHERE archetype_l1_id IS NOT NULL
          AND archetype_l1_id NOT IN (SELECT archetype_id FROM platform.dim_archetype_l1)
        GROUP BY archetype_l1_id
    """)

    if l1_orphans:
        logger.info(f"Found {len(l1_orphans)} orphaned L1 archetype IDs (from old system):")
        total_affected = 0
        for row in l1_orphans:
            logger.info(f"  - {row['archetype_l1_id']}: {row['customer_count']:,} customers")
            total_affected += row['customer_count']

        logger.info(f"\nNulling out {total_affected:,} customer records with orphaned L1 IDs...")

        await conn.execute("""
            UPDATE public.fact_customer_current
            SET archetype_l1_id = NULL,
                archetype_l2_id = NULL,
                archetype_l3_id = NULL
            WHERE archetype_l1_id NOT IN (SELECT archetype_id FROM platform.dim_archetype_l1)
        """)

        logger.info(f"✅ Cleaned up orphaned archetypes")
    else:
        logger.info("✅ No orphaned L1 archetypes found")

    # Check L2 orphans
    l2_orphans = await conn.fetchval("""
        SELECT COUNT(DISTINCT archetype_l2_id)
        FROM public.fact_customer_current
        WHERE archetype_l2_id IS NOT NULL
          AND archetype_l2_id NOT IN (SELECT archetype_id FROM platform.dim_archetype_l2)
    """)

    if l2_orphans > 0:
        logger.info(f"\nFound {l2_orphans} orphaned L2 archetype IDs")
        await conn.execute("""
            UPDATE public.fact_customer_current
            SET archetype_l2_id = NULL,
                archetype_l3_id = NULL
            WHERE archetype_l2_id NOT IN (SELECT archetype_id FROM platform.dim_archetype_l2)
        """)
        logger.info(f"✅ Cleaned up orphaned L2 archetypes")

    # Check L3 orphans
    l3_orphans = await conn.fetchval("""
        SELECT COUNT(DISTINCT archetype_l3_id)
        FROM public.fact_customer_current
        WHERE archetype_l3_id IS NOT NULL
          AND archetype_l3_id NOT IN (SELECT archetype_id FROM platform.dim_archetype_l3)
    """)

    if l3_orphans > 0:
        logger.info(f"\nFound {l3_orphans} orphaned L3 archetype IDs")
        await conn.execute("""
            UPDATE public.fact_customer_current
            SET archetype_l3_id = NULL
            WHERE archetype_l3_id NOT IN (SELECT archetype_id FROM platform.dim_archetype_l3)
        """)
        logger.info(f"✅ Cleaned up orphaned L3 archetypes")


async def reenable_foreign_keys(conn: asyncpg.Connection):
    """Re-enable foreign key constraints"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("RE-ENABLING FOREIGN KEY CONSTRAINTS")
    logger.info("=" * 80)

    # L1
    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        DROP CONSTRAINT IF EXISTS fact_customer_current_archetype_l1_id_fkey
    """)

    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        ADD CONSTRAINT fact_customer_current_archetype_l1_id_fkey
        FOREIGN KEY (archetype_l1_id) REFERENCES platform.dim_archetype_l1(archetype_id)
    """)
    logger.info("✅ L1 foreign key constraint enabled")

    # L2
    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        DROP CONSTRAINT IF EXISTS fact_customer_current_archetype_l2_id_fkey
    """)

    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        ADD CONSTRAINT fact_customer_current_archetype_l2_id_fkey
        FOREIGN KEY (archetype_l2_id) REFERENCES platform.dim_archetype_l2(archetype_id)
    """)
    logger.info("✅ L2 foreign key constraint enabled")

    # L3
    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        DROP CONSTRAINT IF EXISTS fact_customer_current_archetype_l3_id_fkey
    """)

    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        ADD CONSTRAINT fact_customer_current_archetype_l3_id_fkey
        FOREIGN KEY (archetype_l3_id) REFERENCES platform.dim_archetype_l3(archetype_id)
    """)
    logger.info("✅ L3 foreign key constraint enabled")


async def verify_integration(conn: asyncpg.Connection):
    """Verify complete integration"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("VERIFICATION")
    logger.info("=" * 80)

    # Dimension table counts
    l1_dim_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l1")
    l2_dim_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l2")
    l3_dim_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l3")

    logger.info(f"\nDimension tables:")
    logger.info(f"  platform.dim_archetype_l1: {l1_dim_count:,} archetypes")
    logger.info(f"  platform.dim_archetype_l2: {l2_dim_count:,} archetypes")
    logger.info(f"  platform.dim_archetype_l3: {l3_dim_count:,} archetypes")

    # Fact table coverage
    fact_stats = await conn.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(archetype_l1_id) as with_l1,
            COUNT(archetype_l2_id) as with_l2,
            COUNT(archetype_l3_id) as with_l3
        FROM public.fact_customer_current
    """)

    logger.info(f"\nFact table coverage:")
    logger.info(f"  Total customers: {fact_stats['total']:,}")
    logger.info(f"  With L1: {fact_stats['with_l1']:,} ({fact_stats['with_l1']/fact_stats['total']*100:.1f}%)")
    logger.info(f"  With L2: {fact_stats['with_l2']:,} ({fact_stats['with_l2']/fact_stats['total']*100:.1f}%)")
    logger.info(f"  With L3: {fact_stats['with_l3']:,} ({fact_stats['with_l3']/fact_stats['total']*100:.1f}%)")

    # Top archetypes
    logger.info(f"\nTop 5 L1 archetypes by member count:")
    top_archetypes = await conn.fetch("""
        SELECT
            archetype_id,
            member_count,
            population_percentage,
            avg_lifetime_value
        FROM platform.dim_archetype_l1
        ORDER BY member_count DESC
        LIMIT 5
    """)

    for i, row in enumerate(top_archetypes, 1):
        ltv = f"${row['avg_lifetime_value']:.2f}" if row['avg_lifetime_value'] else "N/A"
        logger.info(f"  {i}. {row['archetype_id']}: {row['member_count']:,} customers ({row['population_percentage']:.2f}%), Avg LTV: {ltv}")

    # Test a join query
    logger.info(f"\nTest query - joining fact and dimension tables:")
    test_query = await conn.fetchrow("""
        SELECT
            f.customer_id,
            f.archetype_l1_id,
            d.member_count,
            d.behavioral_traits
        FROM public.fact_customer_current f
        JOIN platform.dim_archetype_l1 d ON f.archetype_l1_id = d.archetype_id
        WHERE f.archetype_l1_id IS NOT NULL
        LIMIT 1
    """)

    if test_query:
        logger.info(f"  ✅ Join successful!")
        logger.info(f"  Sample: Customer {test_query['customer_id']} -> {test_query['archetype_l1_id']}")
        logger.info(f"  Archetype has {test_query['member_count']:,} members")
        logger.info(f"  Behavioral traits: {test_query['behavioral_traits'][:3]}...")

    # Check foreign keys exist
    fk_check = await conn.fetch("""
        SELECT
            conname AS constraint_name,
            conrelid::regclass AS table_name
        FROM pg_constraint
        WHERE contype = 'f'
          AND conrelid = 'public.fact_customer_current'::regclass
          AND conname LIKE '%archetype%'
        ORDER BY conname
    """)

    logger.info(f"\nForeign key constraints:")
    for row in fk_check:
        logger.info(f"  ✅ {row['constraint_name']}")


async def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("ARCHETYPE INTEGRATION FINALIZER")
    logger.info("=" * 80)
    logger.info("")

    # Connect to database
    logger.info("Connecting to database...")
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)

    try:
        # Cleanup orphaned archetypes
        await cleanup_orphaned_archetypes(conn)

        # Re-enable foreign keys
        await reenable_foreign_keys(conn)

        # Verify
        await verify_integration(conn)

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ ARCHETYPE INTEGRATION COMPLETE!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("The hierarchical L1/L2/L3 archetype system is now fully integrated:")
        logger.info("  - Dimension tables populated with archetype metadata")
        logger.info("  - Fact table updated with archetype assignments")
        logger.info("  - Foreign key constraints enabled for referential integrity")
        logger.info("  - Ready for production use!")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
