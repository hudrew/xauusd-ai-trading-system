from __future__ import annotations

from itertools import combinations
import math

import numpy as np
import pandas as pd


class FeatureCalculator:
    """
    Computes a shared feature set for both research and production pipelines.
    """

    def calculate(self, market_data: pd.DataFrame) -> pd.DataFrame:
        frame = market_data.copy()
        frame = frame.sort_values("timestamp").reset_index(drop=True)
        frame = frame.set_index("timestamp", drop=False)

        frame = self._ensure_context_columns(frame)

        frame["spread"] = (frame["ask"] - frame["bid"]).astype(float)
        frame["spread_ratio"] = frame["spread"] / frame["spread"].rolling(60, min_periods=5).median().replace(0, np.nan)
        frame["spread_ratio"] = frame["spread_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
        frame["spread_zscore"] = self._zscore(frame["spread"], window=60)

        frame["tr_m1"] = self._true_range(frame["high"], frame["low"], frame["close"])
        frame["atr_m1_14"] = frame["tr_m1"].rolling(14, min_periods=1).mean()
        frame["atr_expansion_ratio"] = frame["atr_m1_14"] / frame["atr_m1_14"].rolling(60, min_periods=5).mean().replace(0, np.nan)
        frame["atr_expansion_ratio"] = frame["atr_expansion_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)

        returns = np.log(frame["close"]).diff().fillna(0.0)
        frame["realized_volatility"] = returns.rolling(30, min_periods=5).std().fillna(0.0) * math.sqrt(30)
        frame["tick_speed"] = frame["close"].diff().abs().rolling(10, min_periods=1).mean()
        frame["tick_speed"] = frame["tick_speed"] / frame["tick_speed"].rolling(60, min_periods=5).mean().replace(0, np.nan)
        frame["tick_speed"] = frame["tick_speed"].replace([np.inf, -np.inf], np.nan).fillna(1.0)

        candle_range = (frame["high"] - frame["low"]).replace(0, np.nan)
        body = (frame["close"] - frame["open"]).abs()
        frame["candle_body_ratio"] = (body / candle_range).fillna(0.0)
        frame["wick_ratio_up"] = ((frame["high"] - frame[["open", "close"]].max(axis=1)) / candle_range).fillna(0.0)
        frame["wick_ratio_down"] = ((frame[["open", "close"]].min(axis=1) - frame["low"]) / candle_range).fillna(0.0)
        frame["range_width_n"] = (frame["high"].rolling(20, min_periods=2).max() - frame["low"].rolling(20, min_periods=2).min()).fillna(0.0)

        frame["recent_high_n"] = frame["high"].rolling(20, min_periods=2).max().shift(1)
        frame["recent_low_n"] = frame["low"].rolling(20, min_periods=2).min().shift(1)
        frame["breakout_distance"] = self._breakout_distance(frame["close"], frame["recent_high_n"], frame["recent_low_n"])
        frame["breakout_pressure"] = frame["breakout_distance"].abs()
        frame["pullback_depth"] = self._pullback_depth(frame["close"], frame["recent_high_n"], frame["recent_low_n"])
        frame["false_break_count"] = self._false_break_count(frame)
        frame["range_position"] = self._range_position(frame["close"], frame["recent_high_n"], frame["recent_low_n"])
        frame["boundary_touch_count"] = self._boundary_touch_count(frame)
        frame["range_boundary_buffer"] = (0.15 * frame["atr_m1_14"]).fillna(0.0)

        frame["vwap"] = self._vwap(frame)
        frame["vwap_deviation"] = frame["close"] - frame["vwap"]
        frame["midline_target_distance"] = (frame["close"] - ((frame["recent_high_n"] + frame["recent_low_n"]) / 2.0)).abs().fillna(0.0)

        m5 = self._resample(frame, "5min", "m5")
        m15 = self._resample(frame, "15min", "m15")
        h1 = self._resample(frame, "1h", "h1")
        frame = frame.join(m5, how="left")
        frame = frame.join(m15, how="left")
        frame = frame.join(h1, how="left")
        fill_columns = [
            "atr_m5_14",
            "ema20_m5",
            "ema60_m5",
            "ema_slope_20_m5",
            "ema_slope_60_m5",
            "price_distance_to_ema20_m5",
            "atr_m15_14",
            "ema20_m15",
            "ema60_m15",
            "ema_slope_20_m15",
            "ema_slope_60_m15",
            "price_distance_to_ema20_m15",
            "atr_h1_14",
            "ema20_h1",
            "ema60_h1",
            "ema_slope_20_h1",
            "ema_slope_60_h1",
            "price_distance_to_ema20_h1",
            "ema_slope_20",
            "ema_slope_60",
            "price_distance_to_ema20",
            "realized_volatility_m5",
            "realized_volatility_h1",
            "volatility_ratio",
            "session_volatility_baseline",
            "boll_mid",
            "boll_upper",
            "boll_lower",
            "bollinger_position",
        ]
        frame[fill_columns] = frame[fill_columns].ffill().bfill()
        frame["midline_return_speed"] = self._midline_return_speed(frame)
        frame["regime_conflict_score"] = self._regime_conflict_score(frame)

        frame["breakout_retest_confirmed"] = self._breakout_retest_confirmed(frame)
        frame["structural_stop_distance"] = self._structural_stop_distance(frame)
        frame["m1_reversal_confirmed"] = self._m1_reversal_confirmed(frame)
        frame["structure_intact"] = frame["pullback_depth"] < 0.75
        frame["range_defined"] = frame["range_width_n"] > frame["atr_m1_14"] * 1.2
        frame["rejection_up"] = frame["wick_ratio_down"] >= 0.35
        frame["rejection_down"] = frame["wick_ratio_up"] >= 0.35
        frame["liquidity_flag"] = frame["spread_ratio"] > 2.0
        frame["trade_block_flag"] = False
        frame["event_proximity_score"] = self._event_proximity_score(frame["minutes_to_event"])

        frame = frame.reset_index(drop=True)
        return frame

    @staticmethod
    def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        prev_close = close.shift(1)
        ranges = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        )
        return ranges.max(axis=1).fillna(high - low)

    @staticmethod
    def _zscore(series: pd.Series, window: int) -> pd.Series:
        rolling_mean = series.rolling(window, min_periods=5).mean()
        rolling_std = series.rolling(window, min_periods=5).std().replace(0, np.nan)
        return ((series - rolling_mean) / rolling_std).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    @staticmethod
    def _breakout_distance(close: pd.Series, recent_high: pd.Series, recent_low: pd.Series) -> pd.Series:
        bullish = np.where(close > recent_high, close - recent_high, 0.0)
        bearish = np.where(close < recent_low, close - recent_low, 0.0)
        return pd.Series(np.where(np.abs(bullish) >= np.abs(bearish), bullish, bearish), index=close.index).fillna(0.0)

    @staticmethod
    def _pullback_depth(close: pd.Series, recent_high: pd.Series, recent_low: pd.Series) -> pd.Series:
        span = (recent_high - recent_low).replace(0, np.nan)
        normalized = ((recent_high - close) / span).abs()
        return normalized.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(0.0, 2.0)

    @staticmethod
    def _false_break_count(frame: pd.DataFrame) -> pd.Series:
        recent_high = frame["recent_high_n"]
        recent_low = frame["recent_low_n"]
        false_up = ((frame["high"] > recent_high) & (frame["close"] < recent_high)).astype(int)
        false_down = ((frame["low"] < recent_low) & (frame["close"] > recent_low)).astype(int)
        return (false_up + false_down).rolling(60, min_periods=1).sum().fillna(0).astype(int)

    @staticmethod
    def _range_position(close: pd.Series, recent_high: pd.Series, recent_low: pd.Series) -> pd.Series:
        span = (recent_high - recent_low).replace(0, np.nan)
        position = (close - recent_low) / span
        return position.replace([np.inf, -np.inf], np.nan).fillna(0.5).clip(0.0, 1.0)

    @staticmethod
    def _boundary_touch_count(frame: pd.DataFrame) -> pd.Series:
        proximity = 0.15
        range_position = frame["range_position"]
        touches = ((range_position <= proximity) | (range_position >= 1.0 - proximity)).astype(int)
        return touches.rolling(40, min_periods=1).sum().fillna(0).astype(int)

    @staticmethod
    def _vwap(frame: pd.DataFrame) -> pd.Series:
        typical_price = (frame["high"] + frame["low"] + frame["close"]) / 3.0
        cumulative_pv = (typical_price * frame["volume"].replace(0, np.nan)).cumsum()
        cumulative_volume = frame["volume"].replace(0, np.nan).cumsum()
        vwap = cumulative_pv / cumulative_volume
        return vwap.fillna(frame["close"])

    def _resample(self, frame: pd.DataFrame, rule: str, prefix: str) -> pd.DataFrame:
        agg = frame.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "spread": "mean",
            }
        ).dropna()
        tr = self._true_range(agg["high"], agg["low"], agg["close"])
        atr_column = f"atr_{prefix}_14"
        ema20_column = f"ema20_{prefix}"
        ema60_column = f"ema60_{prefix}"
        ema_slope_20_column = f"ema_slope_20_{prefix}"
        ema_slope_60_column = f"ema_slope_60_{prefix}"
        distance_column = f"price_distance_to_ema20_{prefix}"

        agg[atr_column] = tr.rolling(14, min_periods=1).mean()
        agg[ema20_column] = agg["close"].ewm(span=20, adjust=False).mean()
        agg[ema60_column] = agg["close"].ewm(span=60, adjust=False).mean()
        agg[ema_slope_20_column] = agg[ema20_column].diff(3).fillna(0.0)
        agg[ema_slope_60_column] = agg[ema60_column].diff(3).fillna(0.0)
        agg[distance_column] = agg["close"] - agg[ema20_column]

        output_columns = [
            atr_column,
            ema20_column,
            ema60_column,
            ema_slope_20_column,
            ema_slope_60_column,
            distance_column,
        ]

        if prefix == "m5":
            returns = np.log(agg["close"]).diff().fillna(0.0)
            agg["realized_volatility_m5"] = (
                returns.rolling(20, min_periods=5).std().fillna(0.0) * math.sqrt(20)
            )
            atr_baseline = agg[atr_column].rolling(30, min_periods=5).mean().replace(0, np.nan)
            agg["volatility_ratio"] = (
                agg[atr_column] / atr_baseline
            ).replace([np.inf, -np.inf], np.nan).fillna(1.0)
            session_baseline = agg.groupby(agg.index.hour)[atr_column].transform("median").replace(0, np.nan)
            agg["session_volatility_baseline"] = session_baseline.fillna(agg[atr_column].median())

            boll_mid = agg["close"].rolling(20, min_periods=5).mean()
            boll_std = agg["close"].rolling(20, min_periods=5).std().fillna(0.0)
            agg["boll_mid"] = boll_mid.fillna(agg["close"])
            agg["boll_upper"] = agg["boll_mid"] + 2.0 * boll_std
            agg["boll_lower"] = agg["boll_mid"] - 2.0 * boll_std
            boll_span = (agg["boll_upper"] - agg["boll_lower"]).replace(0, np.nan)
            agg["bollinger_position"] = (
                (agg["close"] - agg["boll_lower"]) / boll_span
            ).replace([np.inf, -np.inf], np.nan).fillna(0.5).clip(0.0, 1.0)

            agg["ema_slope_20"] = agg[ema_slope_20_column]
            agg["ema_slope_60"] = agg[ema_slope_60_column]
            agg["price_distance_to_ema20"] = agg[distance_column]

            output_columns.extend(
                [
                    "ema_slope_20",
                    "ema_slope_60",
                    "price_distance_to_ema20",
                    "realized_volatility_m5",
                    "volatility_ratio",
                    "session_volatility_baseline",
                    "boll_mid",
                    "boll_upper",
                    "boll_lower",
                    "bollinger_position",
                ]
            )
        elif prefix == "h1":
            returns = np.log(agg["close"]).diff().fillna(0.0)
            agg["realized_volatility_h1"] = (
                returns.rolling(10, min_periods=3).std().fillna(0.0) * math.sqrt(10)
            )
            output_columns.append("realized_volatility_h1")

        return agg[output_columns]

    @staticmethod
    def _ensure_context_columns(frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.copy()
        frame["weekday"] = frame["timestamp"].dt.weekday.astype(int)
        frame["hour_bucket"] = frame["timestamp"].dt.hour.astype(int)

        if "news_level" not in frame.columns:
            frame["news_level"] = "none"
        frame["news_level"] = frame["news_level"].fillna("none").astype(str)

        if "event_category" not in frame.columns:
            frame["event_category"] = ""
        frame["event_category"] = frame["event_category"].fillna("").astype(str)

        if "event_source" not in frame.columns:
            frame["event_source"] = ""
        frame["event_source"] = frame["event_source"].fillna("").astype(str)
        return frame

    @staticmethod
    def _midline_return_speed(frame: pd.DataFrame) -> pd.Series:
        current_distance = (frame["close"] - frame["boll_mid"]).abs()
        prior_distance = current_distance.shift(3)
        atr_reference = frame["atr_m1_14"].replace(0, np.nan)
        speed = (prior_distance - current_distance) / atr_reference
        return speed.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    def _regime_conflict_score(self, frame: pd.DataFrame) -> pd.Series:
        votes = pd.DataFrame(
            {
                "m5": self._trend_vote(frame["ema20_m5"] - frame["ema60_m5"], frame["ema_slope_20"]),
                "m15": self._trend_vote(frame["ema20_m15"] - frame["ema60_m15"], frame["ema_slope_20_m15"]),
                "h1": self._trend_vote(frame["ema20_h1"] - frame["ema60_h1"], frame["ema_slope_20_h1"]),
            },
            index=frame.index,
        )

        conflict_counts = pd.Series(0.0, index=frame.index)
        valid_pair_counts = pd.Series(0.0, index=frame.index)
        for left, right in combinations(votes.columns, 2):
            pair_valid = (votes[left] != 0) & (votes[right] != 0)
            pair_conflict = pair_valid & (votes[left] != votes[right])
            conflict_counts = conflict_counts + pair_conflict.astype(float)
            valid_pair_counts = valid_pair_counts + pair_valid.astype(float)

        return (conflict_counts / valid_pair_counts.replace(0.0, np.nan)).fillna(0.0)

    @staticmethod
    def _trend_vote(spread: pd.Series, slope: pd.Series) -> pd.Series:
        bullish = (spread > 0) & (slope >= 0)
        bearish = (spread < 0) & (slope <= 0)
        return pd.Series(np.select([bullish, bearish], [1, -1], default=0), index=spread.index)

    @staticmethod
    def _breakout_retest_confirmed(frame: pd.DataFrame) -> pd.Series:
        tolerance = frame["atr_m1_14"].fillna(0.0) * 0.15
        bullish = (frame["breakout_distance"] > 0) & (frame["low"] <= frame["recent_high_n"] + tolerance)
        bearish = (frame["breakout_distance"] < 0) & (frame["high"] >= frame["recent_low_n"] - tolerance)
        return (bullish | bearish).fillna(False)

    @staticmethod
    def _structural_stop_distance(frame: pd.DataFrame) -> pd.Series:
        long_distance = (frame["close"] - frame["recent_low_n"]).abs()
        short_distance = (frame["recent_high_n"] - frame["close"]).abs()
        return pd.concat([long_distance, short_distance], axis=1).min(axis=1).fillna(0.0)

    @staticmethod
    def _m1_reversal_confirmed(frame: pd.DataFrame) -> pd.Series:
        bullish_reversal = (frame["close"] > frame["open"]) & (frame["wick_ratio_down"] >= 0.30)
        bearish_reversal = (frame["close"] < frame["open"]) & (frame["wick_ratio_up"] >= 0.30)
        return (bullish_reversal | bearish_reversal).fillna(False)

    @staticmethod
    def _event_proximity_score(minutes_to_event: pd.Series) -> pd.Series:
        minutes = pd.to_numeric(minutes_to_event, errors="coerce")
        proximity = 1.0 - (minutes / 60.0)
        proximity = proximity.where(minutes.notna(), 0.0)
        return proximity.clip(lower=0.0, upper=1.0).fillna(0.0)
