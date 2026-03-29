from xauusd_ai_system.bootstrap import build_runtime_service, load_default_config
from xauusd_ai_system.core.models import AccountState, MarketSnapshot

from datetime import datetime


if __name__ == "__main__":
    service = build_runtime_service(load_default_config())
    snapshot = MarketSnapshot(
        timestamp=datetime(2026, 3, 29, 14, 30),
        symbol="XAUUSD",
        bid=3062.8,
        ask=3063.0,
        open=3061.9,
        high=3063.2,
        low=3061.7,
        close=3062.9,
        session_tag="us",
        minutes_to_event=8,
        features={
            "atr_m1_14": 0.8,
            "breakout_distance": 0.42,
            "ema20_m5": 3061.8,
            "ema60_m5": 3061.2,
            "ema_slope_20": 0.11,
            "false_break_count": 1,
            "spread_ratio": 1.38,
            "volatility_ratio": 1.28,
            "atr_expansion_ratio": 1.42,
            "breakout_retest_confirmed": True,
            "structural_stop_distance": 1.1,
            "tick_speed": 1.24,
            "breakout_pressure": 0.33,
        },
    )
    account_state = AccountState(equity=10_000.0)
    decision = service.process_snapshot(snapshot, account_state)
    print(decision.as_dict())
    service.shutdown()
