#!/usr/bin/env python3
"""
Create and populate platform.dim_archetype_l1/l2/l3 tables with hierarchical archetype data

This script:
1. Drops and recreates the platform dimension tables
2. Populates them with data from the archetype JSON file
3. Aggregates customer statistics per archetype
4. Re-enables foreign key constraints
"""

import asyncio
import asyncpg
import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_archetype_data(filepath: str) -> Dict:
    """Load archetype data from JSON file"""
    logger.info(f"Loading archetype data from {filepath}")

    with open(filepath, 'r') as f:
        data = json.load(f)

    logger.info(f"✅ Loaded {len(data):,} customer archetypes")
    return data


async def aggregate_archetype_stats(conn: asyncpg.Connection, archetype_data: Dict) -> Tuple[Dict, Dict, Dict]:
    """
    Aggregate statistics for each unique L1/L2/L3 archetype

    Returns: (l1_stats, l2_stats, l3_stats) where each is a dict of:
    {
        archetype_id: {
            'profile': {...},
            'member_count': int,
            'population_percentage': float,
            'avg_lifetime_value': float,
            'avg_order_frequency': float,
            'customer_ids': [...]
        }
    }
    """
    logger.info("Aggregating archetype statistics...")

    l1_stats = defaultdict(lambda: {'customer_ids': [], 'profile': None})
    l2_stats = defaultdict(lambda: {'customer_ids': [], 'profile': None})
    l3_stats = defaultdict(lambda: {'customer_ids': [], 'profile': None})

    # Collect customer IDs per archetype
    for customer_id, customer in archetype_data.items():
        l1_id = customer['archetype_l1_id']
        l2_id = customer['archetype_l2_id']
        l3_id = customer['archetype_l3_id']

        l1_stats[l1_id]['customer_ids'].append(customer_id)
        l1_stats[l1_id]['profile'] = customer['l1_profile']

        l2_stats[l2_id]['customer_ids'].append(customer_id)
        l2_stats[l2_id]['profile'] = customer['l2_profile']

        l3_stats[l3_id]['customer_ids'].append(customer_id)
        l3_stats[l3_id]['profile'] = customer['l3_profile']

    total_customers = len(archetype_data)

    # Get customer business metrics from fact table
    logger.info("Fetching customer business metrics from database...")

    customer_metrics = await conn.fetch("""
        SELECT
            customer_id,
            COALESCE(lifetime_value, 0) as lifetime_value,
            COALESCE(total_orders, 0) as total_orders
        FROM public.fact_customer_current
    """)

    customer_metrics_map = {
        row['customer_id']: {
            'lifetime_value': row['lifetime_value'],
            'total_orders': row['total_orders']
        }
        for row in customer_metrics
    }

    logger.info(f"Loaded metrics for {len(customer_metrics_map):,} customers")

    # Calculate aggregate stats for each archetype
    def calc_stats(archetype_stats):
        for arch_id, data in archetype_stats.items():
            member_count = len(data['customer_ids'])

            # Calculate averages
            total_ltv = 0
            total_orders = 0
            valid_ltv_count = 0
            valid_orders_count = 0

            for customer_id in data['customer_ids']:
                if customer_id in customer_metrics_map:
                    metrics = customer_metrics_map[customer_id]

                    if metrics['lifetime_value'] > 0:
                        total_ltv += metrics['lifetime_value']
                        valid_ltv_count += 1

                    if metrics['total_orders'] > 0:
                        total_orders += metrics['total_orders']
                        valid_orders_count += 1

            data['member_count'] = member_count
            data['population_percentage'] = (member_count / total_customers) * 100
            data['avg_lifetime_value'] = total_ltv / valid_ltv_count if valid_ltv_count > 0 else None
            data['avg_order_frequency'] = total_orders / valid_orders_count if valid_orders_count > 0 else None

    calc_stats(l1_stats)
    calc_stats(l2_stats)
    calc_stats(l3_stats)

    logger.info(f"✅ Aggregated stats for:")
    logger.info(f"   L1: {len(l1_stats):,} archetypes")
    logger.info(f"   L2: {len(l2_stats):,} archetypes")
    logger.info(f"   L3: {len(l3_stats):,} archetypes")

    return dict(l1_stats), dict(l2_stats), dict(l3_stats)


