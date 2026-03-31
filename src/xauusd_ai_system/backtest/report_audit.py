from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    numerator_value = _as_float(numerator)
    denominator_value = _as_float(denominator)
    if numerator_value is None or denominator_value in (None, 0.0):
        return None
    return round(numerator_value / denominator_value, 8)


def _coerce_counter(source: Any) -> dict[str, int]:
    mapping = _as_mapping(source)
    normalized: dict[str, int] = {}
    for key, value in mapping.items():
        normalized[str(key)] = int(value) if isinstance(value, int) else 0
    return normalized


def _extract_check_map(checks: Any) -> dict[str, dict[str, Any]]:
    check_map: dict[str, dict[str, Any]] = {}
    if not isinstance(checks, list):
        return check_map

    for item in checks:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            check_map[name] = dict(item)
    return check_map


def _extract_sample_bars(source_path: Path) -> int | None:
    matches = re.findall(r"(?<!\d)(\d{4,})(?!\d)", source_path.stem)
    if not matches:
        return None
    return max(int(match) for match in matches)


def _build_sample_snapshot(source_path: Path) -> dict[str, Any]:
    envelope = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(envelope, Mapping):
        raise ValueError(f"Report JSON must be an object: {source_path}")

    payload = envelope.get("payload")
    if isinstance(payload, Mapping):
        report_payload = dict(payload)
        envelope_ready = envelope.get("ready")
        ready = envelope_ready if isinstance(envelope_ready, bool) else report_payload.get("ready")
        report_type = envelope.get("report_type")
        saved_at = envelope.get("saved_at")
    else:
        report_payload = dict(envelope)
        ready = report_payload.get("ready")
        report_type = None
        saved_at = None

    backtest = _as_mapping(report_payload.get("backtest"))
    decision_summary = _as_mapping(backtest.get("decision_summary"))
    trade_segmentation = _as_mapping(backtest.get("trade_segmentation"))
    states_by_label = _coerce_counter(decision_summary.get("states_by_label"))
    states_by_session = {
        str(session): _coerce_counter(counts)
        for session, counts in _as_mapping(decision_summary.get("states_by_session")).items()
    }
    signals_by_strategy = _coerce_counter(decision_summary.get("signals_by_strategy"))
    blocked_reasons = _coerce_counter(decision_summary.get("blocked_reasons"))
    performance_by_session = {
        str(label): _as_mapping(metrics)
        for label, metrics in _as_mapping(trade_segmentation.get("performance_by_session")).items()
    }
    performance_by_exit_reason = {
        str(label): _as_mapping(metrics)
        for label, metrics in _as_mapping(trade_segmentation.get("performance_by_exit_reason")).items()
    }
    checks_by_name = _extract_check_map(report_payload.get("checks"))

    rows_processed = _as_int(decision_summary.get("rows_processed")) or 0
    signals_generated = _as_int(decision_summary.get("signals_generated")) or 0
    trades_allowed = _as_int(decision_summary.get("trades_allowed")) or 0
    closed_trades = _as_int(backtest.get("closed_trades")) or 0
    pullback_state_rows = states_by_label.get("pullback_continuation", 0)
    us_pullback_state_rows = states_by_session.get("us", {}).get("pullback_continuation", 0)
    pullback_signal_count = signals_by_strategy.get("pullback", 0)
    dominant_blocked_reason = (
        max(blocked_reasons.items(), key=lambda item: item[1])[0]
        if blocked_reasons
        else None
    )

    return {
        "source_path": str(source_path),
        "source_name": source_path.name,
        "sample_bars": _extract_sample_bars(source_path),
        "report_type": report_type or "acceptance",
        "saved_at": saved_at,
        "checked_at": report_payload.get("checked_at"),
        "ready": bool(ready) if isinstance(ready, bool) else None,
        "checks_summary": _as_mapping(report_payload.get("summary")),
        "acceptance_checks": {
            "total_profit_factor": _as_mapping(checks_by_name.get("total_profit_factor")),
            "out_of_sample_profit_factor": _as_mapping(checks_by_name.get("out_of_sample_profit_factor")),
            "walk_forward_positive_window_rate": _as_mapping(
                checks_by_name.get("walk_forward_positive_window_rate")
            ),
            "close_month_profit_concentration": _as_mapping(
                checks_by_name.get("close_month_profit_concentration")
            ),
            "session_profit_concentration": _as_mapping(
                checks_by_name.get("session_profit_concentration")
            ),
        },
        "backtest": {
            "closed_trades": closed_trades,
            "won_trades": _as_int(backtest.get("won_trades")),
            "lost_trades": _as_int(backtest.get("lost_trades")),
            "net_pnl": _as_float(backtest.get("net_pnl")),
            "profit_factor": _as_float(backtest.get("profit_factor")),
            "win_rate": _as_float(backtest.get("win_rate")),
            "max_drawdown_pct": _as_float(backtest.get("max_drawdown_pct")),
        },
        "coverage": {
            "rows_processed": rows_processed,
            "signals_generated": signals_generated,
            "trades_allowed": trades_allowed,
            "blocked_trades": _as_int(decision_summary.get("blocked_trades")) or 0,
            "pullback_state_rows": pullback_state_rows,
            "us_pullback_state_rows": us_pullback_state_rows,
            "pullback_signal_count": pullback_signal_count,
            "pullback_state_rate": _safe_ratio(pullback_state_rows, rows_processed),
            "pullback_signal_per_state_rate": _safe_ratio(
                pullback_signal_count,
                pullback_state_rows,
            ),
            "pullback_signal_share_of_total_signals": _safe_ratio(
                pullback_signal_count,
                signals_generated,
            ),
            "trade_allow_rate": _safe_ratio(trades_allowed, signals_generated),
            "closed_trade_per_allowed_trade_rate": _safe_ratio(
                closed_trades,
                trades_allowed,
            ),
            "us_pullback_state_share": _safe_ratio(
                us_pullback_state_rows,
                pullback_state_rows,
            ),
        },
        "signal_mix": {
            "signals_by_strategy": signals_by_strategy,
        },
        "blocking": {
            "blocked_reasons": blocked_reasons,
            "dominant_blocked_reason": dominant_blocked_reason,
        },
        "performance": {
            "by_session": performance_by_session,
            "by_exit_reason": performance_by_exit_reason,
        },
        "walk_forward": {
            "summary": _as_mapping(_as_mapping(report_payload.get("walk_forward")).get("summary")),
        },
    }


