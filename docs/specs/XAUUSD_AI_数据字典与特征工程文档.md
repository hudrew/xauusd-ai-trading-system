# XAUUSD AI 程序化交易系统：数据字典与特征工程文档

## 1. 文档目标

定义系统输入数据、衍生特征、计算口径与更新频率，确保开发、回测、模拟盘、实盘口径一致。

---

## 2. 原始输入数据

### 2.1 行情数据
- symbol
- timestamp
- bid
- ask
- spread
- volume（若可得）
- open/high/low/close（M1/M5）

### 2.2 时段数据
- session_tag（亚洲 / 欧洲 / 美国 / 交叉盘）
- weekday
- hour_bucket

### 2.3 事件数据
- news_flag
- news_level
- minutes_to_event
- minutes_from_event
- event_category
- event_source

---

## 3. 核心衍生特征

### 3.1 波动类
- ATR_M1_14
- ATR_M5_14
- realized_volatility
- range_width_n
- atr_expansion_ratio
- realized_volatility_m5
- realized_volatility_h1
- spread_zscore
- tick_speed
- candle_body_ratio

### 3.2 趋势类
- EMA20_M5
- EMA60_M5
- ema_slope_20
- ema_slope_60
- price_distance_to_ema20

### 3.3 结构类
- recent_high_n
- recent_low_n
- breakout_distance
- pullback_depth
- false_break_count
- wick_ratio_up
- wick_ratio_down

### 3.4 均值回归类
- VWAP
- vwap_deviation
- boll_mid
- boll_upper
- boll_lower
- boundary_touch_count

### 3.5 交易条件类
- spread_ratio
- liquidity_flag
- trade_block_flag
- session_volatility_baseline
- event_proximity_score

### 3.6 预警输出类
- volatility_risk_score
- volatility_warning_level
- volatility_forecast_horizon
- volatility_reason_codes
- suggested_risk_action

---

## 4. 计算原则

1. 所有时间字段统一时区
2. 所有特征必须定义窗口长度
3. 回测与实盘使用相同计算口径
4. 不允许未来函数
5. 特征要支持落盘，便于复盘
6. 预警标签必须明确预测窗口，例如未来 5 / 15 / 30 分钟
7. 预警评分必须和真实未来波动结果可对账

---

## 5. 最低落地要求

每次状态分类时，至少保留：
- 原始价格快照
- 当前点差
- 核心特征值
- 当前市场状态标签
- 风控阻断原因
- 当前高波动预警等级
- 预警原因码
- 预警对应时间窗

---

## 6. 一句话总结

如果特征定义不清，后面的 AI、策略、回测都会失真。

所以特征工程文档本质上是整个系统的“数据地基”。
