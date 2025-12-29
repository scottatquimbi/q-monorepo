"""
Ticket Fulfillment Enricher

Enriches support tickets with Shopify fulfillment data for multi-warehouse tracking.
Integrates with the Gorgias AI Assistant to provide context about split shipments.

Usage:
    from integrations.ticket_fulfillment_enricher import enrich_ticket_with_fulfillments

    # In your ticket processing workflow:
    enriched_data = await enrich_ticket_with_fulfillments(
        ticket_data=gorgias_ticket,
        order_number=1001
    )

    # Returns fulfillment data to add to ticket custom_fields
"""
import logging
from typing import Dict, Any, Optional, List
from integrations.shopify_fulfillment_service import get_fulfillment_service

logger = logging.getLogger(__name__)


async def enrich_ticket_with_fulfillments(
    ticket_data: Dict[str, Any],
    order_number: Optional[int] = None,
    order_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enrich a Gorgias ticket with Shopify fulfillment data.

    This function:
    1. Fetches fulfillment data from Shopify
    2. Detects split shipment scenarios
    3. Maps items to specific warehouses/tracking numbers
    4. Returns structured data for ticket custom_fields

    Args:
        ticket_data: Gorgias ticket data dictionary
        order_number: Shopify order number (e.g., 1001)
        order_id: Shopify order ID (GID or legacy ID)

    Returns:
        Dictionary to merge into ticket.custom_fields:
        {
            "order_number": 1001,
            "fulfillment_status": "PARTIALLY_FULFILLED",
            "has_split_shipment": True,
            "fulfillments": [
                {
                    "fulfillment_id": "67890",
                    "warehouse": "New Jersey DC",
                    "tracking": {...},
                    "items": [...]
                },
                ...
            ],
            "unfulfilled_items": [...],
            "split_shipment_message": "Your order will arrive in 2 shipments..."
        }
    """
    service = get_fulfillment_service()

    if not service:
        logger.warning("Shopify fulfillment service not available - skipping enrichment")
        return {}

    try:
        # Fetch fulfillment data
        if order_number:
            logger.info(f"Enriching ticket with fulfillments for order #{order_number}")
            fulfillment_data = await service.get_order_by_number(order_number)
        elif order_id:
            logger.info(f"Enriching ticket with fulfillments for order ID {order_id}")
            fulfillment_data = await service.get_order_fulfillments(order_id)
        else:
            # Try to extract order number from ticket
            order_number = extract_order_number_from_ticket(ticket_data)
            if not order_number:
                logger.warning("No order number or ID provided for fulfillment enrichment")
                return {}

            fulfillment_data = await service.get_order_by_number(order_number)

        if not fulfillment_data or "error" in fulfillment_data:
            logger.warning(f"Could not fetch fulfillment data: {fulfillment_data.get('error', 'Unknown error')}")
            return {}

        # Detect split shipment scenario
        split_analysis = service.detect_split_shipment_scenario(fulfillment_data)

        # Build enriched custom fields data
        enriched = {
            "order_number": fulfillment_data.get("order_number"),
            "order_name": fulfillment_data.get("order_name"),
            "fulfillment_status": fulfillment_data.get("fulfillment_status"),
            "total_items": fulfillment_data.get("total_items"),
            "fulfilled_items_count": fulfillment_data.get("fulfilled_items_count"),
            "unfulfilled_items_count": fulfillment_data.get("unfulfilled_items_count"),
            "has_split_shipment": split_analysis.get("is_split_shipment", False),
            "fulfillment_count": split_analysis.get("fulfillment_count", 0),
            "warehouse_count": split_analysis.get("warehouse_count", 0),
            "carriers": split_analysis.get("unique_carriers", []),

            # Fulfillments array
            "fulfillments": _format_fulfillments_for_ticket(
                fulfillment_data.get("fulfillments", [])
            ),

            # Unfulfilled items
            "unfulfilled_items": _format_unfulfilled_items(
                fulfillment_data.get("unfulfilled_items", [])
            ),

            # Customer-facing message
            "split_shipment_message": split_analysis.get("customer_message_suggestion", ""),

            # Delivery estimates
            "estimated_delivery": split_analysis.get("estimated_delivery_range", {}),

            # Items grouped by warehouse (for easy display)
            "items_by_warehouse": split_analysis.get("items_by_warehouse", {}),

            # Enrichment metadata
            "_enriched_at": fulfillment_data.get("created_at"),
            "_enrichment_version": "1.0"
        }

        logger.info(
            f"✅ Enriched ticket with {len(enriched['fulfillments'])} fulfillment(s) "
            f"({'split shipment' if enriched['has_split_shipment'] else 'single shipment'})"
        )

        return enriched

    except Exception as e:
        logger.error(f"❌ Error enriching ticket with fulfillments: {e}", exc_info=True)
        return {}


def _format_fulfillments_for_ticket(fulfillments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format fulfillment data for storage in ticket custom_fields.

    Simplifies the data structure while keeping essential information.
    """
    formatted = []

    for fulfillment in fulfillments:
        # Get primary tracking info
        tracking_info = fulfillment.get("tracking_info", [])
        primary_tracking = tracking_info[0] if tracking_info else {}

        formatted.append({
            "fulfillment_id": fulfillment.get("fulfillment_id"),
            "status": fulfillment.get("display_status") or fulfillment.get("status"),
            "warehouse": {
                "name": fulfillment.get("location", {}).get("name", "Unknown"),
                "address": fulfillment.get("location", {}).get("address", "")
            },
            "tracking": {
                "number": primary_tracking.get("number", ""),
                "carrier": primary_tracking.get("company", ""),
                "url": primary_tracking.get("url", "")
            },
            "additional_tracking": tracking_info[1:] if len(tracking_info) > 1 else [],
            "created_at": fulfillment.get("created_at"),
            "delivered_at": fulfillment.get("delivered_at"),
            "estimated_delivery_at": fulfillment.get("estimated_delivery_at"),
            "in_transit_at": fulfillment.get("in_transit_at"),
            "items": [
                {
                    "title": item.get("title", ""),
                    "sku": item.get("sku", ""),
                    "quantity": item.get("quantity", 0)
                }
                for item in fulfillment.get("items", [])
            ],
            "item_count": fulfillment.get("item_count", 0)
        })

    return formatted


def _format_unfulfilled_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format unfulfilled items for ticket display."""
    return [
        {
            "title": item.get("title", ""),
            "sku": item.get("sku", ""),
            "quantity": item.get("quantity", 0),
            "status": item.get("fulfillment_status", "UNFULFILLED")
        }
        for item in items
    ]


def extract_order_number_from_ticket(ticket_data: Dict[str, Any]) -> Optional[int]:
    """
    Extract Shopify order number from Gorgias ticket data.

    Checks multiple locations:
    1. custom_fields.order_number
    2. Ticket subject/body for "#1001" format
    3. Ticket tags for "order-1001" format

    Args:
        ticket_data: Gorgias ticket dictionary

    Returns:
        Order number as integer or None if not found
    """
    # Check custom fields first
    custom_fields = ticket_data.get("custom_fields") or {}
    order_number = custom_fields.get("order_number")
    if order_number:
        try:
            return int(order_number)
        except (ValueError, TypeError):
            pass

    # Check ticket subject
    subject = ticket_data.get("subject", "")
    order_num = _extract_order_from_text(subject)
    if order_num:
        return order_num

    # Check most recent message
    messages = ticket_data.get("messages", [])
    if messages:
        message_body = messages[0].get("body_text", "")
        order_num = _extract_order_from_text(message_body)
        if order_num:
            return order_num

    # Check tags
    tags = ticket_data.get("tags", [])
    for tag in tags:
        if tag.get("name", "").startswith("order-"):
            try:
                return int(tag["name"].replace("order-", ""))
            except (ValueError, TypeError):
                pass

    logger.warning("Could not extract order number from ticket")
    return None


def _extract_order_from_text(text: str) -> Optional[int]:
    """
    Extract order number from text (e.g., "#1001", "order 1001", "Order #1001").

    Args:
        text: Text to search for order number

    Returns:
        Order number as integer or None
    """
    import re

    if not text:
        return None

    # Match patterns like "#1001", "order 1001", "Order #1001"
    patterns = [
        r'#(\d{4,6})',           # #1001
        r'order\s+#?(\d{4,6})',  # order 1001 or order #1001
        r'Order\s+#?(\d{4,6})',  # Order 1001 or Order #1001
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return None


def format_fulfillment_summary_for_ai(enriched_data: Dict[str, Any]) -> str:
    """
    Format fulfillment data into a human-readable summary for AI context.

    This generates a concise summary that can be included in the AI prompt
    to help generate better customer responses.

    Args:
        enriched_data: Enriched fulfillment data from enrich_ticket_with_fulfillments()

    Returns:
        Formatted string for AI context, e.g.:
        "ORDER #1001 - Split Shipment (2 packages from 2 warehouses)
         Shipment 1: UPS tracking 1Z999... from New Jersey DC
           - Rose Thread Bundle (qty: 2)
         Shipment 2: FedEx tracking 7712... from California DC
           - Blue Fabric Roll (qty: 3)
         Unfulfilled: Premium Scissors (qty: 1) - Not yet shipped"
    """
    if not enriched_data or not enriched_data.get("fulfillments"):
        return "ORDER STATUS: No fulfillment information available"

    lines = []

    # Header
    order_name = enriched_data.get("order_name", "Order")
    if enriched_data.get("has_split_shipment"):
        fulfillment_count = enriched_data.get("fulfillment_count", 0)
        warehouse_count = enriched_data.get("warehouse_count", 0)
        lines.append(
            f"📦 {order_name} - SPLIT SHIPMENT "
            f"({fulfillment_count} packages from {warehouse_count} warehouse(s))"
        )
    else:
        lines.append(f"📦 {order_name} - Single Shipment")

    lines.append("")  # Blank line

    # Fulfillments
    for i, fulfillment in enumerate(enriched_data.get("fulfillments", []), 1):
        tracking = fulfillment.get("tracking", {})
        warehouse = fulfillment.get("warehouse", {})

        tracking_num = tracking.get("number", "No tracking")
        carrier = tracking.get("carrier", "Unknown carrier")
        warehouse_name = warehouse.get("name", "Unknown warehouse")

        status = fulfillment.get("status", "")
        estimated_delivery = fulfillment.get("estimated_delivery_at", "")

        # Fulfillment header
        lines.append(f"Shipment {i}: {carrier} {tracking_num}")
        lines.append(f"  From: {warehouse_name}")
        if status:
            lines.append(f"  Status: {status}")
        if estimated_delivery:
            lines.append(f"  Est. Delivery: {estimated_delivery}")

        # Items in this fulfillment
        items = fulfillment.get("items", [])
        if items:
            lines.append("  Items:")
            for item in items:
                title = item.get("title", "Unknown item")
                qty = item.get("quantity", 1)
                sku = item.get("sku", "")
                sku_str = f" [{sku}]" if sku else ""
                lines.append(f"    - {title}{sku_str} (qty: {qty})")

        lines.append("")  # Blank line between fulfillments

    # Unfulfilled items
    unfulfilled = enriched_data.get("unfulfilled_items", [])
    if unfulfilled:
        lines.append("⏳ NOT YET SHIPPED:")
        for item in unfulfilled:
            title = item.get("title", "Unknown item")
            qty = item.get("quantity", 1)
            status = item.get("status", "UNFULFILLED")
            lines.append(f"  - {title} (qty: {qty}) - {status}")

    # Customer message suggestion
    if enriched_data.get("split_shipment_message"):
        lines.append("")
        lines.append("💬 SUGGESTED MESSAGE TO CUSTOMER:")
        lines.append(enriched_data["split_shipment_message"])

    return "\n".join(lines)


def format_fulfillment_for_internal_note(enriched_data: Dict[str, Any]) -> str:
    """
    Format fulfillment data as an internal note for Gorgias agents.

    This creates a formatted note that can be posted to the ticket
    to give agents quick visibility into shipping status.

    Args:
        enriched_data: Enriched fulfillment data

    Returns:
        Formatted internal note (Markdown)
    """
    if not enriched_data or not enriched_data.get("fulfillments"):
        return "**Shipping Status**: No fulfillment information available"

    lines = []

    # Header
    order_name = enriched_data.get("order_name", "Order")
    fulfillment_status = enriched_data.get("fulfillment_status", "UNKNOWN")

    lines.append(f"## 📦 Shipping Status for {order_name}")
    lines.append(f"**Status**: {fulfillment_status}")
    lines.append(f"**Total Items**: {enriched_data.get('total_items', 'Unknown')}")
    lines.append(f"**Fulfilled**: {enriched_data.get('fulfilled_items_count', 0)}")
    lines.append(f"**Pending**: {enriched_data.get('unfulfilled_items_count', 0)}")
    lines.append("")

    # Split shipment warning
    if enriched_data.get("has_split_shipment"):
        lines.append(f"⚠️ **SPLIT SHIPMENT**: {enriched_data.get('fulfillment_count')} separate packages")
        lines.append("")

    # Fulfillments table
    for i, fulfillment in enumerate(enriched_data.get("fulfillments", []), 1):
        tracking = fulfillment.get("tracking", {})
        warehouse = fulfillment.get("warehouse", {})

        lines.append(f"### Shipment {i}")
        lines.append(f"- **Warehouse**: {warehouse.get('name', 'Unknown')}")
        lines.append(f"- **Carrier**: {tracking.get('carrier', 'Unknown')}")
        lines.append(f"- **Tracking**: {tracking.get('number', 'N/A')}")

        if tracking.get("url"):
            lines.append(f"- **Track**: [{tracking['number']}]({tracking['url']})")

        estimated = fulfillment.get("estimated_delivery_at")
        if estimated:
            lines.append(f"- **Est. Delivery**: {estimated}")

        # Items
        items = fulfillment.get("items", [])
        if items:
            lines.append(f"- **Items** ({len(items)}):")
            for item in items:
                lines.append(f"  - {item.get('title')} (x{item.get('quantity', 1)})")

        lines.append("")

    # Unfulfilled items
    unfulfilled = enriched_data.get("unfulfilled_items", [])
    if unfulfilled:
        lines.append("### ⏳ Pending Fulfillment")
        for item in unfulfilled:
            lines.append(f"- {item.get('title')} (x{item.get('quantity', 1)})")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Auto-generated fulfillment summary from Shopify*")

    return "\n".join(lines)
