# Direction measurement: first addition

The live UP/DOWN rule remains unchanged. Tracking is measurement, not a demonstrated accuracy improvement. A requested 10% improvement is an evaluation target, not a promised gain.

Only alerts with confirmed Telegram delivery create records. The reference price is the last completed Twelve Data XAU/USD 5m close used for the alert, not an executable XM price or the exact price when the phone receives it. The reference's age and the time of the confirmed delivery response are stored.

For each 5/10/15-minute horizon after confirmed delivery, use the first actual completed 5m close at or after that horizon. Because prices are sampled on 5m boundaries, the actual endpoint is between the requested horizon and less than five minutes later. Store its timestamp and actual elapsed minutes. No interpolation or future candles. Missing endpoints and any gap between reference and endpoint are unavailable, excluded from measured percentages. Flat moves count separately and are not favourable. Already recorded outcomes remain frozen even if provider history is later revised. Legacy alerts without reference prices are not reconstructed.

The public repository file cloud-direction-state.json persists up to 500 latest delivered alert records and counts by horizon. Favourable percentage is the share of measured endpoint movements in the alerted direction. It is not trade win rate, entry success, a prediction confidence score, or profitability. Spreads, fees, slippage, intrabar adverse excursions and target/stop outcomes are not modelled.

Collect a baseline spanning multiple sessions and market conditions before deciding on a filter. Define the primary horizon and whether “10% improvement” means relative improvement or ten percentage points before comparison. Evaluate any proposed choppy-market filter on a separate chronological sample, reporting favourable/adverse/flat/unavailable counts, alert frequency and delay alongside percentages. Preserve an untouched baseline comparison; do not select a filter using the same period used to report its gain. No filter is enabled by this addition.

Telegram output stays the same concise UP/DOWN message. XM remains local and the cloud uses existing free-feed access and encrypted Telegram secrets. No orders, account reads, new credentials or additional data requests are introduced.

## First filter experiment: shadow only

Experiment ema20_slope3_tr14_v1 uses the directional EMA20 change over three completed 5m intervals divided by the simple mean of the latest 14 true ranges. True range is max(high-low, abs(high-previous close), abs(low-previous close)). The fixed threshold is 0.10: scores at/above it would keep an alert, lower scores would suppress it. Missing/invalid inputs are unavailable, not assumed to pass. This is a weak-slope hypothesis, not an independently verified identification of a sideways market. The threshold is an unvalidated preset, not claimed optimal.

The experiment is recorded BEFORE each newly delivered alert using only the same completed candles. Live delivery, direction and duplicate handling are unchanged. No historical filter classifications are backfilled. Evaluation compares only measured alerts classified in this exact version: all classified alerts versus would-keep alerts, also showing suppressed outcomes, flats, missing data and retained-alert percentage. Differences are percentage points, not guaranteed future improvement. This is a contemporaneous subset comparison, not an independently executed filtered strategy; a live filtered strategy could have different alert timing/state.

Primary descriptive horizon is 5 minutes (actual endpoint 5 to less than 10 minutes after confirmed delivery); 10/15 minutes remain secondary. Keep the version and threshold fixed during initial forward collection. Do not enable suppression based on a tiny sample, a selected favourable day, or the same observations used to tune thresholds. This addition is an experiment and has no demonstrated accuracy gain yet.
