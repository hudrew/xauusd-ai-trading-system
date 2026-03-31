# 2026-04-01 Session Handoff

## 本次完成

- 新增 `0.26` 候选纸盘配置：
  - `configs/mt5_paper_pullback_sell_v4_pullback_depth_0_26.yaml`
- 当前 `v4` PowerShell 包装脚本已统一支持：
  - `-ConfigPath`
- 覆盖范围已包含：
  - `prepare`
  - `paper_loop`
  - `register/status/recover/unregister`
  - `monitoring`
  - `daily_check`
- 通用日检注册脚本已补上：
  - 向归档脚本透传 `-ConfigPath`
- 新增候选切换手册：
  - `docs/implementation/pullback_sell_v4_pullback_depth_0_26_vps_candidate_runbook.md`
- 新增候选程序化放行门：
  - `xauusd_ai_system.cli promotion-gate`
  - `scripts/mt5_pullback_sell_v4_candidate_promotion_gate.ps1`
- 当前 `v4 daily_check` 已继续收口：
  - 内嵌精简 `execution_audit`
  - 日检输出会直接显示执行闭环健康
- 当前 `promotion-gate` 已继续支持：
  - 没有单独 `execution-audit` JSON 时，直接复用 `daily_check.execution_audit`
- 当前候选 gate 包装脚本已继续优化：
  - 默认自动刷新日检时，优先走内嵌执行审计，减少单独证据文件依赖
- `2026-04-01` 晚间继续补强 `promotion-gate` 兼容性：
  - 接受 PowerShell `ToString("o")` 产生的 7 位小数时间戳
  - 候选验收 `headline_metrics` 如果是残缺摘要，会继续从 payload / payload.summary / 衍生指标补齐
  - 候选 gate 包装脚本在可复用 `daily_check.execution_audit` 时，不再错误强塞缺失的 `execution_audit latest.json`
  - 导入型 acceptance 只有 `summary.passed/failed/total` 时，也会从 `payload.checks[].observed` 补出：
    - `close_month_profit_concentration`
    - `session_profit_concentration`

## 当前意义

这次不是继续改策略参数，而是把未来从当前 `v4` 切到 `0.26` 的工程入口和程序化放行门都准备好。

当前已经具备：

1. 本地研究主候选 `0.26`
2. 独立候选纸盘配置
3. 同一套 `v4` 运维脚本对候选配置的复用能力
4. 候选切换和回滚的独立 runbook

这意味着后面如果要切候选，不需要再复制一套脚本，也不需要先改当前线上 `v4` 配置。

## 当前边界

- 当前线上继续运行：
  - `configs/mt5_paper_pullback_sell_v4.yaml`
- 当前还没有批准直接切到：
  - `configs/mt5_paper_pullback_sell_v4_pullback_depth_0_26.yaml`
- 当前主流程重点仍然是：
  - 纸盘稳定性观察
  - 切盘放行标准
  - 生产闭环补齐

## 已验证结果

- `python3 -m unittest tests.test_mt5_scripts`
  - `48 tests`
  - `OK`
- `python3 -m unittest tests.test_promotion_gate`
  - `10 tests`
  - `OK`
- `python3 -m unittest tests.test_cli_promotion_gate`
  - `4 tests`
  - `OK`
- `python3 -m unittest tests.test_promotion_gate tests.test_cli_promotion_gate tests.test_mt5_scripts tests.test_config_schema`
  - `63 tests`
  - `OK`
- `git diff --check`
  - 已通过

## 下次继续优先做什么

1. 把本地这轮 `promotion-gate` 修复同步到 VPS，然后重跑：
  - `scripts/mt5_pullback_sell_v4_candidate_promotion_gate.ps1`
  - 目标是确认当前剩余失败项只剩真实执行闭环证据，而不是时间戳 / 指标抽取 / 路径回退问题
2. 如果严格 gate 仍只卡在 execution audit：
  - 优先等待纸盘出现真实执行尝试 / 同步记录
  - 不建议为了“看起来 ready”去伪造闭环证据
3. 继续补生产闭环：
  - 订单状态回传
  - 持仓同步
  - 执行异常归档
4. 在满足条件前，不主动停掉当前默认 `v4` 线上任务

## 当前阻塞

- VPS 远端同步暂时卡在管理通道：
  - `2026-04-01` 已确认可用 `expect + SSH` 方式进入 VPS 并同步关键文件
  - WinRM 5985/5986 端口虽然可达，但当前请求从本机仍超时，尚未形成可复用的远程执行链路
- 从本机访问：
  - `http://38.60.197.97/health`
    - 返回正常
  - `http://38.60.197.97:8765/health`
    - 当前外部请求仍超时
    - 但 VPS 本机 `127.0.0.1:8765/health` 已返回 `200`
    - 说明更像是公网放行 / 宿主机入站规则问题，不是候选监控服务本身异常
- `2026-04-01` 当前严格候选 gate 已缩窄到只剩 4 个失败项：
  - `current_execution_audit_execution_chain_visible`
  - `current_execution_audit_reconcile_chain_visible`
  - `candidate_execution_audit_execution_chain_visible`
  - `candidate_execution_audit_reconcile_chain_visible`
- 这 4 个失败项都来自同一个现实约束：
  - 当前两条纸盘都还没有真实 `execution_attempt / execution_sync / reconcile_sync` 记录
  - 这是业务真实性要求，不是兼容性 bug

## 当前不建议做

1. 继续往更深参数下探
2. 为 `0.26` 再复制一套新脚本
3. 直接覆盖当前线上 `v4` 配置
4. 把长样本研究重新放回 VPS
