# Claim & Outreach System - Future Extensions

**Status**: 📋 Planning Document  
**Last Updated**: 2025-01-16  
**Purpose**: Documentatie voor toekomstige uitbreidingen van het outreach en claim systeem

---

## Overzicht

Dit document beschrijft het migratiepad en architectuur overwegingen voor toekomstige uitbreidingen van het outreach en claim systeem, zoals beschreven in het Claim & Consent Outreach Implementation Plan (Fase 10).

---

## 1. Migratiepad naar Brevo voor Marketing Emails

### Huidige Situatie

- **Service Emails**: Gebruiken AWS SES (via `SESEmailProvider`)
  - Outreach emails
  - Claim confirmations
  - Transactional emails
- **Email Abstraction**: Provider pattern bestaat al (`EmailProvider` interface)
- **Brevo Provider**: Skeleton implementatie bestaat (`BrevoEmailProvider`)

### Doel

- **Service Emails**: Blijven via SES (behouden huidige setup)
- **Marketing Emails**: Migreren naar Brevo (toekomstig)
  - Newsletters
  - Promoties
  - Marketing campagnes

### Implementatie Stappen

1. **Brevo Provider Implementatie**:
   - Volledige implementatie van `BrevoEmailProvider.send_email()`
   - Brevo API client setup (SDK installatie)
   - Error handling (rate limiting, bounces, etc.)
   - Message ID tracking

2. **Provider Switching Logica**:
   - Service emails → SES (via `EMAIL_PROVIDER=ses`)
   - Marketing emails → Brevo (via `EMAIL_PROVIDER=brevo`)
   - Of: Dual provider support (service via SES, marketing via Brevo)

3. **Email Service Uitbreiding**:
   - `send_marketing_email()` methode die Brevo gebruikt
   - `send_service_email()` methode die SES gebruikt
   - Configuratie via env vars (`EMAIL_PROVIDER_SERVICE`, `EMAIL_PROVIDER_MARKETING`)

4. **Consent Systeem Integratie**:
   - Marketing emails checken `marketing_consent` flag
   - Service emails checken `service_consent` flag
   - Opt-out updates beide consents naar false

### Configuratie

```env
# Service emails (SES)
EMAIL_PROVIDER_SERVICE=ses
AWS_SES_REGION=eu-west-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Marketing emails (Brevo)
EMAIL_PROVIDER_MARKETING=brevo
BREVO_API_KEY=...
```

### Migratie Timing

- **Fase 1**: Brevo provider implementatie (skeleton → volledige implementatie)
- **Fase 2**: Dual provider support in EmailService
- **Fase 3**: Marketing email templates en campagnes
- **Fase 4**: Migratie van bestaande marketing flows (indien van toepassing)

---

## 2. Premium Features Integratie (na Expiry)

### Huidige Situatie

- **Token-based Claims**: Gratis periode (30 dagen, configureerbaar)
- **Expiry Systeem**: Automatische expiry na `free_until` datum
- **State Management**: `claimed_free` → `expired`

### Doel

- **Gratis Periode**: Blijft bestaan als onboarding periode
- **Premium Periode**: Betaalde verlenging na expiry
- **Features**: Premium features alleen actief tijdens betaalde periode

### Implementatie Stappen

1. **Database Uitbreidingen**:
   - `location_claims.premium_until` (nieuwe kolom)
   - `location_claims.subscription_status` (gratis / premium / expired)
   - `location_claims.payment_intent_id` (voor Stripe integratie)

2. **State Machine Uitbreiding**:
   - `unclaimed` → `claimed_free` (gratis periode)
   - `claimed_free` → `expired` (na gratis periode)
   - `expired` → `premium` (na betaling)
   - `premium` → `expired` (na premium periode)

3. **Payment Integratie**:
   - Stripe payment intents voor premium verlenging
   - Webhook handlers voor payment success/failure
   - Subscription management (maandelijks/jaarlijks)

4. **Feature Flags**:
   - Check `premium_until` voor premium features
   - Graceful degradation voor expired claims
   - Admin dashboard voor subscription management

### Premium Features (Voorbeelden)

- Logo upload en weergave
- Google Business link weergave
- Enhanced listing (featured location)
- Analytics dashboard
- Priority support

---

## 3. Monetization Flows (Toekomstig)

### Business Model

- **Gratis**: Basisvermelding (altijd gratis)
- **Premium**: Betaalde features (na gratis periode)
- **Pricing**: Maandelijks/jaarlijks abonnement

### Payment Flows

1. **Expiry Reminder → Payment**:
   - Reminder email 7 dagen voor expiry
   - Link naar payment pagina
   - Stripe Checkout integratie
   - Success redirect naar claim pagina

2. **Direct Upgrade**:
   - Upgrade knop op claim pagina
   - Payment flow zonder expiry
   - Immediate activation

3. **Subscription Management**:
   - Dashboard voor subscription beheer
   - Cancellation flow
   - Refund policy

### Pricing Strategy

- **Free Trial**: 30 dagen gratis (huidig)
- **Premium Monthly**: €X/maand
- **Premium Yearly**: €Y/jaar (korting)
- **Enterprise**: Custom pricing (toekomstig)

---

## 4. Scaling Considerations

### Email Volume Groei

- **Huidig**: 50 emails/dag (start volume)
- **Groeifase**: 500 emails/dag (per stad)
- **Schaal**: Meerdere steden = 1000+ emails/dag

### SES/Brevo Splits

