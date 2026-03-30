# 当前未完成任务优先级表

更新时间：

- `2026-03-30`

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
- 但策略研究结果还没有完全收口
- 因此当前最大 blocker 不是部署，而是研究结果

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

### 2. 再导更长的 MT5 历史并复跑研究验收

目标：

- 把当前研究结论从短样本推进到更长样本
- 重新确认 `pullback sell v3` 是否仍具备候选价值

为什么必须做：

- 现在系统链路已经通了
- 当前真实阻塞点是 `acceptance_report_ready = false`
- 不先复验更长样本，不能进入正式生产决策

完成标准：

- 新导出一份更长的 `XAUUSD M1` 历史
- 对候选配置重新跑：
  - `acceptance`
  - `sample-split`
  - `walk-forward`
- 形成新的归档报告

重点看：

- `total_net_pnl`
- `out_of_sample_net_pnl`
- `profit_factor`
- `walk_forward_positive_window_rate`
- `session_profit_concentration`

### 3. 继续收缩当前候选策略，而不是放宽门槛

目标：

- 先解决真实研究问题
- 不靠修改门禁掩盖策略不稳定

当前结论：

- `pullback` 明显优于 `breakout`
- `asia` 时段明显拖累
- 正收益仍主要集中在 `us`

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

建议补的内容：

- 纸盘期间决策数量趋势
- 高波动预警统计
- 风控拦截分布
- 执行尝试结果汇总
- 分时段表现汇总

这块重要，但不先于研究复验。

### 5. 补订单状态回传与持仓同步闭环

目标：

- 让执行层更接近正式生产要求

当前还差：

- 订单状态回传
- 持仓同步闭环
- 更细的成交偏差与滑点追踪

为什么放到下周：

- 当前纸盘主链已经可观察
- 但研究结果还没过关，先不急着把生产闭环做到最重

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

只有一个核心 blocker：

- 研究归档存在，但最新研究结果还没有稳定通过验收

这意味着：

- 现在不是“不能跑”
- 不是“平台没打通”
- 也不是“监控没做好”
- 而是“策略研究还没有足够稳，不能直接推进到正式生产”

## 当前最推荐的推进顺序

1. 先继续跑纸盘，保证运行和监控稳定
2. 再导更长历史，重跑候选线研究验收
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
