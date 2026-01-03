"""
Load L1/L2/L3 archetypes to production database.

This script:
1. Loads archetype data from JSON file
2. Updates fact_customer_current with archetype IDs
3. Populates dim_archetype_l1/l2/l3 dimension tables
"""

import asyncio
import asyncpg
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Set

# Setup logging
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


async def collect_unique_archetypes(archetype_data: Dict) -> Dict[str, Set[str]]:
    """Collect unique archetype IDs and profiles for dimension tables."""
    logger.info("Collecting unique L1/L2/L3 archetypes...")

    l1_archetypes = {}  # arch_id -> profile
    l2_archetypes = {}
    l3_archetypes = {}

    for customer_id, customer in archetype_data.items():
        # L1
        l1_id = customer['archetype_l1_id']
        if l1_id not in l1_archetypes:
            l1_archetypes[l1_id] = customer['l1_profile']

        # L2
        l2_id = customer['archetype_l2_id']
        if l2_id not in l2_archetypes:
            l2_archetypes[l2_id] = customer['l2_profile']

        # L3
        l3_id = customer['archetype_l3_id']
        if l3_id not in l3_archetypes:
            l3_archetypes[l3_id] = customer['l3_profile']

    logger.info(f"  L1: {len(l1_archetypes):,} unique archetypes")
    logger.info(f"  L2: {len(l2_archetypes):,} unique archetypes")
    logger.info(f"  L3: {len(l3_archetypes):,} unique archetypes")

    return {
        'l1': l1_archetypes,
        'l2': l2_archetypes,
        'l3': l3_archetypes
    }


