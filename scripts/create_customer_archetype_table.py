#!/usr/bin/env python3
"""
Create platform.customer_archetypes table to store ALL customer archetype assignments

This table stores archetype assignments for all customers, not just those in fact_customer_current.
It serves as the source of truth for customer-to-archetype mappings.
"""

import asyncio
import asyncpg
import json
import logging
import sys
import os
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_customer_archetype_table(conn: asyncpg.Connection):
    """Create the platform.customer_archetypes table"""
    logger.info("=" * 80)
    logger.info("CREATING platform.customer_archetypes TABLE")
    logger.info("=" * 80)

    # Drop existing table
    logger.info("Dropping existing table if it exists...")
    await conn.execute("DROP TABLE IF EXISTS platform.customer_archetypes CASCADE")

    # Create new table
    logger.info("Creating platform.customer_archetypes...")
    await conn.execute("""
        CREATE TABLE platform.customer_archetypes (
            customer_id VARCHAR(255) PRIMARY KEY,
            store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
            archetype_l1_id VARCHAR(50) NOT NULL,
            archetype_l2_id VARCHAR(50) NOT NULL,
            archetype_l3_id VARCHAR(50) NOT NULL,
            assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            tenant_id UUID,

            -- Foreign keys to dimension tables
            CONSTRAINT fk_customer_archetype_l1
                FOREIGN KEY (archetype_l1_id)
                REFERENCES platform.dim_archetype_l1(archetype_id),

            CONSTRAINT fk_customer_archetype_l2
                FOREIGN KEY (archetype_l2_id)
                REFERENCES platform.dim_archetype_l2(archetype_id),

            CONSTRAINT fk_customer_archetype_l3
                FOREIGN KEY (archetype_l3_id)
                REFERENCES platform.dim_archetype_l3(archetype_id)
        )
    """)

    # Create indexes
    logger.info("Creating indexes...")
    await conn.execute("CREATE INDEX idx_customer_archetypes_l1 ON platform.customer_archetypes(archetype_l1_id)")
    await conn.execute("CREATE INDEX idx_customer_archetypes_l2 ON platform.customer_archetypes(archetype_l2_id)")
    await conn.execute("CREATE INDEX idx_customer_archetypes_l3 ON platform.customer_archetypes(archetype_l3_id)")
    await conn.execute("CREATE INDEX idx_customer_archetypes_store ON platform.customer_archetypes(store_id)")

    logger.info("✅ Table created successfully")


