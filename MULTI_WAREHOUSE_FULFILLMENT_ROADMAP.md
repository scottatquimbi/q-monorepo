# Multi-Warehouse Fulfillment Support - Implementation Roadmap

## Executive Summary

The current support-backend service can handle basic order information but lacks support for multi-warehouse fulfillments. This document outlines the gaps and provides a step-by-step implementation roadmap to add this capability.

---

## Current Gaps Analysis

### Data Retrieval Gaps

#### 1. Shopify GraphQL Queries Don't Include Fulfillments
**Current Query**: Fetches orders and line items only
```graphql
customer(id: $id) {
  orders {
    edges {
      node {
        id
        lineItems { ... }  # ✅ We get line items
        # ❌ No fulfillments edge
      }
    }
  }
}
```

**What's Missing**:
- Fulfillment objects with tracking numbers
- Warehouse/location information
- Fulfillment status per item
- Multiple fulfillments per order

#### 2. Tracking Data Not Fetched from Shopify
**Current State**: 
- Tracking info stored in `Ticket.custom_fields` (lines 545-587 in ai.py)
- BUT data must be pre-populated by external system
- NOT fetched from Shopify API

**Evidence**:
```python
# In ai.py line 542-588
tracking_num = ticket.custom_fields.get('tracking_number')  # Retrieved, not fetched
carrier = ticket.custom_fields.get('carrier')  # Retrieved, not fetched
```

#### 3. No Line-Item to Fulfillment Mapping
**Current State**: 
- Line items stored as simple list: `[{name, qty}, ...]`
- No reference to which fulfillment contains which items

**Impact**: 
- Can't tell customer "Items X and Y shipped separately"
- Can't track partial shipments independently
- Can't handle multi-carrier scenarios

---

## Implementation Roadmap

### Phase 1: Data Model Enhancement (Weeks 1-2)

#### 1.1 Extend Ticket Custom Fields Schema

**File**: `/Users/scottallen/quimbi-platform/backend/models/ticket.py`

**Current Structure**:
```python
custom_fields = {
    "order_number": "1001",
    "tracking_number": "1Z999AA...",      # Single
    "carrier": "UPS",                      # Single
    "items": [{"name": "...", "qty": 1}] # Flat list
}
```

**New Structure**:
```python
custom_fields = {
    "order_number": "1001",
    "order_total": 125.50,
    "currency": "USD",
    
    # LEGACY (for backward compatibility)
    "tracking_number": "1Z999AA...",
    "carrier": "UPS",
    
    # NEW: Multiple fulfillments
    "fulfillments": [
        {
            "fulfillment_id": "gid://shopify/Fulfillment/12345",
            "status": "fulfilled",  # fulfilled, cancelled, in_transit, etc.
            "tracking_info": {
                "number": "1Z999AA10123456784",
                "company": "UPS",
                "url": "https://tracking.ups.com/..."
            },
            "warehouse": {
                "id": "warehouse_us_east",
                "name": "New Jersey Distribution Center",
                "location": "Newark, NJ"
            },
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T15:30:00Z",
            "estimated_delivery": "2025-01-17",
            "delivered_at": "2025-01-17T10:00:00Z",
            "items": [
                {
                    "id": "lineitem_1",
                    "title": "Fabric Roll A",
                    "sku": "FABRIC-A-001",
                    "quantity": 2,
                    "quantity_fulfilled": 2
                }
            ]
        },
        {
            "fulfillment_id": "gid://shopify/Fulfillment/12346",
            "status": "fulfilled",
            # ... second shipment data
        }
    ],
    
    # For backwards compatibility / simple display
    "items": [
        {
            "title": "Fabric Roll A",
            "sku": "FABRIC-A-001",
            "quantity": 2,
            "fulfilled_quantity": 2,
            "fulfillment_ids": ["gid://shopify/Fulfillment/12345"]
        }
    ]
}
```

