# Backend/services/stripe_service.py
from __future__ import annotations

import os
from typing import Dict, Any, Optional
from datetime import datetime

import stripe

from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class StripeService:
    """
    Service for Stripe payment and subscription management.
    """
    
    def __init__(self):
        if not stripe.api_key:
            logger.warning("stripe_api_key_missing", message="Stripe API key not configured")
    
    async def create_customer(
        self,
        business_account_id: int,
        email: str,
        name: Optional[str] = None,
    ) -> str:
        """
        Create a Stripe customer for a business account.
        
        Args:
            business_account_id: Business account ID
            email: Customer email
            name: Customer name (optional)
            
        Returns:
            Stripe customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    "business_account_id": str(business_account_id),
                },
            )
            
            # Update business account with Stripe customer ID
            update_sql = """
                UPDATE business_accounts
                SET stripe_customer_id = $1, updated_at = now()
                WHERE id = $2
            """
            await execute(update_sql, customer.id, business_account_id)
            
            logger.info(
                "stripe_customer_created",
                business_account_id=business_account_id,
                stripe_customer_id=customer.id,
            )
            
            return customer.id
            
        except Exception as e:
            logger.error(
                "stripe_customer_creation_failed",
                business_account_id=business_account_id,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def create_checkout_session(
        self,
        business_account_id: int,
        tier: str,  # 'premium' or 'pro'
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            business_account_id: Business account ID
            tier: Subscription tier ('premium' or 'pro')
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancellation
            
        Returns:
            Dict with checkout session URL
        """
        # Get business account
        account_sql = """
            SELECT owner_user_id, stripe_customer_id, contact_email
            FROM business_accounts
            WHERE id = $1
        """
        account_rows = await fetch(account_sql, business_account_id)
        
        if not account_rows:
            raise ValueError("Business account not found")
        
        account = account_rows[0]
        customer_id = account["stripe_customer_id"]
        email = account.get("contact_email")
        
        # Create or get customer
        if not customer_id:
            customer_id = await self.create_customer(
                business_account_id=business_account_id,
                email=email or f"business-{business_account_id}@example.com",
            )
        
        # Price IDs from Stripe (should be in environment or config)
        price_ids = {
            "premium": os.getenv("STRIPE_PRICE_ID_PREMIUM"),
            "pro": os.getenv("STRIPE_PRICE_ID_PRO"),
        }
        
        price_id = price_ids.get(tier)
        if not price_id:
            raise ValueError(f"Invalid tier: {tier}")
        
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "business_account_id": str(business_account_id),
                    "tier": tier,
                },
            )
            
            logger.info(
                "stripe_checkout_session_created",
                business_account_id=business_account_id,
                session_id=session.id,
                tier=tier,
            )
            
            return {
                "session_id": session.id,
                "url": session.url,
            }
            
        except Exception as e:
            logger.error(
                "stripe_checkout_session_failed",
                business_account_id=business_account_id,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook event.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature header
            
        Returns:
            Dict with processing result
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("Stripe webhook secret not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error("stripe_webhook_invalid_payload", error=str(e))
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error("stripe_webhook_invalid_signature", error=str(e))
            raise
        
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        logger.info(
            "stripe_webhook_received",
            event_type=event_type,
            event_id=event["id"],
        )
        
        # Handle different event types
        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(event_data)
        elif event_type == "customer.subscription.created":
            await self._handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            await self._handle_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(event_data)
        elif event_type == "payment_intent.succeeded":
            await self._handle_payment_intent_succeeded(event_data)
        
        return {"processed": True, "event_type": event_type}
    
    async def _handle_checkout_completed(self, session: Dict[str, Any]) -> None:
        """Handle checkout.session.completed event."""
        business_account_id = session.get("metadata", {}).get("business_account_id")
        if not business_account_id:
            return
        
        # Subscription will be handled by subscription.created event
        logger.info(
            "stripe_checkout_completed",
            business_account_id=business_account_id,
            session_id=session["id"],
        )
    
    async def _handle_subscription_created(self, subscription: Dict[str, Any]) -> None:
        """Handle customer.subscription.created event."""
        customer_id = subscription["customer"]
        
        # Get business account by Stripe customer ID
        account_sql = """
            SELECT id FROM business_accounts WHERE stripe_customer_id = $1
        """
        account_rows = await fetch(account_sql, customer_id)
        
        if not account_rows:
            logger.warning(
                "stripe_subscription_no_account",
                customer_id=customer_id,
            )
            return
        
        business_account_id = account_rows[0]["id"]
        tier = subscription.get("metadata", {}).get("tier", "premium")
        
        # Update business account
        update_sql = """
            UPDATE business_accounts
            SET 
                subscription_tier = $1::subscription_tier,
                subscription_status = 'active',
                stripe_subscription_id = $2,
                current_period_end = to_timestamp($3),
                updated_at = now()
            WHERE id = $4
        """
        await execute(
            update_sql,
            tier,
            subscription["id"],
            subscription["current_period_end"],
            business_account_id,
        )
        
        # Create subscription record
        sub_sql = """
            INSERT INTO business_subscriptions (
                business_account_id, stripe_subscription_id, tier, status,
                current_period_start, current_period_end
            )
            VALUES ($1, $2, $3::subscription_tier, $4, to_timestamp($5), to_timestamp($6))
            ON CONFLICT (stripe_subscription_id) DO UPDATE
            SET tier = EXCLUDED.tier, status = EXCLUDED.status,
                current_period_start = EXCLUDED.current_period_start,
                current_period_end = EXCLUDED.current_period_end,
                updated_at = now()
        """
        await execute(
            sub_sql,
            business_account_id,
            subscription["id"],
            tier,
            subscription["status"],
            subscription["current_period_start"],
            subscription["current_period_end"],
        )
        
        logger.info(
            "stripe_subscription_created",
            business_account_id=business_account_id,
            subscription_id=subscription["id"],
            tier=tier,
        )
    
    async def _handle_subscription_updated(self, subscription: Dict[str, Any]) -> None:
        """Handle customer.subscription.updated event."""
        # Similar to created, update existing subscription
        customer_id = subscription["customer"]
        
        account_sql = """
            SELECT id FROM business_accounts WHERE stripe_customer_id = $1
        """
        account_rows = await fetch(account_sql, customer_id)
        
        if not account_rows:
            return
        
        business_account_id = account_rows[0]["id"]
        
        # Update subscription record
        sub_sql = """
            UPDATE business_subscriptions
            SET 
                tier = $1::subscription_tier,
                status = $2,
                current_period_start = to_timestamp($3),
                current_period_end = to_timestamp($4),
                updated_at = now()
            WHERE stripe_subscription_id = $5
        """
        await execute(
            sub_sql,
            subscription.get("metadata", {}).get("tier", "premium"),
            subscription["status"],
            subscription["current_period_start"],
            subscription["current_period_end"],
            subscription["id"],
        )
        
        # Update business account if subscription is active
        if subscription["status"] == "active":
            update_sql = """
                UPDATE business_accounts
                SET 
                    subscription_status = 'active',
                    current_period_end = to_timestamp($1),
                    updated_at = now()
                WHERE id = $2
            """
            await execute(
                update_sql,
                subscription["current_period_end"],
                business_account_id,
            )
    
    async def _handle_subscription_deleted(self, subscription: Dict[str, Any]) -> None:
        """Handle customer.subscription.deleted event."""
        customer_id = subscription["customer"]
        
        account_sql = """
            SELECT id FROM business_accounts WHERE stripe_customer_id = $1
        """
        account_rows = await fetch(account_sql, customer_id)
        
        if not account_rows:
            return
        
        business_account_id = account_rows[0]["id"]
        
        # Update subscription record
        sub_sql = """
            UPDATE business_subscriptions
            SET status = 'cancelled', updated_at = now()
            WHERE stripe_subscription_id = $1
        """
        await execute(sub_sql, subscription["id"])
        
        # Update business account
        update_sql = """
            UPDATE business_accounts
            SET 
                subscription_tier = 'basic'::subscription_tier,
                subscription_status = 'cancelled',
                updated_at = now()
            WHERE id = $1
        """
        await execute(update_sql, business_account_id)
    
    async def _handle_payment_succeeded(self, invoice: Dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded event."""
        # Log payment transaction
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return
        
        # Get business account
        sub_sql = """
            SELECT business_account_id FROM business_subscriptions
            WHERE stripe_subscription_id = $1
        """
        sub_rows = await fetch(sub_sql, subscription_id)
        
        if not sub_rows:
            return
        
        business_account_id = sub_rows[0]["business_account_id"]
        
        # Log transaction
        trans_sql = """
            INSERT INTO payment_transactions (
                business_account_id, stripe_subscription_id,
                transaction_type, amount, currency, status, description
            )
            VALUES ($1, $2, 'subscription', $3, $4, 'succeeded', $5)
        """
        await execute(
            trans_sql,
            business_account_id,
            subscription_id,
            invoice["amount_paid"],
            invoice["currency"],
            f"Invoice {invoice['id']}",
        )
    
    async def _handle_payment_failed(self, invoice: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed event."""
        # Similar to succeeded, but with status 'failed'
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return
        
        sub_sql = """
            SELECT business_account_id FROM business_subscriptions
            WHERE stripe_subscription_id = $1
        """
        sub_rows = await fetch(sub_sql, subscription_id)
        
        if not sub_rows:
            return
        
        business_account_id = sub_rows[0]["business_account_id"]
        
        trans_sql = """
            INSERT INTO payment_transactions (
                business_account_id, stripe_subscription_id,
                transaction_type, amount, currency, status, description
            )
            VALUES ($1, $2, 'subscription', $3, $4, 'failed', $5)
        """
        await execute(
            trans_sql,
            business_account_id,
            subscription_id,
            invoice["amount_due"],
            invoice["currency"],
            f"Invoice {invoice['id']} - Payment failed",
        )
    
    async def create_promotion_payment_intent(
        self,
        business_account_id: int,
        promotion_type: str,  # 'location' or 'news'
        promotion_id: int,
        amount_cents: int,
        currency: str = "eur",
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent for a promotion.
        
        Args:
            business_account_id: Business account ID
            promotion_type: 'location' or 'news'
            promotion_id: Promotion ID
            amount_cents: Amount in cents
            currency: Currency code (default: 'eur')
            
        Returns:
            Dict with payment intent details
        """
        # Get business account
        account_sql = """
            SELECT stripe_customer_id, contact_email
            FROM business_accounts
            WHERE id = $1
        """
        account_rows = await fetch(account_sql, business_account_id)
        
        if not account_rows:
            raise ValueError("Business account not found")
        
        account = account_rows[0]
        customer_id = account["stripe_customer_id"]
        email = account.get("contact_email")
        
        # Create or get customer
        if not customer_id:
            customer_id = await self.create_customer(
                business_account_id=business_account_id,
                email=email or f"business-{business_account_id}@example.com",
            )
        
        try:
            payment_intent = stripe.PaymentIntent.create(
                customer=customer_id,
                amount=amount_cents,
                currency=currency,
                metadata={
                    "business_account_id": str(business_account_id),
                    "promotion_type": promotion_type,
                    "promotion_id": str(promotion_id),
                },
                automatic_payment_methods={
                    "enabled": True,
                },
            )
            
            # Update promotion with payment intent ID
            from services.promotion_service import get_promotion_service
            promotion_service = get_promotion_service()
            await promotion_service.update_promotion_payment_intent(
                promotion_type=promotion_type,
                promotion_id=promotion_id,
                payment_intent_id=payment_intent.id,
            )
            
            # Create payment record
            payment_sql = """
                INSERT INTO promotion_payments (
                    promotion_type,
                    promotion_id,
                    business_account_id,
                    stripe_payment_intent_id,
                    amount,
                    currency,
                    status
                )
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
            """
            await execute(
                payment_sql,
                promotion_type,
                promotion_id,
                business_account_id,
                payment_intent.id,
                amount_cents,
                currency,
            )
            
            logger.info(
                "promotion_payment_intent_created",
                business_account_id=business_account_id,
                promotion_type=promotion_type,
                promotion_id=promotion_id,
                payment_intent_id=payment_intent.id,
                amount_cents=amount_cents,
            )
            
            return {
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "amount": amount_cents,
                "currency": currency,
            }
            
        except Exception as e:
            logger.error(
                "promotion_payment_intent_failed",
                business_account_id=business_account_id,
                promotion_type=promotion_type,
                promotion_id=promotion_id,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def _handle_payment_intent_succeeded(self, payment_intent: Dict[str, Any]) -> None:
        """Handle payment_intent.succeeded event for promotions."""
        metadata = payment_intent.get("metadata", {})
        promotion_type = metadata.get("promotion_type")
        promotion_id_str = metadata.get("promotion_id")
        
        if not promotion_type or not promotion_id_str:
            # Not a promotion payment, skip
            return
        
        try:
            promotion_id = int(promotion_id_str)
        except ValueError:
            logger.warning(
                "invalid_promotion_id_in_payment_intent",
                payment_intent_id=payment_intent["id"],
                promotion_id_str=promotion_id_str,
            )
            return
        
        # Update payment record
        payment_sql = """
            UPDATE promotion_payments
            SET status = 'succeeded', updated_at = now()
            WHERE stripe_payment_intent_id = $1
        """
        await execute(payment_sql, payment_intent["id"])
        
        # Activate promotion
        from services.promotion_service import get_promotion_service
        promotion_service = get_promotion_service()
        await promotion_service.activate_promotion(
            promotion_type=promotion_type,
            promotion_id=promotion_id,
        )
        
        logger.info(
            "promotion_payment_succeeded",
            payment_intent_id=payment_intent["id"],
            promotion_type=promotion_type,
            promotion_id=promotion_id,
        )


# Singleton instance
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get or create StripeService singleton."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service

