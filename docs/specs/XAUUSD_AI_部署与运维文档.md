# XAUUSD AI 程序化交易系统：部署与运维文档

## 1. 部署阶段

### 阶段 1：本地开发环境
- 本地读取历史数据
- 完成特征计算与回测框架
- 验证 `examples/replay_csv.py` 与 `Backtrader` 研究链

### 阶段 2：模拟盘环境
- 接入实时行情与最近 bars
- 先运行 `preflight`
- 运行 `live-once` / `live-loop`
- `dry_run=true` 下联调
- 记录订单生命周期
- 验证高波动预警模块的实时提醒链路

### 阶段 3：小资金实盘
- 严格风控阈值
- 实时监控与人工兜底
- 将高波动预警与风控降杠杆或禁开仓规则联动

当前建议的实际上线顺序：

1. 历史回放
2. `MT5 + dry_run=true`
3. `MT5` 模拟盘
4. `MT5` 小资金实盘
5. `cTrader` 补完异步会话层后再作为第二生产通道接入

---

## 2. 运维要求

### 2.1 日志
至少记录：
- 行情快照
- 账户权益快照
- 特征快照
- 状态标签
- 高波动预警分数与等级
- 策略信号
- 风控结果
- 订单执行结果
- 异常事件

建议把执行审计拆成两张表或两类事件：

- 决策评估记录
- 执行尝试记录

如果 Windows 宿主机使用 `Task Scheduler` 长期运行，还应额外具备：

- 计划任务状态查询入口
- 最近一次运行结果码
- 最新任务日志文件路径
- 落盘日志目录，例如 `var/xauusd_ai/task_logs/paper/`、`var/xauusd_ai/task_logs/prod/`

### 2.2 告警
建议告警场景：
- 连续亏损达到阈值
- 点差异常
- 高波动预警达到 warning / critical
- 执行失败
- 数据中断
- 系统崩溃 / 重启
- cTrader / MT5 连接失败
- 连续多个 polling cycle 失败

### 2.3 异常恢复
- 进程自动重启
- 订单状态重同步
- 断线后重新订阅数据
- 异常期间禁止盲目补单
- 预警通道失败时要允许降级到备用通知方式
- MT5 / cTrader 会话恢复后先做状态对齐，再恢复下单

---

## 3. 配置管理

建议区分：
- dev
- backtest
- paper
- prod

所有关键参数必须配置化，不允许硬编码散落在各处。

建议额外单独管理：
- 预警阈值
- 通知通道
- 告警抑制时间
- 告警去重键
- `market_data.platform`
- `execution.platform`
- `runtime.poll_interval_seconds`
- `runtime.starting_equity`

当前仓库已经提供：

- `configs/mvp.yaml`
- `configs/mt5_paper.yaml`
- `configs/mt5_prod.yaml`
- `.env.mt5.example`
- 环境变量覆盖
- `host-check`
- `preflight`
- `export-mt5-history`
- `report-import`
- `deploy-gate`
- `live-once`
- `live-loop`
- MT5 账户状态同步与日内基线跟踪
- MT5 一键脚本
- Windows PowerShell 一键脚本
- Windows 宿主机自举脚本
- Windows `Task Scheduler` 注册脚本
- Windows 计划任务状态脚本

建议本地准备：

1. 复制 `.env.mt5.example` 为 `.env.mt5.local`
2. 填入真实 MT5 账号、密码、服务器、终端路径
3. 先跑 `bash scripts/mt5_host_check.sh`
4. 再跑 `bash scripts/mt5_preflight.sh`
5. 如需本机导出研究数据，先跑 `bash scripts/mt5_export_history.sh .env.mt5.local ./tmp/xauusd_m1_history.csv --bars 20000 --timeframe M1`
6. 如果研究报告在别的机器生成，先用 `report-import` 导入 `acceptance latest.json`
7. 再跑 `bash scripts/mt5_deploy_gate.sh .env.mt5.local`
8. 再跑 `bash scripts/mt5_live_once.sh .env.mt5.local`
9. 再跑 `bash scripts/mt5_paper_loop.sh .env.mt5.local --iterations 10`

如果执行宿主机是 Windows，优先使用：

1. `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_bootstrap.ps1`
2. `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_host_check.ps1 .env.mt5.local`
3. `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_preflight.ps1 .env.mt5.local`
4. 如需本机导出研究数据，先运行 `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_export_history.ps1 .env.mt5.local .\tmp\xauusd_m1_history.csv --bars 20000 --timeframe M1`
5. 如果研究报告在别的机器生成，先运行 `report-import`
6. `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_deploy_gate.ps1 .env.mt5.local`
7. `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_live_once.ps1 .env.mt5.local`
8. `powershell -ExecutionPolicy Bypass -File .\scripts\mt5_paper_loop.ps1 .env.mt5.local --iterations 10`
9. 长期运行时，注册 `Task Scheduler`
10. 用 `mt5_task_status.ps1` 检查任务状态和最新日志

当前环境备注：

- 如果本机 `pip install MetaTrader5` 无法成功，说明本机不适合作为 MT5 真实执行宿主机
- 此时建议把当前仓库继续作为研发与编排节点，另准备一台可安装 MT5 Python 依赖的执行宿主机
- 在真正切换到执行宿主机前，可以先按 `docs/implementation/local_mt5_manual_debug.md` 做终端层面的手工联调

建议上线脚本顺序：

1. `host-check --strict`
2. `preflight --strict`
3. 如有需要，先 `report-import`
4. `deploy-gate --strict`
5. `live-once --require-deploy-gate --require-preflight`
6. `live-loop --require-deploy-gate --require-preflight`
7. 需要长期运行时，再注册 `Task Scheduler`
8. 上线后持续用任务状态脚本和日志目录做巡检

当前运维经验补充：

- 如果 `preflight` 里 `latest_tick` 存在，但 `bid/ask=0`
  优先判断是否为停盘期或无活跃报价，而不是先判断成网络故障
- 如果 `recent_bars` 仍然可读，说明 MT5 初始化、symbol 选择和历史数据链通常仍然正常
- `deploy-gate` 使用研究报告中的 `checked_at` 判断新鲜度，所以 `report-import` 不会把旧报告“伪装成新报告”

---

## 4. 上线原则

- 先回测
- 再验证预警模块
- 再模拟盘
- 再小资金
- 最后逐步放量

任何阶段回撤、执行质量或稳定性异常，都必须退回上阶段修复。

---

## 5. 一句话总结

交易系统不是“写完代码就结束”，真正的难点之一是：

> **它要在真实、有噪声、有异常的环境里稳定跑下去。**
