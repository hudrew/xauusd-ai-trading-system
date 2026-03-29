from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import pandas as pd
except ImportError:
    pd = None
    FeatureCalculator = None
else:
    from xauusd_ai_system.features.calculator import FeatureCalculator


@unittest.skipIf(pd is None, "pandas is not installed")
class FeatureCalculatorTests(unittest.TestCase):
    def test_calculate_adds_required_features(self) -> None:
        timestamps = pd.date_range("2026-03-29 09:00:00", periods=180, freq="min")
        close = pd.Series(range(180), dtype="float64") * 0.1 + 3000.0
        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "symbol": "XAUUSD",
                "open": close,
                "high": close + 0.4,
                "low": close - 0.4,
                "close": close + 0.1,
                "bid": close,
                "ask": close + 0.2,
                "volume": 1.0,
                "session_tag": "eu",
                "news_flag": False,
                "minutes_to_event": None,
                "minutes_from_event": None,
            }
        )

        result = FeatureCalculator().calculate(frame)
        tail = result.tail(1).iloc[0]
        for column in [
            "atr_m1_14",
            "atr_m5_14",
            "atr_m15_14",
            "atr_h1_14",
            "ema20_m5",
            "ema60_m5",
            "ema20_m15",
            "ema60_h1",
            "volatility_ratio",
            "breakout_distance",
            "range_position",
            "structural_stop_distance",
            "boll_mid",
            "boll_upper",
            "boll_lower",
            "bollinger_position",
            "midline_return_speed",
            "regime_conflict_score",
            "weekday",
            "hour_bucket",
        ]:
            self.assertIn(column, result.columns)
            self.assertIsNotNone(tail[column])
        self.assertEqual(int(tail["weekday"]), 6)
        self.assertEqual(int(tail["hour_bucket"]), 11)
        self.assertGreaterEqual(float(tail["bollinger_position"]), 0.0)
        self.assertLessEqual(float(tail["bollinger_position"]), 1.0)


if __name__ == "__main__":
    unittest.main()
