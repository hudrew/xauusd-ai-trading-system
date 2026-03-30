# Pullback Sell V3 VPS 日常值守速查手册

## 适用范围

这份手册只给当前这条候选线使用：

- `paper`
- `sell-only`
- `pullback v3`
- `MT5 Windows VPS`

这份速查手册只用于：

- 日常值守
- 页面恢复
- 任务状态检查

不用于：

- 长 `acceptance`
- 长 `walk-forward`
- 大样本研究回测

这类长研究任务统一放到本地研究机或独立研究宿主机，不要压当前这台 `1 核 / 4GB` 的 Windows VPS。

对应配置：

- `configs/mt5_paper_pullback_sell_v3.yaml`

当前监控公网入口默认是：

- `http://<VPS-IP>/`
- `http://<VPS-IP>/health`

## 最短入口

如果你不想记太多命令，先只记住这两个：

日常巡检：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

归档巡检结果：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check_archive.ps1 .env.mt5.local
```

页面异常时恢复：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

如果你希望恢复后顺手把异常 sync 当成失败直接抛出，也可以加：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local -FailOnAttentionSync -FailOnRuntimeIssue
```

如果你希望在 runtime 不健康时顺手把纸盘主任务也重新拉起，可以加：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local -RecoverPaperTaskOnRuntimeIssue
```

## 你每天最常用的 4 件事

### 1. 打开监控页

直接访问：

- `http://<VPS-IP>/`

如果页面能打开，先看这几个点：

- 最近决策时间是不是持续更新
- 最近高波动预警有没有异常暴增
- 最近执行尝试是不是持续刷新
- 页面有没有明显 stale 提示
- `Paper Window` 里的权益变化、日内收益、最大回撤有没有异常
- `Risk Block Reasons` 和 `Execution Error Pressure` 有没有突然集中到某一类原因
- `Execution Price Drift` 里的最新不利滑点、均值、最大值有没有突然抬升
- `Recent Execution Syncs` 里有没有连续出现 `accepted_not_visible / accepted_unmatched`

### 2. 看系统是否还在跑

在 VPS 仓库目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

重点看：

- `health: ok`
- `state: Running`
- `last_task_result_hex: 0x00041301`

上面三项同时正常，通常说明纸盘主任务还在运行。

### 3. 看监控页服务是否正常

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

重点看：

- `serve` 是不是 `Running`
- `refresh` 是不是 `Running`
- `dashboard_updated_at` 有没有持续更新
- `health_status_code` 对应页面能否返回 `200`

如果页面正常刷新，现在优先看的新增面板是：

- `Paper Window`
  - 看窗口开始/结束时间
  - 看最近权益变化
  - 看最新日内收益和最大回撤
  - 看平均点差和最大点差
- `Risk Block Reasons`
  - 看是不是被 `SESSION_NOT_ALLOWED`
  - 看是不是被 `STRATEGY_DISABLED`
  - 看是不是被波动或风控原因大量拦截
- `Execution Outcome Mix`
  - 看 accepted / rejected 比例有没有突然恶化
- `Execution Error Pressure`
  - 看错误是不是集中在同一种执行失败原因
- `Execution Price Drift`
  - 看最新请求价和观察价差多少
  - 看 `Position Ticket / ID`
  - 看 `History Order State`
  - 看 `History Deal Entry / Reason`
  - 看 `Latest Price Offset`
  - 看 `Average / Max Adverse Slippage`
- `Recent Execution Syncs`
  - 看 `Hist Ord / Hist Deal` 是否开始稳定出现
  - 如果 open positions 看不到，但 history deal 已出现，优先按“broker 已记成交”处理

### 4. 页面打不开时直接恢复

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

这条命令会直接：

- 停掉旧监控任务
- 清理占用端口的旧进程
- 重建监控计划任务
- 重启只读监控页面
- 重新检查 `/health`
- 最后再拉一次 `monitoring snapshot`
- 可选按 `attention sync / runtime status` 直接返回失败

