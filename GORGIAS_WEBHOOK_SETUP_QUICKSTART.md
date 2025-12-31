# Gorgias Webhook Setup - Copy/Paste Guide

## 🚀 Quick Setup (2 minutes)

### Step 1: Get Your Webhook Secret

Run this command to get your webhook secret from Railway:

```bash
# Switch to production environment
cd /Users/scottallen/quimbi-platform
railway environment production

# Get webhook secret
railway variables | grep GORGIAS_WEBHOOK_SECRET
```

**Copy the value** - it should look like:
```
GORGIAS_WEBHOOK_SECRET=08130fe49bd19885a555cb81885dfc44ec9b74d26a098a9a95f76ca55888f874
```

---

### Step 2: Configure Gorgias HTTP Integration

1. **Go to Gorgias Settings**: https://lindas.gorgias.com/app/settings/http-integrations

2. **Click "Create Integration"** (or edit existing "Quimbi AI Assistant")

3. **Fill in the form with these exact values**:

---

## 📋 Configuration Values (Copy/Paste)

### Integration Name
```
Quimbi AI Assistant - Production
```

### URL
```
https://ecommerce-backend-production-b9cc.up.railway.app/api/gorgias/webhook
```

### Method
```
POST
```

### Headers

Add this header:

**Header Name:**
```
X-Webhook-Token
```

**Header Value:**
```
[PASTE YOUR GORGIAS_WEBHOOK_SECRET VALUE HERE]
```

Example (use YOUR actual secret):
```
08130fe49bd19885a555cb81885dfc44ec9b74d26a098a9a95f76ca55888f874
```

---

### Trigger Events

Select **ONE** of these options:

**Option A: Ticket Message Created** (Recommended)
- ✅ Fires on every new message (customer OR agent)
- ✅ Best for real-time customer intelligence
- ⚠️ May fire multiple times per ticket

**Option B: Ticket Created**
- ✅ Fires once per new ticket
- ✅ Cleaner (no duplicate processing)
- ⚠️ Won't fire on follow-up messages

**Recommended**: Use **"Ticket Message Created"** for maximum coverage

---

### Enable Integration

- ✅ Check the box: **"Active"**

---

## 🧪 Step 3: Test the Connection

Click the **"Test Connection"** button in Gorgias.

**Expected Response:**
```json
{
  "status": "accepted",
  "ticket_id": "test",
  "message": "Webhook received and queued for processing"
}
```

If you see this, you're good! ✅

---

## 🎯 Step 4: Test with Real Ticket

Create a test ticket in Gorgias:

1. **Click "New Ticket"**
2. **Customer Email**: `mauldenm@earthlink.net` (real customer with order history)
3. **Message**: `Did I buy any rose thread from you recently?`
4. **Send**

**Wait 7-10 seconds** and check the ticket for:

✅ **Internal Note** with customer analytics:
```
🤖 Quimbi Customer Intelligence

📊 CUSTOMER ANALYTICS
💰 Lifetime Value: $71 (Standard)
⚠️  Churn Risk: 23% (LOW - Healthy)
...
```

✅ **Draft Reply** with personalized response

---

## 📸 Visual Guide

Here's what your Gorgias HTTP Integration form should look like:

```
┌────────────────────────────────────────────────────────────┐
│ HTTP Integration Settings                                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Integration Name:                                          │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Quimbi AI Assistant - Production                       ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ URL:                                                       │
│ ┌────────────────────────────────────────────────────────┐│
│ │ https://ecommerce-backend-production-b9cc.up.railway.  ││
│ │ app/api/gorgias/webhook                                ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ Method: [POST ▼]                                          │
│                                                            │
│ Headers:                                                   │
│ ┌──────────────────┬─────────────────────────────────────┐│
│ │ X-Webhook-Token  │ 08130fe49bd19885a555cb81885dfc44... ││
│ └──────────────────┴─────────────────────────────────────┘│
│ [+ Add Header]                                             │
│                                                            │
│ Trigger: [Ticket Message Created ▼]                       │
│                                                            │
│ ☑ Active                                                   │
│                                                            │
│ [Test Connection] [Save]                                   │
└────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Environment Variables Checklist

Verify these are set in Railway:

```bash
# Check all required variables
railway variables | grep -E "GORGIAS|ANTHROPIC|SHOPIFY"
```

**Required Variables:**
```
✓ GORGIAS_WEBHOOK_SECRET      # Webhook authentication
✓ GORGIAS_DOMAIN=lindas        # Your Gorgias subdomain
✓ GORGIAS_USERNAME             # Gorgias API username/email
✓ GORGIAS_API_KEY              # Gorgias API key (base64)
✓ ANTHROPIC_API_KEY            # Claude API key
✓ SHOPIFY_SHOP_NAME=lindas-electric-quilters
✓ SHOPIFY_ACCESS_TOKEN         # Shopify API token
```

If any are missing, set them:
```bash
railway variables set GORGIAS_WEBHOOK_SECRET=your_secret_here
```

---

## 🔍 Monitoring

Watch the webhook in action:

```bash
# Switch to production
railway environment production

