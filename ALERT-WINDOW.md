# Daily alert window — 16 October 2026

User-selected continuous window: 09:00 inclusive to 15:00 exclusive Asia/Kolkata (IST), six hours daily, subject to existing gold-market closure exclusions. This supersedes all-hours notifications. Source, completed-5m EMA20 direction rule and inactive shadow experiments remain unchanged.

The window is checked after the feed returns and immediately before starting Telegram delivery. No new direction send starts outside it. GitHub scheduling and Telegram/network delays can still cause late arrivals; this is not an exact-time execution feed. There are no automatic trades or position closing at 15:00.

The first valid direction during each IST session can notify even if it matches the previous day's last direction. Thereafter, unchanged direction is silent. Notification state includes alert_window=IST_0900_1500_v1 and session_date_ist. Failed delivery never advances notification state.

New confirmed alerts carry alert_window=IST_0900_1500_v1. performance.window_cohorts contains a separate summary and separate shadow comparisons for those records. Old records remain unchanged and the legacy performance.summary remains all-history, capped at the existing latest 500 records. No retrospective tagging or claim of improved accuracy.

The workflow's existing five-minute cron remains active. Outside the window, no feed is requested unless an older delivered alert still needs outcome measurement. Such maintenance can run after 15:00 without notifications; its 5/10/15-minute checkpoints retain their existing elapsed-time definitions and may extend beyond the sitting window. Missing candles remain unavailable rather than invented. No new shadow observations are requested without an in-window confirmed direction delivery.

Tests cover exact IST boundaries, delayed feed crossing 15:00, pre-send boundary recheck, silent outside-window operation, outcome-only maintenance, next-session notification and preservation/separation of older records.
