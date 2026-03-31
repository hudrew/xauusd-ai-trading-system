# Pullback Sell V3 `entry_hour_18` 本地验证结论

日期：

- `2026-03-31`

适用对象：

- `sell-only + us-only pullback v3`
- 本地参数扫描后的首个独立研究候选：
  - `configs/mvp_pullback_sell_research_v3_branch_gate_entry_hour_18.yaml`

---

## 1. 这轮在回答什么

上一轮覆盖率审计确认：

- 当前主瓶颈不是执行链
- 也不是风控拦截
- 而是 `pullback` 信号密度太低

随后本地第一轮 density probe 直接给出：

- `entry_hour_18`
  是当前最强的一维放松方向

所以这轮要回答的是：

1. 把 `pullback.min_entry_hour` 从 `20` 放松到 `18`
   后，这个候选是不是只在 `150k` 上看起来更好
2. 它在 `300k / 500k` 长样本下还能不能站住

---

## 2. 宿主机状态切换

为了避免再把参数研究和执行宿主机混在一起，
`2026-03-31` 已经把 VPS 上以下计划任务全部停掉并禁用：

- `xauusd-ai-paper-mt5-paper-pullback-sell-v3-loop`
- `xauusd-ai-paper-mt5-paper-pullback-sell-v3-monitor-serve`
- `xauusd-ai-paper-mt5-paper-pullback-sell-v3-monitor-refresh`
- `xauusd-ai-paper-mt5-paper-pullback-sell-v3-daily-check`

当前原则改为：

- 参数扫描固定在本地研究机
- Windows VPS 不再承担研究任务
- 后续如果要恢复纸盘，只恢复执行和值守，不恢复研究扫描

---

## 3. `150k` 第一轮 density probe 结果

当前可复用入口：

```bash
./scripts/research_pullback_sell_v3_density_probe.sh
```

默认输出：

- `tmp/research_pullback_sell_v3_density_probe_latest.json`

当前 `150k` 排名结果：

| 变体 | ready | closed_trades | total_net_pnl | profit_factor | pullback_signal_count | trades_allowed |
| --- | --- | --- | --- | --- | --- | --- |
| `entry_hour_18` | `true` | `16` | `3.30` | `2.5966` | `22` | `22` |
| `atr_m5_10_v2_level` | `true` | `14` | `1.46` | `1.6219` | `17` | `17` |
| `density_relaxed_v1` | `true` | `13` | `0.78` | `1.3036` | `17` | `17` |
| `atr_m5_12` | `true` | `11` | `1.62` | `1.9523` | `14` | `14` |
| `entry_hour_19` | `true` | `8` | `1.05` | `1.8117` | `12` | `12` |
| `base_v3_branch_gate` | `true` | `7` | `1.39` | `2.4762` | `10` | `10` |
| `directional_distance_0_45` | `true` | `7` | `1.39` | `2.4762` | `10` | `10` |

第一轮可以先确认：

- `min_entry_hour` 比 `min_directional_distance_to_ema20_atr` 更敏感
- 单独放松到 `18` 的效果明显好于放松到 `19`
- 只放松方向距离阈值几乎没有带来增量

---

## 4. `300k / 500k` 长样本确认

### 4.1 `300k`

本地输出文件：

- `tmp/research_pullback_sell_v3_entry_hour_18_acceptance_300000_local.json`

关键结果：

- `ready = true`
- `passed_checks = 10/10`
- `closed_trades = 18`
- `total_net_pnl = 2.61`
- `profit_factor = 1.9244`
- `out_of_sample_net_pnl = 2.90`
- `out_of_sample_profit_factor = 2.1896`
- `walk_forward_positive_window_rate = 0.9898`
- `pullback_signal_count = 25`
- `trades_allowed = 25`

### 4.2 `500k`

本地输出文件：

- `tmp/research_pullback_sell_v3_entry_hour_18_acceptance_500000_local.json`

关键结果：

- `ready = true`
- `passed_checks = 10/10`
- `closed_trades = 18`
- `total_net_pnl = 2.69`
- `profit_factor = 1.9511`
- `out_of_sample_net_pnl = 3.32`
- `out_of_sample_profit_factor = 2.6121`
- `walk_forward_positive_window_rate = 0.9939`
- `pullback_signal_count = 25`
- `trades_allowed = 25`

---

## 5. 和当前 base v3 的核心对比

`500k` 下：