# Watch logs in real-time
railway logs --follow | grep -i "gorgias\|webhook"
```

**What to look for:**
```
✅ Received Gorgias webhook for ticket #235766516
✅ [ASYNC] Starting background processing for ticket #235766516
✅ Customer ID: 7460267524351
✅ Fetching order history for customer...
✅ Successfully posted draft reply to ticket #235766516
```

---

## 🚨 Troubleshooting

### Webhook Not Firing

**Check:**
1. Integration is **Active** (checkbox enabled)
2. URL is correct (no typos)
3. Railway service is running:
   ```bash
   curl https://ecommerce-backend-production-b9cc.up.railway.app/health
   ```

### 401 Unauthorized

**Problem**: Webhook token mismatch

**Fix:**
```bash
# Get current secret from Railway
railway variables | grep GORGIAS_WEBHOOK_SECRET

# Copy EXACT value to Gorgias HTTP Integration header
# Make sure there are no extra spaces or newlines!
```

### Bot Not Responding

**Check Railway logs:**
```bash
railway logs | grep -i error

# Common issues:
# - Missing ANTHROPIC_API_KEY
# - Invalid GORGIAS_API_KEY
# - Customer not found in Shopify
```

### Wrong Customer Data

**Check:**
1. Customer has Shopify ID in Gorgias customer profile
2. Shopify integration is connected in Gorgias
3. Customer exists in Shopify database

---

## 📊 Production vs Staging URLs

| Environment | Webhook URL |
|-------------|-------------|
| **Production** (USE THIS) | `https://ecommerce-backend-production-b9cc.up.railway.app/api/gorgias/webhook` |
| Staging (testing only) | `https://ecommerce-backend-staging-a14c.up.railway.app/api/gorgias/webhook` |

**Important**: Make sure you're using the **PRODUCTION** URL!

---

## ✅ Verification Checklist

Before going live:

- [ ] Webhook URL is correct (production URL)
- [ ] X-Webhook-Token header is set with correct secret
- [ ] Method is POST
- [ ] Trigger is "Ticket Message Created"
- [ ] Integration is marked "Active"
- [ ] Test Connection returns `{"status": "accepted"}`
- [ ] Test ticket shows internal note + draft reply
- [ ] Railway logs show successful processing
- [ ] All environment variables are set in Railway

---

## 🎉 You're Done!

Once you click **Save**, the integration is live!

Every new ticket in Gorgias will automatically get:
- Customer intelligence (LTV, churn risk, purchase history)
- Priority calculation
- AI-generated draft response
- Internal notes with retention strategies

**Processing time**: 7-10 seconds per ticket
**Cost**: ~$0.0002 per ticket

---

## 🆘 Need Help?

**Check the logs:**
```bash
railway logs --follow
```

**Test endpoint manually:**
```bash
curl -X POST https://ecommerce-backend-production-b9cc.up.railway.app/api/gorgias/webhook \
  -H "X-Webhook-Token: YOUR_SECRET_HERE" \
  -H "Content-Type: application/json" \
  -d '{"id": "test123", "customer": {"email": "test@example.com"}, "messages": []}'
```

**Detailed docs:**
- [GORGIAS_INTEGRATION_ARCHITECTURE.md](GORGIAS_INTEGRATION_ARCHITECTURE.md)
- [GORGIAS_PRODUCTION_WEBHOOK_SETUP.md](docs/operations/GORGIAS_PRODUCTION_WEBHOOK_SETUP.md)

---

**Last Updated**: December 29, 2024
**Deployment**: Production (ecommerce-backend-production-b9cc)
