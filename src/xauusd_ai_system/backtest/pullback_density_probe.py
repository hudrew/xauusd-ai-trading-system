from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..config.schema import SystemConfig, load_system_config
from ..data.csv_loader import CSVMarketDataLoader
from .acceptance import run_acceptance_market_data


@dataclass(frozen=True)
class PullbackDensityVariant:
    name: str
    overrides: dict[str, Any]
    note: str = ""


DEFAULT_PULLBACK_SELL_V3_DENSITY_VARIANTS: tuple[PullbackDensityVariant, ...] = (
    PullbackDensityVariant(
        name="base_v3_branch_gate",
        overrides={},
        note="Current sell-only US-only pullback v3 branch gate baseline.",
    ),
    PullbackDensityVariant(
        name="entry_hour_19",
        overrides={"pullback": {"min_entry_hour": 19}},
        note="Relax the US-entry floor by one hour.",
    ),
    PullbackDensityVariant(
        name="entry_hour_18",
        overrides={"pullback": {"min_entry_hour": 18}},
        note="Relax the US-entry floor by two hours.",
    ),
    PullbackDensityVariant(
        name="atr_m5_12",
        overrides={"pullback": {"min_atr_m5": 12.0}},
        note="Keep the v3 structure but ease the M5 ATR floor slightly.",
    ),
    PullbackDensityVariant(
        name="atr_m5_10_v2_level",
        overrides={"pullback": {"min_atr_m5": 10.0}},
        note="Match the v2 M5 ATR floor for direct comparison.",
    ),
    PullbackDensityVariant(
        name="directional_distance_0_45",
        overrides={"pullback": {"min_directional_distance_to_ema20_atr": 0.45}},
        note="Ease the directional distance floor modestly.",
    ),
    PullbackDensityVariant(
        name="density_relaxed_v1",
        overrides={
            "pullback": {
                "min_entry_hour": 19,
                "min_atr_m5": 12.0,
                "min_directional_distance_to_ema20_atr": 0.45,
            }
        },
        note="First combined density relaxation around the top three suspected bottlenecks.",
    ),
)


def _coerce_override_value(current_value: Any, override_value: Any) -> Any:
    if isinstance(current_value, tuple) and isinstance(override_value, list):
        return tuple(override_value)
    if isinstance(current_value, list) and isinstance(override_value, tuple):
        return list(override_value)
    if isinstance(current_value, list) and isinstance(override_value, list):
        return list(override_value)
    return override_value