| 候选 | ready | closed_trades | total_net_pnl | profit_factor | out_of_sample_net_pnl | out_of_sample_profit_factor | pullback_signal_count | trades_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `base_v3_branch_gate` | `true` | `7` | `1.42` | `2.5152` | `1.42` | `2.5152` | `10` | `10` |
| `entry_hour_18` | `true` | `18` | `2.69` | `1.9511` | `3.32` | `2.6121` | `25` | `25` |

可以明确看到：

- 成交笔数从 `7` 提到 `18`
- `pullback` 信号从 `10` 提到 `25`
- 总净收益从 `1.42` 提到 `2.69`
- 样本外净收益从 `1.42` 提到 `3.32`

同时也要诚实看到：

- Profit Factor 从 `2.5152` 降到 `1.9511`
- 但仍明显高于当前验收门槛 `1.15`

所以它现在的画像是：

- 频率更高
- 总收益更厚
- 利润因子略有回落
- 但仍在可接受范围内

---

## 6. 当前判断

`entry_hour_18` 已经不只是一个短样本探针。

在 `300k / 500k` 下，它都保持：

- `ready = true`
- 成交明显高于当前 base v3
- 样本外结果没有塌

这意味着它已经有资格被视为：

- 当前本地研究主候选

---

## 7. 和 `atr_m5_10` 的正面对比

为了避免“只是第一轮探针里看起来更好”，
`2026-03-31` 又继续把第二名候选

- `configs/mvp_pullback_sell_research_v3_branch_gate_atr_m5_10.yaml`

补做了本地 `300k / 500k` 长样本确认。

### 7.1 `300k`

| 候选 | ready | closed_trades | total_net_pnl | profit_factor | out_of_sample_net_pnl | out_of_sample_profit_factor | pullback_signal_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `entry_hour_18` | `true` | `18` | `2.61` | `1.9244` | `2.90` | `2.1896` | `25` |
| `atr_m5_10` | `true` | `15` | `0.92` | `1.3178` | `1.22` | `1.4749` | `18` |

### 7.2 `500k`

| 候选 | ready | closed_trades | total_net_pnl | profit_factor | out_of_sample_net_pnl | out_of_sample_profit_factor | pullback_signal_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `entry_hour_18` | `true` | `18` | `2.69` | `1.9511` | `3.32` | `2.6121` | `25` |
| `atr_m5_10` | `true` | `15` | `1.59` | `1.6985` | `2.10` | `2.2078` | `18` |

这轮 head-to-head 可以直接确认：

- `atr_m5_10` 虽然也能过门禁
- 但在 `300k / 500k` 都系统性落后于 `entry_hour_18`
- 当前不需要把 `atr_m5_10` 继续往前提到主候选

---

## 8. 当前落地动作

`2026-03-31` 已经把 `entry_hour_18` 正式提升成下一版研究配置：

- `configs/mvp_pullback_sell_research_v4.yaml`

也就是说，当前推荐的研究主入口已经从：

- `entry_hour_18` 试验名

转成：

- `pullback sell v4`

同一天也已经把后续切盘所需的 `MT5 paper v4` 运行包补齐：

- `configs/mt5_paper_pullback_sell_v4.yaml`
- `docs/implementation/pullback_sell_v4_vps_paper_runbook.md`

随后也已经完成了实际 VPS 切盘：

- `xauusd-ai-paper-mt5-paper-pullback-sell-v4-loop` 已运行
- `xauusd-ai-paper-mt5-paper-pullback-sell-v4-monitor-serve` 已运行
- `xauusd-ai-paper-mt5-paper-pullback-sell-v4-monitor-refresh` 已运行
- `xauusd-ai-paper-mt5-paper-pullback-sell-v4-daily-check` 已运行
- 公网页面已切到：
  - `http://38.60.197.97/`
  - `http://38.60.197.97/health`

这意味着当前差的已经不再是“有没有执行封装”或“有没有完成切盘”，而是：

- 持续观察 `v4` 纸盘稳定性
- 把后续参数研究继续固定留在本地研究机

---

## 9. 下一步建议

当前最合理的后续顺序是：

1. 暂时不要再把研究放回 VPS
2. 把 `pullback sell v4` 视为当前研究主候选
3. 后续如果还要继续加密覆盖率，优先围绕 `v4` 再做小步微调
4. 在重新启用纸盘前，再单独确认一次是否要把当前 VPS 纸盘候选从 `v3` 切到 `v4`

---

## 10. 一句话结论

把 `pullback.min_entry_hour` 从 `20` 放松到 `18`，
是当前第一条已经在 `150k / 300k / 500k` 都跑通、而且显著提升成交覆盖率的本地研究线。
