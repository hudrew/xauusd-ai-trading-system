from __future__ import annotations

from datetime import datetime
import html
import json
from typing import Any


def render_monitoring_dashboard(
    snapshot: dict[str, Any],
    *,
    title: str,
    refresh_seconds: int = 15,
) -> str:
    runtime = snapshot["runtime"]
    overview = snapshot["overview"]
    mix = snapshot["mix"]
    latest_decision = snapshot["latest_decision"]
    recent_alerts = snapshot["recent_alerts"]
    recent_decisions = snapshot["recent_decisions"]
    recent_executions = snapshot["recent_executions"]

    title_text = html.escape(title)
    runtime_status = str(runtime["status"]).upper()
    runtime_class = _status_class(str(runtime["status"]))
    generated_at = _format_timestamp(snapshot["generated_at"])
    latest_seen = _format_timestamp(runtime["latest_timestamp"])
    latest_close = (
        f"{latest_decision['close']:.2f}" if isinstance(latest_decision, dict) else "--"
    )
    latest_state = latest_decision["state_label"] if isinstance(latest_decision, dict) else "--"
    latest_volatility = (
        str(latest_decision["volatility_level"]).upper()
        if isinstance(latest_decision, dict)
        else "--"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="refresh" content="{max(refresh_seconds, 5)}" />
  <title>{title_text}</title>
  <style>
    :root {{
      --bg: #0e1417;
      --panel: rgba(17, 25, 29, 0.86);
      --panel-strong: rgba(20, 31, 37, 0.96);
      --line: rgba(255, 255, 255, 0.08);
      --text: #edf0ea;
      --muted: #9ca8a1;
      --gold: #d8b36a;
      --gold-soft: #8d6a30;
      --good: #57c28d;
      --warn: #f0b15d;
      --bad: #ef7d6d;
      --shadow: 0 22px 60px rgba(0, 0, 0, 0.35);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      background:
        radial-gradient(circle at top right, rgba(216, 179, 106, 0.18), transparent 30%),
        radial-gradient(circle at bottom left, rgba(87, 194, 141, 0.14), transparent 28%),
        linear-gradient(160deg, #0b0f12 0%, #10181c 48%, #121b20 100%);
      min-height: 100vh;
    }}
    .shell {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero {{
      display: grid;
      gap: 18px;
      grid-template-columns: 1.4fr 1fr;
      margin-bottom: 20px;
    }}
    .hero-main, .hero-side, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }}
    .hero-main {{
      padding: 28px 28px 22px;
      position: relative;
      overflow: hidden;
    }}
    .hero-main::after {{
      content: "";
      position: absolute;
      inset: auto -10% -45% 35%;
      height: 240px;
      background: radial-gradient(circle, rgba(216, 179, 106, 0.22), transparent 55%);
      pointer-events: none;
    }}
    .eyebrow {{
      color: var(--gold);
      letter-spacing: 0.18em;
      font-size: 11px;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(34px, 5vw, 54px);
      line-height: 0.96;
      letter-spacing: -0.03em;
      max-width: 10ch;
    }}
    .hero-copy {{
      margin: 14px 0 0;
      max-width: 62ch;
      color: var(--muted);
      line-height: 1.55;
    }}
    .runtime-pill {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-top: 22px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
      font-size: 13px;
    }}
    .runtime-pill::before {{
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--warn);
      box-shadow: 0 0 18px currentColor;
    }}
    .runtime-pill.healthy::before {{ color: var(--good); background: var(--good); }}
    .runtime-pill.stale::before {{ color: var(--warn); background: var(--warn); }}
    .runtime-pill.inactive::before,
    .runtime-pill.missing::before {{ color: var(--bad); background: var(--bad); }}
    .hero-side {{
      padding: 22px;
      display: grid;
      gap: 14px;
      grid-template-columns: 1fr 1fr;
      align-content: start;
    }}
    .metric {{
      padding: 16px;
      background: var(--panel-strong);
      border-radius: 18px;
      border: 1px solid var(--line);
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .metric-value {{
      margin-top: 8px;
      font-size: 28px;
      font-weight: 600;
      letter-spacing: -0.03em;
    }}
    .metric-meta {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(12, minmax(0, 1fr));
    }}
    .panel {{
      padding: 22px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .panel h2 {{
      margin: 0 0 16px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: 24px;
      letter-spacing: -0.02em;
    }}
    .mix-list {{
      display: grid;
      gap: 12px;
    }}
    .mix-item {{
      display: grid;
      gap: 8px;
    }}
    .mix-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      font-size: 14px;
    }}
    .mix-name {{ color: var(--text); }}
    .mix-count {{ color: var(--muted); }}
    .mix-bar {{
      overflow: hidden;
      height: 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
    }}
    .mix-bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--gold-soft), var(--gold));
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 11px 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 600;
    }}
    td {{
      color: var(--text);
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }}
    .pill.info {{ color: #d8e5ef; background: rgba(132, 170, 205, 0.12); }}
    .pill.warning {{ color: #f5d7a2; background: rgba(240, 177, 93, 0.13); }}
    .pill.critical {{ color: #ffd6d1; background: rgba(239, 125, 109, 0.14); }}
    .pill.allowed {{ color: #ccf7df; background: rgba(87, 194, 141, 0.14); }}
    .pill.blocked {{ color: #ffd8d3; background: rgba(239, 125, 109, 0.14); }}
    .muted {{ color: var(--muted); }}
    .mono {{
      font-family: "SFMono-Regular", "Menlo", "Consolas", monospace;
      font-size: 12px;
    }}
    .stack {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .tag {{
      padding: 5px 8px;
      border-radius: 999px;
      font-size: 11px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--muted);
    }}
    .empty {{
      color: var(--muted);
      font-size: 14px;
      padding: 8px 0 4px;
    }}
    @media (max-width: 1040px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}
      .hero-side {{
        grid-template-columns: 1fr 1fr;
      }}
      .span-4, .span-6, .span-8 {{
        grid-column: span 12;
      }}
    }}
    @media (max-width: 720px) {{
      .shell {{ padding: 16px; }}
      .hero-main, .hero-side, .panel {{ border-radius: 20px; }}
      .hero-side {{ grid-template-columns: 1fr; }}
      table, thead, tbody, th, td, tr {{ display: block; }}
      thead {{ display: none; }}
      tr {{
        padding: 10px 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
      }}
      td {{
        border-bottom: 0;
        padding: 6px 0;
      }}
      td::before {{
        content: attr(data-label);
        display: block;
        color: var(--muted);
        font-size: 10px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 4px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-main">
        <div class="eyebrow">XAUUSD AI Monitoring</div>
        <h1>{title_text}</h1>
        <p class="hero-copy">
          只读监控面板，聚合最近决策、波动预警、执行尝试与运行新鲜度。
          这个页面不改交易链路，适合先挂在 VPS 上做低风险观察。
        </p>
        <div class="runtime-pill {runtime_class}">
          Runtime {runtime_status} · last seen {html.escape(latest_seen)}
        </div>
      </div>
      <div class="hero-side">
        {_metric_card("最新价格", latest_close, f"state {latest_state}")}
        {_metric_card("波动等级", latest_volatility, f"刷新 {html.escape(generated_at)}")}
        {_metric_card("风险拦截率", _percent(overview["risk_block_rate"]), f"{overview['risk_blocked']} / {overview['decision_window_size']}")}
        {_metric_card("执行尝试", str(overview["execution_window_size"]), f"accepted {overview['accepted_executions']}")}
      </div>
    </section>

    <section class="grid">
      <div class="panel span-4">
        <h2>State Mix</h2>
        {_render_mix(mix["state_labels"])}
      </div>
      <div class="panel span-4">
        <h2>Volatility Mix</h2>
        {_render_mix(mix["volatility_levels"])}
      </div>
      <div class="panel span-4">
        <h2>Session Mix</h2>
        {_render_mix(mix["sessions"])}
      </div>

      <div class="panel span-12">
        <h2>Recent Volatility Alerts</h2>
        {_render_alert_table(recent_alerts)}
      </div>

      <div class="panel span-8">
        <h2>Recent Decisions</h2>
        {_render_decision_table(recent_decisions[:18])}
      </div>
      <div class="panel span-4">
        <h2>Strategy Pressure</h2>
        {_render_mix(mix["signal_strategies"])}
      </div>

      <div class="panel span-12">
        <h2>Recent Execution Attempts</h2>
        {_render_execution_table(recent_executions[:14])}
      </div>

      <div class="panel span-12">
        <h2>Runtime Meta</h2>
        <table>
          <tbody>
            <tr><td data-label="Field">Generated At</td><td data-label="Value" class="mono">{html.escape(generated_at)}</td></tr>
            <tr><td data-label="Field">Database</td><td data-label="Value" class="mono">{html.escape(snapshot["database"]["path"])}</td></tr>
            <tr><td data-label="Field">Latest Timestamp</td><td data-label="Value" class="mono">{html.escape(latest_seen)}</td></tr>
            <tr><td data-label="Field">Staleness</td><td data-label="Value">{html.escape(_staleness_text(runtime["staleness_seconds"]))}</td></tr>
            <tr><td data-label="Field">Refresh</td><td data-label="Value">{max(refresh_seconds, 5)}s auto-refresh</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</body>
</html>
"""


def _metric_card(label: str, value: str, meta: str) -> str:
    return f"""
    <div class="metric">
      <div class="metric-label">{html.escape(label)}</div>
      <div class="metric-value">{html.escape(value)}</div>
      <div class="metric-meta">{html.escape(meta)}</div>
    </div>
    """


def _render_mix(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">暂无可展示数据</div>'

    items = []
    for row in rows[:8]:
        share_pct = max(min(float(row["share"]) * 100.0, 100.0), 0.0)
        items.append(
            f"""
            <div class="mix-item">
              <div class="mix-row">
                <span class="mix-name">{html.escape(str(row["name"]))}</span>
                <span class="mix-count">{int(row["count"])} · {_percent(row["share"])}</span>
              </div>
              <div class="mix-bar"><div class="mix-bar-fill" style="width: {share_pct:.2f}%"></div></div>
            </div>
            """
        )
    return '<div class="mix-list">' + "".join(items) + "</div>"


def _render_alert_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">最近窗口内还没有 warning / critical 级别的波动预警。</div>'

    body = []
    for row in rows:
        reasons = "".join(
            f'<span class="tag">{html.escape(reason)}</span>'
            for reason in row["volatility_reasons"][:5]
        )
        body.append(
            f"""
            <tr>
              <td data-label="Time" class="mono">{html.escape(_format_timestamp(row["timestamp"]))}</td>
              <td data-label="Session">{html.escape(str(row["session_tag"]))}</td>
              <td data-label="Level"><span class="pill {html.escape(str(row["volatility_level"]))}">{html.escape(str(row["volatility_level"]))}</span></td>
              <td data-label="Score">{_float_text(row["volatility_score"])}</td>
              <td data-label="Action">{html.escape(str(row["suggested_action"]))}</td>
              <td data-label="Reasons"><div class="stack">{reasons or '<span class="muted">none</span>'}</div></td>
            </tr>
            """
        )
    return (
        "<table><thead><tr>"
        "<th>Time</th><th>Session</th><th>Level</th><th>Score</th><th>Action</th><th>Reasons</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def _render_decision_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">还没有决策数据。</div>'

    body = []
    for row in rows:
        reasons = "".join(
            f'<span class="tag">{html.escape(reason)}</span>'
            for reason in row["risk_reason"][:3]
        )
        signal = row["signal_strategy"] or "none"
        signal_side = row["signal_side"] or "--"
        body.append(
            f"""
            <tr>
              <td data-label="Time" class="mono">{html.escape(_format_timestamp(row["timestamp"]))}</td>
              <td data-label="State">{html.escape(str(row["state_label"]))}</td>
              <td data-label="Volatility"><span class="pill {html.escape(str(row["volatility_level"]))}">{html.escape(str(row["volatility_level"]))}</span></td>
              <td data-label="Signal">{html.escape(signal)} / {html.escape(signal_side)}</td>
              <td data-label="Risk"><span class="pill {'allowed' if row['risk_allowed'] else 'blocked'}">{'allowed' if row['risk_allowed'] else 'blocked'}</span></td>
              <td data-label="Position">{row["position_size"]:.2f}</td>
              <td data-label="Price">{row["close"]:.2f}</td>
              <td data-label="Notes"><div class="stack">{reasons or '<span class="muted">none</span>'}</div></td>
            </tr>
            """
        )
    return (
        "<table><thead><tr>"
        "<th>Time</th><th>State</th><th>Volatility</th><th>Signal</th><th>Risk</th><th>Pos</th><th>Close</th><th>Notes</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def _render_execution_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">最近窗口内没有执行尝试。</div>'

    body = []
    for row in rows:
        error_text = row["error_message"] or "--"
        status_label = "accepted" if row["accepted"] else "blocked"
        body.append(
            f"""
            <tr>
              <td data-label="Time" class="mono">{html.escape(_format_timestamp(row["timestamp"]))}</td>
              <td data-label="Platform">{html.escape(str(row["platform"]))}</td>
              <td data-label="Strategy">{html.escape(str(row["strategy_name"] or "--"))}</td>
              <td data-label="Status"><span class="pill {'allowed' if row['accepted'] else 'blocked'}">{status_label}</span></td>
              <td data-label="Order">{html.escape(str(row["order_id"] or "--"))}</td>
              <td data-label="Side">{html.escape(str(row["order_side"] or "--"))}</td>
              <td data-label="Volume">{_float_text(row["order_volume"])}</td>
              <td data-label="Error">{html.escape(str(error_text))}</td>
            </tr>
            """
        )
    return (
        "<table><thead><tr>"
        "<th>Time</th><th>Platform</th><th>Strategy</th><th>Status</th><th>Order</th><th>Side</th><th>Volume</th><th>Error</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def _status_class(value: str) -> str:
    if value in {"healthy", "stale", "inactive", "missing"}:
        return value
    return "stale"


def _format_timestamp(value: Any) -> str:
    if not value:
        return "--"
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "--"


def _float_text(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "--"


def _staleness_text(value: Any) -> str:
    if value is None:
        return "--"
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "--"
    if seconds < 60:
        return f"{seconds}s"
    minutes, remain = divmod(seconds, 60)
    return f"{minutes}m {remain}s"


def serialize_monitoring_snapshot(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, ensure_ascii=False)
