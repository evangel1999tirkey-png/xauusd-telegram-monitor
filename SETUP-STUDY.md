# Direction + entry study: 09:00–15:00 IST

User objective: two or three possible trades during the six-hour sitting. User selected a maximum of three setup alerts, fewer if conditions fail. Three is a ceiling, never a quota. A detector cannot ensure the market supplies two or three opportunities or that any opportunity is profitable.

## Current deployment stage

`setup_watch.py` runs a separate SHADOW_ONLY study after the existing cloud direction check. It sends no Telegram messages. The original direction rule/messages/deduplication remain unchanged. Research failures cannot undo a delivered baseline alert. This stage tests the new path before it becomes an entry-notification service; the chosen maximum-three alert policy is stored as a maximum-three research-selection policy for now. It is not a count of trades actually taken.

## Fixed first rule set

- Use validated Twelve Data XAU/USD reference candles, never claim an XM executable quote or verified real execution cost.
- Completed 5m and 15m EMA20 direction must agree; this is technical direction agreement, not independent fundamental confirmation.
- Reuse the existing technical_evidence closed-5m breakout/retest/continuation heuristic: reference range is the six bars before the three pattern bars, true-range mean14 and fixed volatility/extension limits. The entire three-bar pattern must begin after 09:00 IST. The preceding reference range can use earlier history.
- UP requires a break above the range, a held retest and a higher low/continuation; DOWN uses the symmetric failed reclaim/lower high pattern. Observed retest extreme is structural invalidation, not a guaranteed broker stop fill.
- Require a fresh completed 1m continuation after the latest completed 5m bar, max75-second candle age. No observed post-retest invalidation, no excessive 1m spike or extension beyond0.5 times the recorded5m mean true range from the latest5m close. Do not describe this snapshot as a continuing live entry.
- At most three distinct research setups per IST session, at least30minutes apart, no repeated notification of the same breakout pattern. These fixed settings are unvalidated research choices; no outcome claim.
- Flat/conflicting direction, failed retest, stale/missing/invalid candles, session closures and outside-window checks cannot create an entry candidate. Data requests and selections stop outside09:00–15:00 IST. No manual evidence flags, news/yield confirmations or broker-cost claims are fabricated.

## Forward evaluation

Research candidates are stored separately under setup_study, with source, version, pattern identity, check/closed-candle times, invalidation, reference price and session date. Cap storage at500. Where available, subsequent completed1m reference prices evaluate5/10/15minutes after selection, rounded up to the next completed minute (actual elapsed duration retained). Require complete1m history through the endpoint; missing data is unavailable and recorded outcomes are frozen. Endpoints after15:00 are excluded. These are research-selection outcomes, not Telegram delivery outcomes, actual fills, spread/cost-adjusted profits or matched baseline comparisons. Later gaps in GitHub checks can leave outcome data unavailable.

The1m request happens only when the 5m/15m structure qualifies or prior candidates require measurement. All requests use the existing free connector and fail honestly on entitlement/rate/access errors; no new account, key exposure, paid plan or XM cloud login. Setup workflow step is best-effort after baseline delivery. A five-minute schedule with known26–40minute observed gaps is a material entry-timing limitation; this study does not repair that scheduler or prove suitability for real-time scalping.

Before entry notifications are promoted, review forward observations from this session, failures, timing and sample size; validate unchanged rules on later sessions. No promised10% improvement, trade frequency or deadline. Existing direction alerts remain the only live Telegram messages at this stage.
