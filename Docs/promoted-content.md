---
title: Promoted Content (Locations & News)
status: active
last_updated: 2025-01-XX
scope: monetization
owners: [tda-core]
---

# Promoted Content (Locations & News)

## Overview

Promoted Content enables businesses to boost visibility of their locations and news posts through one-time payments via Stripe. This complements the subscription-based Premium Features Layer (EPIC-3).

## Features

### Promoted Locations
- **Trending Promotion**: Boost location visibility in trending lists (1.5x score multiplier)
- **Feed Promotion**: Prioritize location in activity feed (shown at top)
- **Both**: Combine trending and feed promotion for maximum visibility
- **Duration**: Configurable (1-365 days)
- **Payment**: One-time payment via Stripe Payment Intent

### Promoted News
- **News Feed Promotion**: Show business-created news posts at top of news feed
- **Duration**: Configurable (1-365 days)
- **Payment**: One-time payment via Stripe Payment Intent

## Database Schema

### `promoted_locations` Table
```sql
CREATE TABLE promoted_locations (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT REFERENCES business_accounts(id),
    location_id BIGINT REFERENCES locations(id),
    promotion_type promotion_type NOT NULL, -- 'trending', 'feed', 'both'
    status promotion_status NOT NULL DEFAULT 'pending', -- 'pending', 'active', 'expired', 'canceled'
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'eur',
    stripe_payment_intent_id TEXT UNIQUE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### `promoted_news` Table
```sql
CREATE TABLE promoted_news (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT REFERENCES business_accounts(id),
    news_id BIGINT REFERENCES raw_ingested_news(id),
    status promotion_status NOT NULL DEFAULT 'pending',
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'eur',
    stripe_payment_intent_id TEXT UNIQUE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

## Backend Implementation

### Services

**`PromotionService`** (`Backend/services/promotion_service.py`)
- `create_location_promotion()` - Create location promotion record
- `create_news_promotion()` - Create news promotion record
- `get_active_location_promotions()` - Query active promotions for ranking
- `get_active_news_promotions()` - Query active news promotions
- `get_promotions_for_business_account()` - List all promotions for a business
- `expire_old_promotions()` - Mark expired promotions (called by worker)

**`StripeService`** (extended in `Backend/services/stripe_service.py`)
- `create_payment_intent()` - Create one-time payment intent for promotions
- `_handle_payment_intent_succeeded()` - Process successful payment and create promotion record

### API Endpoints

**`POST /api/v1/promotions`**
- Create a new promotion (location or news)
- Returns Stripe Payment Intent client_secret for frontend confirmation
- Request body:
```json
{
  "target_id": 123,
  "promotion_type": "trending", // or "feed", "both", "news_feed"
  "duration_days": 7,
  "amount": 25.00,
  "currency": "eur",
  "success_url": "https://...",
  "cancel_url": "https://..."
}
```

**`GET /api/v1/promotions/my`**
- List all promotions for authenticated business account
- Returns combined list of location and news promotions

**`POST /api/v1/promotions/{promotion_id}/cancel`**
- Cancel an active promotion
- Only allowed for promotions owned by the business account

### Ranking Logic

**Trending Endpoints** (`Backend/api/routers/trending.py`)
- Promoted locations get 1.5x score boost
- Promoted locations appear first in results (ordered by `is_promoted DESC, boosted_score DESC`)

**Activity Feed** (`Backend/api/routers/activity.py`)
- Promoted locations appear at top of feed
- Ordered by `is_promoted DESC, created_at DESC`

**News Feed** (`Backend/api/routers/news.py`)
- Promoted news posts appear at top of feed
- Ordered by `is_promoted DESC, published_at DESC`

## Frontend Implementation

### Components

**`BusinessPromotionsPage`** (`Frontend/src/pages/BusinessPromotionsPage.tsx`)
- Main management page for promotions
- Tabs: Overview, Promote Location, Promote News
- Lists all promotions with status badges
- Cancel functionality for active promotions

**`PromoteLocationForm`** (`Frontend/src/components/promotions/PromoteLocationForm.tsx`)
- Form to create location promotion
- Fields: location_id, promotion_type, duration_days, amount
- Integrates with Stripe.js for payment confirmation

**`PromoteNewsForm`** (`Frontend/src/components/promotions/PromoteNewsForm.tsx`)
- Form to create news promotion
- Fields: news_id, duration_days, amount
- Integrates with Stripe.js for payment confirmation

### Visual Indicators

**Activity Cards** (`Frontend/src/components/feed/ActivityCard.tsx`)
- Shows "Gepromoot" badge for promoted content

**Trending Cards** (`Frontend/src/components/trending/TrendingLocationCard.tsx`)
- Shows "Gepromoot" badge for promoted locations

**News Cards** (`Frontend/src/components/news/NewsCard.tsx`)
- Shows "Gepromoot" badge for promoted news posts

## Automation

### Promotion Expiry Worker

**`Backend/app/workers/promotion_expiry_worker.py`**
- Runs hourly via GitHub Actions (`.github/workflows/tda_promotion_expiry.yml`)
- Marks expired promotions as 'expired' status
- Updates `promoted_locations` and `promoted_news` tables
- Logs expiry events for monitoring

**Schedule**: Hourly (`0 * * * *`)

## Payment Flow

1. Business creates promotion via frontend form
2. Backend creates Stripe Payment Intent
3. Frontend confirms payment using Stripe.js
4. Stripe webhook `payment_intent.succeeded` triggers promotion creation
5. Promotion record created with status 'active'
6. Promotion automatically expires at `ends_at` timestamp

## Pricing Configuration

Environment variables (see `Docs/env-config.md`):
- `STRIPE_PRICE_ID_PROMOTION_LOCATION_TRENDING`
- `STRIPE_PRICE_ID_PROMOTION_LOCATION_FEED`
- `STRIPE_PRICE_ID_PROMOTION_LOCATION_BOTH`
- `STRIPE_PRICE_ID_PROMOTION_NEWS_FEED`

Note: Currently uses flexible pricing (amount specified in request), but can be configured with fixed Stripe Price IDs.

## Security Considerations

- All endpoints require authenticated business account
- Payment intents are created server-side
- Webhook signature verification via Stripe
- Promotion records only created after successful payment
- Business account ownership verified for all operations

## Testing

- Stripe test mode for development
- Webhook testing with Stripe CLI
- Promotion lifecycle testing (create → active → expired)
- Ranking logic verification (promoted content appears first)
- Payment failure handling

## Future Enhancements

- Fixed pricing tiers (7 days, 14 days, 30 days)
- Promotion analytics (views, clicks, engagement)
- A/B testing for promotion effectiveness
- Bulk promotion discounts
- Promotion scheduling (start in future)







