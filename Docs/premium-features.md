---
title: Premium Features Layer
status: active
last_updated: 2025-01-XX
scope: monetization
owners: [tda-core]
---

# Premium Features Layer

## Overview

Premium Features Layer enables monetization through subscription tiers, providing businesses with enhanced location information, advanced analytics, and premium visuals.

## Subscription Tiers

### Basic (Free)
- Standard location claiming
- Basic analytics (views, likes)
- Standard location display

### Premium
- Enhanced location information
- Advanced analytics dashboard
- Priority support
- Premium location badges
- Extended analytics history (90 days)

### Pro
- All Premium features
- API access
- Custom branding
- Dedicated account manager
- Unlimited analytics history

## Payment Provider

### Stripe (Primary)
- **Decision**: Use Stripe for payment processing
- **Rationale**:
  - Industry standard
  - Excellent documentation
  - Webhook support for subscription events
  - Support for multiple payment methods
  - Strong security and compliance

### Implementation
- Stripe Customer creation on business account creation
- Subscription management via Stripe
- Webhook handling for subscription events
- Payment intent handling for one-time payments (promoted content - see `Docs/promoted-content.md`)

## Premium Features

### 1. Enhanced Location Information
- Extended business hours
- Multiple photos
- Video content
- Menu/price information
- Special offers/promotions

### 2. Advanced Analytics
- Extended analytics history (90 days vs 30 days)
- Export capabilities
- Custom date ranges
- Comparison tools
- Predictive insights

### 3. Premium Visuals
- Custom location badges
- Featured placement in search results
- Enhanced map markers
- Custom location pages

### 4. Priority Features
- Priority verification for location claims
- Faster support response times
- Early access to new features

## Database Schema

### Existing Tables
- `business_accounts`: Contains `subscription_tier` and Stripe fields
- `business_subscriptions`: Subscription history

### New Tables
- `premium_features`: Feature flags per account
- `payment_transactions`: Audit trail for all payments

## API Endpoints

### `POST /premium/subscribe`
Initiates subscription flow:
- Creates Stripe Checkout session
- Returns checkout URL
- Handles subscription creation

### `GET /premium/features`
Lists available features per tier:
```json
{
  "tier": "premium",
  "features": [
    "enhanced_location_info",
    "advanced_analytics",
    "priority_support"
  ]
}
```

### `POST /premium/webhook`
Stripe webhook handler:
- Processes subscription events
- Updates business_accounts table
- Handles payment failures
- Manages subscription cancellations

### `GET /premium/subscription`
Returns current subscription status:
```json
{
  "tier": "premium",
  "status": "active",
  "current_period_end": "2025-02-01T00:00:00Z",
  "cancel_at_period_end": false
}
```

## Frontend Components

### PremiumPage
- Subscription tiers comparison
- Feature list per tier
- Payment form (Stripe Elements)
- Current subscription status
- Upgrade/downgrade flows

### FeatureGate
- Betaalmuur component
- Shows upgrade prompt for premium features
- Handles feature access checks

## Access Control

- Feature checks via `premium_service.py`
- Middleware for premium endpoints
- Frontend feature gating
- Graceful degradation for non-premium users

## Security Considerations

- Stripe webhook signature verification
- Secure storage of Stripe customer IDs
- PCI compliance (Stripe handles card data)
- Audit logging for all payment transactions

## Testing

- Stripe test mode for development
- Webhook testing with Stripe CLI
- Subscription lifecycle testing
- Payment failure handling
- Refund processing

## Future Enhancements

- Annual subscription discounts
- Team plans (multiple business accounts)
- Usage-based pricing
- Add-on features
- Gift subscriptions