## 最省事的标准操作顺序

如果你只是想判断今天系统是不是正常，按这个顺序就够了：

1. 打开 `http://<VPS-IP>/`
2. 如果页面正常，先不动
3. 如果页面异常，执行 `mt5_pullback_sell_v3_monitoring_recover.ps1`
4. 如果还是异常，再执行主任务状态检查
5. 只有在脚本版本落后时，才执行 `git pull`

## 你最常用的命令

先进入项目目录：

```powershell
cd /d C:\work\xauusd-ai-trading-system
```

更新代码：

```powershell
git pull
```

一键日常巡检：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

一键巡检并归档结果：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check_archive.ps1 .env.mt5.local
```

一键监控恢复：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

检查主任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_task_status.ps1 .env.mt5.local -TailLog
```

恢复主任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_task_recover.ps1 .env.mt5.local -TailLog
```

检查监控任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_task_status.ps1 .env.mt5.local -TailLog
```

恢复监控页：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

严格模式恢复：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local -FailOnAttentionSync -FailOnRuntimeIssue
```

重建监控自启任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_register_tasks.ps1 .env.mt5.local -BindHost 0.0.0.0 -StartAfterRegister
```

移除监控自启任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_unregister_tasks.ps1 .env.mt5.local
```

重建纸盘主任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_register_task.ps1 .env.mt5.local -StartAfterRegister
```

## 出问题时怎么判断

### 场景 1：页面打不开

先做：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

再看：

- `http://<VPS-IP>/health`

如果返回 `200`，通常说明监控层已经恢复。

### 场景 2：页面能打开，但数据不刷新

优先检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_task_status.ps1 .env.mt5.local -TailLog
```

重点看：

- `refresh` 是否 `Running`
- `dashboard_updated_at` 是否更新
- `refresh.log` 最近有没有新增输出

### 场景 3：监控正常，但交易主任务不正常

执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_task_status.ps1 .env.mt5.local -TailLog
```

如果主任务不在 `Running`，再执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_register_task.ps1 .env.mt5.local -StartAfterRegister
```

## 当前默认值

这条候选线当前默认值已经固定为：

- 监控页默认公网端口：`80`
- 监控入口：`http://<VPS-IP>/`
- 健康检查：`http://<VPS-IP>/health`

所以后续常规操作时，通常不需要再手动传：

- `-Port 80`

日常巡检归档默认会写到：

- `var\xauusd_ai\ops_checks\paper\mt5-paper-pullback-sell-v3\`

监控页里看执行同步时，当前优先关注：

- `Latest Sync Origin`
  是否已经从 `submission` 平滑切到后续 `reconcile`
- `Execution Sync Status`
  是否出现 `position_closed_tp / position_closed_sl / position_closed_manual`
- `Execution Sync Origin`
  最近窗口里是否同时还能看到 `submission / reconcile`
- `Broker Close Status`
  最近平仓是否主要来自 `tp / sl / manual / expert`
- `Broker Deal Reason`
  broker 返回的成交原因是否和状态判断一致
- `Recent Execution Syncs`
  是否长时间只重复同一条异常状态

当前 `daily_check` 也会额外打印一段 `monitoring-snapshot`，直接给出：

- `latest_sync_status / latest_sync_origin`
- `recent_submission_syncs / recent_reconcile_syncs`
- `recent_tp_close_events / recent_sl_close_events`
- `recent_manual_close_events / recent_expert_close_events`
- `recent_attention_syncs`

## 什么时候看完整文档

如果你遇到下面这些情况，再去看完整 runbook：

- 需要重新导入研究验收报告
- 需要重新做 `deploy-gate`
- 需要重新做 MT5 宿主机检查
- 需要从零重建整条候选线

完整文档：

- `docs/implementation/pullback_sell_v3_vps_paper_runbook.md`
- `docs/implementation/pullback_sell_v3_paper_observation_template.md`
