# Shopify Integration - Code Reference Guide

## Quick Navigation

### 1. Gorgias Webhook Processing
**File**: `/Users/scottallen/quimbi-platform/integrations/gorgias_ai_assistant.py`

#### Key Methods:
- **`handle_ticket_webhook()`** (line 123-282)
  - Main entry point for webhook processing
  - Extracts customer ID and processes message
  - Calls enrichment and draft generation
  
- **`_extract_shopify_metrics()`** (line 689-767)
  - Extracts LTV, order count, customer tags from webhook
  - Looks for `customer.integrations.shopify` in webhook data
  - Returns: `shopify_metrics` dict with lifetime_value, total_orders, tags, etc.

- **`_extract_customer_id()`** (line 284-357)
  - Tries multiple methods to find customer ID:
    1. external_id (Shopify customer ID)
    2. meta.shopify_customer_id
    3. integrations.shopify.customer.id
    4. phone number lookup
    5. email fallback
  - Supports SMS phone lookups via `shopify_customer_lookup`

- **`_merge_analytics()`** (line 769-830)
  - Merges Shopify metrics with behavioral database
  - Shopify data is PRIMARY, DB data is supplemental
  - Returns combined analytics object

### 2. Direct Shopify API Integration
**File**: `/Users/scottallen/quimbi-platform/backend/api/routers/customers.py`

#### Endpoint:
```
GET /api/mcp/customer/{customer_id}/orders
Query params:
  - limit: int (default 50, max 100)
  - search_terms: comma-separated products (optional)
  - months_ago: filter to N months (optional)
```

#### Method: `get_customer_order_history()` (line 320-549)
```python
# Converts customer_id to Shopify GID
shopify_gid = f"gid://shopify/Customer/{customer_id}"

# GraphQL query fetches:
# - customer.orders with sorting by CREATED_AT
# - lineItems (up to 100 per order)
# - product metadata: title, vendor, productType

# Returns order array with:
# - order_id (order name like "#1001")
# - shopify_order_id (GID)
# - created_at
# - total, currency
# - products array with vendor, product_title, product_type
```

### 3. AI Draft Generation
**File**: `/Users/scottallen/quimbi-platform/backend/api/routers/ai.py`

#### Endpoints:
```
GET /api/ai/tickets/{ticket_id}/draft-response
POST /api/ai/tickets/{ticket_id}/draft-response/regenerate
```

#### Key Functions:

- **`get_customer_recent_products()`** (line 63-141)
  - Queries Shopify GraphQL for customer orders
  - Extracts line items: title, vendor, sku, variant, quantity
  - Returns up to 20 unique products

- **`generate_draft_response()`** (line 441-666)
  - Builds prompt with customer context
  - Includes tracking info from ticket.custom_fields:
    ```python
    order_num = ticket.custom_fields.get('order_number')
    tracking_num = ticket.custom_fields.get('tracking_number')
    carrier = ticket.custom_fields.get('carrier')
    carrier_status = ticket.custom_fields.get('carrier_status')
    items = ticket.custom_fields.get('items', [])  # Array of {name, quantity}
    ```
  - Includes customer behavioral profile
  - Uses Claude Haiku for generation

#### Tracking Data Built into Prompt (lines 541-588):
```python
tracking_str = ""
if ticket.custom_fields and isinstance(ticket.custom_fields, dict):
    order_num = ticket.custom_fields.get('order_number')
    tracking_num = ticket.custom_fields.get('tracking_number')
    carrier = ticket.custom_fields.get('carrier')
    status = ticket.custom_fields.get('carrier_status')
    last_update = ticket.custom_fields.get('last_update')
    estimated_delivery = ticket.custom_fields.get('estimated_delivery')
    delivered_date = ticket.custom_fields.get('delivered_date')
    items = ticket.custom_fields.get('items', [])
    
    if order_num:
        tracking_str = f"\n\nOrder Information (USE THIS DATA - it's real):"
        tracking_str += f"\n- Order Number: {order_num}"
        if items:
            tracking_str += "\n- Items in this order:"
            for item in items:
                tracking_str += f"\n  * {item.get('name')} (qty: {item.get('quantity')})"
        # ... carrier info, tracking, status, dates
```

