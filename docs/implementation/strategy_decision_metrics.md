# 策略决策指标说明

## 1. 文档目的

这份文档专门解释一件事：

- 代码里的这些指标是拿来干嘛的
- 它们分别服务于哪些决策
- 什么时候应该看实时指标
- 什么时候应该看回测 / 验收指标

当前最常见的 3 个研究决策是：

1. 是否继续关闭 `breakout`
2. 是否继续限制 `asia`
3. 是否继续加严 `pullback` 触发

这 3 个问题都不能只看一个数字，而要看一组有层次的指标。

---

## 2. 先分清两类指标

### 2.1 运行时指标

运行时指标是系统在每次行情轮询、每根 K 线更新、每次准备生成信号时直接使用的指标。

它们的作用是：

- 判断当前市场状态
- 判断是否允许某个策略出候选信号
- 判断某个候选信号是否应该被过滤
- 判断是否进入高波动预警或 no-trade

常见例子：

- `breakout_distance`
- `ema_spread`
- `ema_slope_20`
- `pullback_depth`
- `atr_m1_14`
- `atr_m5_14`
- `volatility_ratio`
- `price_distance_to_ema20`
- `vwap_deviation`
- `range_position`
- `bollinger_position`
- `session_tag`

这些指标主要出现在：

- 市场状态分类器
- 策略信号生成器
- 风控 / 路由准入层

### 2.2 研究验收指标

研究验收指标不是给实时下单用的，而是给“版本决策”用的。

它们的作用是：

- 判断某个策略是否值得继续保留
- 判断某个时段是否应继续放行
- 判断当前过滤是否真的提升了样本外表现
- 判断当前配置能不能推进到纸盘 / 生产前门禁

常见例子：

- `net_pnl`
- `profit_factor`
- `win_rate`
- `max_drawdown_pct`
- `out_of_sample_net_pnl`
- `out_of_sample_profit_factor`
- `walk_forward_positive_window_rate`
- `session_profit_concentration`
- `close_month_profit_concentration`

这些指标主要来自：

- `backtest`
- `sample-split`
- `walk-forward`
- `acceptance`

---

## 3. 指标和决策的对应关系

### 3.1 是否继续关闭 breakout

这个问题本质上是在回答：

- `breakout` 这个策略本身有没有独立正贡献
- 它打开之后有没有拖累整体验收

优先看的研究指标：

- `trade_segmentation.performance_by_strategy.breakout.net_pnl`
- `trade_segmentation.performance_by_strategy.breakout.profit_factor`
- `trade_segmentation.performance_by_strategy.breakout.win_rate`
- `total_net_pnl`
- `out_of_sample_net_pnl`
- `walk_forward_positive_window_rate`

当前项目里的已知依据：

- `breakout net_pnl = -0.4162`
- `pullback net_pnl = 0.106`
- `pullback profit_factor = 1.0509`

这说明在当前基线样本里，`breakout` 相对更弱，所以主线配置先把它关掉。

如果后面要重新放开 `breakout`，至少要看到：

- `breakout` 自身不再持续负收益
- 打开后不会把 `out_of_sample_net_pnl` 拉回负数
- 打开后不会明显压低 `walk_forward_positive_window_rate`

对应的运行时判定因子主要是：

- `breakout_distance`
- `ema_spread`
- `ema_slope_20`
- `volatility_ratio`
- `false_break_count`
- `breakout_failed`
- `MTF_ALIGNMENT_OK`

这些因子决定一段行情是否会被归类为 `trend_breakout`。

---

### 3.2 是否继续限制 asia

这个问题本质上是在回答：

- `asia` 时段本身是不是长期拖累表现
- 去掉它之后，整体是不是更稳

优先看的研究指标：

- `trade_segmentation.performance_by_session.asia.net_pnl`
- `trade_segmentation.performance_by_session.asia.profit_factor`
- `trade_segmentation.performance_by_session.asia.win_rate`
- `trade_segmentation.performance_by_session.us.net_pnl`
- `trade_segmentation.performance_by_session.us.profit_factor`
- `session_profit_concentration`

当前项目里的已知依据：

- `asia net_pnl = -1.6712`
- `asia profit_factor = 0.0`
- `us net_pnl = 1.361`
- `us profit_factor = 2.6428`

这说明目前不是“所有时段都差不多”，而是 `asia` 对结果有明显拖累。

但这里还有一个重要约束：

- 当前验收里会检查 `session_profit_concentration`
- 如果直接切成“只做 us”，这个值很容易天然变成 `1.0`
- 所以研究主线先做的是“禁 `asia`”，而不是“一刀切只保留 `us`”

也就是说，`asia` 的时段判断不是只看它亏不亏，还要看：

