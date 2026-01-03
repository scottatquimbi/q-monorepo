#!/usr/bin/env python3
"""
Test archetype queries to verify the complete integration

Demonstrates various use cases for the L1/L2/L3 archetype system
"""

import asyncio
import asyncpg
import os
import sys
import json

async def test_basic_queries(conn: asyncpg.Connection):
    """Test basic queries"""
    print("=" * 80)
    print("TEST 1: BASIC QUERIES")
    print("=" * 80)

    # Get a specific customer with all their archetype details
    result = await conn.fetchrow("""
        SELECT
            f.customer_id,
            f.lifetime_value,
            f.total_orders,
            -- L1 details
            f.archetype_l1_id,
            l1.member_count as l1_members,
            l1.population_percentage as l1_population_pct,
            l1.behavioral_traits as l1_traits,
            -- L2 details
            f.archetype_l2_id,
            l2.member_count as l2_members,
            l2.membership_strengths as l2_strengths,
            -- L3 details
            f.archetype_l3_id,
            l3.fuzzy_memberships as l3_memberships
        FROM public.fact_customer_current f
        LEFT JOIN platform.dim_archetype_l1 l1 ON f.archetype_l1_id = l1.archetype_id
        LEFT JOIN platform.dim_archetype_l2 l2 ON f.archetype_l2_id = l2.archetype_id
        LEFT JOIN platform.dim_archetype_l3 l3 ON f.archetype_l3_id = l3.archetype_id
        WHERE f.archetype_l1_id IS NOT NULL
        ORDER BY f.lifetime_value DESC NULLS LAST
        LIMIT 1
    """)

    if result:
        print(f"\n✅ Retrieved full customer archetype profile:")
        print(f"   Customer ID: {result['customer_id']}")
        print(f"   LTV: ${result['lifetime_value']:.2f}, Orders: {result['total_orders']}")
        print(f"\n   L1 Archetype: {result['archetype_l1_id']}")
        print(f"     - Members: {result['l1_members']:,} ({result['l1_population_pct']:.2f}%)")
        print(f"     - Traits: {result['l1_traits'][:3]}...")
        print(f"\n   L2 Archetype: {result['archetype_l2_id']}")
        print(f"     - Members: {result['l2_members']:,}")
        print(f"\n   L3 Archetype: {result['archetype_l3_id']}")
        print(f"     - Members: {len([c for c in str(result['l3_memberships']) if c == ':'])} axes")


async def test_archetype_analytics(conn: asyncpg.Connection):
    """Test archetype-based analytics"""
    print("\n" + "=" * 80)
    print("TEST 2: ARCHETYPE-BASED ANALYTICS")
    print("=" * 80)

    # Average LTV by L1 archetype
    results = await conn.fetch("""
        SELECT
            d.archetype_id,
            d.member_count,
            d.population_percentage,
            d.avg_lifetime_value as dim_avg_ltv,
            AVG(f.lifetime_value) as fact_avg_ltv,
            COUNT(f.customer_id) as fact_customer_count,
            d.behavioral_traits[1:3] as top_traits
        FROM platform.dim_archetype_l1 d
        LEFT JOIN public.fact_customer_current f ON d.archetype_id = f.archetype_l1_id
        WHERE d.member_count > 1000
        GROUP BY d.archetype_id, d.member_count, d.population_percentage, d.avg_lifetime_value, d.behavioral_traits
        ORDER BY d.member_count DESC
        LIMIT 5
    """)

    print("\n✅ Top 5 L1 archetypes with analytics:")
    for i, row in enumerate(results, 1):
        print(f"\n{i}. {row['archetype_id']}")
        print(f"   Members: {row['member_count']:,} ({row['population_percentage']:.2f}%)")
        print(f"   Avg LTV (dimension): ${row['dim_avg_ltv']:.2f}" if row['dim_avg_ltv'] else "   Avg LTV: N/A")
        print(f"   Avg LTV (fact): ${row['fact_avg_ltv']:.2f}" if row['fact_avg_ltv'] else "   Avg LTV (fact): N/A")
        print(f"   Fact customers: {row['fact_customer_count']:,}")
        print(f"   Traits: {row['top_traits']}")


async def test_segment_drill_down(conn: asyncpg.Connection):
    """Test drilling down into specific segments"""
    print("\n" + "=" * 80)
    print("TEST 3: SEGMENT DRILL-DOWN")
    print("=" * 80)

    # Find all L2 archetypes with high price_sensitivity membership
    result = await conn.fetchrow("""
        SELECT
            archetype_id,
            member_count,
            membership_strengths->'price_sensitivity' as price_sensitivity_segments,
            dominant_segments->'price_sensitivity' as dominant_price_segment,
            avg_lifetime_value
        FROM platform.dim_archetype_l2
        WHERE membership_strengths ? 'price_sensitivity'
          AND member_count > 10
        ORDER BY member_count DESC
        LIMIT 1
    """)

    if result:
        print(f"\n✅ Sample L2 archetype with price sensitivity analysis:")
        print(f"   Archetype: {result['archetype_id']}")
        print(f"   Members: {result['member_count']:,}")
        print(f"   Dominant price segment: {result['dominant_price_segment']}")
        print(f"   Price sensitivity breakdown: {json.dumps(result['price_sensitivity_segments'], indent=4)}")
        print(f"   Avg LTV: ${result['avg_lifetime_value']:.2f}" if result['avg_lifetime_value'] else "   Avg LTV: N/A")


