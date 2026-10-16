"""Cloud session-setup study. No Telegram messages, broker access or orders."""
from datetime import datetime, timezone
from candle_feed import fetch
from cloud_direction import read_state, write_state, session_open
from setup_strategy import assess, in_window, record_candidate, update_outcomes

UTC = timezone.utc


def run(now, load=read_state, save=write_state, feed=fetch, clock=lambda: datetime.now(UTC)):
    if not in_window(now) or not session_open(now):
        print('Setup study outside session; no notification or data request.')
        return 0
    try:
        state, sha = load()
        five, _ = feed(5, now, size=80)
        fifteen, _ = feed(15, now, size=80)
        observation = assess(five, fifteen, None, clock())
        study = state.get('setup_study', {})
        pending = any(any(str(m) not in r.get('outcomes',{}) for m in (5,10,15))
                      for r in study.get('candidates',[]))
        one = None
        if observation['status'] == 'ENTRY_PENDING' or pending:
            try:
                one, _ = feed(1, clock(), size=80)
            except Exception:
                one = []  # No provider errors/URLs/keys in logs.
            if observation['status'] == 'ENTRY_PENDING':
                observation = assess(five, fifteen, one, clock())
        checked = clock()
        # The existing live notification fields are preserved verbatim.
        state['setup_study'] = record_candidate(study, observation, checked)
        if one:
            state['setup_study'] = update_outcomes(state['setup_study'], one, checked)
        save(state, sha)
        print('Setup study: '+state['setup_study']['latest']['status']+'; SHADOW_ONLY, no alert sent.')
        return 0
    except Exception:
        print('Setup study unavailable; live baseline preserved; no setup alert sent.')
        return 1


if __name__ == '__main__':
    raise SystemExit(run(datetime.now(UTC)))
