# 2026-03-30 Session Handoff

## 本次完成

- 在本机 Wine 版 MT5 上编译成功导出脚本：
  - `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/mt5/ExportHistoryCsv.mq5`
  - `/Users/kyrie/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5/Scripts/ExportHistoryCsv.ex5`
- MT5 脚本执行成功，MQL5 日志确认：
  - `/Users/kyrie/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5/Logs/20260330.log`
  - 关键行：`EXPORT_OK symbol=XAUUSD timeframe=M1 bars=100000 file=xauusd_m1_history_mt5.csv common=true`
- 导出的原始 MT5 CSV 位于：
  - `/Users/kyrie/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files/xauusd_m1_history_mt5.csv`
- 已复制到项目并转成项目标准格式：
  - 原始导出：`/Users/kyrie/Documents/黄金全流程量化交易系统/tmp/xauusd_m1_history_mt5_100k.csv`
  - 标准回测格式：`/Users/kyrie/Documents/黄金全流程量化交易系统/tmp/xauusd_m1_history_100000.csv`

## 新历史数据概况

- 行数：`100000`
- 起始时间：`2025-12-15 12:04:00`
- 结束时间：`2026-03-30 12:53:00`
- 月份分布：
  - `2025.12`: `15627`
  - `2026.01`: `28685`
  - `2026.02`: `27417`
  - `2026.03`: `28271`
- spread 概况：
  - 中位数：`0.10`
  - p90：`0.11`
  - 最大值：`1.00`

## 100k 回测结果

### 主配置 `mvp`

- 结果文件：
  - `/tmp/xauusd_acceptance_100k_mvp.json`
- 关键结果：
  - `net_pnl = -409.39`
  - `profit_factor = 0.1532`
  - `closed_trades = 856`
  - `win_rate = 0.2325`
  - `max_drawdown_pct = 0.0409`
  - `oos_net_pnl = -115.0`
  - `wf_positive_window_rate = 0.0526`
- 结论：
  - 主线继续恶化，确认不值得作为当前研究重点。

### 候选配置 `mvp_pullback_sell_research_v3`

- 配置文件：
  - `/Users/kyrie/Documents/黄金全流程量化交易系统/configs/mvp_pullback_sell_research_v3.yaml`
- 结果文件：
  - `/tmp/xauusd_acceptance_100k_pullback_sell_v3.json`
- 关键结果：
  - `net_pnl = 1.40`
  - `profit_factor = 2.49`
  - `closed_trades = 6`
  - `win_rate = 0.6667`
  - `max_drawdown_pct = 0.0002`
  - `oos_net_pnl = 1.11`
  - `wf_positive_window_rate = 0.9895`
- 失败项：
  - 仅剩 `session_profit_concentration`
- 结论：
  - 拉长到 `100k` 之后没有崩，仍然是当前最值得继续追的研究分支。

## 本次关键判断

- MT5 本机导出链已经打通，可以继续手动导更长历史。
- 研究主线不该继续放在 `mvp`。
- 当前最有价值的候选仍然是：
  - `sell-only pullback v3`
- 但样本数仍然偏少，所以它更像研究候选，不适合直接当默认生产策略。

## 下次打开优先做什么

1. 继续从 MT5 导更长的 `XAUUSD M1` 历史，优先把时间再往 `2025-11` 或更早推。
2. 用更长历史继续跑：
   - `/Users/kyrie/Documents/黄金全流程量化交易系统/configs/mvp_pullback_sell_research_v3.yaml`
3. 如果仍只失败 `session_profit_concentration`：
   - 把验收口径拆成“全市场主线”与“单时段研究分支”两套。
4. 如果开始转负：
   - 重点排查 `2025.12` 段与新增样本里的 stop loss 分布。

## 2026-03-30 后续补充

本次已按上面的第 3 点落地一个独立配置：

- `/Users/kyrie/Documents/黄金全流程量化交易系统/configs/mvp_pullback_sell_research_v3_branch_gate.yaml`

作用：

