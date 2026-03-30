# Pullback Sell V3 Windows VPS 纸盘落地清单

如果你只是做日常值守、看监控页、恢复页面或检查任务状态，优先看这份更短的速查手册：

- `docs/implementation/pullback_sell_v3_daily_ops_quickstart.md`

## 适用范围

这份清单只针对当前这条候选分支：

- `sell-only`
- `us-only`
- `pullback v3`

对应配置：

- 研究 branch gate：
  - `configs/mvp_pullback_sell_research_v3_branch_gate.yaml`
- MT5 paper 运行配置：
  - `configs/mt5_paper_pullback_sell_v3.yaml`

目标不是替换主线 paper，而是把这条候选线单独接入 Windows VPS 做持续纸盘验证。

## 当前已确认的本地状态

本地已经完成：

- 候选线 acceptance 归档已生成
- 候选线 `deploy-gate` 已通过
- 候选线最新可传输验收文件已导出

当前可直接使用的文件：

- 归档 latest：
  - `reports/research_pullback_sell_v3/acceptance/latest.json`
- 可传输副本：
  - `tmp/research_pullback_sell_v3_acceptance_latest.json`

## A. 在研究机执行

### 1. 重新生成候选线验收归档

```bash
./scripts/research_pullback_sell_v3_acceptance.sh
```

默认输入：

- `tmp/xauusd_m1_history_100000.csv`

默认输出归档目录：

- `reports/research_pullback_sell_v3`

### 2. 导出一份可传输 JSON

```bash
./scripts/research_pullback_sell_v3_export_latest.sh
```

默认输出：

- `tmp/research_pullback_sell_v3_acceptance_latest.json`

### 3. 传到 Windows VPS

推荐落点：

- `C:\work\incoming\research_pullback_sell_v3_acceptance_latest.json`

如果你当前已经通过 `Microsoft Remote Desktop` 连接 VPS，优先用：

- RDP 共享文件夹
- 复制粘贴
- 临时网盘/对象存储下载

目标只有一个：把上面这份 JSON 放到 VPS 本地磁盘。

## B. 在 Windows VPS 执行

### 0. 最省事的方式

如果你希望一次串起来执行，也可以直接用仓库里新增的辅助脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_prepare.ps1 .env.mt5.local C:\work\incoming\research_pullback_sell_v3_acceptance_latest.json -RunLiveOnce -LoopIterations 10
```

这条命令会顺序执行：

- `report-import`
- `reports latest`
- `host-check --strict`
- `preflight --strict`
- `deploy-gate --strict`
- `live-once --require-deploy-gate --require-preflight`
- `live-loop --iterations 10 --require-deploy-gate --require-preflight`

如果你更希望逐步排查，就按下面的分步流程执行。

如果你希望后续长期只记住“候选线专用入口”，项目里还额外提供了这几个包装脚本：

- `scripts/mt5_pullback_sell_v3_paper_loop.ps1`
- `scripts/mt5_pullback_sell_v3_register_task.ps1`
- `scripts/mt5_pullback_sell_v3_task_status.ps1`
- `scripts/mt5_pullback_sell_v3_unregister_task.ps1`

它们内部已经固定绑定：

- `configs/mt5_paper_pullback_sell_v3.yaml`

### 1. 导入候选线验收报告

```powershell
.venv\Scripts\python.exe -m xauusd_ai_system.cli report-import C:\work\incoming\research_pullback_sell_v3_acceptance_latest.json --report-dir reports\research_pullback_sell_v3
```

### 2. 确认导入结果

```powershell
.venv\Scripts\python.exe -m xauusd_ai_system.cli reports latest --report-dir reports\research_pullback_sell_v3
```

应该看到：

- `ready = true`
- `failed_check_names = []`

### 3. 跑宿主机检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_host_check.ps1 .env.mt5.local -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml
```

### 4. 跑平台预检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_preflight.ps1 .env.mt5.local -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml
```

### 5. 跑候选线门禁

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_deploy_gate.ps1 .env.mt5.local -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml
```

### 6. 先做一次单次联调

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_live_once.ps1 .env.mt5.local -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml
```

### 7. 再做短轮询验证

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_paper_loop.ps1 .env.mt5.local -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml --iterations 10
```