def apply_dataclass_overrides(instance: Any, overrides: Mapping[str, Any]) -> Any:
    if not is_dataclass(instance):
        raise TypeError("apply_dataclass_overrides expects a dataclass instance.")

    valid_fields = {field_info.name for field_info in fields(instance)}
    updates: dict[str, Any] = {}
    for key, value in overrides.items():
        if key not in valid_fields:
            raise KeyError(f"Unknown override field '{key}' for {type(instance).__name__}")

        current_value = getattr(instance, key)
        if isinstance(value, Mapping) and is_dataclass(current_value):
            updates[key] = apply_dataclass_overrides(current_value, value)
            continue

        updates[key] = _coerce_override_value(current_value, value)

    return replace(instance, **updates)


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _safe_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _build_variant_result(
    payload: dict[str, Any],
    *,
    variant: PullbackDensityVariant,
) -> dict[str, Any]:
    backtest = _mapping_or_empty(payload.get("backtest"))
    decision_summary = _mapping_or_empty(backtest.get("decision_summary"))
    trade_segmentation = _mapping_or_empty(backtest.get("trade_segmentation"))
    sample_split = _mapping_or_empty(payload.get("sample_split"))
    out_of_sample = _mapping_or_empty(sample_split.get("out_of_sample"))
    out_of_sample_backtest = _mapping_or_empty(out_of_sample.get("backtest"))
    walk_forward = _mapping_or_empty(payload.get("walk_forward"))
    walk_forward_summary = _mapping_or_empty(walk_forward.get("summary"))
    checks_by_name = {
        str(item.get("name")): item
        for item in payload.get("checks", [])
        if isinstance(item, Mapping) and item.get("name")
    }

    session_perf = _mapping_or_empty(trade_segmentation.get("performance_by_session"))
    pullback_signal_count = int(
        _mapping_or_empty(decision_summary.get("signals_by_strategy")).get("pullback", 0)
    )

    return {
        "name": variant.name,
        "note": variant.note,
        "overrides": variant.overrides,
        "ready": bool(payload.get("ready")),
        "summary": _mapping_or_empty(payload.get("summary")),
        "backtest": {
            "closed_trades": int(backtest.get("closed_trades", 0)),
            "won_trades": int(backtest.get("won_trades", 0)),
            "lost_trades": int(backtest.get("lost_trades", 0)),
            "net_pnl": _safe_number(backtest.get("net_pnl")),
            "profit_factor": _safe_number(backtest.get("profit_factor")),
            "win_rate": _safe_number(backtest.get("win_rate")),
            "max_drawdown_pct": _safe_number(backtest.get("max_drawdown_pct")),
        },
        "out_of_sample": {
            "closed_trades": int(out_of_sample_backtest.get("closed_trades", 0)),
            "net_pnl": _safe_number(out_of_sample_backtest.get("net_pnl")),
            "profit_factor": _safe_number(out_of_sample_backtest.get("profit_factor")),
            "max_drawdown_pct": _safe_number(out_of_sample_backtest.get("max_drawdown_pct")),
        },
        "coverage": {
            "signals_generated": int(decision_summary.get("signals_generated", 0)),
            "trades_allowed": int(decision_summary.get("trades_allowed", 0)),
            "blocked_trades": int(decision_summary.get("blocked_trades", 0)),
            "pullback_state_rows": int(
                _mapping_or_empty(decision_summary.get("states_by_label")).get(
                    "pullback_continuation", 0
                )
            ),
            "pullback_signal_count": pullback_signal_count,
            "signal_rate": _safe_number(decision_summary.get("signal_rate")),
            "trade_allow_rate": _safe_number(decision_summary.get("trade_allow_rate")),
            "blocked_reasons": _mapping_or_empty(decision_summary.get("blocked_reasons")),
        },
        "performance": {
            "by_session": session_perf,
            "us_closed_trades": int(_mapping_or_empty(session_perf.get("us")).get("closed_trades", 0)),
            "us_net_pnl": _safe_number(_mapping_or_empty(session_perf.get("us")).get("net_pnl")),
        },
        "walk_forward": {
            "total_windows": int(walk_forward_summary.get("total_windows", 0)),
            "positive_window_rate": _safe_number(walk_forward_summary.get("positive_window_rate")),
            "total_net_pnl": _safe_number(walk_forward_summary.get("total_net_pnl")),
        },
        "acceptance_checks": {
            "session_profit_concentration": _mapping_or_empty(
                checks_by_name.get("session_profit_concentration")
            ),
            "close_month_profit_concentration": _mapping_or_empty(
                checks_by_name.get("close_month_profit_concentration")
            ),
            "walk_forward_positive_window_rate": _mapping_or_empty(
                checks_by_name.get("walk_forward_positive_window_rate")
            ),
        },
    }


def _ranking_key(result: Mapping[str, Any]) -> tuple[int, int, float, float, int]:
    backtest = _mapping_or_empty(result.get("backtest"))
    coverage = _mapping_or_empty(result.get("coverage"))
    return (
        1 if result.get("ready") else 0,
        int(backtest.get("closed_trades", 0)),
        float(backtest.get("net_pnl") or 0.0),
        float(backtest.get("profit_factor") or 0.0),
        int(coverage.get("pullback_signal_count", 0)),
    )


