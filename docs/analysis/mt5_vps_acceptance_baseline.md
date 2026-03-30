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

## 第三轮：同一份 40,000 根 M1 bars 本地复验

复验背景：

- 复用了 VPS 导出的同一份 `xauusd_m1_history_40000.csv`
- 样本范围约为 `2026-02-16 20:52:00+00:00` 到 `2026-03-27 23:54:00+00:00`
- 本轮代码新增了 `pullback.required_state_reasons`
- 研究实验中启用了更严格的 `pullback` 过滤
- 在这个实验里，`pullback` 不仅看状态标签，还要求状态原因码里必须包含：
  - `MTF_ALIGNMENT_OK`
  - `PULLBACK_DEPTH_OK`
  - `STRUCTURE_INTACT`
  - `VOLATILITY_NOT_DEAD`

目的：

- 不去重写策略框架
- 只把 `pullback` 的低质量候选单进一步挡掉
- 验证“保守加过滤”是否能提升真实历史样本表现

复验结果：

- `ready = false`
- `passed_checks = 5`
- `failed_checks = 5`
- `checked_at = 2026-03-29T18:29:33.584596+00:00`

失败项：

- `out_of_sample_net_pnl`
  `-1.26 < 0`
- `out_of_sample_profit_factor`
  `0.0 < 1.0`
- `walk_forward_positive_window_rate`
  `0.5143 < 0.55`
- `close_month_profit_concentration`
  `1.0 > 0.65`
- `session_profit_concentration`
  `1.0 > 0.75`

相比第二轮的改进：

- `total_net_pnl`
  `-0.31 -> 1.70`
- `total_profit_factor`
  `0.8759 -> 2.3569`
- `win_rate`
  `0.3333 -> 0.5000`
- `walk_forward_positive_window_rate`
  `0.3429 -> 0.5143`

说明：

- 这轮保守过滤是有效的
- 说明当前 `pullback` 确实存在一部分“状态勉强过线但质量不够”的候选单
- 但它还不足以把样本外和集中度问题彻底解决

第三轮细节：

整体回测：

- `closed_trades = 6`
- `win_rate = 0.5`
- `net_pnl = 1.7`
- `profit_factor = 2.3569`
- `max_drawdown_pct = 0.0001`

样本外：

- `closed_trades = 3`
- `win_rate = 0.0`
- `net_pnl = -1.26`
- `profit_factor = 0.0`

walk-forward：

- `total_windows = 35`
- `positive_windows = 18`
- `positive_window_rate = 0.5143`
- `average_profit_factor = 1.2504`

时段拆分：

- `us`
  `net_pnl = 2.188`
  `win_rate = 1.0`
- `overlap`
  `net_pnl = -0.4196`
  `win_rate = 0.0`
- `eu`
  `net_pnl = -0.0639`
  `win_rate = 0.3333`

方向拆分：

- 当前放行成交全部为 `sell`
- 说明问题已经不只是“哪一个策略在亏”
- 还要继续看“哪一类入场结构在亏”

### 第三轮附加实验：只改时段，不改策略本体

为了确认问题是不是仅由时段造成，又做了三组对比：

1. 默认 `eu + overlap + us`
2. `eu + us`
3. `us only`

结论：

- 去掉 `overlap` 之后，总收益变化不大，但 `walk_forward_positive_window_rate` 反而从 `0.5143` 降到 `0.4571`
- 只做 `us` 之后，样本外虽然从 `-1.26` 改善到 `-0.36`，但仍然没有转正
- 并且 `session_profit_concentration` 仍然会固定为 `1.0`

这说明当前问题不是只靠时段开关就能解决：

- 不能只做“禁 overlap”
- 也不能直接切成“只做 us”就当成研究完成
- 下一轮还是要继续收紧 `pullback` 的具体入场质量

## 第四轮：同一版严格过滤在 80,000 根 M1 bars 上的长样本复验

复验背景：

- 使用本地拉取的 `xauusd_m1_history_80000.csv`
- 样本范围约为 `2026-01-06 16:24:00+00:00` 到 `2026-03-27 23:54:00+00:00`
- 仍然使用第三轮同一套严格 `pullback` 原因码过滤实验

复验结果：

- `ready = false`
- 失败项只剩 3 个：
  - `total_net_pnl`
  - `total_profit_factor`
  - `walk_forward_positive_window_rate`

关键指标：

- `total_net_pnl = -1.3`
- `total_profit_factor = 0.3742`
- `closed_trades = 6`
- `win_rate = 0.1667`
- `out_of_sample_net_pnl = 0.55`
- `out_of_sample_profit_factor = 1.2156`
- `walk_forward_positive_window_rate = 0.36`

说明：

- 严格过滤在 `40k` 上改善了短样本结果
- 但放到 `80k` 长样本后，整体收益和稳定性并没有成立
- 反而是：
  - 样本外转正了
  - 但整体净利润转负了
  - walk-forward 仍明显不足

对比 VPS 上旧代码的 `80k` 基线：