#### 1.2 Create Migration Script

**File**: Create `/Users/scottallen/quimbi-platform/alembic/versions/add_fulfillments_support.py`

```python
"""Add multi-fulfillment support to tickets.

Revision ID: xxxxx
Revises: xxxxx
Create Date: 2025-01-XX XX:XX:XX.XXXXXX
"""
from alembic import op
import sqlalchemy as sa

revision = 'xxxxx'
down_revision = 'xxxxx'

def upgrade():
    # No schema change needed - custom_fields is JSONB
    # Just document the new structure in comment
    pass

def downgrade():
    pass
```

---

### Phase 2: Shopify GraphQL Enhancement (Weeks 2-3)

#### 2.1 Update Customer Orders Query

**File**: `/Users/scottallen/quimbi-platform/backend/api/routers/customers.py`

**Current Query** (lines 373-412): Fetches orders and line items

**Enhanced Query**:
```graphql
query ($id: ID!, $limit: Int!) {
  customer(id: $id) {
    id
    email
    firstName
    lastName
    orders(first: $limit, sortKey: CREATED_AT, reverse: true) {
      edges {
        node {
          id
          name
          createdAt
          totalPriceSet {
            shopMoney {
              amount
              currencyCode
            }
          }
          lineItems(first: 100) {
            edges {
              node {
                id
                title
                quantity
                sku
                variant {
                  product {
                    title
                    vendor
                    productType
                  }
                }
              }
            }
          }
          
          # NEW: Fulfillment data
          fulfillments(first: 10) {
            edges {
              node {
                id
                status
                createdAt
                updatedAt
                estimatedDeliveryAt
                displayStatus
                trackingInfo {
                  number
                  company
                  url
                }
                line_items(first: 100) {
                  edges {
                    node {
                      id
                      lineItem {
                        id
                        title
                        sku
                        quantity
                      }
                      quantity
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### 2.2 Update Response Processing

**Location**: `/Users/scottallen/quimbi-platform/backend/api/routers/customers.py` 
Lines 463-510 (order processing loop)

**Changes**:
```python
for edge in customer_data.get("orders", {}).get("edges", []):
    order = edge["node"]
    
    # Extract fulfillments (NEW)
    fulfillments = []
    for fulfillment_edge in order.get("fulfillments", {}).get("edges", []):
        fulfillment_node = fulfillment_edge["node"]
        
        # Get items in this fulfillment
        fulfillment_items = []
        for item_edge in fulfillment_node.get("line_items", {}).get("edges", []):
            item_node = item_edge["node"]
            line_item = item_node.get("lineItem", {})
            fulfillment_items.append({
                "id": line_item.get("id"),
                "title": line_item.get("title"),
                "sku": line_item.get("sku"),
                "quantity": item_node.get("quantity")
            })
        
        fulfillments.append({
            "fulfillment_id": fulfillment_node.get("id"),
            "status": fulfillment_node.get("status"),
            "created_at": fulfillment_node.get("createdAt"),
            "updated_at": fulfillment_node.get("updatedAt"),
            "estimated_delivery": fulfillment_node.get("estimatedDeliveryAt"),
            "tracking": {
                "number": fulfillment_node.get("trackingInfo", {}).get("number"),
                "company": fulfillment_node.get("trackingInfo", {}).get("company"),
                "url": fulfillment_node.get("trackingInfo", {}).get("url")
            },
            "items": fulfillment_items
        })
    
    order_data["fulfillments"] = fulfillments
