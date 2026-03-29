from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close"}


class CSVMarketDataLoader:
    """
    Loads historical market data from CSV into a normalized M1 dataframe.

    Expected minimum columns:
    - timestamp
    - open
    - high
    - low
    - close

    Optional columns:
    - bid
    - ask
    - spread
    - volume
    - session_tag
    - news_flag
    - news_level
    - minutes_to_event
    - minutes_from_event
    - event_category
    - event_source
    """

    def load(self, path: str | Path, *, symbol: str = "XAUUSD") -> pd.DataFrame:
        frame = pd.read_csv(path)
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"CSV data is missing required columns: {sorted(missing)}")

        frame = frame.copy()
        parsed_timestamp = pd.to_datetime(frame["timestamp"], utc=True)
        frame["timestamp"] = parsed_timestamp.dt.tz_localize(None)
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp")
        frame["symbol"] = frame.get("symbol", symbol)

        frame["close"] = frame["close"].astype(float)
        frame["open"] = frame["open"].astype(float)
        frame["high"] = frame["high"].astype(float)
        frame["low"] = frame["low"].astype(float)

        if "spread" not in frame.columns:
            if {"bid", "ask"}.issubset(frame.columns):
                frame["spread"] = frame["ask"].astype(float) - frame["bid"].astype(float)
            else:
                frame["spread"] = 0.0
        else:
            frame["spread"] = frame["spread"].astype(float)

        if "bid" not in frame.columns:
            frame["bid"] = frame["close"] - frame["spread"] / 2.0
        if "ask" not in frame.columns:
            frame["ask"] = frame["close"] + frame["spread"] / 2.0

        frame["bid"] = frame["bid"].astype(float)
        frame["ask"] = frame["ask"].astype(float)
        if "volume" not in frame.columns:
            frame["volume"] = 0.0
        frame["volume"] = frame["volume"].fillna(0.0).astype(float)

        if "news_flag" not in frame.columns:
            frame["news_flag"] = False
        frame["news_flag"] = frame["news_flag"].fillna(False).astype(bool)

        if "news_level" not in frame.columns:
            frame["news_level"] = "none"
        frame["news_level"] = frame["news_level"].fillna("none").astype(str)

        if "minutes_to_event" not in frame.columns:
            frame["minutes_to_event"] = None
        if "minutes_from_event" not in frame.columns:
            frame["minutes_from_event"] = None

        if "event_category" not in frame.columns:
            frame["event_category"] = ""
        frame["event_category"] = frame["event_category"].fillna("").astype(str)

        if "event_source" not in frame.columns:
            frame["event_source"] = ""
        frame["event_source"] = frame["event_source"].fillna("").astype(str)

        if "session_tag" not in frame.columns:
            frame["session_tag"] = ""
        frame["session_tag"] = frame["session_tag"].fillna("")
        frame["session_tag"] = frame["session_tag"].where(
            frame["session_tag"].astype(bool),
            self._derive_sessions(frame["timestamp"]),
        )

        return frame.reset_index(drop=True)

    @staticmethod
    def _derive_sessions(timestamp_series: pd.Series) -> pd.Series:
        hours = timestamp_series.dt.hour
        conditions = [
            (hours >= 0) & (hours < 7),
            (hours >= 7) & (hours < 12),
            (hours >= 12) & (hours < 17),
            (hours >= 17) & (hours < 24),
        ]
        labels = ["asia", "eu", "overlap", "us"]
        session = pd.Series(index=timestamp_series.index, dtype="object")
        for condition, label in zip(conditions, labels):
            session.loc[condition] = label
        return session.fillna("unknown")
