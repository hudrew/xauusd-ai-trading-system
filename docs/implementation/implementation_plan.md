# 实施路线图

## 当前阶段

当前仓库已经完成的是“系统骨架”和“文档入库”，不是最终可实盘版本。

已完成：

- 需求文档纳入仓库
- 开源底座可行性分析
- 配置文件样例
- 多周期特征计算主链
- 市场状态分类主链
- 策略路由主链
- 风控审核主链
- cTrader / Backtrader 适配层占位
- cTrader / MT5 双平台执行抽象
- 生产运行时骨架
- 审计落库与结构化日志骨架
- 高波动预警与通知主链
- `PullbackStrategy` 已接入主流程
- `HistoricalReplayRunner` 结构化验收报告已接入
- `Backtrader` 第一版成交收益验收报告已接入
- `preflight / host-check / replay / backtest / smoke` CLI 已可直接运行
- `reports list / latest / trend` 研究归档查询入口已可直接运行
- `deploy-gate` 统一上线门禁入口已可直接运行

## 当前延期事项

当前有一条已明确延期、但后续一定会恢复的任务：

- `MT5` 执行宿主机采购与部署

延期记录与恢复清单见：

- `docs/implementation/mt5_host_procurement_backlog.md`

这份文档已经记录了：

- 已试过的云厂商 / VPS 路线
- 支付方式限制
- `TradeMaxGlobal-Live` 的已知线索
- 后续恢复时的最小验收标准

## 推荐开发顺序

### 阶段 1：把规则进一步量化

目标：

- 把文档里的阈值彻底参数化
- 明确每个特征的单位和归一化方式
- 确定 `breakout_distance`、`pullback_depth`、`range_position` 等字段的计算公式

交付物：

- 特征口径补充文档
- 指标计算模块
- 参数版本记录

### 阶段 2：历史数据和回测跑通

目标：

- 接入 XAUUSD 历史 M1 数据
- 生成 M5/M15/H1 聚合数据
- 用 Backtrader 或独立回放器跑出第一版回测

交付物：

- 数据加载器
- 时间框架聚合器
- 成本模型
- 回测报告

当前进度补充：

- 特征层已经支持基于 `M1` 历史序列派生 `M5 / M15 / H1` 多周期特征
- 状态分类与趋势型风控已经开始消费 `M15 / H1` 对齐信息
- `HistoricalReplayRunner` 已能输出状态、策略、风险阻断、高波动分布等结构化验收报告
- `run_backtrader_csv` 已能输出收益、回撤、胜率、持仓时长、成本影响等第一版成交结果
- `Backtrader` 回测结果已能按月份、策略、市场状态和交易时段拆分成交表现
- `sample-split` 与 `walk-forward` 验收链已可直接运行
- `acceptance` 自动验收判定层已可直接运行
- `acceptance` 结果默认会归档到项目内
- 归档结果已经可以通过 CLI 直接查询最近结果、失败项和通过率趋势
- `deploy-gate` 已能把研究验收与 live 前检查串成统一放行报告
- 但正式历史数据准备、样本切片规则优化和门槛调优仍需继续完善

### 阶段 3：模拟盘联调

目标：

- 接入 cTrader demo
- 把风控和下单映射到真实接口
- 校验日志、状态同步和异常恢复

并行要求：
- cTrader 和 MT5 共享同一套业务决策内核
- 仅在执行与账户接入层按平台分流

交付物：

- OpenApiPy 执行适配器
- MetaTrader5 执行适配器
- 订单同步器
- 日志和告警链路

### 阶段 4：策略扩展和 AI 增强

目标：

- 增强 `pullback_continuation`
- 补全报表
- 再考虑引入轻量 AI 分类器，替代部分规则阈值判断

交付物：

- 第二阶段策略模块
- 状态分类评估脚本
- walk-forward 结果

## 当前代码边界

目前代码中已经实现的是“业务决策内核”，包括：

- `TradingSystem`
- `RuleBasedMarketStateClassifier`
- `StrategyRouter`
- `RiskManager`
- `BreakoutStrategy`
- `PullbackStrategy`
- `MeanReversionStrategy`
- `HistoricalReplayRunner`
- `LiveTradingRunner`
- `PreflightRunner`

仍未实现的关键部分：

- 月度 / 时段 / 状态切片收益报表
- 更细的验收规则与门槛分级
- 更细的延迟与成交偏差成本模型
- 成交回报与订单同步闭环
- cTrader 持久连接与历史 bar 主链
- 更完整的生产级数据库与消息队列适配

当前新增的一个正向变化：

- 虽然还没有上完整数据库报表层，但研究验收结果已经不再是“一次性输出”
- 现在已经有项目内归档和查询入口，可以作为后续上线门禁和运维排查的最小可用台账
- 现在还新增了统一部署门禁层，可以把“研究达标”和“live 环境就绪”放进同一份判断里

## 后续开发建议

优先做以下三件事：

1. 先准备一份干净的 XAUUSD M1 历史数据
2. 用 `replay / backtest / sample-split / walk-forward / acceptance` 报告先把决策链、收益链和泛化能力验收一遍
3. 再补更细的门槛调优和自动化集成

只要这三件事完成，这个仓库就会从“可运行决策系统”进入“可验收益质量的研究系统”。