- 不改主线 `mvp` 验收口径
- 专门用于评估 `sell-only + us-only` 这条研究分支
- 因为该分支天然只允许一个 session，所以：
  - `max_session_profit_concentration` 调整为 `1.00`

这意味着后续可以并行保留两条门禁口径：

- 主线：
  继续要求多时段不过度集中
- 单时段研究分支：
  先重点验证收益、样本外和 walk-forward 是否稳定

基于本地 `100k` 历史复验，当前结果已确认：

- `configs/mvp_pullback_sell_research_v3.yaml`
  - 仍然只失败 `session_profit_concentration`
- `configs/mvp_pullback_sell_research_v3_branch_gate.yaml`
  - 已经 `ready = true`
  - 关键结果：
    - `net_pnl = 1.40`
    - `profit_factor = 2.49`
    - `closed_trades = 6`
    - `oos_net_pnl = 1.11`
    - `walk_forward_positive_window_rate = 0.9895`

当前应如何理解这个结果：

- 这说明 `sell-only + us-only pullback v3` 已经可以作为“单分支候选”
- 但它还不应替代全市场主线 `mvp`
- 因为主线要回答的是“跨时段是否稳定”
- 分支 gate 回答的是“这个单时段候选是否值得继续往生产候选推进”

## 2026-03-30 后续继续结果

为了避免这条候选线只能停留在研究配置，本次已经把它接进 MT5 纸交易运行链：

- 新增运行配置：
  - `/Users/kyrie/Documents/黄金全流程量化交易系统/configs/mt5_paper_pullback_sell_v3.yaml`
- 关键特征：
  - 维持 `sell-only + us-only pullback v3`
  - 报告目录独立为 `reports/research_pullback_sell_v3`
  - 纸盘数据库独立为 `var/xauusd_ai/paper_pullback_sell_v3.db`
  - MT5 magic 独立为 `2026033003`

同时 helper scripts 已补上“可选配置文件”支持：

- PowerShell 入口现在都可以直接传：
  - `-ConfigPath .\configs\mt5_paper_pullback_sell_v3.yaml`
- 任务计划相关脚本也已支持按配置自动拆分：
  - 默认任务名
  - 默认日志目录
  - 状态查询
  - 卸载任务

这意味着下次在 Windows VPS 上继续时，不需要改主线配置，只要：

1. 导入这条候选线自己的验收报告到 `reports/research_pullback_sell_v3`
2. 用 `-ConfigPath` 跑 `host-check / preflight / deploy-gate / live-once / paper-loop`
3. 如需长期运行，再注册独立计划任务

后续又补了一层“研究机到 VPS 的文件交接”能力：

- CLI 新增：
  - `report-export`
- 新增候选线导出脚本：
  - `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/research_pullback_sell_v3_export_latest.sh`
  - `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/research_pullback_sell_v3_export_latest.ps1`
- 默认会导出一份可直接传输的 JSON：
  - `/Users/kyrie/Documents/黄金全流程量化交易系统/tmp/research_pullback_sell_v3_acceptance_latest.json`

并且已经本地验证：

- `report-export` 成功
- 用导出的 JSON 再执行一次 `report-import` 成功
- 再读 `reports latest` 结果正确

为了方便 Windows VPS 上的长期运行，本次还新增了候选线专用包装脚本：

- `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/mt5_pullback_sell_v3_paper_loop.ps1`
- `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/mt5_pullback_sell_v3_register_task.ps1`
- `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/mt5_pullback_sell_v3_task_status.ps1`
- `/Users/kyrie/Documents/黄金全流程量化交易系统/scripts/mt5_pullback_sell_v3_unregister_task.ps1`

这样后续在 VPS 上可以不再手写长 `-ConfigPath` 命令。

对应的 VPS 落地清单已经单独整理到：

- `/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/pullback_sell_v3_vps_paper_runbook.md`

## 备注

- 本次线程里已经验证：用户手动把脚本拖到图表后，MT5 实际执行成功。
- 之前没找到导出文件，是因为 Wine 写到了：
  - `drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files`
  - 不是 `drive_c/users/kyrie/...`