- 去掉它以后，收益是否更稳
- 是否引入新的时段集中度问题

运行时真正落地到配置里，对应的是：

- `routing.allowed_sessions`
- `routing.blocked_sessions`
- `session_tag`

---

### 3.3 是否继续加严 pullback 触发

这个问题本质上是在回答：

- `pullback` 有没有放进太多“看起来像回踩、但质量其实不够”的单子
- 这些低质量单子是不是主要亏损来源

这里要分两层看。

### 第一层：状态层

先看一段行情有没有资格被认成 `pullback_continuation`。

核心状态因子：

- `MTF_ALIGNMENT_OK`
- `PULLBACK_DEPTH_OK`
- `STRUCTURE_INTACT`
- `REVERSAL_CONFIRMED`
- `VOLATILITY_NOT_DEAD`

这些不是为了直接下单，而是为了回答：

- 现在是不是顺势回踩环境

### 第二层：入场质量层

就算状态是 `pullback_continuation`，也不代表这笔单一定值得做。

当前系统里已经在继续过滤：

- `min_pullback_depth`
- `min_atr_m1`
- `min_atr_m5`
- `min_volatility_ratio`
- `min_directional_distance_to_ema20_atr`
- `max_reference_distance_atr`
- `max_directional_extension_atr`
- `edge_position_threshold`
- `allowed_sides`
- `min_entry_hour`

它们实际对应的市场特征包括：

- `pullback_depth`
- `atr_m1_14`
- `atr_m5_14`
- `volatility_ratio`
- `price_distance_to_ema20`
- `vwap_deviation`
- `range_position`
- `bollinger_position`

这些指标是为了回答：

- 回踩是不是太浅，没到值得做的位置
- 回踩是不是已经过深，结构快坏了
- 当前是不是已经离均值太远，还在高波动追单
- 是不是某个方向或某个时段的回踩质量更差

当前研究里已经看到的典型问题是：

- 一部分 `sell pullback` 会在“已经明显偏离均值、波动仍偏大”的位置继续追空
- 一部分 `buy pullback` 会在“位置已经偏高”的地方继续追多

所以“加严 pullback 触发”并不是为了让系统少交易而已，而是为了更明确地砍掉低质量入场。

---

## 4. 一张表看懂这些指标

| 决策问题 | 先看哪类指标 | 核心指标 | 决策用途 |
| --- | --- | --- | --- |
| 是否继续关闭 `breakout` | 策略表现 + 总体验收 | `performance_by_strategy.breakout.net_pnl`、`performance_by_strategy.breakout.profit_factor`、`out_of_sample_net_pnl`、`walk_forward_positive_window_rate` | 判断 `breakout` 是不是在拖累系统 |
| 是否继续限制 `asia` | 时段表现 + 集中度验收 | `performance_by_session.asia.net_pnl`、`performance_by_session.asia.profit_factor`、`session_profit_concentration` | 判断 `asia` 是否持续拖累，以及是否会造成收益过度集中 |
| 是否继续加严 `pullback` | 单笔成交审计 + 样本外表现 | `trade_audit.worst_losses`、`price_distance_to_ema20`、`vwap_deviation`、`volatility_ratio`、`out_of_sample_net_pnl` | 判断低质量 `pullback` 是否是主要亏损来源 |

---

## 5. 实操时怎么用

每轮研究建议按下面顺序看：

1. 先跑 `acceptance`
2. 先看总体验收有没有过
3. 再看 `performance_by_strategy`
4. 再看 `performance_by_session`
5. 最后看 `trade_audit.worst_losses`

这样做的原因是：

- 先确认是不是整体不过关
- 再定位是策略问题、时段问题，还是入场质量问题
- 避免一上来就凭感觉调参数

对应到当前项目，最常用的判断方式就是：

1. 看 `breakout` 是否在策略拆分里持续负贡献
2. 看 `asia` 是否在时段拆分里持续负贡献
3. 看最亏单子是不是集中在某种 `pullback` 结构

---

## 6. 当前项目的实际结论

截至当前这轮研究，项目里的结论不是：

- 系统完全不能用

而是：

- `pullback` 有一定可用性
- `breakout` 当前相对偏弱，所以先关闭
- `asia` 当前明显拖累，所以先限制
- 下一轮研究重点不是继续乱改大框架
- 而是继续收紧低质量 `pullback` 入场

这也是为什么现在的研究主线更像：

- 先保留完整策略框架
- 再对 `breakout / asia / pullback` 做有证据的收缩

---

## 7. 一句话总结

这些指标不是“为了让报表更好看”。

它们真正的作用是：

- 让系统知道什么时候该交易
- 让研究知道哪些规则该保留、哪些规则该收缩
- 让上线前的决策建立在样本和审计上，而不是建立在感觉上
