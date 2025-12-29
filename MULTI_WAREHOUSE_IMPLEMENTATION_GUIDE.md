# Multi-Warehouse Fulfillment Implementation Guide

**Status**: ✅ **IMPLEMENTED** - Ready for integration and testing
**Created**: December 29, 2024
**Author**: Claude Code

---

## Executive Summary

The multi-warehouse fulfillment tracking feature is now **fully implemented** and ready for integration into the Gorgias webhook workflow.

### What's Been Built

✅ **Shopify Fulfillment Service** ([integrations/shopify_fulfillment_service.py](integrations/shopify_fulfillment_service.py))
- Fetches complete fulfillment data via Shopify GraphQL API
- Supports multiple fulfillments per order
- Tracks warehouse/location information
- Extracts tracking numbers and carrier details
- Detects split shipment scenarios automatically

✅ **Ticket Enrichment Module** ([integrations/ticket_fulfillment_enricher.py](integrations/ticket_fulfillment_enricher.py))
- Enriches Gorgias tickets with fulfillment data
- Formats data for AI context
- Generates internal notes for agents
- Extracts order numbers from tickets automatically

✅ **Test Suite** ([scripts/test_fulfillment_service.py](scripts/test_fulfillment_service.py))
- Comprehensive testing script
- Example usage demonstrations
- Sharon's scenario simulation

---

## Quick Start

### 1. Prerequisites

**Environment Variables** (already configured in Railway authentic-comfort):
```bash
SHOPIFY_SHOP_NAME=lindas-electric-quilters  # ✅ Already set
SHOPIFY_ACCESS_TOKEN=shpat_590bdb...          # ✅ Already set
SHOPIFY_API_VERSION=2024-10                   # ✅ Already set
```

### 2. Test the Service

```bash
# Navigate to platform root
cd /Users/scottallen/quimbi-platform

# Make test script executable
chmod +x scripts/test_fulfillment_service.py

# Test with a real order number
python scripts/test_fulfillment_service.py --order-number 1001

# Test Sharon's scenario (requires actual order with split shipment)
python scripts/test_fulfillment_service.py --customer sharonbrz@verizon.net
```

### 3. Expected Output

The test will show:
- ✅ Order details (ID, name, status)
- ✅ Split shipment detection
- ✅ Fulfillment details (warehouse, tracking, items)
- ✅ Unfulfilled items
- ✅ AI-formatted context
- ✅ Internal note format

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     GORGIAS WEBHOOK FLOW                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              gorgias_ai_assistant.py (existing)                 │
│  - Receives webhook                                             │
│  - Validates signature                                          │
│  - Extracts customer + order info                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│         ticket_fulfillment_enricher.py (NEW)                    │
│  - Enriches ticket with fulfillment data                        │
│  - Calls Shopify Fulfillment Service                            │
│  - Detects split shipments                                      │
│  - Formats for AI and agents                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│       shopify_fulfillment_service.py (NEW)                      │
│  - GraphQL queries to Shopify                                   │
│  - Fetches fulfillments, tracking, warehouses                   │
│  - Returns structured data                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ Shopify API   │
                      └───────────────┘
```

### Data Flow

1. **Gorgias Ticket Created** → Webhook arrives
2. **Extract Order Number** → From subject, body, or custom fields
3. **Fetch Fulfillments** → Query Shopify GraphQL API
4. **Detect Split Shipments** → Analyze warehouse/tracking data
5. **Enrich Ticket** → Add to `custom_fields`
6. **Format for AI** → Include in draft generation context
7. **Post Internal Note** → Display to agents in Gorgias

---

## API Reference

### ShopifyFulfillmentService

```python
from integrations.shopify_fulfillment_service import get_fulfillment_service

service = get_fulfillment_service()

# Get fulfillments by order number
fulfillments = await service.get_order_by_number(1001)

# Get fulfillments by order ID
fulfillments = await service.get_order_fulfillments("gid://shopify/Order/12345")