### 4. Customer Phone Lookup
**File**: `/Users/scottallen/quimbi-platform/integrations/shopify_customer_lookup.py`

#### Usage:
```python
from integrations.shopify_customer_lookup import get_shopify_lookup

lookup = get_shopify_lookup()
customer_id = await lookup.lookup_by_phone("+1 555 123 4567")
```

#### Key Method: `lookup_by_phone()` (line 80-173)
- Normalizes phone to E.164 format: "+1234567890"
- GraphQL query with Shopify search syntax: `phone:{phone}`
- Returns legacyResourceId (numeric customer ID)

#### Phone Normalization (line 41-78):
- "(555) 123-4567" → "+15551234567"
- "555-123-4567" → "+15551234567"
- "10 digits" → "+1{digits}"

### 5. Data Models
**File**: `/Users/scottallen/quimbi-platform/backend/models/ticket.py`

#### Ticket Model (line 21-82):
```python
class Ticket(Base):
    id = Column(UUID, primary_key=True)
    ticket_number = Column(String(20), unique=True)
    customer_id = Column(String(255))
    channel = Column(String(50))  # email, sms, phone, chat
    status = Column(String(50))  # open, pending, closed
    priority = Column(String(50))  # urgent, high, normal, low
    subject = Column(String(500))
    tags = Column(JSONB)  # ["vip", "shipping_issue", ...]
    custom_fields = Column(JSONB)  # Flexible for order/tracking data
    
    # Relationships
    messages = relationship("TicketMessage")
    notes = relationship("TicketNote")
    ai_recommendations = relationship("TicketAIRecommendation")
```

#### Custom Fields Structure (from ai.py usage):
```python
custom_fields = {
    "order_number": "1001",
    "tracking_number": "1Z999AA10123456784",
    "carrier": "UPS",
    "carrier_status": "in_transit",
    "last_update": "2025-01-15T15:30:00Z",
    "estimated_delivery": "2025-01-17",
    "delivered_date": "2025-01-17T10:00:00Z",
    "items": [
        {"name": "Fabric Roll A", "quantity": 2},
        {"name": "Thread Pack", "quantity": 1}
    ],
    "replacement_order": "1002",
    "replacement_tracking": "1Z999AA10123456785",
    "replacement_status": "shipped",
    "estimated_ship_date": "2025-01-16"
}
```

---

## Data Flow Diagram

### Gorgias Webhook Flow:
```
[Gorgias Ticket Webhook]
         ↓
[GorgiasAIAssistant.handle_ticket_webhook()]
         ├── Extract customer ID
         │   └── _extract_customer_id()
         │       ├── Try external_id
         │       ├── Try meta.shopify_customer_id
         │       ├── Try integrations.shopify.customer.id
         │       ├── Try phone lookup
         │       └── Fallback to email
         │
         ├── Extract Shopify metrics
         │   └── _extract_shopify_metrics()
         │       ├── LTV (total_spent)
         │       ├── Order count (orders_count)
         │       ├── Customer age (created_at)
         │       ├── Recent orders (first 3)
         │       └── Tags (LCC_Member, etc.)
         │
         ├── Fetch behavioral analytics
         │   └── _get_customer_analytics()
         │       └── [Query analytics DB]
         │
         ├── Merge analytics
         │   └── _merge_analytics()
         │       └── Shopify + DB = combined
         │
         └── Generate draft reply
             └── _generate_draft_reply()
                 ├── Claude Haiku API call
                 └── Post to Gorgias as internal note
```

### Direct API Flow:
```
[Client Request]
GET /api/mcp/customer/{id}/orders
         ↓
[get_customer_order_history()]
         ├── Convert ID to Shopify GID
         ├── Build GraphQL query
         ├── Query Shopify Admin API
         ├── Parse order edges
         ├── Extract line items per order
         ├── Optional: Filter by search_terms
         ├── Optional: Filter by date (months_ago)
         └── Return orders array
```