def _is_flat(series: Sequence[int | None]) -> bool:
    comparable = [value for value in series if value is not None]
    return len(comparable) >= 2 and len(set(comparable)) == 1


def _is_strictly_increasing(series: Sequence[int | None]) -> bool:
    comparable = [value for value in series if value is not None]
    return len(comparable) >= 2 and all(
        current > previous for previous, current in zip(comparable, comparable[1:])
    )


def _aggregate_counts(samples: Sequence[dict[str, Any]], key_path: Sequence[str]) -> Counter[str]:
    totals: Counter[str] = Counter()
    for sample in samples:
        current: Any = sample
        for key in key_path:
            current = _as_mapping(current).get(key)
        totals.update(_coerce_counter(current))
    return totals


def _all_ready(samples: Sequence[dict[str, Any]]) -> bool:
    ready_values = [sample.get("ready") for sample in samples]
    return bool(ready_values) and all(value is True for value in ready_values)


def _build_diagnosis(samples: Sequence[dict[str, Any]]) -> tuple[str | None, list[str], list[str], list[str]]:
    diagnosis: list[str] = []
    recommended_focus: list[str] = []
    deprioritized_changes: list[str] = []

    closed_trade_counts = [sample["backtest"]["closed_trades"] for sample in samples]
    pullback_signal_counts = [sample["coverage"]["pullback_signal_count"] for sample in samples]
    trades_allowed_counts = [sample["coverage"]["trades_allowed"] for sample in samples]
    pullback_state_counts = [sample["coverage"]["pullback_state_rows"] for sample in samples]
    session_top_labels = [
        _as_mapping(sample["acceptance_checks"]["session_profit_concentration"].get("metadata")).get("top_label")
        for sample in samples
    ]

    if _all_ready(samples):
        diagnosis.append(
            "Longer samples kept the candidate in ready=true, so the branch gate is not the current blocker."
        )
    if _is_flat(closed_trade_counts):
        diagnosis.append(
            "Closed trades stayed flat across the audited samples, so trade coverage did not scale with more bars."
        )
    if _is_strictly_increasing(pullback_state_counts) and _is_flat(pullback_signal_counts):
        diagnosis.append(
            "Pullback state rows increased with sample size, but pullback signal count stayed flat, which points to overly strict pullback trigger conditions."
        )
    if pullback_signal_counts == trades_allowed_counts and any(pullback_signal_counts):
        diagnosis.append(
            "Every generated pullback signal was still allowed through routing/risk, so pullback coverage is constrained before execution gating."
        )
    if session_top_labels and all(label == "us" for label in session_top_labels):
        diagnosis.append(
            "Positive PnL stayed concentrated in the US session across all audited samples."
        )

    aggregate_signal_mix = _aggregate_counts(samples, ("signal_mix", "signals_by_strategy"))
    dominant_signal_strategy = (
        max(aggregate_signal_mix.items(), key=lambda item: item[1])[0]
        if aggregate_signal_mix
        else None
    )
    aggregate_blocked_reasons = _aggregate_counts(samples, ("blocking", "blocked_reasons"))
    dominant_blocked_reason = (
        max(aggregate_blocked_reasons.items(), key=lambda item: item[1])[0]
        if aggregate_blocked_reasons
        else None
    )

    coverage_bottleneck: str | None = None
    if _is_strictly_increasing(pullback_state_counts) and _is_flat(pullback_signal_counts):
        coverage_bottleneck = "pullback_signal_generation"
        recommended_focus.extend(
            [
                "pullback.min_entry_hour",
                "pullback.min_directional_distance_to_ema20_atr",
                "pullback.min_pullback_depth",
                "pullback.min_atr_m1",
                "pullback.min_atr_m5",
            ]
        )
        deprioritized_changes.extend(
            [
                "Do not reopen breakout before pullback trigger density is audited and improved.",
                "Do not reopen asia before pullback trigger density is audited and improved.",
            ]
        )
    elif _is_flat(trades_allowed_counts) and not _is_flat(pullback_signal_counts):
        coverage_bottleneck = "routing_or_risk_gating"
        recommended_focus.extend(
            [
                "routing.allowed_sessions",
                "risk.max_spread_ratio",
                "routing.enabled_strategies",
            ]
        )

    if dominant_signal_strategy == "breakout":
        diagnosis.append(
            "Breakout remains the dominant dormant signal source, but the current bottleneck is still the sparse pullback trigger path rather than a runtime failure."
        )
    if dominant_blocked_reason == "STRATEGY_DISABLED":
        diagnosis.append(
            "Most blocked signals come from intentionally disabled strategies, which confirms the low frequency is caused by deliberate research-time narrowing."
        )

    return coverage_bottleneck, diagnosis, recommended_focus, deprioritized_changes


