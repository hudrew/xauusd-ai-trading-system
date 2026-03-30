from __future__ import annotations

import argparse
from dataclasses import replace
import json
import sys
from datetime import datetime
from pathlib import Path

from .config.schema import SystemConfig, load_system_config
from .core.models import AccountState, MarketSnapshot
from .core.pipeline import TradingSystem


def _load_cli_config(path: str | None) -> SystemConfig:
    project_root = Path(__file__).resolve().parents[2]
    config_path = Path(path) if path else project_root / "configs" / "mvp.yaml"
    try:
        return load_system_config(config_path)
    except RuntimeError:
        return SystemConfig()


def _run_smoke(config: SystemConfig) -> None:
    system = TradingSystem(config)

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
        features={
            "atr_m1_14": 0.8,
            "breakout_distance": 0.42,
            "ema20_m5": 3061.8,
            "ema60_m5": 3061.2,
            "ema_slope_20": 0.11,
            "false_break_count": 1,
            "spread_ratio": 1.1,
            "volatility_ratio": 1.28,
            "atr_expansion_ratio": 1.42,
            "breakout_retest_confirmed": True,
            "structural_stop_distance": 1.1,
            "spread_ratio": 1.38,
            "tick_speed": 1.24,
            "breakout_pressure": 0.33,
        },
        minutes_to_event=8,
    )
    account_state = AccountState(equity=10_000.0)

    decision = system.evaluate(snapshot, account_state)
    print(json.dumps(decision.as_dict(), indent=2, ensure_ascii=False))


def _run_preflight(config: SystemConfig) -> bool:
    from .bootstrap import build_preflight_runner

    runner = build_preflight_runner(config)
    report = runner.run()
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    return report.ready


def _run_host_check(config: SystemConfig) -> bool:
    from .bootstrap import build_host_check_runner

    runner = build_host_check_runner(config)
    report = runner.run()
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    return report.ready


def _require_preflight_if_needed(
    config: SystemConfig,
    *,
    require_preflight: bool,
) -> None:
    should_require = require_preflight or not config.runtime.dry_run
    if not should_require:
        return

    ready = _run_preflight(config)
    if not ready:
        raise SystemExit(2)


def _require_live_gate_if_needed(
    config: SystemConfig,
    *,
    require_preflight: bool,
    require_deploy_gate: bool,
) -> None:
    should_require_deploy_gate = require_deploy_gate or not config.runtime.dry_run
    if should_require_deploy_gate:
        ready = _run_deploy_gate(
            config,
            report_dir=None,
            report_type="acceptance",
            max_acceptance_age_hours=None,
            require_acceptance_report=None,
            require_host_check=None,
            require_preflight=True if require_preflight else None,
        )
        if not ready:
            raise SystemExit(2)
        return

    _require_preflight_if_needed(config, require_preflight=require_preflight)


def _run_live_once(
    config: SystemConfig,
    require_preflight: bool = False,
    require_deploy_gate: bool = False,
) -> None:
    from .bootstrap import build_live_runner

    _require_live_gate_if_needed(
        config,
        require_preflight=require_preflight,
        require_deploy_gate=require_deploy_gate,
    )
    runner = build_live_runner(config)
    try:
        decision = runner.run_once()
        print(json.dumps(decision.as_dict(), indent=2, ensure_ascii=False))
    finally:
        runner.shutdown()


def _run_live_loop(
    config: SystemConfig,
    iterations: int | None,
    require_preflight: bool = False,
    require_deploy_gate: bool = False,
) -> None:
    from .bootstrap import build_live_runner

    _require_live_gate_if_needed(
        config,
        require_preflight=require_preflight,
        require_deploy_gate=require_deploy_gate,
    )
    runner = build_live_runner(config)
    try:
        runner.run_loop(iterations=iterations)
    finally:
        runner.shutdown()