---

## GraphQL Query Examples

### Customer Orders (from customers.py):
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
                title
                quantity
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
        }
      }
    }
  }
}
```

### Recent Products (from ai.py):
```graphql
query ($id: ID!, $limit: Int!) {
  customer(id: $id) {
    orders(first: $limit, sortKey: CREATED_AT, reverse: true) {
      nodes {
        createdAt
        lineItems(first: 20) {
          nodes {
            title
            vendor
            sku
            quantity
            variant {
              title
            }
          }
        }
      }
    }
  }
}
```

### Customer Phone Lookup (from shopify_customer_lookup.py):
```graphql
query ($query: String!) {
  customers(first: 1, query: $query) {
    edges {
      node {
        id
        legacyResourceId
        phone
        email
        firstName
        lastName
      }
    }
  }
}
```

---

## Configuration

### Environment Variables:
```
# Shopify API
SHOPIFY_SHOP_NAME=linda                    # Shop name (not full URL)
SHOPIFY_ACCESS_TOKEN=shpat_xxxxx...       # Admin API token
SHOPIFY_API_VERSION=2024-10               # GraphQL API version

# Gorgias
GORGIAS_DOMAIN=yourcompany                # Gorgias domain
GORGIAS_USERNAME=admin@example.com        # Gorgias account email
GORGIAS_API_KEY=xxxxx...                  # Gorgias API key
GORGIAS_WEBHOOK_SECRET=xxxxx...           # Webhook validation token

# Analytics
ADMIN_KEY=xxxxx...                        # API key for analytics endpoints
ANTHROPIC_API_KEY=sk-ant-xxxxx...         # Claude API key
API_BASE_URL=http://localhost:8000        # Analytics server URL
```

---

## Key Limitations & Gaps

### ❌ NOT IMPLEMENTED:
1. **Fulfillment Queries**: No `fulfillments` edge in GraphQL
2. **Tracking Numbers**: Not fetched, stored externally
3. **Multi-warehouse**: Can't handle split shipments
4. **Fulfillment Status**: Not queried per item
5. **Warehouse Identification**: No origin tracking

### ⚠️ PARTIAL IMPLEMENTATION:
1. **Tracking Data**: Stored in custom_fields but not fetched from Shopify
2. **Recent Orders**: Extracted from webhook but fields not documented
3. **Line Items**: Available in API but not in real-time webhook context

### ✅ IMPLEMENTED:
1. **LTV & Order Count**: From Shopify webhook integration data
2. **Customer Tags**: Shopify tags parsed for LCC membership
3. **Product History**: Via GraphQL API query
4. **Phone Lookup**: By phone number using GraphQL search

---

## Testing Endpoints

### Get Customer Orders:
```bash
curl -H "X-API-Key: {ADMIN_KEY}" \
  http://localhost:8000/api/mcp/customer/7408502702335/orders?limit=10
```

### Get AI Draft:
```bash
curl -H "X-API-Key: {ADMIN_KEY}" \
  http://localhost:8000/api/ai/tickets/T-001/draft-response
```

### Regenerate with Parameters:
```bash
curl -X POST \
  -H "X-API-Key: {ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"tone": "apologetic", "length": "long"}' \
  http://localhost:8000/api/ai/tickets/T-001/draft-response/regenerate
```

---

## Common Issues & Troubleshooting

### Issue: "Customer not found in Shopify"
**Cause**: Customer ID format incorrect or doesn't exist
**Solution**: Verify Shopify customer ID is numeric, not GID

### Issue: "No customer message to respond to"
**Cause**: Webhook has no customer messages
**Solution**: Check `_is_automated_or_test_message()` filters

### Issue: "Tracking information missing"
**Cause**: custom_fields not populated in ticket
**Solution**: Tracking must be pre-populated from external source (not fetched from Shopify)

### Issue: "Multiple shipments showing as one"
**Cause**: Only single tracking number supported
**Solution**: Would need fulfillment array implementation (currently not supported)

