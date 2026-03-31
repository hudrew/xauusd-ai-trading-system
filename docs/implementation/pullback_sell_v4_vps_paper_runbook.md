# Pullback Sell V4 Windows VPS 纸盘切换手册

日期：

- `2026-03-31`

适用范围：

- 本地研究已经确认通过的 `pullback sell v4`
- Windows VPS 只承担 `MT5 执行 / 纸盘 / 监控 / 值守`
- 不再把参数扫描和长样本研究放到 VPS

## 当前状态

`pullback sell v4` 已经完成两件事：

- 本地研究确认：
  - `300k` 与 `500k` 样本都保持 `ready = true`
  - 相比 `base v3`，成交从 `7` 笔提升到 `18` 笔
  - `total_net_pnl` 从 `1.42` 提升到 `2.69`
- VPS 纸盘切换包已补齐：
  - `configs/mt5_paper_pullback_sell_v4.yaml`
  - `scripts/mt5_pullback_sell_v4_prepare.ps1`
  - `scripts/mt5_pullback_sell_v4_paper_loop.ps1`
  - `scripts/mt5_pullback_sell_v4_register_task.ps1`
  - `scripts/mt5_pullback_sell_v4_task_status.ps1`
  - `scripts/mt5_pullback_sell_v4_task_recover.ps1`
  - `scripts/mt5_pullback_sell_v4_unregister_task.ps1`
  - `scripts/mt5_pullback_sell_v4_monitoring_dashboard.ps1`
  - `scripts/mt5_pullback_sell_v4_monitoring_register_tasks.ps1`
  - `scripts/mt5_pullback_sell_v4_monitoring_task_status.ps1`
  - `scripts/mt5_pullback_sell_v4_monitoring_recover.ps1`
  - `scripts/mt5_pullback_sell_v4_monitoring_unregister_tasks.ps1`
  - `scripts/mt5_pullback_sell_v4_daily_check.ps1`
  - `scripts/mt5_pullback_sell_v4_daily_check_archive.ps1`
  - `scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1`
  - `scripts/mt5_pullback_sell_v4_daily_check_task_status.ps1`
  - `scripts/mt5_pullback_sell_v4_daily_check_unregister_task.ps1`
  - `scripts/mt5_pullback_sell_v4_daily_recover.ps1`

`2026-03-31` 同日已实际完成 VPS 切盘，当前线上状态：

- 纸盘主任务正在运行：
  - `xauusd-ai-paper-mt5-paper-pullback-sell-v4-loop`
- 监控任务正在运行：
  - `xauusd-ai-paper-mt5-paper-pullback-sell-v4-monitor-serve`
  - `xauusd-ai-paper-mt5-paper-pullback-sell-v4-monitor-refresh`
- 日检任务已注册并成功归档：
  - `xauusd-ai-paper-mt5-paper-pullback-sell-v4-daily-check`
- 当前公网入口：
  - Dashboard: `http://38.60.197.97/`
  - Health: `http://38.60.197.97/health`
- 当前最新日检归档目录：
  - `var/xauusd_ai/ops_checks/paper/mt5-paper-pullback-sell-v4`

仍然保持：

- VPS 上旧的 `v3` 任务处于停用状态
- 研究任务不回到 VPS
- 后续只在这条 `v4` 线上继续做执行观察和值守

## 配置隔离

`v4` 纸盘配置已经和 `v3` 做了隔离：

- 报告目录：
  - `reports/research_pullback_sell_v4`
- 数据库：
  - `var/xauusd_ai/paper_pullback_sell_v4.db`
- 运行服务名：
  - `xauusd-ai-paper-pullback-sell-v4`
- MT5 comment 前缀：
  - `xauusd-ai-pbsv4`
- MT5 magic：
  - `2026033104`

策略差异目前只保留一条核心变更：

- `pullback.min_entry_hour = 18`

## 切换前准备

先在本地研究机确认最新 `v4` 验收归档已经存在：

- `reports/research_pullback_sell_v4/acceptance/latest.json`

如果需要导出到 VPS，可以直接用 CLI：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-export ./tmp/research_pullback_sell_v4_acceptance_latest.json --report-dir reports/research_pullback_sell_v4
```

然后把导出的 JSON 传到 VPS，例如：

- `C:\work\incoming\research_pullback_sell_v4_acceptance_latest.json`

## VPS 上的标准切换顺序

如果你接手时发现 `v4` 已经在跑，先不要重复注册任务。

优先先确认：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_task_status.ps1 .env.mt5.local -TailLog
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_monitoring_task_status.ps1 .env.mt5.local -TailLog
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_daily_check_task_status.ps1 .env.mt5.local
```

只有在任务未运行、端口冲突或监控页失效时，再按下面顺序重建。

### 1. 导入最新验收报告并做准备检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_prepare.ps1 .env.mt5.local C:\work\incoming\research_pullback_sell_v4_acceptance_latest.json
```

这一步会顺序执行：

- `report-import`
- `reports latest`
- `host-check --strict`
- `preflight --strict`
- `deploy-gate --strict`

### 2. 先做一次短烟雾测试

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_prepare.ps1 .env.mt5.local C:\work\incoming\research_pullback_sell_v4_acceptance_latest.json -RunLiveOnce -LoopIterations 10
```

目的：

- 验证 MT5 终端、行情拉取、下单仿真和日志落地正常
- 先确认 `v4` 没有把执行层封装带坏

### 3. 注册纸盘主任务

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_register_task.ps1 .env.mt5.local -StartAfterRegister
```

状态检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_task_status.ps1 .env.mt5.local -TailLog
```

### 4. 注册监控页面任务

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_monitoring_register_tasks.ps1 .env.mt5.local -Port 80 -StartAfterRegister
```

状态检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_monitoring_task_status.ps1 .env.mt5.local -TailLog
```

当前实际落地说明：

- `8765` 在宿主机内部曾可用，但公网不稳定可达
- 由于这台 VPS 公网 `80` 已放通，所以最终已把 `v4` 监控页固定切到 `80`
- 切换过程中也已清掉旧的手工 `v3` 页面进程，避免公网仍然看到旧页面

如果后面页面异常，优先用恢复脚本，不要手工杀散进程：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_monitoring_recover.ps1 .env.mt5.local -Port 80
```

### 5. 注册日检任务

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_daily_check_register_task.ps1 .env.mt5.local -StartAfterRegister
```

状态检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_daily_check_task_status.ps1 .env.mt5.local
```

## 回滚与停用

如果切盘后需要立即停掉 `v4`：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_monitoring_unregister_tasks.ps1 .env.mt5.local
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_daily_check_unregister_task.ps1 .env.mt5.local
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v4_unregister_task.ps1 .env.mt5.local
```

## 关键原则

- 研究和参数扫描继续固定留在本地研究机
- VPS 只负责执行、监控和值守
- 当前 `v4` 已经在 VPS 上真实运行，不再是“待切换”
- 真正需要恢复时，优先走 `task_status / monitoring_task_status / daily_check_task_status`
- 只有确认任务失效后，再走 `prepare / recover / register`