## C. 短轮询通过后

如果上面的 `live_once` 和 `paper_loop --iterations 10` 都稳定，再注册独立计划任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_register_task.ps1 -Mode paper -EnvFile .env.mt5.local -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml -StartAfterRegister
```

或者直接用候选线专用包装脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_register_task.ps1 .env.mt5.local -StartAfterRegister
```

查看状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_task_status.ps1 -Mode paper -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml -TailLog
```

或者：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_task_status.ps1 .env.mt5.local -TailLog
```

如果你想连续盯几轮，不要反复手敲，可以直接：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_task_status.ps1 .env.mt5.local -WatchCount 6 -WatchIntervalSeconds 10 -TailLog
```

几个关键读数：

- `health: ok` 表示当前没有发现明显异常
- `state: Running` 表示计划任务正在跑
- `last_task_result_hex: 0x00041301` 在这里是正常值，含义是任务当前正在运行
- `latest_log_age_seconds` 如果持续大于 `freshness_warning_seconds`，说明任务可能卡住，需要看日志
- `latest_log_has_failure_pattern: True` 说明最近日志里已经出现 `live_cycle_failed` 或 `task_runner_failed`

兼容性说明：

- Windows Server 2019 上计划任务注册使用 `Interactive` 登录类型
- 任务运行器已改成子进程日志收集，避免把普通 Python 输出误判成失败

### 监控页

如果你想直接看页面，不想只盯终端日志，现在可以直接导出或启动只读监控面板。

导出静态 HTML：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_dashboard.ps1 .env.mt5.local
```

默认会输出到：

- `var\xauusd_ai\dashboards\mt5-paper-pullback-sell-v3.html`

直接启动只读 HTTP 页面：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_dashboard.ps1 .env.mt5.local -Serve -Host 0.0.0.0
```

启动后可访问：

- `http://<VPS-IP>/`
- `http://<VPS-IP>/api/snapshot`
- `http://<VPS-IP>/health`

这个监控页当前会展示：

- 最近决策
- 最近高波动预警
- 最近执行尝试
- 最新决策时间和是否 stale
- 风险拦截率
- 状态 / 波动 / 时段 / 策略分布

安全提醒：

- 这是只读监控页，不会下单
- 但默认没有鉴权，建议只在 VPS 内网、堡垒机或临时开放端口场景下使用
- 如果对公网开放，请至少配合 Windows 防火墙白名单或反向代理鉴权

如果你希望 VPS 重启后自动恢复监控，并且持续把静态 HTML 落盘刷新，可以直接注册两条监控计划任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_register_tasks.ps1 .env.mt5.local -BindHost 0.0.0.0 -StartAfterRegister
```

这条命令会注册：

- `...-monitor-serve`
  负责把只读监控 HTTP 页面拉起来
- `...-monitor-refresh`
  负责周期性刷新静态 HTML 到本地磁盘

当前这条候选线已经把公网监控默认端口统一成 `80`。

- 直接访问入口：`http://<VPS-IP>/`
- 如果你手动执行恢复脚本，也建议直接用默认值，不再额外传 `-Port 8765`

查看状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_task_status.ps1 .env.mt5.local -TailLog
```

移除监控自启任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_monitoring_unregister_tasks.ps1 .env.mt5.local
```

如果需要移除：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_unregister_task.ps1 -Mode paper -ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml
```

或者：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_unregister_task.ps1 .env.mt5.local
```

## D. 候选线和主线的隔离点

这条候选线默认会单独使用：

- 报告目录：
  - `reports/research_pullback_sell_v3`
- 数据库：
  - `var/xauusd_ai/paper_pullback_sell_v3.db`
- MT5 magic：
  - `2026033003`
- 计划任务名：
  - 默认会带配置名后缀
- 任务日志目录：
  - 默认也会带配置名后缀

所以它可以和主线 `mt5_paper.yaml` 并行运行。

## E. 最关键的判断标准

进入持续纸盘前，至少确认这几点：

- `report-import` 成功
- `reports latest` 显示 `ready=true`
- `host-check` 通过
- `preflight` 通过
- `deploy-gate` 通过
- `live_once` 没有结构化异常
- `paper_loop --iterations 10` 没有连续失败

如果其中任何一步失败，不要直接注册计划任务。
