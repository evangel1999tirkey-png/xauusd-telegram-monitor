# XAU/USD cloud Telegram monitor — data verification stage

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

## Verified on 10 October 2026, 01:00–01:05 IST
Free Twelve Data Basic account was created with explicit consent. Its XAU/USD trial returned 1-minute and 2,000 5-minute bars. Explicit UTC timestamps were validated locally, including 666 complete 15-minute, 166 hourly and 40 four-hour aggregates. The key was transferred directly to encrypted GitHub Actions secrets with specific approval, without a local credential file. Cloud run 37980719323 succeeded after connection, confirming Telegram delivery; inspect subsequent logs for candle confirmation rather than assuming a successful delivery proves feed freshness.

The cloud now also checks the publisher's weekly economic calendar export and official Fed monetary-policy RSS. Calendar forecasts/previous values do not include actuals/revisions, so they cannot confirm a news surprise. The Fed RSS responded successfully in the local test. BLS CPI/employment RSS could not be verified and is explicitly marked unavailable. These sources do not cover all news, live Treasury yields, DXY or broker spread.

Two candle requests per five-minute check (5m history and recent 1m) use up to 576 requests/day, below Basic's advertised 800/day limit before extra tests/retries. Trial entitlement may change. No paid plan selected. Run all ten guard tests with `python -m unittest test_signal_rules.py test_public_quote.py test_candle_feed.py test_news_context.py`. Publication/quote/candle freshness is reported separately. Missing confirmation must never be represented as a verified neutral market or profitable signal.

## Further source verification, 10 October 2026
Official BEA RSS was fetched and its publication timezone validated. It is now included as GDP/PCE and other release context, without turning titles into a news-surprise signal. DOL/BLS public RSS requests failed; Treasury's public rates are daily rather than intraday. A Twelve Data EUR/USD 15-minute cross-check is scheduled once per quarter-hour (the first five minutes of each UTC quarter), adding at most 96 daily requests for a total advertised budget of 672/day before tests/retries. It is explicitly a single-pair dollar proxy, not DXY or Treasury yields. Account entitlement and live currency access must be verified in cloud logs before claiming this cross-check works. All eleven tests pass, including prevention of currency candles being accepted as gold.

User trades an XM account through the phone app, with no MT5/API connection. Installed MetaTrader/XM terminals were found, but neither was running. XM execution spread is unverified; aggregate XAU/USD midpoint data cannot substitute for account-specific bid/ask. Secure read-only broker authentication is still required. No broker credentials were requested in chat and no trades were placed. Confirmed combined BUY/SELL remains disabled while required confirmation is missing.