async def load_customer_archetypes(conn: asyncpg.Connection, archetype_file: str):
    """Load all customer archetype assignments from JSON"""
    logger.info("=" * 80)
    logger.info("LOADING CUSTOMER ARCHETYPE ASSIGNMENTS")
    logger.info("=" * 80)

    # Load JSON
    logger.info(f"Loading {archetype_file}...")
    with open(archetype_file, 'r') as f:
        archetype_data = json.load(f)

    logger.info(f"✅ Loaded {len(archetype_data):,} customer archetypes")

    # Prepare records
    logger.info("Preparing records for insertion...")
    records = []
    for customer_id, customer in archetype_data.items():
        records.append((
            str(customer_id),  # customer_id
            'linda_quilting',  # store_id
            customer['archetype_l1_id'],
            customer['archetype_l2_id'],
            customer['archetype_l3_id'],
            datetime.now(),  # assigned_at
            datetime.now(),  # updated_at
            None  # tenant_id
        ))

    logger.info(f"Prepared {len(records):,} records")

    # Insert in batches
    logger.info("Inserting records...")
    batch_size = 5000
    inserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]

        await conn.executemany("""
            INSERT INTO platform.customer_archetypes (
                customer_id, store_id, archetype_l1_id, archetype_l2_id, archetype_l3_id,
                assigned_at, updated_at, tenant_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, batch)

        inserted += len(batch)

        if inserted % 10000 == 0:
            logger.info(f"  Progress: {inserted:,}/{len(records):,} ({inserted/len(records)*100:.1f}%)")

    logger.info(f"✅ Inserted {inserted:,} customer archetype assignments")


async def verify_customer_archetypes(conn: asyncpg.Connection):
    """Verify the customer archetype table"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("VERIFICATION")
    logger.info("=" * 80)

    # Count total
    total = await conn.fetchval("SELECT COUNT(*) FROM platform.customer_archetypes")
    logger.info(f"\nTotal customer archetype assignments: {total:,}")

    # Count by archetype level
    stats = await conn.fetchrow("""
        SELECT
            COUNT(DISTINCT archetype_l1_id) as unique_l1,
            COUNT(DISTINCT archetype_l2_id) as unique_l2,
            COUNT(DISTINCT archetype_l3_id) as unique_l3
        FROM platform.customer_archetypes
    """)

    logger.info(f"\nUnique archetypes in use:")
    logger.info(f"  L1: {stats['unique_l1']:,}")
    logger.info(f"  L2: {stats['unique_l2']:,}")
    logger.info(f"  L3: {stats['unique_l3']:,}")

    # Top L1 archetypes
    logger.info(f"\nTop 5 L1 archetypes:")
    top = await conn.fetch("""
        SELECT
            ca.archetype_l1_id,
            COUNT(*) as customer_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
            d.avg_lifetime_value
        FROM platform.customer_archetypes ca
        JOIN platform.dim_archetype_l1 d ON ca.archetype_l1_id = d.archetype_id
        GROUP BY ca.archetype_l1_id, d.avg_lifetime_value
        ORDER BY customer_count DESC
        LIMIT 5
    """)

    for i, row in enumerate(top, 1):
        ltv = f"${row['avg_lifetime_value']:.2f}" if row['avg_lifetime_value'] else "N/A"
        logger.info(f"  {i}. {row['archetype_l1_id']}: {row['customer_count']:,} customers ({row['percentage']}%), Avg LTV: {ltv}")

    # Test join with fact table
    logger.info(f"\nJoin test with fact_customer_current:")
    join_test = await conn.fetchrow("""
        SELECT
            COUNT(*) as matched_customers,
            COUNT(DISTINCT f.customer_id) as fact_customers
        FROM platform.customer_archetypes ca
        INNER JOIN public.fact_customer_current f ON ca.customer_id = f.customer_id
    """)

    logger.info(f"  Matched customers: {join_test['matched_customers']:,}")
    logger.info(f"  Fact table customers: {join_test['fact_customers']:,}")

    # Sample customer with full details
    logger.info(f"\nSample customer with full archetype details:")
    sample = await conn.fetchrow("""
        SELECT
            ca.customer_id,
            ca.archetype_l1_id,
            l1.member_count as l1_members,
            l1.behavioral_traits as l1_traits,
            ca.archetype_l2_id,
            l2.member_count as l2_members,
            ca.archetype_l3_id,
            l3.member_count as l3_members,
            f.lifetime_value,
            f.total_orders
        FROM platform.customer_archetypes ca
        LEFT JOIN platform.dim_archetype_l1 l1 ON ca.archetype_l1_id = l1.archetype_id
        LEFT JOIN platform.dim_archetype_l2 l2 ON ca.archetype_l2_id = l2.archetype_id
        LEFT JOIN platform.dim_archetype_l3 l3 ON ca.archetype_l3_id = l3.archetype_id
        LEFT JOIN public.fact_customer_current f ON ca.customer_id = f.customer_id
        ORDER BY RANDOM()
        LIMIT 1
    """)

    if sample:
        logger.info(f"  Customer: {sample['customer_id']}")
        logger.info(f"  L1: {sample['archetype_l1_id']} ({sample['l1_members']:,} members)")
        logger.info(f"  L2: {sample['archetype_l2_id']} ({sample['l2_members']:,} members)")
        logger.info(f"  L3: {sample['archetype_l3_id']} ({sample['l3_members']:,} members)")
        if sample['lifetime_value']:
            logger.info(f"  LTV: ${sample['lifetime_value']:.2f}, Orders: {sample['total_orders']}")
        else:
            logger.info(f"  (Not in fact table - no purchase history)")


async def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python3 create_customer_archetype_table.py <archetype_json_file>")
        print("Example: python3 create_customer_archetype_table.py /tmp/archetypes_l1_l2_l3_20260102_123550.json")
        sys.exit(1)

    archetype_file = sys.argv[1]

    logger.info("=" * 80)
    logger.info("CUSTOMER ARCHETYPE TABLE CREATOR")
    logger.info("=" * 80)
    logger.info(f"Archetype file: {archetype_file}")
    logger.info("")

    # Connect to database
    logger.info("Connecting to database...")
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)

    try:
        # Create table
        await create_customer_archetype_table(conn)

        # Load data
        await load_customer_archetypes(conn, archetype_file)

        # Verify
        await verify_customer_archetypes(conn)

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ COMPLETE! All customer archetype assignments loaded.")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Table: platform.customer_archetypes")
        logger.info("Purpose: Store archetype assignments for ALL customers")
        logger.info("Usage: Join with fact_customer_current or use standalone for segmentation")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