- 旧代码：
  - `total_net_pnl = 0.87`
  - `total_profit_factor = 1.2785`
  - `out_of_sample_net_pnl = -0.18`
  - `walk_forward_positive_window_rate = 0.3733`
- 严格过滤实验：
  - `total_net_pnl = -1.3`
  - `total_profit_factor = 0.3742`
  - `out_of_sample_net_pnl = 0.55`
  - `walk_forward_positive_window_rate = 0.36`

这代表：

- 严格过滤并不是“全面变好”
- 它只是把指标从“整体略好、样本外偏弱”改成了“样本外变好、整体变弱”
- 所以当前不能把它直接当成生产默认配置

## 当前综合判断

- 本轮代码改动值得保留为“可配置研究能力”
- 但当前还不适合直接改成默认正式配置
- `40k` 结果说明它对短样本有改善作用
- `80k` 结果说明它在更长样本上还没有稳定成立

当前真正需要继续解决的问题是：

- 长样本下 `total_net_pnl` 仍为负
- 长样本下 `total_profit_factor` 明显不足
- `walk_forward_positive_window_rate` 在 `40k / 80k` 都没有稳定过线
- 当前 `pullback` 的 `sell` 入场质量仍不够稳定
- 只靠 session 开关还不足以把问题修好

所以下一轮研究优先级应转成：

- 继续筛掉低质量 `sell pullback`
- 补充更细的单笔成交审计，定位具体亏损入场结构
- 不要只靠 session 开关做表面修复
- 在进入生产前，固定使用 `80k bars` 作为默认长样本复验基线

## 第五轮：单笔成交审计发现

为了不再只看总收益，这一轮已把单笔成交审计接入回测输出。

当前回测结果中，已经可以直接查看：

- `trade_audit.records_count`
- `trade_audit.latest_closed`
- `trade_audit.worst_losses`
- `trade_audit.best_wins`

### 40k 整体回测的亏损结构

当前最亏的几笔单有非常清晰的共性：

- 4 笔亏损样本全部是 `pullback sell`
- 其中 3 笔发生在 `eu`
- 亏损样本比盈利样本更明显地处在：
  - 更高的 `volatility_ratio`
  - 更大的负向 `price_distance_to_ema20`
  - 更大的负向 `vwap_deviation`
  - 更高的 `atr_m1_14 / atr_m5_14`

这说明：

- 当前 `sell pullback` 在“已经偏离均值很远、波动仍偏大”的位置还在继续追空
- 这类入场在 `eu` 时段尤其需要继续收紧

### 40k 样本外亏损结构

当前样本外失败并不是来自 `sell`，而是：

- 3 笔亏损样本全部是 `eu` 时段的 `pullback buy`
- 这些亏损单有共同特征：
  - `price_distance_to_ema20 > 0`
  - `vwap_deviation > 0`
  - `bollinger_position` 偏高
  - 多数发生在 `range_position` 偏上半区

这说明：

- 当前样本外更像是在 `eu` 时段去追“位置已经偏高的回踩做多”
- 换句话说，问题不是单纯“只要是 buy 就不行”
- 而是“高位 `buy pullback` 的入场质量不够”

### 80k 样本外亏损结构

当前 `80k` 样本外虽然整体转正，但最亏样本仍显示出两个风险点：

- 亏损主要集中在 `us / overlap`
- 其中大部分仍然是 `sell pullback`
- 这些亏损样本普遍带有：
  - 明显负向 `price_distance_to_ema20`
  - 明显负向 `vwap_deviation`
  - 较高 `atr_m1_14 / atr_m5_14`

说明：

- 长样本里最需要继续收紧的，仍然是“已经很深的空头偏离后继续追空”
- 但短样本 `40k` 的样本外又暴露出“高位 `buy pullback` 追多”问题
- 所以下一轮不能只针对一个方向简单开关
- 更合适的是增加“位置过偏 + 波动过高”的统一过滤规则

## 已完成的下一步代码动作

基于上面的判断，仓库当前已补上统一 `routing` 准入层，并完成本地回归测试：

- 新增按策略开关过滤候选信号
- 新增按时段过滤候选信号
- 候选信号即使被挡下，也会保留审计上下文
- 回放 / 回测 / live 共用同一套准入口径
- 新增环境变量覆盖：
  - `XAUUSD_AI_ENABLED_STRATEGIES`
  - `XAUUSD_AI_DISABLED_STRATEGIES`
  - `XAUUSD_AI_ALLOWED_SESSIONS`
  - `XAUUSD_AI_BLOCKED_SESSIONS`

当前 `configs/mvp.yaml` 默认设置为：

- `disabled_strategies = ["breakout"]`
- `allowed_sessions = ["eu", "overlap", "us"]`

说明：

- 这里先不直接切成“只做 us”
- 因为在当前验收规则下，这会让 `session_profit_concentration` 更容易固定为 `1.0`
- 所以下一轮 VPS 复验应先验证“禁 asia + 关 breakout”是否已经足够改善基线

本地状态：

- 全量单元测试已通过
- 下一步待在 VPS 上重新导出 / 复用历史数据并复跑 `acceptance`

而不是：

- “整套系统完全不可用”
