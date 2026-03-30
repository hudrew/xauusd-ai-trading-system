# Pullback Sell V3 长样本 Probe 复验结论

日期：

- `2026-03-31`

适用对象：

- `sell-only + us-only pullback v3`
- 分支门禁配置：
  - `configs/mvp_pullback_sell_research_v3_branch_gate.yaml`

---

## 1. 这轮复验回答什么问题

这轮不是为了回答“系统能不能跑”。

这个问题已经解决了。

这轮真正要回答的是：

1. 当样本从 `150k` 拉到 `300k`、再拉到 `500k` 时，这条候选线会不会被打穿
2. 如果没有被打穿，当前真正的阻塞点到底是什么

---

## 2. 样本范围

本次已经完成的长样本 probe：

- `150000` 根 `M1`
- `300000` 根 `M1`
- `500000` 根 `M1`

其中 `500000` 根样本由 VPS 上 MT5 实测导出：

- `bars_available = 500000`
- `oldest_timestamp = 2024-10-28T07:03:00+00:00`
- `newest_timestamp = 2026-03-30T23:58:00+00:00`

本地研究输入文件：

- `tmp/xauusd_m1_history_150000_chunked_vps_full.csv`
- `tmp/xauusd_m1_history_300000_chunked_vps_full.csv`
- `tmp/xauusd_m1_history_500000.csv`

对应导出 JSON：

- `tmp/research_pullback_sell_v3_probe_acceptance_150000_local.json`
- `tmp/research_pullback_sell_v3_probe_acceptance_300000_local.json`
- `tmp/research_pullback_sell_v3_probe_acceptance_500000_local.json`

---

## 3. 结果对比

| 样本 | ready | closed_trades | total_net_pnl | profit_factor | out_of_sample_net_pnl | out_of_sample_profit_factor | walk_forward_positive_window_rate | session_profit_concentration |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `150k` | `true` | `7` | `1.39` | `2.4762` | `1.09` | `null` | `0.9931` | `1.0` |
| `300k` | `true` | `7` | `1.39` | `2.4762` | `1.00` | `1.7565` | `0.9966` | `1.0` |
| `500k` | `true` | `7` | `1.42` | `2.5152` | `1.42` | `2.5152` | `0.9980` | `1.0` |

---

## 4. 能确认的事

### 4.1 候选线没有被更长样本直接打穿

这是这轮最重要的正面结论。

当前至少可以确认：

- 从 `150k` 到 `500k`
- 候选线没有出现明显崩塌
- `ready` 一直保持 `true`
- `net_pnl` 和 `profit_factor` 没有反向恶化

所以当前不能再把它理解成：

- “只是在短样本里偶然过线”

### 4.2 当前阻塞点不是门禁没过

当前阻塞点已经不是：

- 收益转负
- walk-forward 不够
- 样本外不过关

而是：

- 成交数量太少
- 收益来源太窄
- 仍然全部集中在 `us`

---

## 5. 当前真正的问题

## 5.1 成交数量没有随着样本显著增加

最关键的异常是：

- `150k = 7` 笔
- `300k = 7` 笔
- `500k = 7` 笔

这说明：

- 更长样本没有把结果打坏
- 但也没有把样本做厚

换句话说，当前候选线更像：

- “低频、强收缩、可过门禁”

还不是：

- “已经形成稳定、可放大的交易覆盖”

## 5.2 收益仍全部来自 `us`

当前 `500k` 结果里：

- `performance_by_session` 仍只有 `us`
- `session_profit_concentration = 1.0`

这说明：

- 这条候选线的盈利逻辑还没有扩展到更多时段
- 当前本质上仍然是一个单时段候选

## 5.3 低频不是系统故障，而是当前过滤本来就很紧

`500k` 样本里：

- `signals_generated = 7292`
- `trades_allowed = 10`
- `blocked_trades = 7282`
- `blocked_signal_rate = 0.9986`

同时：

- `signals_by_strategy.breakout = 7065`
- `pullback = 10`
- `blocked_reasons.STRATEGY_DISABLED = 7282`
- `blocked_reasons.SESSION_NOT_ALLOWED = 5867`

这说明当前低频不是因为系统坏了，而是因为：

- 大部分候选信号本来就是 `breakout`
- 而 `breakout` 被主动关闭
- 非 `us` 时段又被主动拦掉
- 在剩下的 `us + sell-only + pullback` 交集里，本来就只剩极少数信号

这是一种“研究主动收缩”结果，不是运行异常。

---

## 6. 500k 里新增的有用信息

相比 `150k / 300k`，`500k` 至少多给了一个正面信息：

- 收益月份不再只落在 `2026-01 ~ 2026-03`
- 已经出现 `2025-10` 的正收益样本
- `close_month_profit_concentration` 仍在可接受范围内：
  - `0.5515`

这说明：

- 当前收益不再完全集中在最近两三个月
- 但这个改善仍然建立在非常少的成交样本上

所以它是：

- 正面信号

但还不是：

- 足够强的生产依据

---

## 7. 下一步最该做什么

当前最合理的研究重心不再是“继续盲目加 bars”。

因为现在已经到 `500k`，核心现象仍然没变。

下一步更应该做的是：

1. 诊断为什么当前 `pullback sell v3` 在 `500k` 下仍只有 `7` 笔成交
2. 拆开看这 `7` 笔之外，被挡掉的究竟是哪一层：
   - `breakout` 被关
   - 非 `us` 时段被挡
   - `pullback` 自身条件过严
3. 判断项目目标到底是：
   - 保留低频高筛选候选
   - 还是提高覆盖率，让成交更有统计意义

如果目标是后者，下一轮优先级建议是：

1. 不要急着恢复 `breakout`
2. 也不要急着放开 `asia`
3. 先做 `pullback` 信号覆盖率审计：
   - `pullback_continuation` 总状态数
   - `pullback` 候选信号数
   - 被哪条过滤规则最终挡掉
4. 再决定是否适度放宽：
   - `min_entry_hour`
   - `min_directional_distance_to_ema20_atr`
   - `min_pullback_depth`
   - `min_atr_m1 / min_atr_m5`

---

## 8. 当前一句话判断

`pullback sell v3` 在 `500k` 长样本下仍然站住了，
但它现在暴露出来的主问题已经不是“能不能赚钱”，
而是“交易频次太低，统计厚度仍然不够”。