def _with_deltas(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not results:
        return results

    base_result = results[0]
    base_backtest = _mapping_or_empty(base_result.get("backtest"))
    base_coverage = _mapping_or_empty(base_result.get("coverage"))
    base_walk_forward = _mapping_or_empty(base_result.get("walk_forward"))

    for result in results:
        result["delta_vs_base"] = {
            "closed_trades": int(_mapping_or_empty(result.get("backtest")).get("closed_trades", 0))
            - int(base_backtest.get("closed_trades", 0)),
            "net_pnl": round(
                float(_mapping_or_empty(result.get("backtest")).get("net_pnl") or 0.0)
                - float(base_backtest.get("net_pnl") or 0.0),
                4,
            ),
            "profit_factor": round(
                float(_mapping_or_empty(result.get("backtest")).get("profit_factor") or 0.0)
                - float(base_backtest.get("profit_factor") or 0.0),
                4,
            ),
            "pullback_signal_count": int(
                _mapping_or_empty(result.get("coverage")).get("pullback_signal_count", 0)
            )
            - int(base_coverage.get("pullback_signal_count", 0)),
            "trades_allowed": int(_mapping_or_empty(result.get("coverage")).get("trades_allowed", 0))
            - int(base_coverage.get("trades_allowed", 0)),
            "walk_forward_positive_window_rate": round(
                float(_mapping_or_empty(result.get("walk_forward")).get("positive_window_rate") or 0.0)
                - float(base_walk_forward.get("positive_window_rate") or 0.0),
                6,
            ),
        }
    return results


def _build_probe_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(results, key=_ranking_key, reverse=True)
    base_result = results[0] if results else {}
    base_closed_trades = int(_mapping_or_empty(base_result.get("backtest")).get("closed_trades", 0))
    improved_ready_variants = [
        result["name"]
        for result in ranked
        if result.get("ready")
        and int(_mapping_or_empty(result.get("backtest")).get("closed_trades", 0)) > base_closed_trades
    ]
    improved_signal_variants = [
        result["name"]
        for result in ranked
        if int(_mapping_or_empty(result.get("coverage")).get("pullback_signal_count", 0))
        > int(_mapping_or_empty(base_result.get("coverage")).get("pullback_signal_count", 0))
    ]
    return {
        "best_variant_by_rank": ranked[0]["name"] if ranked else None,
        "ranking": [result["name"] for result in ranked],
        "improved_ready_variants": improved_ready_variants,
        "improved_signal_variants": improved_signal_variants,
    }


def build_pullback_density_probe(
    csv_path: str | Path,
    *,
    config_path: str | Path,
    output_path: str | Path | None = None,
    variants: Sequence[PullbackDensityVariant] | None = None,
    symbol: str | None = None,
    train_ratio: float = 0.7,
    warmup_bars: int = 720,
    train_bars: int = 5000,
    test_bars: int = 1000,
    step_bars: int | None = None,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> dict[str, Any]:
    resolved_config_path = Path(config_path)
    resolved_csv_path = Path(csv_path)
    base_config = load_system_config(resolved_config_path)
    resolved_symbol = (
        symbol
        or base_config.market_data.symbol
        or base_config.execution.symbol
        or base_config.market_data.mt5.symbol
        or "XAUUSD"
    )
    variant_specs = list(variants or DEFAULT_PULLBACK_SELL_V3_DENSITY_VARIANTS)

    market_data = CSVMarketDataLoader().load(resolved_csv_path, symbol=resolved_symbol)
    results: list[dict[str, Any]] = []
    for variant in variant_specs:
        variant_config = apply_dataclass_overrides(base_config, variant.overrides)
        report = run_acceptance_market_data(
            market_data,
            variant_config,
            symbol=resolved_symbol,
            train_ratio=train_ratio,
            warmup_bars=warmup_bars,
            train_bars=train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
            initial_cash=initial_cash,
            commission=commission,
            slippage_perc=slippage_perc,
            slippage_fixed=slippage_fixed,
        )
        results.append(_build_variant_result(report.as_dict(), variant=variant))

    results = _with_deltas(results)
    payload = {
        "probed": True,
        "report_type": "pullback_density_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(resolved_config_path),
        "csv_path": str(resolved_csv_path),
        "symbol": resolved_symbol,
        "variant_count": len(results),
        "probe_summary": _build_probe_summary(results),
        "results": results,
    }

    if output_path is not None:
        resolved_output_path = Path(output_path)
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        payload["output_path"] = str(resolved_output_path)

    return payload
