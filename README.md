# XAU/USD cloud Telegram monitor — prepared, not deployed

This package can run on GitHub Actions without your laptop. Standard Linux
GitHub-hosted runners are free in a public repository. Schedules can be delayed
or dropped, and inactive public repository schedules can be disabled. This is
not a continuous or guaranteed five-minute trading feed.

## Current capability

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