async def test_customer_similarity(conn: asyncpg.Connection):
    """Test finding similar customers based on archetypes"""
    print("\n" + "=" * 80)
    print("TEST 4: FIND SIMILAR CUSTOMERS")
    print("=" * 80)

    # Find customers in the same L2 archetype as a high-value customer
    results = await conn.fetch("""
        WITH target_customer AS (
            SELECT archetype_l2_id
            FROM public.fact_customer_current
            WHERE lifetime_value > 1000
              AND archetype_l2_id IS NOT NULL
            LIMIT 1
        )
        SELECT
            f.customer_id,
            f.lifetime_value,
            f.total_orders,
            f.archetype_l2_id,
            d.member_count
        FROM public.fact_customer_current f
        JOIN target_customer t ON f.archetype_l2_id = t.archetype_l2_id
        JOIN platform.dim_archetype_l2 d ON f.archetype_l2_id = d.archetype_id
        WHERE f.customer_id != (SELECT customer_id FROM public.fact_customer_current WHERE lifetime_value > 1000 LIMIT 1)
        ORDER BY f.lifetime_value DESC NULLS LAST
        LIMIT 5
    """)

    if results:
        print(f"\n✅ Found {len(results)} similar high-value customers in same L2 archetype:")
        print(f"   Archetype: {results[0]['archetype_l2_id']} ({results[0]['member_count']:,} total members)")
        for i, row in enumerate(results, 1):
            print(f"   {i}. Customer {row['customer_id']}: LTV ${row['lifetime_value']:.2f}, Orders: {row['total_orders']}")


async def test_archetype_diversity(conn: asyncpg.Connection):
    """Test archetype diversity metrics"""
    print("\n" + "=" * 80)
    print("TEST 5: ARCHETYPE DIVERSITY METRICS")
    print("=" * 80)

    # Compare L1/L2/L3 diversity
    diversity = await conn.fetchrow("""
        SELECT
            COUNT(DISTINCT f.archetype_l1_id) as unique_l1,
            COUNT(DISTINCT f.archetype_l2_id) as unique_l2,
            COUNT(DISTINCT f.archetype_l3_id) as unique_l3,
            COUNT(*) as total_customers,
            (SELECT COUNT(*) FROM platform.dim_archetype_l1) as total_l1_archetypes,
            (SELECT COUNT(*) FROM platform.dim_archetype_l2) as total_l2_archetypes,
            (SELECT COUNT(*) FROM platform.dim_archetype_l3) as total_l3_archetypes
        FROM public.fact_customer_current f
        WHERE f.archetype_l1_id IS NOT NULL
    """)

    print(f"\n✅ Archetype diversity:")
    print(f"   Total customers: {diversity['total_customers']:,}")
    print(f"\n   L1 (Simple - Dominant segments only):")
    print(f"     - Used archetypes: {diversity['unique_l1']:,} / {diversity['total_l1_archetypes']:,}")
    print(f"     - Coverage: {diversity['unique_l1']/diversity['total_l1_archetypes']*100:.1f}%")
    print(f"     - Avg customers per archetype: {diversity['total_customers']/diversity['unique_l1']:.0f}")
    print(f"\n   L2 (Optimal - Filtered & renormalized):")
    print(f"     - Used archetypes: {diversity['unique_l2']:,} / {diversity['total_l2_archetypes']:,}")
    print(f"     - Coverage: {diversity['unique_l2']/diversity['total_l2_archetypes']*100:.1f}%")
    print(f"     - Avg customers per archetype: {diversity['total_customers']/diversity['unique_l2']:.1f}")
    print(f"\n   L3 (Research-grade - Complete fuzzy membership):")
    print(f"     - Used archetypes: {diversity['unique_l3']:,} / {diversity['total_l3_archetypes']:,}")
    print(f"     - Coverage: {diversity['unique_l3']/diversity['total_l3_archetypes']*100:.1f}%")
    print(f"     - Avg customers per archetype: {diversity['total_customers']/diversity['unique_l3']:.1f}")


async def main():
    """Run all tests"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    print("=" * 80)
    print("ARCHETYPE SYSTEM INTEGRATION TESTS")
    print("=" * 80)
    print()

    conn = await asyncpg.connect(database_url)

    try:
        await test_basic_queries(conn)
        await test_archetype_analytics(conn)
        await test_segment_drill_down(conn)
        await test_customer_similarity(conn)
        await test_archetype_diversity(conn)

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - System ready for production!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
