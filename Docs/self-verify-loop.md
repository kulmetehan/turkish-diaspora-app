# Self-Verifying AI Loop

**Epic:** Data-Ops & AI Expansion  
**Story:** TDA-C2-S9 — Self-Verifying AI Loop

Deze loop combineert **Classify** en **Verify/Enrich** in één autonome worker die nieuwe `CANDIDATE` records verwerkt en — bij voldoende zekerheid — promoot naar `VERIFIED`.

## Doelen
- Nieuwe CANDIDATEs automatisch classificeren & verifiëren
- Promotie naar `VERIFIED` bij `confidence_score ≥ threshold`
- Volledige logging naar `ai_logs` (TDA-10/20)
- Metrics tellers (processed/promoted/skipped/below_threshold)

## Instellingen (.env)
```env
SELF_VERIFY_CONF_MIN=0.80
SELF_VERIFY_BATCH_LIMIT=200
SELF_VERIFY_CONCURRENCY=5
