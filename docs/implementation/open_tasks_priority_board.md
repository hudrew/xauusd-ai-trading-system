# 当前未完成任务优先级表

更新时间：

- `2026-03-31`

适用范围：

- 当前仓库主线
- 当前已落地的 `MT5 paper pullback sell v3` 候选线

这份文档只回答三个问题：

1. 现在还有哪些任务没完成
2. 哪些是本周必须继续做的
3. 哪些现在不要急着做

## 当前判断

当前项目已经不是“系统没搭起来”，而是进入了：

- MT5 纸盘链路已打通
- 监控与值守入口已打通
- 研究验收链已打通
- `150000` 和 `300000` 根 `M1` 的安全 probe 验收都已在本地研究机通过
- 当前不再是“最新研究门禁没过”
- 现在真正要继续收口的是：
  - 纸盘连续运行稳定性
  - 更长样本下的稳健性
  - 生产执行闭环

## 本周必须做

### 1. 持续观察 pullback sell v3 纸盘运行

目标：

- 确认纸盘主任务持续运行
- 确认监控页持续刷新
- 确认高波动预警、执行尝试、审计库写入没有中断

当前状态：

- 已在 VPS 上恢复
- 主任务 `Running`
- 监控任务 `Running`
- 监控页公网入口可访问

完成标准：

- 连续多个交易时段观察无中断
- `daily_check` 持续返回正常
- 页面与日志时间持续更新

推荐入口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