# Detect split shipment scenario
analysis = service.detect_split_shipment_scenario(fulfillments)
```

**Returns**:
```python
{
    "order_id": "12345",
    "order_name": "#1001",
    "order_number": 1001,
    "fulfillment_status": "PARTIALLY_FULFILLED",
    "total_items": 5,
    "fulfilled_items_count": 3,
    "unfulfilled_items_count": 2,
    "has_split_shipments": True,
    "fulfillment_count": 2,
    "fulfillments": [
        {
            "fulfillment_id": "67890",
            "status": "SUCCESS",
            "tracking_info": [
                {
                    "number": "1Z999AA10123456784",
                    "company": "UPS",
                    "url": "https://..."
                }
            ],
            "location": {
                "id": "123",
                "name": "New Jersey Distribution Center",
                "address": "Newark, NJ"
            },
            "items": [
                {"title": "Rose Thread", "sku": "THREAD-001", "quantity": 2}
            ]
        },
        ...
    ],
    "unfulfilled_items": [...]
}
```

### Ticket Enrichment

```python
from integrations.ticket_fulfillment_enricher import enrich_ticket_with_fulfillments

# Enrich a Gorgias ticket
enriched = await enrich_ticket_with_fulfillments(
    ticket_data=gorgias_ticket,
    order_number=1001  # or order_id="gid://..."
)

# Add to ticket custom_fields
ticket["custom_fields"].update(enriched)
```

### AI Context Formatting

```python
from integrations.ticket_fulfillment_enricher import format_fulfillment_summary_for_ai

# Generate AI-readable summary
ai_context = format_fulfillment_summary_for_ai(enriched)

# Include in AI prompt
prompt = f"""
Customer message: {message}

Fulfillment Status:
{ai_context}

Generate a helpful response...
"""
```

### Internal Note Formatting

```python
from integrations.ticket_fulfillment_enricher import format_fulfillment_for_internal_note

# Generate Markdown note for agents
note = format_fulfillment_for_internal_note(enriched)

# Post to Gorgias
await gorgias_client.add_note(ticket_id, note)
```

---

## Integration with Gorgias Webhook

### Step 1: Update `gorgias_ai_assistant.py`

Add fulfillment enrichment to the webhook processing flow:

```python
# In gorgias_ai_assistant.py, around line 500 (in handle_ticket_webhook method)

from integrations.ticket_fulfillment_enricher import (
    enrich_ticket_with_fulfillments,
    format_fulfillment_summary_for_ai,
    format_fulfillment_for_internal_note
)