- **Service Emails (SES)**:
  - Volume: ~500-1000/dag (outreach + confirmations)
  - Rate Limits: SES production limits (50k/dag)
  - Costs: $0.10 per 1000 emails

- **Marketing Emails (Brevo)**:
  - Volume: Variabel (campagne-afhankelijk)
  - Rate Limits: Brevo plan limits
  - Costs: Brevo subscription pricing

### Database Performance

- **Indexen**: Belangrijk voor consent checks en email lookups
- **Partitioning**: Overweeg voor `outreach_audit_log` (retention 2 jaar)
- **Archiving**: Oude audit logs archiveren na 2 jaar

### Infrastructure

- **Queue Management**: Redis/SQS voor email queue (toekomstig)
- **Worker Scaling**: Horizontale scaling van outreach mailer workers
- **Monitoring**: Metrics dashboard voor email deliverability

---

## 5. Consent Systeem Uitbreidingen

### Huidige Implementatie

- **Service Consent**: Implicit voor outreach (default true)
- **Marketing Consent**: Explicit opt-in (default false)
- **Opt-out**: Beide consents naar false

### Toekomstige Uitbreidingen

1. **Granular Consent**:
   - Service consent sub-categories (outreach, confirmations, etc.)
   - Marketing consent sub-categories (newsletters, promotions, etc.)

2. **Consent History**:
   - Track consent changes over tijd
   - Audit trail voor AVG compliance
   - Consent withdrawal tracking

3. **Preference Center**:
   - UI voor gebruikers om consents te beheren
   - Email preference management
   - Opt-out / opt-in flows

4. **Data Retention**:
   - Automatische cleanup na opt-out
   - Retention policy enforcement
   - Data deletion workflows

---

## 6. Testing & Quality Assurance

### Email Testing

- **Service Emails**: Test suite voor outreach emails
- **Marketing Emails**: A/B testing framework (toekomstig)
- **Deliverability**: Monitoring email deliverability rates

### Integration Testing

- **Claim Flows**: E2E tests voor claim workflows
- **Payment Flows**: Test Stripe integration (test mode)
- **Consent Flows**: Test consent management workflows

### Performance Testing

- **Email Sending**: Load tests voor email volumes
- **Database Queries**: Performance tests voor consent checks
- **API Endpoints**: Load tests voor claim endpoints

---

## 7. Monitoring & Observability

### Metrics

- **Email Metrics**: Send rate, delivery rate, bounce rate, click rate
- **Claim Metrics**: Claim rate, expiry rate, premium conversion rate
- **Consent Metrics**: Opt-out rate, consent changes

### Alerts

- **Email Failures**: Alert bij hoge bounce rate
- **Payment Failures**: Alert bij payment errors
- **Consent Issues**: Alert bij consent check failures

### Dashboards

- **Outreach Dashboard**: Email performance, claim rates
- **Revenue Dashboard**: Premium subscriptions, revenue metrics
- **Compliance Dashboard**: Consent tracking, opt-out rates

---

## 8. Security Considerations

### Email Security

- **SPF/DKIM/DMARC**: Proper email authentication (al geïmplementeerd)
- **Rate Limiting**: Prevent email abuse
- **Token Security**: Secure opt-out tokens (al geïmplementeerd)

### Payment Security

- **PCI Compliance**: Stripe handles PCI compliance
- **Webhook Security**: Verify Stripe webhook signatures
- **Data Encryption**: Encrypt payment data at rest

### Consent Security

- **Audit Logging**: All consent changes logged (al geïmplementeerd)
- **Data Privacy**: GDPR/AVG compliance
- **Access Control**: Admin-only access to consent data

---

## 9. Documentation Updates

### API Documentation

- **Claim Endpoints**: Update met premium flows
- **Payment Endpoints**: Document Stripe integration
- **Consent Endpoints**: Document consent management API

### User Documentation

- **Claim Guide**: How to claim a location
- **Premium Features**: What are premium features?
- **Payment Guide**: How to upgrade to premium

### Developer Documentation

- **Architecture**: System architecture diagrams
- **Integration Guides**: How to integrate new features
- **Testing Guide**: How to test email/payment flows

---

## 10. Rollout Plan

### Phase 1: Foundation (Voltooid)
- ✅ Email abstraction layer
- ✅ Consent flags system
- ✅ Outreach infrastructure
- ✅ Token-based claims

### Phase 2: Premium Features (Toekomstig)
- [ ] Payment integration (Stripe)
- [ ] Premium state management
- [ ] Feature flags voor premium
- [ ] Payment webhooks

### Phase 3: Marketing Emails (Toekomstig)
- [ ] Brevo provider implementatie
- [ ] Marketing email templates
- [ ] Campaign management
- [ ] Analytics integration

### Phase 4: Scaling (Toekomstig)
- [ ] Queue system (Redis/SQS)
- [ ] Worker scaling
- [ ] Monitoring dashboards
- [ ] Performance optimization

---

## Conclusie

Dit document schetst het migratiepad en architectuur overwegingen voor toekomstige uitbreidingen. De basis infrastructuur is nu in plaats (email abstraction, consent system, outreach infrastructure), wat toekomstige uitbreidingen mogelijk maakt zonder grote refactoring.

**Volgende Stappen**:
1. Implementeer Brevo provider wanneer marketing emails nodig zijn
2. Integreer Stripe voor premium features wanneer business model dat vereist
3. Schaal infrastructure wanneer volume groeit