def _run_replay(
    config: SystemConfig,
    csv_path: str,
    *,
    symbol: str,
    equity: float,
) -> None:
    from .backtest.runner import HistoricalReplayRunner

    report = HistoricalReplayRunner(config).run_csv(
        csv_path,
        symbol=symbol,
        equity=equity,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


def _run_backtest(
    config: SystemConfig,
    csv_path: str,
    *,
    symbol: str | None,
    initial_cash: float | None,
    commission: float | None,
    slippage_perc: float | None,
    slippage_fixed: float | None,
) -> None:
    from .backtest.backtrader_runner import run_backtrader_csv

    report = run_backtrader_csv(
        csv_path,
        config,
        symbol=symbol,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


def _run_sample_split(
    config: SystemConfig,
    csv_path: str,
    *,
    symbol: str | None,
    train_ratio: float,
    warmup_bars: int,
    initial_cash: float | None,
    commission: float | None,
    slippage_perc: float | None,
    slippage_fixed: float | None,
) -> None:
    from .backtest.evaluation import run_in_out_sample_csv

    report = run_in_out_sample_csv(
        csv_path,
        config,
        symbol=symbol,
        train_ratio=train_ratio,
        warmup_bars=warmup_bars,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


def _run_walk_forward(
    config: SystemConfig,
    csv_path: str,
    *,
    symbol: str | None,
    train_bars: int,
    test_bars: int,
    step_bars: int | None,
    warmup_bars: int,
    initial_cash: float | None,
    commission: float | None,
    slippage_perc: float | None,
    slippage_fixed: float | None,
) -> None:
    from .backtest.evaluation import run_walk_forward_csv

    report = run_walk_forward_csv(
        csv_path,
        config,
        symbol=symbol,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
        warmup_bars=warmup_bars,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


def _run_acceptance(
    config: SystemConfig,
    csv_path: str,
    *,
    symbol: str | None,
    train_ratio: float,
    warmup_bars: int,
    train_bars: int,
    test_bars: int,
    step_bars: int | None,
    initial_cash: float | None,
    commission: float | None,
    slippage_perc: float | None,
    slippage_fixed: float | None,
    save_archive: bool,
    report_dir: str | None,
) -> None:
    from .backtest.acceptance import run_acceptance_csv
    from .storage.report_archive import FileReportArchive

    report = run_acceptance_csv(
        csv_path,
        config,
        symbol=symbol,
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
    archive_config = replace(config.report_archive)
    if report_dir is not None:
        archive_config.base_dir = report_dir
    archive_config.enabled = bool(save_archive and archive_config.enabled)

    payload = report.as_dict()
    archive_record = FileReportArchive(archive_config).save(
        "acceptance",
        payload,
        summary=report.summary.as_dict(),
        ready=report.ready,
    )
    payload["archive"] = archive_record.as_dict() if archive_record is not None else None
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _build_report_archive_config(config: SystemConfig, report_dir: str | None):
    archive_config = replace(config.report_archive)
    if report_dir is not None:
        archive_config.base_dir = report_dir
    return archive_config


def _run_reports(
    config: SystemConfig,
    *,
    view: str,
    report_type: str | None,
    limit: int,
    report_dir: str | None,
    full: bool,
) -> None:
    from .storage.report_catalog import FileReportCatalog

    archive_config = _build_report_archive_config(config, report_dir)
    catalog = FileReportCatalog(archive_config)
    base_payload = {
        "view": view,
        "report_dir": str(catalog.base_dir),
        "report_type": report_type,
    }

    if view == "list":
        records = catalog.list_records(report_type=report_type, limit=limit)
        base_payload["count"] = len(records)
        base_payload["records"] = [record.as_dict() for record in records]
        print(json.dumps(base_payload, indent=2, ensure_ascii=False))
        return

    if view == "latest":
        details = catalog.latest_report(report_type=report_type)
        base_payload["result"] = (
            details.as_dict(include_payload=full)
            if details is not None
            else None
        )
        print(json.dumps(base_payload, indent=2, ensure_ascii=False))
        return

    trend = catalog.build_trend(report_type=report_type, limit=limit)
    base_payload["window_size"] = limit
    base_payload.update(trend.as_dict())
    print(json.dumps(base_payload, indent=2, ensure_ascii=False))


def _run_report_import(
    config: SystemConfig,
    *,
    json_path: str,
    report_type: str | None,
    report_dir: str | None,
) -> None:
    from .storage.report_archive import FileReportArchive

    source_path = Path(json_path)
    envelope = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(envelope, dict):
        raise SystemExit("Imported report JSON must be an object.")

    if isinstance(envelope.get("payload"), dict):
        payload = dict(envelope["payload"])
        inferred_report_type = envelope.get("report_type")
        summary = envelope.get("summary") or payload.get("summary") or {}
        ready = envelope.get("ready")
        if ready is None:
            ready = payload.get("ready")
    else:
        payload = dict(envelope)
        inferred_report_type = None
        summary = payload.get("summary") or {}
        ready = payload.get("ready")

    payload.pop("archive", None)

    archive_config = _build_report_archive_config(config, report_dir)
    archive_config.enabled = True

    resolved_report_type = report_type or inferred_report_type or "acceptance"
    archive_record = FileReportArchive(archive_config).save(
        resolved_report_type,
        payload,
        summary=summary if isinstance(summary, dict) else {},
        ready=ready if isinstance(ready, bool) else None,
    )
    if archive_record is None:
        raise SystemExit("Report archive is disabled; unable to import report.")

    print(
        json.dumps(
            {
                "imported": True,
                "source_path": str(source_path),
                "report_type": resolved_report_type,
                "checked_at": payload.get("checked_at"),
                "ready": ready if isinstance(ready, bool) else None,
                "record": archive_record.as_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _run_report_export(
    config: SystemConfig,
    *,
    output_path: str,
    report_type: str | None,
    report_dir: str | None,
) -> None:
    from .storage.report_catalog import FileReportCatalog

    archive_config = _build_report_archive_config(config, report_dir)
    catalog = FileReportCatalog(archive_config)
    details = catalog.latest_report(report_type=report_type)
    if details is None:
        raise SystemExit("No archived report available for export.")

    source_path = Path(details.record.latest_path or details.record.archive_path)
    if not source_path.exists():
        raise SystemExit(f"Archived report file not found: {source_path}")

    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(
        json.dumps(
            {
                "exported": True,
                "report_type": details.record.report_type,
                "checked_at": details.checked_at,
                "ready": details.record.ready,
                "source_path": str(source_path),
                "output_path": str(resolved_output_path),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _run_export_mt5_history(
    config: SystemConfig,
    *,
    output_path: str,
    symbol: str | None,
    timeframe: str | None,
    bars: int | None,
) -> None:
    from .data.mt5_history_exporter import MT5HistoryCsvExporter

    result = MT5HistoryCsvExporter(config).export_csv(
        output_path,
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
    )
    print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))


def _run_deploy_gate(
    config: SystemConfig,
    *,
    report_dir: str | None,
    report_type: str,
    max_acceptance_age_hours: float | None,
    require_acceptance_report: bool | None,
    require_host_check: bool | None,
    require_preflight: bool | None,
) -> bool:
    from .bootstrap import build_deployment_gate_runner

    runner = build_deployment_gate_runner(
        config,
        report_dir=report_dir,
        report_type=report_type,
        max_acceptance_age_hours=max_acceptance_age_hours,
        require_acceptance_report=require_acceptance_report,
        require_host_check=require_host_check,
        require_preflight=require_preflight,
    )
    report = runner.run()
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    return report.ready


def main() -> None:
    parser = argparse.ArgumentParser(description="XAUUSD AI quant trading system CLI")
    parser.add_argument(
        "--config",
        help="Optional path to a YAML config file. Defaults to configs/mvp.yaml.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("smoke", help="Run the built-in static smoke scenario.")
    host_check_parser = subparsers.add_parser(
        "host-check",
        help="Check whether this machine is suitable as an MT5 execution host.",
    )
    host_check_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 2 when the host check is not ready.",
    )
    subparsers.add_parser(
        "live-once",
        help="Pull live market data once, calculate features, and process one decision.",
    )
    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Run live platform readiness checks before paper/live deployment.",
    )
    preflight_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 2 when the preflight report is not ready.",
    )
    live_once_parser = subparsers.choices["live-once"]
    live_once_parser.add_argument(
        "--require-preflight",
        action="store_true",
        help="Run preflight before live-once when dry_run=true. In live mode deploy-gate already implies preflight.",
    )
    live_once_parser.add_argument(
        "--require-deploy-gate",
        action="store_true",
        help="Force deploy-gate before live-once even when dry_run=true.",
    )
    live_loop_parser = subparsers.add_parser(
        "live-loop",
        help="Continuously poll market data and process decisions.",
    )
    live_loop_parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Optional number of polling cycles to run before exiting.",
    )
    live_loop_parser.add_argument(
        "--require-preflight",
        action="store_true",
        help="Run preflight before live-loop when dry_run=true. In live mode deploy-gate already implies preflight.",
    )
    live_loop_parser.add_argument(
        "--require-deploy-gate",
        action="store_true",
        help="Force deploy-gate before live-loop even when dry_run=true.",
    )
    replay_parser = subparsers.add_parser(
        "replay",
        help="Replay a historical CSV file and emit a structured acceptance report.",
    )
    replay_parser.add_argument("csv_path", help="Path to the historical CSV file.")
    replay_parser.add_argument(
        "--symbol",
        default="XAUUSD",
        help="Trading symbol label.",
    )
    replay_parser.add_argument(
        "--equity",
        type=float,
        default=10_000.0,
        help="Starting equity for risk sizing during replay.",
    )
    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Run a Backtrader execution backtest and emit a structured PnL report.",
    )
    backtest_parser.add_argument("csv_path", help="Path to the historical CSV file.")
    backtest_parser.add_argument(
        "--symbol",
        default=None,
        help="Optional trading symbol label. Defaults to the config symbol.",
    )
    backtest_parser.add_argument(
        "--initial-cash",
        type=float,
        default=None,
        help="Override backtest.initial_cash from config.",
    )
    backtest_parser.add_argument(
        "--commission",
        type=float,
        default=None,
        help="Override backtest.commission from config. Uses absolute percentage, for example 0.0005 = 5 bps.",
    )
    backtest_parser.add_argument(
        "--slippage-perc",
        type=float,
        default=None,
        help="Override backtest.slippage_perc from config. Uses absolute percentage, for example 0.0001 = 1 bp.",
    )
    backtest_parser.add_argument(
        "--slippage-fixed",
        type=float,
        default=None,
        help="Override backtest.slippage_fixed from config in instrument price units.",
    )
    split_parser = subparsers.add_parser(
        "sample-split",
        help="Run chronological in-sample / out-of-sample evaluation with warmup bars.",
    )
    split_parser.add_argument("csv_path", help="Path to the historical CSV file.")
    split_parser.add_argument(
        "--symbol",
        default=None,
        help="Optional trading symbol label. Defaults to the config symbol.",
    )
    split_parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Chronological fraction used for the in-sample split.",
    )
    split_parser.add_argument(
        "--warmup-bars",
        type=int,
        default=720,
        help="Number of bars to prepend before the out-of-sample slice for feature warmup.",
    )
    split_parser.add_argument(
        "--initial-cash",
        type=float,
        default=None,
        help="Override backtest.initial_cash from config.",
    )
    split_parser.add_argument(
        "--commission",
        type=float,
        default=None,
        help="Override backtest.commission from config. Uses absolute percentage, for example 0.0005 = 5 bps.",
    )
    split_parser.add_argument(
        "--slippage-perc",
        type=float,
        default=None,
        help="Override backtest.slippage_perc from config. Uses absolute percentage, for example 0.0001 = 1 bp.",
    )
    split_parser.add_argument(
        "--slippage-fixed",
        type=float,
        default=None,
        help="Override backtest.slippage_fixed from config in instrument price units.",
    )
    walk_forward_parser = subparsers.add_parser(
        "walk-forward",
        help="Run rolling walk-forward backtests with test-only statistics and warmup bars.",
    )
    walk_forward_parser.add_argument("csv_path", help="Path to the historical CSV file.")
    walk_forward_parser.add_argument(
        "--symbol",
        default=None,
        help="Optional trading symbol label. Defaults to the config symbol.",
    )
    walk_forward_parser.add_argument(
        "--train-bars",
        type=int,
        default=5000,
        help="Number of chronological bars in each rolling training window.",
    )
    walk_forward_parser.add_argument(
        "--test-bars",
        type=int,
        default=1000,
        help="Number of chronological bars in each rolling test window.",
    )
    walk_forward_parser.add_argument(
        "--step-bars",
        type=int,
        default=None,
        help="Number of bars to move the window forward each iteration. Defaults to test-bars.",
    )
    walk_forward_parser.add_argument(
        "--warmup-bars",
        type=int,
        default=720,
        help="Number of bars to prepend before each test window for feature warmup.",
    )
    walk_forward_parser.add_argument(
        "--initial-cash",
        type=float,
        default=None,
        help="Override backtest.initial_cash from config.",
    )
    walk_forward_parser.add_argument(
        "--commission",
        type=float,
        default=None,
        help="Override backtest.commission from config. Uses absolute percentage, for example 0.0005 = 5 bps.",
    )
    walk_forward_parser.add_argument(
        "--slippage-perc",
        type=float,
        default=None,
        help="Override backtest.slippage_perc from config. Uses absolute percentage, for example 0.0001 = 1 bp.",
    )
    walk_forward_parser.add_argument(
        "--slippage-fixed",
        type=float,
        default=None,
        help="Override backtest.slippage_fixed from config in instrument price units.",
    )
    acceptance_parser = subparsers.add_parser(
        "acceptance",
        help="Run backtest, sample-split, and walk-forward together and emit an automatic acceptance verdict.",
    )
    acceptance_parser.add_argument("csv_path", help="Path to the historical CSV file.")
    acceptance_parser.add_argument(
        "--symbol",
        default=None,
        help="Optional trading symbol label. Defaults to the config symbol.",
    )
    acceptance_parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Chronological fraction used for the in-sample split.",
    )
    acceptance_parser.add_argument(
        "--warmup-bars",
        type=int,
        default=720,
        help="Bars to prepend before test windows for feature warmup.",
    )
    acceptance_parser.add_argument(
        "--train-bars",
        type=int,
        default=5000,
        help="Bars in each rolling walk-forward training window.",
    )
    acceptance_parser.add_argument(
        "--test-bars",
        type=int,
        default=1000,
        help="Bars in each rolling walk-forward test window.",
    )
    acceptance_parser.add_argument(
        "--step-bars",
        type=int,
        default=None,
        help="Bars to move the walk-forward window each iteration. Defaults to test-bars.",
    )
    acceptance_parser.add_argument(
        "--initial-cash",
        type=float,
        default=None,
        help="Override backtest.initial_cash from config.",
    )
    acceptance_parser.add_argument(
        "--commission",
        type=float,
        default=None,
        help="Override backtest.commission from config. Uses absolute percentage, for example 0.0005 = 5 bps.",
    )
    acceptance_parser.add_argument(
        "--slippage-perc",
        type=float,
        default=None,
        help="Override backtest.slippage_perc from config. Uses absolute percentage, for example 0.0001 = 1 bp.",
    )
    acceptance_parser.add_argument(
        "--slippage-fixed",
        type=float,
        default=None,
        help="Override backtest.slippage_fixed from config in instrument price units.",
    )
    acceptance_parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional override for report_archive.base_dir. Relative paths are resolved from the project root.",
    )
    acceptance_parser.add_argument(
        "--no-save-archive",
        action="store_true",
        help="Disable automatic acceptance JSON archiving for this run.",
    )
    reports_parser = subparsers.add_parser(
        "reports",
        help="Query archived research reports from the local report index.",
    )
    reports_parser.add_argument(
        "view",
        nargs="?",
        choices=["list", "latest", "trend"],
        default="trend",
        help="Query mode. Defaults to trend.",
    )
    reports_parser.add_argument(
        "--report-type",
        default="acceptance",
        help="Report type to query. Defaults to acceptance.",
    )
    reports_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of archived records to inspect.",
    )
    reports_parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional override for report_archive.base_dir. Relative paths are resolved from the project root.",
    )
    reports_parser.add_argument(
        "--full",
        action="store_true",
        help="Include the full archived payload in latest mode.",
    )
    report_import_parser = subparsers.add_parser(
        "report-import",
        help="Import a previously generated report JSON into the local research archive.",
    )
    report_import_parser.add_argument(
        "json_path",
        help="Path to a raw report JSON or an archived latest.json envelope.",
    )
    report_import_parser.add_argument(
        "--report-type",
        default=None,
        help="Optional override for the imported report type. Defaults to the JSON envelope value or acceptance.",
    )
    report_import_parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional override for report_archive.base_dir. Relative paths are resolved from the project root.",
    )
    report_export_parser = subparsers.add_parser(
        "report-export",
        help="Export the latest archived report envelope into a portable JSON file.",
    )
    report_export_parser.add_argument(
        "output_path",
        help="Path to the JSON file to write.",
    )
    report_export_parser.add_argument(
        "--report-type",
        default="acceptance",
        help="Report type to export. Defaults to acceptance.",
    )
    report_export_parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional override for report_archive.base_dir. Relative paths are resolved from the project root.",
    )
    export_mt5_parser = subparsers.add_parser(
        "export-mt5-history",
        help="Export MT5 historical bars into a normalized CSV for replay/backtest/acceptance.",
    )
    export_mt5_parser.add_argument(
        "output_path",
        help="Path to the CSV file to write.",
    )
    export_mt5_parser.add_argument(
        "--symbol",
        default=None,
        help="Optional MT5 symbol override. Defaults to config symbol.",
    )
    export_mt5_parser.add_argument(
        "--timeframe",
        default=None,
        help="Optional MT5 timeframe override such as M1/M5/M15/H1. Defaults to config timeframe.",
    )
    export_mt5_parser.add_argument(
        "--bars",
        type=int,
        default=20000,
        help="Number of most recent bars to export. Defaults to 20000.",
    )
    deploy_gate_parser = subparsers.add_parser(
        "deploy-gate",
        help="Run research acceptance and live readiness checks as a single deployment gate.",
    )
    deploy_gate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 2 when the deployment gate is not ready.",
    )
    deploy_gate_parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional override for report_archive.base_dir. Relative paths are resolved from the project root.",
    )
    deploy_gate_parser.add_argument(
        "--report-type",
        default="acceptance",
        help="Archived report type to use for the research gate. Defaults to acceptance.",
    )
    deploy_gate_parser.add_argument(
        "--max-acceptance-age-hours",
        type=float,
        default=None,
        help="Override deployment_gate.max_acceptance_report_age_hours from config.",
    )
    deploy_gate_parser.add_argument(
        "--skip-acceptance",
        dest="require_acceptance_report",
        action="store_false",
        default=None,
        help="Skip the archived acceptance gate for this run.",
    )
    deploy_gate_parser.add_argument(
        "--require-host-check",
        dest="require_host_check",
        action="store_true",
        default=None,
        help="Force host-check even when dry_run=true.",
    )
    deploy_gate_parser.add_argument(
        "--skip-host-check",
        dest="require_host_check",
        action="store_false",
        help="Skip host-check for this run.",
    )
    deploy_gate_parser.add_argument(
        "--require-preflight",
        dest="require_preflight",
        action="store_true",
        default=None,
        help="Force preflight even when dry_run=true.",
    )
    deploy_gate_parser.add_argument(
        "--skip-preflight",
        dest="require_preflight",
        action="store_false",
        help="Skip preflight for this run.",
    )

    args = parser.parse_args()
    config = _load_cli_config(args.config)

    if args.command in {None, "smoke"}:
        _run_smoke(config)
        return
    if args.command == "host-check":
        ready = _run_host_check(config)
        if args.strict and not ready:
            raise SystemExit(2)
        return
    if args.command == "live-once":
        _run_live_once(
            config,
            require_preflight=args.require_preflight,
            require_deploy_gate=args.require_deploy_gate,
        )
        return
    if args.command == "preflight":
        ready = _run_preflight(config)
        if args.strict and not ready:
            raise SystemExit(2)
        return
    if args.command == "live-loop":
        _run_live_loop(
            config,
            args.iterations,
            require_preflight=args.require_preflight,
            require_deploy_gate=args.require_deploy_gate,
        )
        return
    if args.command == "replay":
        _run_replay(
            config,
            args.csv_path,
            symbol=args.symbol,
            equity=args.equity,
        )
        return
    if args.command == "backtest":
        _run_backtest(
            config,
            args.csv_path,
            symbol=args.symbol,
            initial_cash=args.initial_cash,
            commission=args.commission,
            slippage_perc=args.slippage_perc,
            slippage_fixed=args.slippage_fixed,
        )
        return
    if args.command == "sample-split":
        _run_sample_split(
            config,
            args.csv_path,
            symbol=args.symbol,
            train_ratio=args.train_ratio,
            warmup_bars=args.warmup_bars,
            initial_cash=args.initial_cash,
            commission=args.commission,
            slippage_perc=args.slippage_perc,
            slippage_fixed=args.slippage_fixed,
        )
        return
    if args.command == "walk-forward":
        _run_walk_forward(
            config,
            args.csv_path,
            symbol=args.symbol,
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            step_bars=args.step_bars,
            warmup_bars=args.warmup_bars,
            initial_cash=args.initial_cash,
            commission=args.commission,
            slippage_perc=args.slippage_perc,
            slippage_fixed=args.slippage_fixed,
        )
        return
    if args.command == "acceptance":
        _run_acceptance(
            config,
            args.csv_path,
            symbol=args.symbol,
            train_ratio=args.train_ratio,
            warmup_bars=args.warmup_bars,
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            step_bars=args.step_bars,
            initial_cash=args.initial_cash,
            commission=args.commission,
            slippage_perc=args.slippage_perc,
            slippage_fixed=args.slippage_fixed,
            save_archive=not args.no_save_archive,
            report_dir=args.report_dir,
        )
        return
    if args.command == "reports":
        _run_reports(
            config,
            view=args.view,
            report_type=args.report_type,
            limit=args.limit,
            report_dir=args.report_dir,
            full=args.full,
        )
        return
    if args.command == "report-import":
        _run_report_import(
            config,
            json_path=args.json_path,
            report_type=args.report_type,
            report_dir=args.report_dir,
        )
        return
    if args.command == "report-export":
        _run_report_export(
            config,
            output_path=args.output_path,
            report_type=args.report_type,
            report_dir=args.report_dir,
        )
        return
    if args.command == "export-mt5-history":
        _run_export_mt5_history(
            config,
            output_path=args.output_path,
            symbol=args.symbol,
            timeframe=args.timeframe,
            bars=args.bars,
        )
        return
    if args.command == "deploy-gate":
        ready = _run_deploy_gate(
            config,
            report_dir=args.report_dir,
            report_type=args.report_type,
            max_acceptance_age_hours=args.max_acceptance_age_hours,
            require_acceptance_report=args.require_acceptance_report,
            require_host_check=args.require_host_check,
            require_preflight=args.require_preflight,
        )
        if args.strict and not ready:
            raise SystemExit(2)
        return
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