```

---

### Phase 3: Integration Layer Updates (Weeks 3-4)

#### 3.1 Update Gorgias Webhook Processing

**File**: `/Users/scottallen/quimbi-platform/integrations/gorgias_ai_assistant.py`

**New Method**: `_extract_fulfillment_data()`
```python
def _extract_fulfillment_data(self, customer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract fulfillment information from Shopify integration data in webhook.
    
    Args:
        customer_data: Gorgias customer object
        
    Returns:
        List of fulfillments with tracking info
    """
    fulfillments = []
    
    integrations = customer_data.get("integrations") or {}
    for integration_id, integration_data in integrations.items():
        if integration_data.get("__integration_type__") == "shopify":
            # Extract fulfillments from webhook data if present
            orders = integration_data.get("orders", [])
            for order in orders:
                order_fulfillments = order.get("fulfillments", [])
                for fulfillment in order_fulfillments:
                    fulfillments.append({
                        "fulfillment_id": fulfillment.get("id"),
                        "status": fulfillment.get("status"),
                        "tracking_number": fulfillment.get("trackingInfo", {}).get("number"),
                        "carrier": fulfillment.get("trackingInfo", {}).get("company"),
                        "tracking_url": fulfillment.get("trackingInfo", {}).get("url"),
                        "items": fulfillment.get("line_items", [])
                    })
    
    return fulfillments
```

#### 3.2 Update Webhook Handler

**Location**: `handle_ticket_webhook()` method

**Addition**: After line 213 (after extracting Shopify metrics):
```python
# Extract fulfillment data from webhook (NEW)
fulfillment_data = self._extract_fulfillment_data(customer_data)
if fulfillment_data:
    logger.info(f"Found {len(fulfillment_data)} fulfillments in webhook data")
    analytics["fulfillments"] = fulfillment_data
```

---

### Phase 4: AI Context Enhancement (Weeks 4-5)

#### 4.1 Update Draft Generation Context Building

**File**: `/Users/scottallen/quimbi-platform/backend/api/routers/ai.py`

**Enhanced Tracking Context** (lines 541-588):

```python
# Build tracking/fulfillment context from ticket custom_fields
fulfillment_str = ""
if ticket.custom_fields and isinstance(ticket.custom_fields, dict):
    fulfillments = ticket.custom_fields.get('fulfillments', [])
    
    if fulfillments:
        # Multiple fulfillments case (NEW)
        fulfillment_str = f"\n\nOrder Information (USE THIS DATA - it's real):"
        fulfillment_str += f"\n- Order Number: {ticket.custom_fields.get('order_number')}"
        fulfillment_str += f"\n\n*** IMPORTANT: This order shipped in {len(fulfillments)} separate fulfillments ***\n"
        
        for i, fulfillment in enumerate(fulfillments, 1):
            fulfillment_str += f"\nShipment {i} of {len(fulfillments)}:"
            fulfillment_str += f"\n- Status: {fulfillment.get('status')}"
            fulfillment_str += f"\n- Tracking: {fulfillment.get('tracking_info', {}).get('number')}"
            fulfillment_str += f"\n- Carrier: {fulfillment.get('tracking_info', {}).get('company')}"
            
            if fulfillment.get('warehouse'):
                fulfillment_str += f"\n- Shipped from: {fulfillment['warehouse'].get('name', 'Unknown')} ({fulfillment['warehouse'].get('location')})"
            
            fulfillment_str += f"\n- Shipped: {fulfillment.get('created_at')}"
            
            if fulfillment.get('delivered_at'):
                fulfillment_str += f"\n- Delivered: {fulfillment.get('delivered_at')}"
            elif fulfillment.get('estimated_delivery'):
                fulfillment_str += f"\n- Est. Delivery: {fulfillment.get('estimated_delivery')}"
            
            # Items in this fulfillment
            items = fulfillment.get('items', [])
            if items:
                fulfillment_str += f"\n- Items in this shipment:"
                for item in items:
                    qty_fulfilled = item.get('quantity_fulfilled', item.get('quantity'))
                    fulfillment_str += f"\n  * {item.get('title')} (qty: {qty_fulfilled}/{item.get('quantity')})"
    
    elif ticket.custom_fields.get('order_number'):
        # Single fulfillment case (backward compatible)
        # ... existing code ...
```

#### 4.2 Update AI Instructions

**Location**: `generate_draft_response()` prompt building (lines 602-642)

**Add to CRITICAL INSTRUCTIONS**:
```python
# In the prompt template, add:
"""
MULTI-FULFILLMENT HANDLING:
If the customer's order has multiple fulfillments (shipments):
- Reference each shipment separately with its tracking number
- Explain why items shipped separately if applicable
- If one shipment is delayed but others arrived, acknowledge this
- If customer is asking about a specific item, check which fulfillment it's in
- For missing items, determine if they're in a different shipment before offering replacement

Example:
"I see your order shipped in 2 separate packages:
- Fabrics (UPS tracking 1Z999AA...) delivered Jan 15
- Batting and thread (FedEx tracking 7H999BB...) in transit, expected Jan 17"
"""
```

---

### Phase 5: Testing & Validation (Weeks 5-6)

#### 5.1 Unit Tests

**File**: Create `/Users/scottallen/quimbi-platform/tests/test_fulfillment_handling.py`

```python
import pytest
from backend.api.routers.customers import get_customer_order_history

@pytest.mark.asyncio
async def test_multi_fulfillment_order_extraction():
    """Test that orders with multiple fulfillments are extracted correctly."""
    # Mock Shopify response with 2 fulfillments
    # Assert both fulfillments in response
    pass

@pytest.mark.asyncio
async def test_fulfillment_tracking_data():
    """Test that tracking info is extracted per fulfillment."""
    # Assert tracking_number, carrier, url for each fulfillment
    pass

@pytest.mark.asyncio
async def test_warehouse_identification():
    """Test that warehouse info is extracted."""
    # Assert warehouse name and location in response
    pass

def test_ai_context_multi_fulfillment():
    """Test that AI gets correct fulfillment context."""
    # Create ticket with multiple fulfillments in custom_fields
    # Generate draft and verify it mentions both shipments
    pass
```

#### 5.2 Integration Tests

**Flow**: Gorgias webhook with embedded fulfillment data → AI draft generation → Verify fulfillment details in draft

#### 5.3 Manual Testing Checklist

- [ ] Test single fulfillment (backward compatibility)
- [ ] Test 2 fulfillments (one delivered, one in transit)
- [ ] Test 3+ fulfillments (typical Amazon/Shopify scenario)
- [ ] Test partial shipment (some items fulfilled, some pending)
- [ ] Test multi-warehouse scenario (items from different warehouses)
- [ ] Test missing tracking info (graceful handling)
- [ ] Test warehouse data missing (fallback behavior)

---

### Phase 6: Ticket Enrichment UI Updates (Weeks 6-7)

#### 6.1 Update Ticket Display Component (Frontend)

This depends on your frontend framework, but the principle:

**Before**: Single tracking number display
```
Order #1001
Tracking: 1Z999AA...
```

**After**: Multiple fulfillments display
```
Order #1001 (3 shipments)

Shipment 1/3 - DELIVERED
├── Tracking: 1Z999AA...
├── Carrier: UPS
├── From: NJ Distribution Center
├── Delivered: Jan 15
└── Items: Fabrics (2x)

Shipment 2/3 - IN TRANSIT
├── Tracking: 7H999BB...
├── Carrier: FedEx
├── From: CA Distribution Center
├── Estimated: Jan 17
└── Items: Batting (1x), Thread (3x)

Shipment 3/3 - PENDING
└── Expected to ship: Jan 18
    Items: Backing fabric (1x)
```

---

## Implementation Checklist

### Phase 1: Data Model
- [ ] Design new `fulfillments` schema in `custom_fields`
- [ ] Document backward compatibility requirements
- [ ] Create migration plan (JSONB, no schema migration needed)
- [ ] Update type hints in Python code

### Phase 2: Shopify API
- [ ] Extend GraphQL query with `fulfillments` edge
- [ ] Test new query against Shopify API
- [ ] Parse fulfillment responses
- [ ] Handle edge cases (no fulfillments, pending orders, cancelled)
- [ ] Update response mapping code

### Phase 3: Gorgias Integration
- [ ] Parse fulfillments from webhook data
- [ ] Extract tracking info per fulfillment
- [ ] Update `_extract_shopify_metrics()` if needed
- [ ] Handle cases where webhook doesn't have fulfillment data

### Phase 4: AI Draft Generation
- [ ] Update prompt template with fulfillment context
- [ ] Test prompt with various scenarios
- [ ] Verify AI references correct shipments
- [ ] Test edge cases (delayed items, partial shipments)

### Phase 5: Testing
- [ ] Write unit tests for fulfillment extraction
- [ ] Write integration tests for full flow
- [ ] Manual testing on staging environment
- [ ] Load testing (multi-fulfillment response times)

### Phase 6: UI Updates
- [ ] Update ticket detail view
- [ ] Update order history display
- [ ] Update AI recommendation UI if needed

### Phase 7: Deployment
- [ ] Code review and approval
- [ ] Deploy to staging
- [ ] Staging smoke tests
- [ ] Deploy to production
- [ ] Monitor for errors
- [ ] Document changes for support team

---

## Backward Compatibility Considerations

### Critical: Old Tickets Won't Have Fulfillments

**Solution**:
```python
# In ai.py draft generation:
fulfillments = ticket.custom_fields.get('fulfillments', [])
if not fulfillments:
    # Fallback to old format
    order_num = ticket.custom_fields.get('order_number')
    tracking_num = ticket.custom_fields.get('tracking_number')
    # ... use single tracking number
else:
    # New format with multiple fulfillments
    # ... process array
```

### Webhook Data May Be Incomplete

**Solution**: Don't require fulfillments to be present; make them optional
```python
if fulfillments:
    analytics["fulfillments"] = fulfillments
else:
    logger.info("No fulfillment data in webhook - will use order-level tracking if available")
```

### Customers.py Order History

**Solution**: Return both formats
```python
{
    "orders": [{
        "order_id": "#1001",
        # ... existing fields ...
        "fulfillments": [...]  # NEW (optional)
    }]
}
```

---

## Performance Considerations

### GraphQL Query Size
- Adding `fulfillments` edge will increase response size
- Consider pagination: `fulfillments(first: 10)` limits to 10
- Typical order: 1-3 fulfillments, acceptable overhead

### Database Impact
- Custom fields already JSONB, no schema change
- No new tables needed
- Index on `custom_fields` may benefit full-text search

### API Response Times
- Shopify GraphQL request time: +100-200ms (estimated)
- Processing time: negligible (JSON parsing)
- Total impact: minimal

---

## Rollback Plan

If multi-fulfillment implementation causes issues:

1. **Revert Shopify Query**: Use old query without fulfillments edge
2. **Revert AI Prompt**: Remove fulfillment context from prompt template
3. **Revert Code**: Switch off fulfillment processing with feature flag
4. **Data**: No schema migration, safe to revert
5. **Tickets**: Old custom_fields will still work (backward compatible)

---

## Success Metrics

After implementation:

1. **AI Accuracy**: Can correctly identify and reference multiple shipments
2. **Customer Clarity**: Support agents can see which items shipped when/where
3. **Data Completeness**: 95%+ of orders have fulfillment data available
4. **User Experience**: Multi-warehouse orders handled as well as single-warehouse
5. **Performance**: No degradation in API response times
6. **Support Team Efficiency**: Reduction in "where is my item?" follow-ups

---

## Next Steps

1. **Week 1**: Present this roadmap to team
2. **Week 1**: Estimate effort for each phase
3. **Week 1-2**: Begin Phase 1 implementation
4. **Weekly**: Review progress and adjust timeline
5. **After Phase 3**: Begin Phase 4 testing
6. **After Phase 6**: Plan rollout and communication

