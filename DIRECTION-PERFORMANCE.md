# Direction measurement: first addition

The live UP/DOWN rule remains unchanged. Tracking is measurement, not a demonstrated accuracy improvement. A requested 10% improvement is an evaluation target, not a promised gain.

Only alerts with confirmed Telegram delivery create records. The reference price is the last completed Twelve Data XAU/USD 5m close used for the alert, not an executable XM price or the exact price when the phone receives it. The reference's age and the time of the confirmed delivery response are stored.

For each 5/10/15-minute horizon after confirmed delivery, use the first actual completed 5m close at or after that horizon. Because prices are sampled on 5m boundaries, the actual endpoint is between the requested horizon and less than five minutes later. Store its timestamp and actual elapsed minutes. No interpolation or future candles. Missing endpoints and any gap between reference and endpoint are unavailable, excluded from measured percentages. Flat moves count separately and are not favourable. Already recorded outcomes remain frozen even if provider history is later revised. Legacy alerts without reference prices are not reconstructed.

The public repository file cloud-direction-state.json persists up to 500 latest delivered alert records and counts by horizon. Favourable percentage is the share of measured endpoint movements in the alerted direction. It is not trade win rate, entry success, a prediction confidence score, or profitability. Spreads, fees, slippage, intrabar adverse excursions and target/stop outcomes are not modelled.

Collect a baseline spanning multiple sessions and market conditions before deciding on a filter. Define the primary horizon and whether “10% improvement” means relative improvement or ten percentage points before comparison. Evaluate any proposed choppy-market filter on a separate chronological sample, reporting favourable/adverse/flat/unavailable counts, alert frequency and delay alongside percentages. Preserve an untouched baseline comparison; do not select a filter using the same period used to report its gain. No filter is enabled by this addition.

Telegram output stays the same concise UP/DOWN message. XM remains local and the cloud uses existing free-feed access and encrypted Telegram secrets. No orders, account reads, new credentials or additional data requests are introduced.
