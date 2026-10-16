# Baseline and sequential experiments — 16 October 2026

User-authorized schedule update: alerts are now restricted to 09:00–15:00 IST. The direction calculation remains the baseline. Daily deduplication now uses the IST session date and window identity, and new alerts have their own performance cohort. See ALERT-WINDOW.md; its window rules supersede the all-hours/UTC-day description below. Existing records and experiments remain intact.

## Preserve the live baseline

The production baseline remains Twelve Data XAU/USD, 80 completed 5m candles, price above a rising EMA20 for UP / below a falling EMA20 for DOWN, comparing EMA[-1] to EMA[-4]. Keep the existing freshness, source/closed-candle guards, session exclusions, direction-change and UTC-day duplicate rules, concise Telegram message and delivery confirmation requirement. No experimental filter gates live alerts. Reference baseline implementation: commit d3f846f6c485f55d3d9c94b85555298296df6b8a. Later commits may add measurement but must preserve this decision rule.

## One-by-one plan

1. Continue baseline outcome tracking. Existing weak-slope experiment stays inactive; its first 34 completed alerts showed worse favourable percentages at all three horizons. Do not retune it to fit those observations.
2. Independently test completed 15m EMA20 trend agreement, shadow mode only. A matching direction would keep; opposite or flat would suppress; missing data remains unavailable. No combination with the weak-slope filter. All existing alerts continue unchanged.
3. Compare future, classified baseline alerts against the would-keep subset, reporting counts, flats, unavailable data, retained-alert fraction and percentage-point differences. Primary horizon stays the existing 5-minute checkpoint (actual completed-5m endpoint 5 to less than 10 minutes after confirmed delivery), with 10/15-minute secondary checkpoints. Do not count three horizons as three independent alerts or claim trade profitability.
4. Address scheduling as a separate reliability project. GitHub remains active during preparation; a new cloud host needs user authentication and secure secret entry. Switch only after verified timing and Telegram delivery, preserving decision logic and previous outcome history. No Cloudflare deployment has occurred.
5. Enable a filter only after enough forward evidence across sessions and an untouched chronological validation period supports it. No automatic activation or promised 10% gain.

## 15m collection details

Experiment completed15m_ema20_agreement_v1. The baseline send and baseline state save happen first. Only for a newly confirmed delivery, make one additional free-feed request for 80 15m candles. Filter out any candle that had not closed at the baseline decision time. Require at least 30 completed candles, current 15m history and recent continuity. Record decision/review timestamps, source close and trend. Retrieval happens after delivery; this is a historical-at-decision shadow assessment, not a claim that the extra feed was available before the live send. Provider revisions are possible and not independently authenticated.

Extra feed, state-read or enrichment-write failures never undo the confirmed baseline state. Record unavailable where possible; otherwise leave unclassified. No retroactive classification of old alerts. Existing weak-slope and outcome records remain unchanged. Each experiment has its own matched-sample comparison. Subset statistics do not simulate the different notification timing/deduplication that an actually enabled filter might produce.

No orders, XM cloud login, extra broker account or paid service. Any free-provider limit/access error blocks only the shadow observation, not a delivery already made.