async def recreate_dimension_tables(conn: asyncpg.Connection):
    """Drop and recreate platform dimension tables"""
    logger.info("=" * 80)
    logger.info("RECREATING PLATFORM DIMENSION TABLES")
    logger.info("=" * 80)

    # Drop existing tables
    logger.info("Dropping existing tables...")
    await conn.execute("DROP TABLE IF EXISTS platform.dim_archetype_l1 CASCADE")
    await conn.execute("DROP TABLE IF EXISTS platform.dim_archetype_l2 CASCADE")
    await conn.execute("DROP TABLE IF EXISTS platform.dim_archetype_l3 CASCADE")

    # Create L1 table
    logger.info("Creating platform.dim_archetype_l1...")
    await conn.execute("""
        CREATE TABLE platform.dim_archetype_l1 (
            archetype_id VARCHAR(50) PRIMARY KEY,
            store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
            dominant_segments JSONB NOT NULL,
            description TEXT,
            behavioral_traits TEXT[],
            member_count INTEGER NOT NULL,
            population_percentage DOUBLE PRECISION NOT NULL,
            avg_lifetime_value DOUBLE PRECISION,
            avg_order_frequency DOUBLE PRECISION,
            last_calculated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            tenant_id UUID
        )
    """)

    # Create L2 table
    logger.info("Creating platform.dim_archetype_l2...")
    await conn.execute("""
        CREATE TABLE platform.dim_archetype_l2 (
            archetype_id VARCHAR(50) PRIMARY KEY,
            store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
            dominant_segments JSONB NOT NULL,
            membership_strengths JSONB NOT NULL,
            description TEXT,
            behavioral_traits TEXT[],
            member_count INTEGER NOT NULL,
            population_percentage DOUBLE PRECISION NOT NULL,
            avg_lifetime_value DOUBLE PRECISION,
            avg_order_frequency DOUBLE PRECISION,
            last_calculated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            tenant_id UUID
        )
    """)

    # Create L3 table
    logger.info("Creating platform.dim_archetype_l3...")
    await conn.execute("""
        CREATE TABLE platform.dim_archetype_l3 (
            archetype_id VARCHAR(50) PRIMARY KEY,
            store_id VARCHAR(255) NOT NULL DEFAULT 'linda_quilting',
            fuzzy_memberships JSONB NOT NULL,
            dominant_segments JSONB NOT NULL,
            description TEXT,
            behavioral_traits TEXT[],
            member_count INTEGER NOT NULL,
            population_percentage DOUBLE PRECISION NOT NULL,
            avg_lifetime_value DOUBLE PRECISION,
            avg_order_frequency DOUBLE PRECISION,
            last_calculated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            tenant_id UUID
        )
    """)

    logger.info("✅ Tables created successfully")


async def populate_l1_dimension(conn: asyncpg.Connection, l1_stats: Dict):
    """Populate platform.dim_archetype_l1"""
    logger.info("=" * 80)
    logger.info("POPULATING platform.dim_archetype_l1")
    logger.info("=" * 80)

    records = []
    for arch_id, stats in l1_stats.items():
        # For L1: dominant_segments is the profile (one segment per axis)
        dominant_segments = stats['profile']

        # Create behavioral traits array
        behavioral_traits = [f"{axis}:{segment}" for axis, segment in dominant_segments.items()]

        records.append((
            arch_id,
            'linda_quilting',  # store_id
            json.dumps(dominant_segments),  # dominant_segments
            None,  # description
            behavioral_traits,
            stats['member_count'],
            stats['population_percentage'],
            stats['avg_lifetime_value'],
            stats['avg_order_frequency'],
            datetime.now(),  # last_calculated
            datetime.now(),  # created_at
            datetime.now(),  # updated_at
            None  # tenant_id
        ))

    await conn.executemany("""
        INSERT INTO platform.dim_archetype_l1 (
            archetype_id, store_id, dominant_segments, description, behavioral_traits,
            member_count, population_percentage, avg_lifetime_value, avg_order_frequency,
            last_calculated, created_at, updated_at, tenant_id
        ) VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    """, records)

    logger.info(f"✅ Inserted {len(records):,} L1 archetypes")


async def populate_l2_dimension(conn: asyncpg.Connection, l2_stats: Dict):
    """Populate platform.dim_archetype_l2"""
    logger.info("=" * 80)
    logger.info("POPULATING platform.dim_archetype_l2")
    logger.info("=" * 80)

    records = []
    for arch_id, stats in l2_stats.items():
        profile = stats['profile']

        # For L2: dominant_segments = highest scoring segment per axis
        # membership_strengths = full filtered scores per axis
        dominant_segments = {}
        membership_strengths = {}

        for axis, segments in profile.items():
            if segments:  # If there are any segments for this axis
                # Get dominant (highest score)
                dominant_segment = max(segments.items(), key=lambda x: x[1])[0]
                dominant_segments[axis] = dominant_segment
                # Store all strengths
                membership_strengths[axis] = segments
            else:
                # Empty dict for this axis
                membership_strengths[axis] = {}

        # Create behavioral traits from dominant segments
        behavioral_traits = [f"{axis}:{segment}" for axis, segment in dominant_segments.items()]

        records.append((
            arch_id,
            'linda_quilting',
            json.dumps(dominant_segments),
            json.dumps(membership_strengths),
            None,
            behavioral_traits,
            stats['member_count'],
            stats['population_percentage'],
            stats['avg_lifetime_value'],
            stats['avg_order_frequency'],
            datetime.now(),
            datetime.now(),
            datetime.now(),
            None
        ))

    await conn.executemany("""
        INSERT INTO platform.dim_archetype_l2 (
            archetype_id, store_id, dominant_segments, membership_strengths, description,
            behavioral_traits, member_count, population_percentage, avg_lifetime_value,
            avg_order_frequency, last_calculated, created_at, updated_at, tenant_id
        ) VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
    """, records)

    logger.info(f"✅ Inserted {len(records):,} L2 archetypes")