async def handle_ticket_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming Gorgias ticket webhook."""

    # ... existing code ...

    # NEW: Enrich with fulfillment data
    enriched_fulfillment = await enrich_ticket_with_fulfillments(
        ticket_data=webhook_data,
        order_number=extracted_order_number  # From existing extraction logic
    )

    # Add to analytics for AI context
    if enriched_fulfillment:
        analytics["fulfillment"] = enriched_fulfillment

        # Format for AI prompt
        fulfillment_context = format_fulfillment_summary_for_ai(enriched_fulfillment)

        # Add to AI prompt (in generate_draft_response method)
        # ... include fulfillment_context in prompt ...

        # Post internal note to Gorgias
        if enriched_fulfillment.get("has_split_shipment"):
            note = format_fulfillment_for_internal_note(enriched_fulfillment)
            await self.post_internal_note(ticket_id, note)

    # ... rest of existing code ...
```

### Step 2: Update AI Prompt Template

Modify the prompt generation to include fulfillment context:

```python
def _build_ai_prompt(self, customer_context, message, analytics):
    """Build prompt for AI draft generation."""

    # ... existing prompt building ...

    # NEW: Add fulfillment context
    fulfillment = analytics.get("fulfillment", {})
    if fulfillment:
        prompt += "\n\nFULFILLMENT INFORMATION:\n"
        prompt += format_fulfillment_summary_for_ai(fulfillment)

        # Special instructions for split shipments
        if fulfillment.get("has_split_shipment"):
            prompt += "\n\nIMPORTANT: This order has SPLIT SHIPMENTS. "
            prompt += "If the customer asks about a missing item, check if it's "
            prompt += "in a different shipment before assuming it's actually missing."

    return prompt
```

### Step 3: Deploy to Railway

```bash
# Commit changes
git add integrations/shopify_fulfillment_service.py
git add integrations/ticket_fulfillment_enricher.py
git add scripts/test_fulfillment_service.py
git add MULTI_WAREHOUSE_IMPLEMENTATION_GUIDE.md

git commit -m "Add multi-warehouse fulfillment tracking

- Shopify GraphQL integration for fulfillment data
- Split shipment detection
- AI context formatting
- Internal note generation
- Test suite and documentation
"

# Push to Railway (auto-deploys)
git push origin main

# Monitor deployment
railway logs --follow
```

---

## Sharon's Scenario - How It Works

### Before Implementation ❌

**Customer Email**: "Where is Item X from my order?"

**Agent Workflow**:
1. Read ticket
2. Go to Shopify manually
3. Search order number
4. Check fulfillments
5. Find second warehouse shipment
6. Copy tracking number
7. Reply to customer

**Time**: 2-3 minutes per ticket

---

### After Implementation ✅

**Customer Email**: "Where is Item X from my order?"

**Automated Workflow**:
1. Webhook arrives in Gorgias
2. System extracts order number
3. Fetches fulfillment data from Shopify
4. Detects split shipment (2 warehouses)
5. Generates AI draft:

```
Hi Sharon,

Thank you for reaching out! I can see your order #1001 is being delivered
in two separate shipments from different warehouses for faster delivery.

**Shipment 1** (Already delivered)
From: New Jersey Distribution Center
Tracking: UPS 1Z999AA10123456784
Items: Rose Thread Bundle (qty: 2), Blue Fabric Roll (qty: 1)

**Shipment 2** (In transit - this includes Item X you asked about!)
From: California Distribution Center
Tracking: FedEx 771234567890
Items: Premium Scissors (qty: 1), Item X (qty: 2)
Estimated Delivery: January 17, 2025

Your second package is currently on its way and should arrive by Thursday.
You can track it here: [tracking link]

Is there anything else I can help you with?

Best regards,
Linda's Team
```

6. Internal note posted automatically for agent review
7. Agent reviews, edits if needed, sends

**Time**: 30 seconds to review and send

**Time Saved**: 1.5-2.5 minutes per ticket × 10 tickets/week = **15-25 minutes/week**

---

## Testing Checklist

### Unit Tests

- [ ] Test `ShopifyFulfillmentService.get_order_fulfillments()`
- [ ] Test `ShopifyFulfillmentService.get_order_by_number()`
- [ ] Test `ShopifyFulfillmentService.detect_split_shipment_scenario()`
- [ ] Test `enrich_ticket_with_fulfillments()`
- [ ] Test `extract_order_number_from_ticket()`
- [ ] Test `format_fulfillment_summary_for_ai()`
- [ ] Test `format_fulfillment_for_internal_note()`

### Integration Tests

- [ ] Test with single fulfillment order
- [ ] Test with split shipment (2+ warehouses)
- [ ] Test with partially fulfilled order
- [ ] Test with unfulfilled order
- [ ] Test with invalid order number
- [ ] Test with Gorgias webhook payload

### End-to-End Tests

- [ ] Create test ticket in Gorgias
- [ ] Verify fulfillment data fetched
- [ ] Verify internal note posted
- [ ] Verify AI draft generated with fulfillment context
- [ ] Verify split shipment detection works
- [ ] Verify tracking URLs are correct

---

## Monitoring & Observability

### Logs to Watch

```bash
# In Railway logs, look for:
✅ "Shopify fulfillment service initialized"
✅ "Fetching fulfillments for order #1001"
✅ "Retrieved 2 fulfillment(s) for order #1001"
✅ "Enriched ticket with 2 fulfillment(s) (split shipment)"

# Errors to watch for:
❌ "Shopify API error: 429" (rate limit)
❌ "Order not found: #1001" (invalid order)
❌ "Timeout fetching fulfillments" (slow API)
```

### Metrics to Track

- **Fulfillment Fetch Success Rate**: Should be >95%
- **Average Fetch Time**: Should be <2 seconds
- **Split Shipment Detection Rate**: Track % of orders with splits
- **Agent Time Saved**: Track time spent on fulfillment-related tickets

---

## Troubleshooting

### Issue: "Fulfillment service not configured"

**Solution**: Check environment variables
```bash
railway variables | grep SHOPIFY
```

### Issue: "Order not found"

**Possible causes**:
- Order number extraction failed
- Order doesn't exist in Shopify
- Permissions issue with API token

**Solution**: Check logs for order number extraction, verify order exists

### Issue: "No fulfillments returned"

**Possible causes**:
- Order not yet fulfilled
- Fulfillment created in Shopify POS (different data structure)

**Solution**: Check order status in Shopify admin

### Issue: "Split shipment not detected"

**Possible causes**:
- All items from same warehouse (not actually a split)
- Fulfillments created as single fulfillment with multiple tracking numbers

**Solution**: Review fulfillment structure in Shopify

---

## Rollback Plan

If issues occur after deployment:

1. **Immediate**: Disable fulfillment enrichment in webhook handler
   ```python
   # Comment out the enrichment call:
   # enriched_fulfillment = await enrich_ticket_with_fulfillments(...)
   ```

2. **Redeploy**:
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **Monitor**: Check logs for errors to clear

4. **Fix**: Address issues, re-test, re-deploy

---

## Next Steps

### Phase 1: Integration (1-2 hours)
- [ ] Add enrichment call to `gorgias_ai_assistant.py`
- [ ] Update AI prompt template
- [ ] Add internal note posting
- [ ] Test locally with mock data

### Phase 2: Testing (2-3 hours)
- [ ] Write unit tests
- [ ] Test with real Shopify orders
- [ ] Test Gorgias webhook flow end-to-end
- [ ] Verify AI drafts include fulfillment context

### Phase 3: Deployment (30 minutes)
- [ ] Commit and push to Railway
- [ ] Monitor deployment logs
- [ ] Test with real ticket
- [ ] Verify in Gorgias UI

### Phase 4: Validation (1 week)
- [ ] Monitor error logs daily
- [ ] Collect agent feedback
- [ ] Measure time savings
- [ ] Adjust AI prompts based on draft quality

---

## Cost Analysis

### API Calls

**Per ticket with order**:
- 1x Shopify GraphQL query for fulfillments (~0.5s)
- Cost: Free (included in Shopify plan)

**Impact**:
- Adds ~0.5-1 second to webhook processing time
- Well within Gorgias webhook timeout (30s)

### Compute

**Additional compute**: Minimal
- Enrichment logic runs in-memory
- No database writes
- Async processing (non-blocking)

### ROI

**Time Saved**:
- 2 minutes per multi-warehouse ticket
- Estimate 10-20 tickets/week
- **20-40 minutes saved per week**

**Agent Experience**:
- Faster responses
- More accurate information
- Better customer satisfaction

---

## Success Criteria

✅ **Technical**:
- Fulfillment data fetched successfully >95% of time
- Webhook processing time <5 seconds
- No increase in error rate
- Split shipment detection works correctly

✅ **Business**:
- Reduced time spent on fulfillment-related tickets
- Improved first-response accuracy
- Positive agent feedback
- Reduced customer confusion about split shipments

---

## Support

**Documentation**:
- This guide: `MULTI_WAREHOUSE_IMPLEMENTATION_GUIDE.md`
- API docs: See docstrings in source files
- Test examples: `scripts/test_fulfillment_service.py`

**Questions**:
- Check logs: `railway logs --follow`
- Review code comments in implementation files
- Test locally with `test_fulfillment_service.py`

---

**Last Updated**: December 29, 2024
**Implementation Status**: ✅ Complete - Ready for Integration
**Next Action**: Integrate into Gorgias webhook handler