async def populate_dimension_tables(conn: asyncpg.Connection, unique_archetypes: Dict):
    """Populate dim_archetype_l1/l2/l3 dimension tables."""
    logger.info("=" * 80)
    logger.info("POPULATING DIMENSION TABLES")
    logger.info("=" * 80)

    # L1 Dimension - Use UPSERT to avoid conflicts
    logger.info("Populating dim_archetype_l1...")

    l1_records = []
    for arch_id, profile in unique_archetypes['l1'].items():
        profile_json = json.dumps(profile)
        l1_records.append((arch_id, profile_json))

    await conn.executemany(
        """
        INSERT INTO platform.dim_archetype_l1 (archetype_id, profile)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (archetype_id) DO UPDATE SET
            profile = EXCLUDED.profile,
            updated_at = NOW()
        """,
        l1_records
    )
    logger.info(f"✅ Upserted {len(l1_records):,} L1 archetypes to platform.dim_archetype_l1")

    # L2 Dimension - Use UPSERT
    logger.info("Populating platform.dim_archetype_l2...")

    l2_records = []
    for arch_id, profile in unique_archetypes['l2'].items():
        profile_json = json.dumps(profile)
        l2_records.append((arch_id, profile_json))

    await conn.executemany(
        """
        INSERT INTO platform.dim_archetype_l2 (archetype_id, profile)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (archetype_id) DO UPDATE SET
            profile = EXCLUDED.profile,
            updated_at = NOW()
        """,
        l2_records
    )
    logger.info(f"✅ Upserted {len(l2_records):,} L2 archetypes to platform.dim_archetype_l2")

    # L3 Dimension - Use UPSERT
    logger.info("Populating platform.dim_archetype_l3...")

    l3_records = []
    for arch_id, profile in unique_archetypes['l3'].items():
        profile_json = json.dumps(profile)
        l3_records.append((arch_id, profile_json))

    await conn.executemany(
        """
        INSERT INTO platform.dim_archetype_l3 (archetype_id, profile)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (archetype_id) DO UPDATE SET
            profile = EXCLUDED.profile,
            updated_at = NOW()
        """,
        l3_records
    )
    logger.info(f"✅ Upserted {len(l3_records):,} L3 archetypes to platform.dim_archetype_l3")


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

    # Debug first record
    logger.info(f"DEBUG: First update record:")
    logger.info(f"  L1 ID: {repr(update_records[0][0])}")
    logger.info(f"  L2 ID: {repr(update_records[0][1])}")
    logger.info(f"  L3 ID: {repr(update_records[0][2])}")
    logger.info(f"  Customer ID: {repr(update_records[0][3])}")

    # Update in batches
    batch_size = 1000
    updated_count = 0

    for i in range(0, len(update_records), batch_size):
        batch = update_records[i:i+batch_size]

        await conn.executemany(
            """
            UPDATE fact_customer_current
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
        FROM fact_customer_current
    """)

    logger.info(f"fact_customer_current:")
    logger.info(f"  Total customers: {result['total']:,}")
    logger.info(f"  With L1 archetype: {result['with_l1']:,} ({result['with_l1']/result['total']*100:.1f}%)")
    logger.info(f"  With L2 archetype: {result['with_l2']:,} ({result['with_l2']/result['total']*100:.1f}%)")
    logger.info(f"  With L3 archetype: {result['with_l3']:,} ({result['with_l3']/result['total']*100:.1f}%)")

    # Check dimension tables
    l1_count = await conn.fetchval("SELECT COUNT(*) FROM dim_archetype_l1")
    l2_count = await conn.fetchval("SELECT COUNT(*) FROM dim_archetype_l2")
    l3_count = await conn.fetchval("SELECT COUNT(*) FROM dim_archetype_l3")

    logger.info(f"dim_archetype_l1: {l1_count:,} archetypes")
    logger.info(f"dim_archetype_l2: {l2_count:,} archetypes")
    logger.info(f"dim_archetype_l3: {l3_count:,} archetypes")

    # Top 10 L1 archetypes
    logger.info("")
    logger.info("Top 10 L1 archetypes in database:")
    top_l1 = await conn.fetch("""
        SELECT
            archetype_l1_id,
            COUNT(*) as customer_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM fact_customer_current
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
        print("Usage: python3 load_archetypes_to_db.py <archetype_json_file>")
        print("Example: python3 load_archetypes_to_db.py /tmp/archetypes_l1_l2_l3_20260102_123550.json")
        sys.exit(1)

    archetype_file = sys.argv[1]

    logger.info("=" * 80)
    logger.info("L1/L2/L3 ARCHETYPE DATABASE LOADER")
    logger.info("=" * 80)
    logger.info(f"Archetype file: {archetype_file}")
    logger.info("")

    # Load archetype data
    archetype_data = await load_archetypes_from_file(archetype_file)

    # Collect unique archetypes
    unique_archetypes = await collect_unique_archetypes(archetype_data)

    # Connect to database
    logger.info("Connecting to database...")
    import os
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)

    try:
        # Step 1: Populate dimension tables (separate transaction)
        async with conn.transaction():
            await populate_dimension_tables(conn, unique_archetypes)

        logger.info("")
        logger.info("✅ Dimension tables transaction committed")
        logger.info("")

        # Verify dimension tables were populated (force a fresh read)
        logger.info("Verifying dimension table population...")
        l1_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l1")
        l2_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l2")
        l3_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l3")
        logger.info(f"  platform.dim_archetype_l1: {l1_count:,} records")
        logger.info(f"  platform.dim_archetype_l2: {l2_count:,} records")
        logger.info(f"  platform.dim_archetype_l3: {l3_count:,} records")

        # Check specific archetype that was failing
        test_arch = await conn.fetchval(
            "SELECT archetype_id FROM platform.dim_archetype_l1 WHERE archetype_id = $1",
            'arch_L1_696466'
        )
        if test_arch:
            logger.info(f"  ✅ Test archetype arch_L1_696466 found in database")
        else:
            logger.error(f"  ❌ Test archetype arch_L1_696466 NOT found - will fail!")

        logger.info("")

        # Close and reopen connection to ensure fresh view of database
        logger.info("Closing and reopening database connection for fact table update...")
        await conn.close()
        conn = await asyncpg.connect(database_url)
        logger.info("✅ Fresh connection established")
        logger.info("")

        # Step 2: Update fact table (NO transaction block - updates are atomic per statement)
        # This ensures we can see the committed dimension table rows
        await update_fact_customer_current(conn, archetype_data)

        logger.info("")
        logger.info("✅ Fact table updates completed")
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