async def populate_l3_dimension(conn: asyncpg.Connection, l3_stats: Dict):
    """Populate platform.dim_archetype_l3"""
    logger.info("=" * 80)
    logger.info("POPULATING platform.dim_archetype_l3")
    logger.info("=" * 80)

    records = []
    for arch_id, stats in l3_stats.items():
        profile = stats['profile']

        # For L3: fuzzy_memberships = complete profile
        # dominant_segments = highest scoring segment per axis
        fuzzy_memberships = profile
        dominant_segments = {}

        for axis, segments in profile.items():
            if segments:
                dominant_segment = max(segments.items(), key=lambda x: x[1])[0]
                dominant_segments[axis] = dominant_segment

        behavioral_traits = [f"{axis}:{segment}" for axis, segment in dominant_segments.items()]

        records.append((
            arch_id,
            'linda_quilting',
            json.dumps(fuzzy_memberships),
            json.dumps(dominant_segments),
            None,
            behavioral_traits,
            stats['member_count'],
            stats['population_percentage'],
            stats['avg_lifetime_value'],
            stats['avg_order_frequency'],
            datetime.now(),
            datetime.now(),
            datetime.now(),
            None
        ))

    await conn.executemany("""
        INSERT INTO platform.dim_archetype_l3 (
            archetype_id, store_id, fuzzy_memberships, dominant_segments, description,
            behavioral_traits, member_count, population_percentage, avg_lifetime_value,
            avg_order_frequency, last_calculated, created_at, updated_at, tenant_id
        ) VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
    """, records)

    logger.info(f"✅ Inserted {len(records):,} L3 archetypes")


async def reenable_foreign_keys(conn: asyncpg.Connection):
    """Re-enable foreign key constraints"""
    logger.info("=" * 80)
    logger.info("RE-ENABLING FOREIGN KEY CONSTRAINTS")
    logger.info("=" * 80)

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


async def verify_installation(conn: asyncpg.Connection):
    """Verify the dimension tables and foreign keys"""
    logger.info("=" * 80)
    logger.info("VERIFICATION")
    logger.info("=" * 80)

    # Count records
    l1_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l1")
    l2_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l2")
    l3_count = await conn.fetchval("SELECT COUNT(*) FROM platform.dim_archetype_l3")

    logger.info(f"\nDimension table record counts:")
    logger.info(f"  platform.dim_archetype_l1: {l1_count:,}")
    logger.info(f"  platform.dim_archetype_l2: {l2_count:,}")
    logger.info(f"  platform.dim_archetype_l3: {l3_count:,}")

    # Check fact table coverage
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

    # Sample archetype
    sample = await conn.fetchrow("SELECT * FROM platform.dim_archetype_l1 ORDER BY member_count DESC LIMIT 1")
    if sample:
        logger.info(f"\nLargest L1 archetype:")
        logger.info(f"  ID: {sample['archetype_id']}")
        logger.info(f"  Members: {sample['member_count']:,} ({sample['population_percentage']:.2f}%)")
        logger.info(f"  Avg LTV: ${sample['avg_lifetime_value']:.2f}" if sample['avg_lifetime_value'] else "  Avg LTV: N/A")
        logger.info(f"  Behavioral traits: {sample['behavioral_traits']}")


async def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python3 create_platform_dimension_tables.py <archetype_json_file>")
        print("Example: python3 create_platform_dimension_tables.py /tmp/archetypes_l1_l2_l3_20260102_123550.json")
        sys.exit(1)

    archetype_file = sys.argv[1]

    logger.info("=" * 80)
    logger.info("PLATFORM DIMENSION TABLE CREATOR")
    logger.info("=" * 80)
    logger.info(f"Archetype file: {archetype_file}")
    logger.info("")

    # Load archetype data
    archetype_data = await load_archetype_data(archetype_file)

    # Connect to database
    logger.info("Connecting to database...")
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)

    try:
        # Aggregate statistics
        l1_stats, l2_stats, l3_stats = await aggregate_archetype_stats(conn, archetype_data)

        # Recreate tables
        await recreate_dimension_tables(conn)

        # Populate tables
        await populate_l1_dimension(conn, l1_stats)
        await populate_l2_dimension(conn, l2_stats)
        await populate_l3_dimension(conn, l3_stats)

        # Re-enable foreign keys
        await reenable_foreign_keys(conn)

        # Verify
        await verify_installation(conn)

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ COMPLETE! Platform dimension tables ready for use.")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