def build_acceptance_report_audit(json_paths: Sequence[str | Path]) -> dict[str, Any]:
    if not json_paths:
        raise ValueError("At least one report JSON path is required.")

    samples = [_build_sample_snapshot(Path(path)) for path in json_paths]
    samples.sort(
        key=lambda sample: (
            sample["sample_bars"] is None,
            sample["sample_bars"] or 0,
            sample["source_name"],
        )
    )

    closed_trade_counts = [sample["backtest"]["closed_trades"] for sample in samples]
    pullback_signal_counts = [sample["coverage"]["pullback_signal_count"] for sample in samples]
    trades_allowed_counts = [sample["coverage"]["trades_allowed"] for sample in samples]
    pullback_state_counts = [sample["coverage"]["pullback_state_rows"] for sample in samples]
    coverage_bottleneck, diagnosis, recommended_focus, deprioritized_changes = _build_diagnosis(samples)

    aggregate_signal_mix = _aggregate_counts(samples, ("signal_mix", "signals_by_strategy"))
    aggregate_blocked_reasons = _aggregate_counts(samples, ("blocking", "blocked_reasons"))
    dominant_signal_strategy = (
        max(aggregate_signal_mix.items(), key=lambda item: item[1])[0]
        if aggregate_signal_mix
        else None
    )
    dominant_blocked_reason = (
        max(aggregate_blocked_reasons.items(), key=lambda item: item[1])[0]
        if aggregate_blocked_reasons
        else None
    )

    return {
        "audited": True,
        "report_type": "acceptance_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(samples),
        "samples": samples,
        "comparison": {
            "sample_bars": [sample["sample_bars"] for sample in samples],
            "ready_all": _all_ready(samples),
            "closed_trade_counts": closed_trade_counts,
            "pullback_signal_counts": pullback_signal_counts,
            "trades_allowed_counts": trades_allowed_counts,
            "pullback_state_counts": pullback_state_counts,
            "trade_count_plateau_detected": _is_flat(closed_trade_counts),
            "pullback_signal_plateau_detected": _is_flat(pullback_signal_counts),
            "trades_allowed_plateau_detected": _is_flat(trades_allowed_counts),
            "pullback_state_rows_increasing": _is_strictly_increasing(pullback_state_counts),
            "dominant_signal_strategy": dominant_signal_strategy,
            "dominant_blocked_reason": dominant_blocked_reason,
            "aggregate_signals_by_strategy": dict(aggregate_signal_mix),
            "aggregate_blocked_reasons": dict(aggregate_blocked_reasons),
            "coverage_bottleneck": coverage_bottleneck,
            "diagnosis": diagnosis,
            "recommended_focus": recommended_focus,
            "deprioritized_changes": deprioritized_changes,
        },
    }
