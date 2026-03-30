# Pullback Sell V3 纸盘连续观察记录模板

记录日期：

- `YYYY-MM-DD`

记录人：

- ``

观察窗口：

- `asia / eu / overlap / us`

## 1. 基本状态

监控页地址：

- `http://<VPS-IP>/`

主任务状态：

- `Running / Ready / Failed`

监控任务状态：

- `serve:`
- `refresh:`

健康检查：

- `http://<VPS-IP>/health`
- 返回值：

## 2. 本轮检查命令

日常巡检：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

归档巡检结果：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check_archive.ps1 .env.mt5.local
```

如需留存机器可读摘要，可直接读取：

- `var\xauusd_ai\ops_checks\paper\mt5-paper-pullback-sell-v3\latest.json`

如需恢复监控：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

## 3. 巡检摘要

本轮是否正常：

- `是 / 否`

主任务是否持续刷新：

- `是 / 否`

监控页是否持续刷新：

- `是 / 否`

高波动预警是否异常暴增：

- `是 / 否`

是否出现明显 stale：

- `是 / 否`

## 4. 关键观察

最近决策时间：

- ``

最近高波动预警情况：

- `无 / 少量 / 频繁 / 异常`

最近执行尝试情况：

- `无 / 正常 / 异常`

风险拦截情况：

- `正常 / 偏多 / 异常`

`Paper Window` 观察：

- 窗口权益变化：
- 最新日内收益：
- 最大回撤：
- 平均/最大点差：

`Risk Block Reasons` 观察：

- 主要拦截原因：
- 是否出现某一类原因突然暴增：

`Execution Outcome Mix / Execution Error Pressure` 观察：

- accepted / rejected 比例：
- 主要执行失败原因：

`Execution Sync Status / Recent Execution Syncs` 观察：

- 最新 sync 状态：
- 最新 sync origin：
- 最近 submission / reconcile 数量：
- 最新 requested / observed price：
- 最新 observed source：
- latest position ticket / id：
- latest history order state：
- latest history deal entry / reason：
- 最新 price offset：
- 最新 adverse slippage points：
- average / max adverse slippage points：
- latest history orders / deals：
- latest history deal ticket：
- 当前 open orders 数量：
- 当前 open positions 数量：
- 最近 close events 数量：
- 最近 tp / sl / manual / expert 数量：
- 最近 attention sync 数量：
- 是否出现 `accepted_not_visible / accepted_unmatched`：
- 是否出现 `position_closed_tp / position_closed_sl / position_closed_manual / position_closed_expert`：

日志是否出现失败关键词：

- `无 / 有`

## 5. 问题记录

是否发现问题：

- `否 / 是`

问题现象：

- ``

问题发生时间：

- ``

是否已恢复：

- `否 / 是`

恢复动作：

- ``

## 6. 本轮结论

本轮结论：

- `继续观察 / 需要恢复 / 需要重新拉主任务 / 需要研究排查`

下一步动作：

- ``

## 7. 巡检归档文件

建议把每次归档结果记录到：

- `var\xauusd_ai\ops_checks\paper\mt5-paper-pullback-sell-v3\`

建议同步记录：

- 本次归档文件路径
- 本次是否执行过恢复
- 本次结论
