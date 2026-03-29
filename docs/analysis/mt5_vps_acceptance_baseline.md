# MT5 VPS 研究验收基线记录

## 背景

本记录用于沉淀 `2026-03-30` 这轮在 Windows MT5 VPS 上完成的真实联调结果，避免后续重复踩坑。

当前已完成的关键链路：

- VPS 已拉取最新仓库代码
- `MetaTrader5` 与 `backtrader` 依赖已安装
- `export-mt5-history` 已在 VPS 上实跑成功
- `acceptance` 已在 VPS 上实跑成功并写入 `reports/research`
- `deploy-gate` 已确认会读取最新研究归档，而不是再报“缺少 acceptance 报告”

## 本轮使用的代码版本

- `dea1857`
  `Add MT5 history export workflow`
- `e28afe9`
  `Normalize CSV timestamps for backtests`

## 运行环境

- 宿主机：Windows VPS
- 项目目录：`C:\work\xauusd-ai-trading-system`
- MT5 终端路径：`C:\Program Files\MetaTrader 5\terminal64.exe`
- 研究归档目录：`C:\work\xauusd-ai-trading-system\reports\research`

## 关键修复

### 1. MT5 历史数据导出

新增：

- `xauusd_ai_system.cli export-mt5-history`
- `scripts/mt5_export_history.ps1`
- `scripts/mt5_export_history.sh`

这一步已验证可以直接从 MT5 导出标准 CSV，供：

- `replay`
- `backtest`
- `sample-split`
- `walk-forward`
- `acceptance`

共用。

### 2. CSV 时区归一化

实跑中发现：

- MT5 导出的 CSV 时间戳包含 `+00:00`
- 回测链里有 offset-aware / offset-naive 比较
- 会导致 `acceptance` 在 walk-forward 阶段报错

已修复为：

- CSV 加载时统一转成“UTC 语义的无时区时间”

## 验收结果

### 第一轮：20,000 根 M1 bars

导出结果：

- `bars_requested = 20000`
- `bars_exported = 20000`

验收结果：

- `ready = false`
- `passed_checks = 7`
- `failed_checks = 3`

失败项：

- `walk_forward_positive_window_rate`
  `0.5333 < 0.55`
- `close_month_profit_concentration`
  `1.0 > 0.65`
- `session_profit_concentration`
  `1.0 > 0.75`

解释：

- 这一轮更像“首份基线”
- 其中月度集中度为 `1.0`，很大概率受样本窗口过短影响
- 不能仅凭这轮就下结论说策略收益一定失效

### 第二轮：40,000 根 M1 bars

导出结果：

- `bars_requested = 40000`
- `bars_exported = 40000`

最新归档：

- `saved_at = 2026-03-29T17-04-04-445493Z`
- `checked_at = 2026-03-29T17:04:04.429704+00:00`

验收结果：

- `ready = false`
- `passed_checks = 4`
- `failed_checks = 6`

失败项：

- `total_net_pnl`
  `-0.31 < 0`
- `total_profit_factor`
  `0.8759 < 1.15`
- `out_of_sample_net_pnl`
  `-1.26 < 0`
- `out_of_sample_profit_factor`
  `0.0 < 1.0`
- `walk_forward_positive_window_rate`
  `0.3429 < 0.55`
- `session_profit_concentration`
  `1.0 > 0.75`

### 第二轮细节

整体回测：

- `closed_trades = 6`
- `win_rate = 0.3333`
- `net_pnl = -0.31`
- `profit_factor = 0.8759`
- `max_drawdown_pct = 0.0002`

样本外：

- `closed_trades = 3`
- `win_rate = 0.0`
- `net_pnl = -1.26`
- `profit_factor = 0.0`

walk-forward：

- `total_windows = 35`
- `positive_windows = 12`
- `positive_window_rate = 0.3429`
- `average_profit_factor = 0.7636`

策略拆分：

- `breakout`
  `net_pnl = -0.4162`
- `pullback`
  `net_pnl = 0.106`
  `profit_factor = 1.0509`

时段拆分：

- `asia`
  `net_pnl = -1.6712`
  `profit_factor = 0.0`
- `us`
  `net_pnl = 1.361`
  `profit_factor = 2.6428`

月度拆分：

- 当前样本的平仓仍全部落在 `2026-02`
- 所以 `close_month_profit_concentration` 在第二轮不再是主要阻塞项
- 但 `session_profit_concentration` 仍然为 `1.0`
  说明当前正收益几乎都集中在 `us` 时段

## deploy-gate 当前状态

在 VPS 上实跑 `mt5_deploy_gate.ps1` 后，当前结果为：

- `acceptance_report_available = true`
- `acceptance_report_freshness = true`
- `acceptance_report_ready = false`

这说明当前系统的真实阻塞点已经从：

- “缺少研究归档”

转为：

- “研究归档存在，但尚未通过验收”

也就是说，链路本身已经打通，当前阻塞点是研究结果，而不是部署流程。

## 当前判断

### 已经确认没问题的部分

- MT5 宿主机接入链
- MT5 历史 bars 导出链
- CSV 到 `acceptance` 的研究链
- 研究归档写入链
- `deploy-gate` 读取研究归档的门禁链

### 当前真正的核心问题

- 策略在更长样本上没有达到当前验收门槛
- 正收益主要集中在 `us` 时段
- `asia` 时段明显拖累表现
- `breakout` 当前表现弱于 `pullback`

## 建议下一步

优先顺序建议：

1. 先不要动 `deploy-gate` 逻辑
2. 先把研究问题当成研究问题来处理，不要靠放宽门槛掩盖
3. 重点检查 `asia` 时段为什么持续亏损
4. 重点检查 `breakout` 的入场过滤是否过松
5. 再决定是否需要：
   - 增加交易时段过滤
   - 调整 `breakout` 阈值
   - 调整 `pullback` 触发条件
   - 重新设定第一版验收门槛

当前更像是：

- `pullback` 有一定可用性
- `breakout` 和非美盘时段需要重点收缩

而不是：

- “整套系统完全不可用”