建议同时归档：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check_archive.ps1 .env.mt5.local
```

### 2. 继续扩展样本，但放到研究机跑，不要压 VPS

目标：

- 把当前研究结论从短样本推进到更长样本
- 重新确认 `pullback sell v3` 是否仍具备候选价值

为什么必须做：

- 现在系统链路已经通了
- 当前 branch gate 最新报告已经是 `ready = true`
- 当前 `probe` 报告目录里的 `150000` 和 `300000` 根 `M1` 本地复验都已经是 `ready = true`
- 但“更长样本是否还能站住”还没有验证完
- 不先复验更长样本，不能进入正式生产决策

完成标准：

- 新导出一份更长的 `XAUUSD M1` 历史
- 对候选配置重新跑：
  - `acceptance`
  - `sample-split`
  - `walk-forward`
- 形成新的归档报告
- 明确后续研究入口固定在本地研究机或独立研究宿主机，而不是当前 Windows VPS

重点看：

- `total_net_pnl`
- `out_of_sample_net_pnl`
- `profit_factor`
- `walk_forward_positive_window_rate`
- `session_profit_concentration`

当前额外注意：

- 这条“宿主机历史深度不够”的 blocker 在 `2026-03-31` 已被解除
- 当天先用 `probe` 看到旧限制：
  - `bars_available = 100000`
  - `oldest_timestamp = 2025-12-15T18:54:00+00:00`
  - `newest_timestamp = 2026-03-30T19:39:00+00:00`
  - `stopped_reason = (-1, 'Terminal: Call failed')`
- 随后已在 VPS 上把 MT5 数据目录 `config\\common.ini` 中的 `[Charts] MaxBars` 从 `100000` 提升到 `500000`
- 调整后再次实测：
  - `probe --max-bars 300000` 已达到上限停止
  - `bars_available >= 300000`
  - `oldest_timestamp = 2025-05-23T10:04:00+00:00`
  - `newest_timestamp = 2026-03-30T19:49:00+00:00`
  - `stopped_reason = probe_limit_reached max_bars=300000`
- `150000` 根 `M1` 导出已成功
- 随后已在本地研究机对这份 `150000` 样本跑通安全 probe 验收，当前最新结果：
  - `ready = true`
  - `passed_checks = 10/10`
  - `total_net_pnl = 1.39`
  - `profit_factor = 2.4762`
  - `out_of_sample_net_pnl = 1.09`
  - `walk_forward_positive_window_rate = 0.9931`
  - `session_profit_concentration = 1.0`
- 随后又继续完成了 `300000` 根 `M1` 的本地安全 probe 验收，结果仍然通过：
  - `ready = true`
  - `passed_checks = 10/10`
  - `total_net_pnl = 1.39`
  - `profit_factor = 2.4762`
  - `out_of_sample_net_pnl = 1.00`
  - `out_of_sample_profit_factor = 1.7565`
  - `walk_forward_positive_window_rate = 0.9966`
  - `session_profit_concentration = 1.0`
- 这说明当前门禁没有被更长样本直接打掉
- 但也说明另一个问题：
  - 从 `150000` 扩到 `300000` 后，实际成交仍只有 `7` 笔
  - 总收益没有继续放大
  - 收益仍全部来自 `us`
- 当前需要继续看的，不再是“能不能导出更长历史”，而是“更长样本验收结果是否还能站住”
- 复验时优先走 `probe` 报告目录，避免覆盖当前纸盘正在使用的正式 latest
- 当前这台 VPS 不适合长研究任务：
  - `1` 个物理核心
  - `2` 个逻辑处理器
  - 约 `4.29 GB` 内存
  - 长验收时可用内存一度只剩约 `244 MB`
  - Python 回测进程工作集约 `1.59 GB`
- 结论：
  - VPS 只用于 `MT5 执行 / 纸盘 / 监控 / 短检查`
  - 长 `acceptance / walk-forward / sample-split` 固定放到本地研究机或单独研究宿主机
- 当前可直接使用：
  - `scripts/research_pullback_sell_v3_refresh_probe.sh`
  - `scripts/research_pullback_sell_v3_refresh_probe.ps1`
  - `scripts/mt5_probe_history_capacity.sh`
  - `scripts/mt5_probe_history_capacity.ps1`

### 3. 继续收缩当前候选策略，而不是放宽门槛

目标：

- 先解决真实研究问题
- 不靠修改门禁掩盖策略不稳定

当前结论：

- `pullback` 明显优于 `breakout`
- `asia` 时段明显拖累
- 正收益仍主要集中在 `us`
- 最新 `150000` 样本里实际成交仍全部来自 `us`
- 最新 `300000` 样本里实际成交仍全部来自 `us`
- 从 `150000` 扩到 `300000` 后，成交笔数仍然只有 `7`
- `session_profit_concentration = 1.0` 只是压线通过，不代表时段分散已经足够好

完成标准：

- 形成下一轮策略收缩动作
- 至少明确下列其中 1 到 2 项：
  - 是否继续关闭 `breakout`
  - 是否继续限制 `asia`
  - 是否增加“位置过偏 + 波动过高”的统一过滤
  - 是否继续加严 `pullback` 触发条件

## 下周再做

### 4. 补纸盘运行报表和复盘看板

目标：

- 不只看任务是否在跑
- 还要能更容易看纸盘期间的真实表现

当前进度：

- 基础版纸盘复盘摘要已经接进现有监控页
- 现在页面里已经能直接看到：
  - `Paper Window`
  - `Risk Block Reasons`
  - `Risk Advisories`
  - `Execution Outcome Mix`
  - `Execution Error Pressure`

建议补的内容：

- 纸盘期间决策数量趋势
- 高波动预警统计
- 风控拦截分布
- 执行尝试结果汇总
- 分时段表现汇总

当前剩余的不是“有没有基础看板”，而是“要不要继续把趋势图和归档统计做得更完整”。

### 5. 补订单状态回传与持仓同步闭环

目标：

- 让执行层更接近正式生产要求

当前进度：

- 首版 `MT5 execution sync` 已接入主执行链
- 现在下单后会额外回读一次 broker 侧：
  - `open orders`
  - `open positions`
- 现在 live 轮询每一轮还会再补一次 broker reconcile：
  - 持续回读 `open orders / open positions`
  - 持续回读最近窗口内的 `history_orders / history_deals`
  - 生命周期状态变化时才会新增写入，避免每轮刷重复 sync
- 同步结果会单独落库到：
  - `execution_syncs`
- 监控页里已经能直接看到：
  - `Execution Sync Status`
  - `Recent Execution Syncs`
- 最新补充：
  - 已开始归档 `requested_price / observed_price`
  - 已开始跟踪 `price_offset / adverse_slippage_points`
  - 监控页已新增 `Execution Price Drift`
  - 已开始补 `history_orders / history_deals` 首版回读
  - 已开始补 `submission / reconcile` 来源区分
  - 已开始补 `position_closed_tp / position_closed_sl / position_closed_manual / position_closed_expert` 生命周期状态

当前还差：

- 用真实纸盘持续验证 broker close reason 归因是否稳定
- 按策略 comment / magic 继续收缩更细的持仓归档字段
- 把同一套生命周期闭环补到后续 `cTrader` 通道

为什么放到下周：

- 当前纸盘主链已经可观察
- 但还没经历足够长时间的纸盘观察，也还没完成更长样本复验，先不急着把生产闭环做到最重

### 6. 补真实事件日历接入

目标：

- 让高波动预警与风控逻辑更接近真实新闻时段

当前状态：

- 高波动预警模块已经存在
- 但事件日历真实接入还没补完

这块适合在研究收缩方向基本稳定后再做。

## 暂缓

### 7. cTrader 第二生产通道

当前判断：

- 不要和 MT5 纸盘链路并行抢时间
- cTrader 目前还缺完整异步会话层
- 还缺持久连接、重连、历史 bar 主链、账户状态同步

结论：

- 当前不应作为第一条上线通道
- 等 MT5 路线稳定后，再补第二执行通道

### 8. 正式生产宿主机定版

当前判断：

- 现在这台 VPS 已经足够继续测试与纸盘
- 但“正式长期生产宿主机”还没必要在本周强行收口

适合后移到：

- 研究结果通过
- 纸盘稳定一段时间
- 接近实盘切换前

### 9. 更完整的生产级数据库与消息队列

当前判断：

- 现在已有 SQLite 审计库和监控页
- 足够支撑当前纸盘和运维观察

结论：

- 当前不必先上更重的数据库和消息队列
- 等进入更正式的生产治理阶段再做

## 当前真正的 blocker

现在已经没有“平台没通”这种单点 blocker。

离正式生产还差的，主要是 3 件事：

- 纸盘连续运行观察时间还不够
- 更长样本虽然已经扩到 `300000` 并继续通过，但交易频次和时段分散度仍然偏窄
- 订单状态回传、持仓同步、成交偏差跟踪这些生产闭环还没补齐

这意味着：

- 现在不是“不能跑”
- 不是“平台没打通”
- 也不是“最新研究门禁还没过”
- 而是“还没积累到足够的稳定运行证据，不能直接推进到正式生产”

## 当前最推荐的推进顺序

1. 先继续跑纸盘，保证运行和监控稳定
2. 再在研究机导更长历史，重跑候选线研究验收
3. 根据结果继续收缩策略
4. 再补纸盘复盘看板和执行闭环
5. 最后再处理 cTrader 和正式生产宿主机

## 对你最有用的两个入口

日常巡检：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

页面或监控异常时恢复：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```
