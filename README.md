# XAU/USD cloud Telegram monitor — prepared, not deployed

Delivery is now verified: GitHub Actions connection test and normal status run succeeded on 10 October 2026 at 00:47 and 00:49 IST. Credentials are in Actions secrets, not repository files. This verifies messaging only. Missing candle data now displays DATA UNAVAILABLE and missing news/execution confirmation displays CONFIRMATION INCOMPLETE; neither is a neutral market signal. Directional alerts remain unimplemented until those confirmations are connected.

An optional Twelve Data trial candle connector is prepared. Set TWELVE_DATA_API_KEY only after account consent and XAU/USD entitlement testing. The public demo rejected XAU/USD with HTTP 401. The connector requests 2,000 genuine 5-minute OHLC bars, excludes the current bar, validates identity/continuity/freshness, and aggregates complete 15-minute/hourly/four-hour segments. Missing segments are discarded, never filled. One request per five-minute check is 288 requests/day, within the advertised Basic 800/day quota if trial entitlement permits this symbol; additional requests and retries consume that budget. This is not a claim of successful candle access. Run `python -m unittest test_signal_rules.py test_public_quote.py test_candle_feed.py` (eight tests).

The free no-key Gold API quote cross-check has now been tested locally. The code rejects wrong symbol/currency, invalid prices and source timestamps older than 90 seconds or in the future. This quote does not supply completed candles, broker spread, news surprises or independent USD/yield confirmation; it cannot enable BUY/SELL. Source: https://gold-api.com/docs and https://gold-api.com/llms.txt. Minute/hour history is listed as premium and is not used. Run `python -m unittest test_signal_rules.py test_public_quote.py` for the six verification tests.

This package can run on GitHub Actions without your laptop. Standard Linux
GitHub-hosted runners are free in a public repository. Schedules can be delayed
or dropped, and inactive public repository schedules can be disabled. This is
not a continuous or guaranteed five-minute trading feed.

## Current capability

The signal rules now require a completed 5m breakout, held retest and higher
low (or bearish mirror), agreeing with the slope and position of a 15m EMA.
They reject large volatility spikes, narrow ranges and extended moves.
The combined bias gate additionally requires fresh data, verified matching
news, verified market reaction, acceptable spread and no imminent high-impact
release. These are conservative heuristics, not backtested profitability or
calibrated confidence estimates. The current cloud workflow still emits only
NEUTRAL because the required confirmation feeds are absent.

Run `python -m unittest test_signal_rules.py` to verify failure guards.

Hourly context must now agree, and four-hour context must not oppose the
intraday candidate. Daily/weekly charts are background context for the desktop
monitor, not a vote that substitutes for a confirmed scalp setup. All technical
evidence is separate from verified news and from 1m execution confirmation.

Additional feed research: Twelve Data lists XAU/USD as a commodity trial symbol
(https://twelvedata.com/exchanges/commodity?group=reference). Trial access and
continued free entitlement have not been tested. Its general commodity market
data is listed under Grow, so this is not a promise of unlimited free gold data.
Trading Economics documents calendar streaming with actual/forecast metadata,
but requires credentials; no economic-news API has been connected. Browser
TradingView access cannot be described as a server-side cloud data connection.

- Five-minute scheduled Telegram status and a manual delivery test.
- New York session boundaries and IST message times.
- Optional read-only OANDA practice XAU_USD completed 5m/15m candles with
  symbol, interval, continuity and freshness verification.
- No trades, order requests or paid AI API calls.

**The automated news and cross-asset confirmation feed is not connected.**
This version therefore always reports NEUTRAL, including when candles are
available. It is a delivery/data-verification stage, not a replacement for the
existing Codex news analysis. It must not be described as working BUY/SELL
cloud alerts until that missing feed and analysis are implemented and tested.
XAU_USD availability and account eligibility must be tested in the chosen
provider account. No brokerage account should be opened automatically.

## Deployment steps

1. Sign in to your GitHub account.
2. Create a public repository containing only this folder's files. Do not upload
   the local Telegram XML connection file or any token. The code is public;
   all credentials and private chat identifiers belong in Actions secrets.
3. Add Actions secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. Authorize
   the credential transfer before uploading the existing bot credential to
   GitHub. Add OANDA_PRACTICE_TOKEN only if an eligible practice data account
   already exists and access to gold candles has been verified.
4. Open Actions → Gold Telegram monitor → Run workflow with test_delivery
   checked. Confirm an actual Telegram test message arrived.
5. Run without test_delivery during an open session to verify candle access.
6. Connect and validate the missing news/cross-asset feed before enabling
   directional labels. Never substitute headline keyword guessing for verified
   actual-versus-consensus/revision analysis.
7. Pause the local Codex automation only after the intended cloud replacement
   has been verified, to avoid losing coverage or producing duplicates.

## Stop

Disable the Gold Telegram monitor workflow in GitHub Actions. Never put
credentials in repository files, workflow text, screenshots or chat messages.

## Sources

- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
- https://developer.oanda.com/rest-live-v20/development-guide/
- https://developer.oanda.com/rest-live-v20/instrument-df/
- https://core.telegram.org/bots/api#sendmessage
