from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import VolatilityMonitorConfig
from xauusd_ai_system.core.enums import WarningLevel
from xauusd_ai_system.core.models import MarketSnapshot
from xauusd_ai_system.volatility.monitor import VolatilityMonitor


class VolatilityMonitorTests(unittest.TestCase):
    def test_emits_warning_alert_when_multiple_risk_signals_stack(self) -> None:
        monitor = VolatilityMonitor(VolatilityMonitorConfig())
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.8,
            ask=3063.0,
            open=3062.0,
            high=3063.1,
            low=3061.8,
            close=3062.9,
            session_tag="us",
            minutes_to_event=5,
            features={
                "atr_expansion_ratio": 1.8,
                "volatility_ratio": 1.6,
                "spread_ratio": 1.55,
                "tick_speed": 1.3,
                "breakout_pressure": 0.42,
            },
        )

        assessment = monitor.assess(snapshot)
        self.assertEqual(assessment.primary_alert.warning_level, WarningLevel.WARNING)
        self.assertIn("NEWS_NEAR", assessment.primary_alert.reason_codes)


if __name__ == "__main__":
    unittest.main()
