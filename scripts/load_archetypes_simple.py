#!/usr/bin/env python3
"""
Simple L1/L2/L3 Archetype Loader - Just update fact table, no dimension tables

This script:
1. Temporarily drops foreign key constraints
2. Updates fact_customer_current with archetype IDs
3. Re-adds foreign key constraints

Note: This bypasses dimension table population. Use when dimension tables
don't match the expected schema or are managed separately.
"""

import asyncio
import asyncpg
import json
import logging
import sys
from datetime import datetime
from typing import Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_archetypes_from_file(filepath: str) -> Dict:
    """Load archetypes from JSON file."""
    logger.info(f"Loading archetypes from {filepath}")

    with open(filepath, 'r') as f:
        data = json.load(f)

    logger.info(f"✅ Loaded {len(data):,} customer archetypes")
    return data


async def drop_fk_constraints(conn: asyncpg.Connection):
    """Temporarily drop foreign key constraints."""
    logger.info("Dropping foreign key constraints...")

    await conn.execute("ALTER TABLE public.fact_customer_current DROP CONSTRAINT IF EXISTS fact_customer_current_archetype_l1_id_fkey")
    await conn.execute("ALTER TABLE public.fact_customer_current DROP CONSTRAINT IF EXISTS fact_customer_current_archetype_l2_id_fkey")
    await conn.execute("ALTER TABLE public.fact_customer_current DROP CONSTRAINT IF EXISTS fact_customer_current_archetype_l3_id_fkey")

    logger.info("✅ Dropped foreign key constraints")


async def readd_fk_constraints(conn: asyncpg.Connection):
    """Re-add foreign key constraints."""
    logger.info("Re-adding foreign key constraints...")

    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        ADD CONSTRAINT fact_customer_current_archetype_l1_id_fkey
        FOREIGN KEY (archetype_l1_id) REFERENCES platform.dim_archetype_l1(archetype_id)
    """)

    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        ADD CONSTRAINT fact_customer_current_archetype_l2_id_fkey
        FOREIGN KEY (archetype_l2_id) REFERENCES platform.dim_archetype_l2(archetype_id)
    """)

    await conn.execute("""
        ALTER TABLE public.fact_customer_current
        ADD CONSTRAINT fact_customer_current_archetype_l3_id_fkey
        FOREIGN KEY (archetype_l3_id) REFERENCES platform.dim_archetype_l3(archetype_id)
    """)

    logger.info("✅ Re-added foreign key constraints")


async def update_fact_customer_current(conn: asyncpg.Connection, archetype_data: Dict):
    """Update fact_customer_current with archetype IDs."""
    logger.info("=" * 80)
    logger.info("UPDATING fact_customer_current")
    logger.info("=" * 80)

    # Prepare update records
    update_records = []
    for customer_id, customer in archetype_data.items():
        update_records.append((
            customer['archetype_l1_id'],
            customer['archetype_l2_id'],
            customer['archetype_l3_id'],
            str(customer_id)  # Keep as string to match VARCHAR column
        ))

    logger.info(f"Updating {len(update_records):,} customer records...")

    # Update in batches
    batch_size = 1000
    updated_count = 0

    for i in range(0, len(update_records), batch_size):
        batch = update_records[i:i+batch_size]

        await conn.executemany(
            """
            UPDATE public.fact_customer_current
            SET
                archetype_l1_id = $1,
                archetype_l2_id = $2,
                archetype_l3_id = $3
            WHERE customer_id = $4
            """,
            batch
        )

        updated_count += len(batch)

        if updated_count % 10000 == 0:
            logger.info(f"  Progress: {updated_count:,}/{len(update_records):,} ({updated_count/len(update_records)*100:.1f}%)")

    logger.info(f"✅ Updated {updated_count:,} customer records")


async def verify_updates(conn: asyncpg.Connection):
    """Verify database updates were successful."""
    logger.info("=" * 80)
    logger.info("VERIFICATION")
    logger.info("=" * 80)

    # Check fact_customer_current
    result = await conn.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(archetype_l1_id) as with_l1,
            COUNT(archetype_l2_id) as with_l2,
            COUNT(archetype_l3_id) as with_l3
        FROM public.fact_customer_current
    """)

    logger.info(f"fact_customer_current:")
    logger.info(f"  Total customers: {result['total']:,}")
    logger.info(f"  With L1 archetype: {result['with_l1']:,} ({result['with_l1']/result['total']*100:.1f}%)")
    logger.info(f"  With L2 archetype: {result['with_l2']:,} ({result['with_l2']/result['total']*100:.1f}%)")
    logger.info(f"  With L3 archetype: {result['with_l3']:,} ({result['with_l3']/result['total']*100:.1f}%)")

    # Top 10 L1 archetypes
    logger.info("")
    logger.info("Top 10 L1 archetypes in database:")
    top_l1 = await conn.fetch("""
        SELECT
            archetype_l1_id,
            COUNT(*) as customer_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM public.fact_customer_current
        WHERE archetype_l1_id IS NOT NULL
        GROUP BY archetype_l1_id
        ORDER BY customer_count DESC
        LIMIT 10
    """)

    for row in top_l1:
        logger.info(f"  {row['archetype_l1_id']}: {row['customer_count']:,} customers ({row['percentage']}%)")


async def main():
    """Main execution."""
    if len(sys.argv) < 2:
        print("Usage: python3 load_archetypes_simple.py <archetype_json_file>")
        print("Example: python3 load_archetypes_simple.py /tmp/archetypes_l1_l2_l3_20260102_123550.json")
        sys.exit(1)

    archetype_file = sys.argv[1]

    logger.info("=" * 80)
    logger.info("SIMPLE L1/L2/L3 ARCHETYPE DATABASE LOADER")
    logger.info("=" * 80)
    logger.info(f"Archetype file: {archetype_file}")
    logger.info("")

    # Load archetype data
    archetype_data = await load_archetypes_from_file(archetype_file)

    # Connect to database
    logger.info("Connecting to database...")
    import os
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)

    try:
        # Drop FK constraints
        await drop_fk_constraints(conn)

        logger.info("")

        # Update fact table
        await update_fact_customer_current(conn, archetype_data)

        logger.info("")
        logger.info("✅ Fact table updates completed")
        logger.info("")

        # Re-add FK constraints
        await readd_fk_constraints(conn)

        logger.info("")

        # Verify
        await verify_updates(conn)

    except Exception as e:
        logger.error(f"❌ Error during database update: {e}")
        raise
    finally:
        await conn.close()

    logger.info("")
    logger.info("=" * 80)
    logger.info("COMPLETE!")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
