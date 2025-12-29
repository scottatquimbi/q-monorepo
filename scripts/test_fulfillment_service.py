#!/usr/bin/env python3
"""
Test Shopify Fulfillment Service

Example script demonstrating the new multi-warehouse fulfillment tracking capabilities.

Usage:
    # Test with a specific order number
    python scripts/test_fulfillment_service.py --order-number 1001

    # Test with Sharon's example
    python scripts/test_fulfillment_service.py --customer sharonbrz@verizon.net

    # Test with order ID
    python scripts/test_fulfillment_service.py --order-id gid://shopify/Order/12345

Prerequisites:
    Set environment variables:
    - SHOPIFY_SHOP_NAME (e.g., "lindas-electric-quilters")
    - SHOPIFY_ACCESS_TOKEN (Admin API token)
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations.shopify_fulfillment_service import get_fulfillment_service
from integrations.ticket_fulfillment_enricher import (
    enrich_ticket_with_fulfillments,
    format_fulfillment_summary_for_ai,
    format_fulfillment_for_internal_note
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_order_fulfillments(order_number: int = None, order_id: str = None):
    """
    Test fetching fulfillment data for an order.

    Demonstrates:
    1. Fetching fulfillment data from Shopify
    2. Detecting split shipments
    3. Formatting for AI context
    4. Formatting for internal notes
    """
    logger.info("=" * 80)
    logger.info("SHOPIFY FULFILLMENT SERVICE TEST")
    logger.info("=" * 80)

    # Get service
    service = get_fulfillment_service()

    if not service:
        logger.error("❌ Fulfillment service not configured. Check environment variables:")
        logger.error("   - SHOPIFY_SHOP_NAME")
        logger.error("   - SHOPIFY_ACCESS_TOKEN")
        return False

    logger.info(f"✅ Fulfillment service initialized for shop: {service.shop_name}")

    try:
        # Fetch fulfillment data
        if order_number:
            logger.info(f"\n🔍 Fetching fulfillments for order #{order_number}...")
            fulfillment_data = await service.get_order_by_number(order_number)
        elif order_id:
            logger.info(f"\n🔍 Fetching fulfillments for order {order_id}...")
            fulfillment_data = await service.get_order_fulfillments(order_id)
        else:
            logger.error("❌ No order number or ID provided")
            return False

        if not fulfillment_data or "error" in fulfillment_data:
            logger.error(f"❌ Failed to fetch fulfillment data: {fulfillment_data.get('error', 'Unknown error')}")
            return False

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("ORDER DETAILS")
        logger.info("=" * 80)
        logger.info(f"Order ID: {fulfillment_data.get('order_id')}")
        logger.info(f"Order Name: {fulfillment_data.get('order_name')}")
        logger.info(f"Order Number: {fulfillment_data.get('order_number')}")
        logger.info(f"Created: {fulfillment_data.get('created_at')}")
        logger.info(f"Status: {fulfillment_data.get('fulfillment_status')}")
        logger.info(f"Total Items: {fulfillment_data.get('total_items')}")
        logger.info(f"Fulfilled: {fulfillment_data.get('fulfilled_items_count')}")
        logger.info(f"Unfulfilled: {fulfillment_data.get('unfulfilled_items_count')}")

        # Split shipment detection
        split_analysis = service.detect_split_shipment_scenario(fulfillment_data)

        logger.info("\n" + "=" * 80)
        logger.info("SPLIT SHIPMENT ANALYSIS")
        logger.info("=" * 80)
        logger.info(f"Is Split Shipment: {split_analysis.get('is_split_shipment')}")
        logger.info(f"Fulfillment Count: {split_analysis.get('fulfillment_count')}")
        logger.info(f"Warehouse Count: {split_analysis.get('warehouse_count')}")
        logger.info(f"Carriers: {', '.join(split_analysis.get('unique_carriers', []))}")

        delivery_range = split_analysis.get('estimated_delivery_range', {})
        if delivery_range.get('earliest'):
            logger.info(f"Earliest Delivery: {delivery_range.get('earliest')}")
            logger.info(f"Latest Delivery: {delivery_range.get('latest')}")

        # Fulfillments details
        fulfillments = fulfillment_data.get('fulfillments', [])
        if fulfillments:
            logger.info("\n" + "=" * 80)
            logger.info(f"FULFILLMENTS ({len(fulfillments)})")
            logger.info("=" * 80)

            for i, fulfillment in enumerate(fulfillments, 1):
                logger.info(f"\n--- Fulfillment {i} ---")
                logger.info(f"ID: {fulfillment.get('fulfillment_id')}")
                logger.info(f"Status: {fulfillment.get('display_status')} ({fulfillment.get('status')})")
                logger.info(f"Created: {fulfillment.get('created_at')}")

                # Location
                location = fulfillment.get('location', {})
                logger.info(f"Warehouse: {location.get('name')}")
                logger.info(f"Address: {location.get('address')}")

                # Tracking
                tracking_info = fulfillment.get('tracking_info', [])
                if tracking_info:
                    logger.info(f"Tracking:")
                    for track in tracking_info:
                        logger.info(f"  - {track.get('company')}: {track.get('number')}")
                        logger.info(f"    URL: {track.get('url')}")

                # Delivery dates
                if fulfillment.get('estimated_delivery_at'):
                    logger.info(f"Est. Delivery: {fulfillment.get('estimated_delivery_at')}")
                if fulfillment.get('delivered_at'):
                    logger.info(f"Delivered: {fulfillment.get('delivered_at')}")

                # Items
                items = fulfillment.get('items', [])
                if items:
                    logger.info(f"Items ({len(items)}):")
                    for item in items:
                        logger.info(f"  - {item.get('title')} [{item.get('sku')}] (qty: {item.get('quantity')})")

        # Unfulfilled items
        unfulfilled = fulfillment_data.get('unfulfilled_items', [])
        if unfulfilled:
            logger.info("\n" + "=" * 80)
            logger.info(f"UNFULFILLED ITEMS ({len(unfulfilled)})")
            logger.info("=" * 80)

            for item in unfulfilled:
                logger.info(f"- {item.get('title')} [{item.get('sku')}] (qty: {item.get('quantity')}) - {item.get('fulfillment_status')}")

        # Customer message
        if split_analysis.get('customer_message_suggestion'):
            logger.info("\n" + "=" * 80)
            logger.info("CUSTOMER MESSAGE SUGGESTION")
            logger.info("=" * 80)
            logger.info(split_analysis.get('customer_message_suggestion'))

        # Test ticket enrichment
        logger.info("\n" + "=" * 80)
        logger.info("TICKET ENRICHMENT TEST")
        logger.info("=" * 80)

        # Simulate a Gorgias ticket
        mock_ticket = {
            "id": "123456",
            "subject": f"Missing item from order #{order_number or fulfillment_data.get('order_number')}",
            "custom_fields": {},
            "messages": []
        }

        enriched = await enrich_ticket_with_fulfillments(
            ticket_data=mock_ticket,
            order_number=order_number or fulfillment_data.get('order_number')
        )

        logger.info("\nEnriched custom_fields:")
        logger.info(f"  has_split_shipment: {enriched.get('has_split_shipment')}")
        logger.info(f"  fulfillment_count: {enriched.get('fulfillment_count')}")
        logger.info(f"  warehouse_count: {enriched.get('warehouse_count')}")
        logger.info(f"  carriers: {enriched.get('carriers')}")

        # AI Context Format
        logger.info("\n" + "=" * 80)
        logger.info("AI CONTEXT FORMAT (for draft generation)")
        logger.info("=" * 80)
        ai_context = format_fulfillment_summary_for_ai(enriched)
        logger.info(ai_context)

        # Internal Note Format
        logger.info("\n" + "=" * 80)
        logger.info("INTERNAL NOTE FORMAT (for Gorgias agents)")
        logger.info("=" * 80)
        internal_note = format_fulfillment_for_internal_note(enriched)
        logger.info(internal_note)

        logger.info("\n" + "=" * 80)
        logger.info("✅ TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        return False

    finally:
        # Cleanup
        await service.close()
        logger.info("\n✅ Service connection closed")


async def test_sharon_scenario():
    """
    Test the specific scenario from Sharon's email:
    - Customer: sharonbrz@verizon.net
    - Issue: Missing item from shipment (actually shipped separately)

    This demonstrates how the system would handle this case.
    """
    logger.info("=" * 80)
    logger.info("SHARON'S SCENARIO TEST")
    logger.info("=" * 80)
    logger.info("Scenario: Customer emails about missing item (shipped from different warehouse)")
    logger.info("")

    # In a real scenario, you'd:
    # 1. Get the order number from the Gorgias ticket
    # 2. Fetch fulfillment data
    # 3. Generate AI response explaining the split shipment

    # For testing, let's use a sample order number
    # You'll need to replace this with an actual order number from your shop
    logger.info("❗ To test Sharon's scenario, you need:")
    logger.info("   1. A real order number that has split fulfillments")
    logger.info("   2. Run: python scripts/test_fulfillment_service.py --order-number <NUMBER>")
    logger.info("")
    logger.info("Example workflow when ticket arrives:")
    logger.info("   1. Gorgias webhook triggers")
    logger.info("   2. Extract order number from ticket")
    logger.info("   3. Fetch fulfillments (shows 2+ warehouses)")
    logger.info("   4. AI generates response:")
    logger.info("      'Hi Sharon, I see your order is arriving in 2 separate shipments'")
    logger.info("      'Shipment 1 from NJ: [items] - tracking: 1Z999...'")
    logger.info("      'Shipment 2 from CA: [missing item] - tracking: 7712...'")
    logger.info("   5. Agent reviews and sends")


def main():
    parser = argparse.ArgumentParser(description="Test Shopify Fulfillment Service")
    parser.add_argument("--order-number", type=int, help="Shopify order number (e.g., 1001)")
    parser.add_argument("--order-id", type=str, help="Shopify order ID (GID or legacy)")
    parser.add_argument("--customer", type=str, help="Test customer scenario (e.g., sharonbrz@verizon.net)")

    args = parser.parse_args()

    # Check environment variables
    if not os.getenv("SHOPIFY_SHOP_NAME") or not os.getenv("SHOPIFY_ACCESS_TOKEN"):
        logger.error("❌ Missing required environment variables:")
        logger.error("   - SHOPIFY_SHOP_NAME")
        logger.error("   - SHOPIFY_ACCESS_TOKEN")
        logger.error("")
        logger.error("Set them in your .env file or export them:")
        logger.error('   export SHOPIFY_SHOP_NAME="lindas-electric-quilters"')
        logger.error('   export SHOPIFY_ACCESS_TOKEN="shpat_..."')
        sys.exit(1)

    # Run tests
    if args.customer == "sharonbrz@verizon.net" or (not args.order_number and not args.order_id):
        asyncio.run(test_sharon_scenario())
    else:
        success = asyncio.run(test_order_fulfillments(
            order_number=args.order_number,
            order_id=args.order_id
        ))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
