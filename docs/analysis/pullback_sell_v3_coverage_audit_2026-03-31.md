# Pullback Sell V3 覆盖率审计结论

日期：

- `2026-03-31`

适用对象：

- `sell-only + us-only pullback v3`
- 分支门禁配置：
  - `configs/mvp_pullback_sell_research_v3_branch_gate.yaml`

---

## 1. 这轮审计回答什么问题

这轮不再回答“更长样本会不会把候选线打穿”。

这个问题在 `150k / 300k / 500k` probe 里已经回答过：

- 没有被直接打穿
- `ready` 仍持续为 `true`

这轮真正要回答的是：

1. 为什么样本从 `150k` 扩到 `500k` 后，实际成交仍然只有 `7` 笔
2. 当前覆盖率瓶颈到底在：
   - `routing / risk`
   - 还是 `pullback` 信号自身生成过少

---

## 2. 审计入口

当前仓库已经补了可复用入口：

```bash
./scripts/research_pullback_sell_v3_coverage_audit.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\research_pullback_sell_v3_coverage_audit.ps1
```

默认会直接比较：

- `tmp/research_pullback_sell_v3_probe_acceptance_150000_local.json`
- `tmp/research_pullback_sell_v3_probe_acceptance_300000_local.json`
- `tmp/research_pullback_sell_v3_probe_acceptance_500000_local.json`

默认输出：

- `tmp/research_pullback_sell_v3_coverage_audit_latest.json`

底层通用命令：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-audit \
  tmp/research_pullback_sell_v3_probe_acceptance_150000_local.json \
  tmp/research_pullback_sell_v3_probe_acceptance_300000_local.json \
  tmp/research_pullback_sell_v3_probe_acceptance_500000_local.json
```

---

## 3. 审计结果

| 样本 | ready | closed_trades | pullback_state_rows | pullback_signal_count | trades_allowed | signals_generated | pullback_signal_per_state_rate | dominant_blocked_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `150k` | `true` | `7` | `63820` | `10` | `10` | `2345` | `0.00015669` | `STRATEGY_DISABLED` |
| `300k` | `true` | `7` | `125833` | `10` | `10` | `4556` | `0.00007947` | `STRATEGY_DISABLED` |
| `500k` | `true` | `7` | `207517` | `10` | `10` | `7292` | `0.00004819` | `STRATEGY_DISABLED` |

当前聚合结果：

- `aggregate_signals_by_strategy.breakout = 13804`
- `aggregate_signals_by_strategy.mean_reversion = 359`
- `aggregate_signals_by_strategy.pullback = 30`
- `aggregate_blocked_reasons.STRATEGY_DISABLED = 14163`
- `aggregate_blocked_reasons.SESSION_NOT_ALLOWED = 11255`
- `coverage_bottleneck = pullback_signal_generation`

---

## 4. 能确认的结论

### 4.1 当前不是执行链或风控链把 pullback 大量挡掉

三组样本里都出现了同一个现象：

- `pullback_signal_count = 10`
- `trades_allowed = 10`

这意味着：

- 每一个真正生成出来的 `pullback` 信号都通过了当前 `routing / risk`
- 当前覆盖率问题不在 MT5 执行链
- 也不在 live runtime 或下单链路

所以现在不能再把低频理解成：

- “系统没跑起来”
- “风控把 pullback 都挡掉了”

### 4.2 当前真正的瓶颈是 pullback 触发密度过低

随着样本扩大：

- `pullback_state_rows` 从 `63820` 增到 `207517`
- 但 `pullback_signal_count` 始终卡在 `10`
- `pullback_signal_per_state_rate` 反而持续下降

这说明：

- 市场里出现了大量 `pullback_continuation` 状态
- 但真正满足当前 `pullback v3` 入场条件的案例非常少

也就是说，现在最该怀疑的是：

- `pullback` 触发条件过严

而不是：

- `breakout` 关掉导致系统坏掉
- `asia` 没放开导致执行失败

### 4.3 当前仍然是单时段收益结构

三组样本里：

- `session_profit_concentration = 1.0`
- `top_label = us`

说明当前这条候选线仍然没有摆脱：

- 收益全部集中在 `us`

这依然是它离正式生产很远的地方之一。

### 4.4 breakout 仍然是主导信号池，但不是当前优先修复项

聚合后：

- `breakout = 13804`
- `pullback = 30`

说明当前市场里最常见的仍然是 `breakout` 型候选。

但当前最合理的动作不是立刻恢复 `breakout`，
而是先把 `pullback` 这条当前候选线的触发密度做厚。

否则会把研究问题重新混回：

- 策略切换问题
- 会话开放问题
- 信号来源混杂问题

---

## 5. 下一步建议

当前下一轮优化优先级建议固定为：

1. 先调 `pullback.min_entry_hour`
2. 再看 `pullback.min_directional_distance_to_ema20_atr`
3. 再看 `pullback.min_pullback_depth`
4. 再看 `pullback.min_atr_m1`
5. 再看 `pullback.min_atr_m5`

当前明确不建议作为第一步的动作：

1. 不要先恢复 `breakout`
2. 不要先放开 `asia`
3. 不要先修改验收门槛

---

## 6. 一句话判断

`pullback sell v3` 当前不是“执行链有问题”，
而是“策略触发太稀，导致成交覆盖率做不厚”。
