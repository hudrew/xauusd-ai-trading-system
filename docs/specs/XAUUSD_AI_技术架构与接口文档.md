# XAUUSD AI 程序化交易系统：技术架构与接口文档

## 1. 模块划分

系统当前建议并已经开始按以下模块落地：

1. MarketDataService
2. AccountStateService
3. PreflightRunner
4. LiveTradingRunner
5. FeatureEngine / FeatureCalculator
6. MarketStateClassifier
7. VolatilityMonitor
8. AlertNotifier
9. StrategyRouter / StrategyEngine
10. RiskManager
11. ExecutionService / ExecutionEngine
12. BacktestEngine
13. AuditRepository / ReportEngine
14. ConfigManager
15. Logger / Monitor

---

## 2. 数据流

实时行情 / K 线 → `MarketDataService` → `LiveTradingRunner` → 特征计算 → 市场状态分类 → 策略生成候选信号 → 路由准入 → 风控审核 → 执行下单 → 审计落库 / 告警 / 日志

账户权益 / 持仓数 / 交易可用状态 → `AccountStateService` → `LiveTradingRunner`

实时行情 / K 线 → 特征计算 → 高波动预警评分 → 预警等级输出 → 提醒通知 / 风控联动

---

## 3. 模块职责

### 3.1 MarketDataService
职责：根据配置对接 `MT5` 或 `cTrader`，输出统一的 quote / bars 数据

### 3.2 LiveTradingRunner
职责：拉取最近 bars、合并最新 bid/ask、计算特征、构建 `MarketSnapshot`、驱动运行时处理

### 3.3 AccountStateService
职责：同步真实账户权益、持仓数、交易可用状态，并维护日内基线和峰值给风控使用

### 3.4 PreflightRunner
职责：在进入 paper / live 前检查平台初始化、账号状态、symbol 可用性、最新 tick、最近 bars、交易权限

### 3.5 FeatureEngine / FeatureCalculator
职责：校验特征是否齐备，并计算 ATR、EMA、VWAP、假突破等共享特征

### 3.6 MarketStateClassifier
职责：输出状态标签、置信度、原因码

### 3.7 VolatilityMonitor
职责：输出未来多个时间窗的高波动风险评分、预警等级、原因码

### 3.8 AlertNotifier
职责：把高波动预警发送到企业微信 / Telegram / 邮件 / Webhook 等通道

### 3.9 StrategyEngine / StrategyRouter
职责：根据状态调用对应策略，输出候选信号，并结合 `routing` 配置做策略与时段准入

### 3.10 RiskManager
职责：在订单提交前做统一否决或放行

### 3.11 ExecutionEngine
职责：提交订单、修改止损止盈、同步订单状态；当前通过统一 `ExecutionService` 路由到 `MT5` 或 `cTrader`

### 3.12 BacktestEngine
职责：基于统一逻辑跑历史验证

### 3.13 AuditRepository / ReportEngine
职责：沉淀审计记录、输出收益、回撤、状态表现、时段表现等报表

---

## 4. 建议接口

### 4.1 市场状态输出
```json
{
  "state_label": "trend_breakout",
  "confidence_score": 0.82,
  "reason_codes": ["EMA_UP", "ATR_EXPAND", "BREAK_HIGH"],
  "blocked_by_risk": false
}
```

### 4.2 策略信号输出
```json
{
  "strategy_name": "breakout",
  "side": "buy",
  "entry_type": "market",
  "entry_price": 3050.2,
  "stop_loss": 3048.8,
  "take_profit": 3053.0,
  "signal_reason": ["BREAK_CONFIRMED"]
}
```

### 4.3 风控审核输出
```json
{
  "allowed": true,
  "risk_reason": [],
  "position_size": 0.12
}
```

### 4.4 高波动预警输出
```json
{
  "warning_level": "warning",
  "forecast_horizon_minutes": 15,
  "risk_score": 0.78,
  "reason_codes": ["ATR_EXPAND", "SPREAD_EXPAND", "NEWS_NEAR"],
  "suggested_action": "reduce_risk"
}
```

---

## 5. 设计原则

- 策略和执行解耦
- 候选信号与准入策略解耦
- 行情和执行解耦
- 风控独立且有最高优先级
- 日志字段完整可追溯
- 模块尽量无状态或弱状态
- 参数配置化
- 预警模块独立于策略模块，既可做提醒，也可反向约束风控
- 研究 / 回测 / 生产三条链共用同一套业务决策内核

---

## 6. 当前实现状态说明

已落地：

- `Backtrader` 作为研究 / 回放适配层
- `LiveTradingRunner` 作为实时轮询入口
- `AccountStateService` 作为真实账户状态同步入口
- `PreflightRunner` 作为上线前体检入口
- `MT5` 行情与执行适配器
- `cTrader` 配置校验、订阅请求构建、执行适配器接口
- `SQLiteAuditRepository` 审计落库
- `AlertNotifier` Webhook / stdout 通知
- `routing` 统一准入层，支持：
  - 按时段过滤候选信号
  - 按策略开关过滤候选信号
  - 回测 / replay / live 共用同一套口径
  - 环境变量快速覆盖

当前仍需补完：

- `cTrader` 完整异步会话层
- 事件日历真实接入
- 订单回报与持仓状态同步
- 报表聚合与验收看板

---

## 7. 一句话总结

技术架构的核心不是堆功能，而是让每个模块边界清晰、能单独测试、能替换、能复盘。
