# XAUUSD AI 程序化交易系统：高波动预警模块设计文档

## 1. 文档目标

本文件用于定义一个独立于策略模块的高波动预警能力，用来提前识别 XAUUSD 未来短时间内进入高波动状态的风险，并给出统一提醒。

注意：
- 目标不是精确预测未来价格方向
- 目标是预测未来一段时间是否更可能进入高波动状态
- 该模块既可以独立提醒，也可以联动 RiskManager

---

## 2. 业务定位

高波动预警模块的核心价值：

1. 提前识别即将放大的波动风险
2. 在重大事件或结构突破前发出提醒
3. 为交易系统提供“是否降风险 / 是否禁开仓”的辅助依据
4. 为人工盯盘提供更早的关注信号

---

## 3. 预警目标定义

建议初版先做三个预测窗口：

1. 未来 5 分钟是否进入高波动
2. 未来 15 分钟是否进入高波动
3. 未来 30 分钟是否进入高波动

高波动建议定义为以下任一成立：
- 未来 N 分钟 realized volatility 超过过去一段时间基线阈值
- 未来 N 分钟 ATR 扩张达到阈值
- 未来 N 分钟价格振幅超过预设比例

说明：
- 初版可以只选一个统一标签定义，避免多标准并存
- 推荐优先采用 “未来 N 分钟 realized volatility 超过 rolling baseline 的倍数”

---

## 4. 输入数据

### 4.1 行情输入
- Tick 或 M1 行情
- bid / ask / spread
- open / high / low / close
- volume（若可得）

### 4.2 衍生特征输入
- ATR_M1_14
- ATR_M5_14
- realized_volatility
- atr_expansion_ratio
- spread_ratio
- spread_zscore
- wick_ratio_up
- wick_ratio_down
- breakout_distance
- range_width_n
- tick_speed

### 4.3 环境输入
- session_tag
- weekday
- hour_bucket
- news_flag
- news_level
- minutes_to_event
- minutes_from_event

---

## 5. 初版实现方案

初版建议采用“规则评分 + 统计模型增强”的双层方案。

### 5.1 第一层：规则评分

根据以下信号给出基础分：
- ATR 突然扩张
- spread 突然扩张
- 接近高影响新闻事件
- 区间压缩后临近突破
- 突破后价格未回落并伴随 tick_speed 上升

### 5.2 第二层：统计增强

在规则评分基础上，可加入：
- rolling realized volatility baseline
- GARCH / EGARCH 等条件波动率预测
- 在线漂移检测或 regime shift 检测

初版原则：
- 先让规则版跑通
- 再增加统计模型
- 不建议一开始就做黑盒深度学习

---

## 6. 预警输出

建议统一输出结构：

```json
{
  "warning_level": "warning",
  "forecast_horizon_minutes": 15,
  "risk_score": 0.78,
  "reason_codes": ["ATR_EXPAND", "NEWS_NEAR", "BREAKOUT_PRESSURE"],
  "suggested_action": "reduce_risk"
}
```

字段说明：
- `warning_level`：`info / warning / critical`
- `forecast_horizon_minutes`：预测窗口
- `risk_score`：0 到 1 的风险评分
- `reason_codes`：触发原因码
- `suggested_action`：建议动作，例如 `observe` / `reduce_risk` / `block_new_trade`

---

## 7. 与主交易系统的关系

### 7.1 独立提醒
可单独用于人工盯盘和消息提醒。

### 7.2 风控联动
当预警达到高等级时：
- 降低允许仓位
- 收紧点差阈值
- 暂停新开仓
- 仅允许已有仓位保护性处理

### 7.3 策略联动
预警模块不直接替代策略，但可作为上下文输入：
- 趋势突破策略可在高波动启动前提高关注度
- 区间回归策略在高波动预警下应更谨慎或直接禁做

---

## 8. 验收建议

至少评估以下内容：
- 预警命中率
- 误报率
- 提前量是否足够
- 不同时间窗下表现
- 不同时段下表现
- 不同事件场景下表现

初版不建议用“看起来很准”做验收，必须做样本内 / 样本外验证。

---

## 9. 开发顺序建议

1. 先定义高波动标签
2. 再确定特征口径
3. 做规则评分版
4. 做历史回放验证
5. 接入实时提醒
6. 再考虑统计模型增强

---

## 10. 一句话总结

高波动预警模块不是为了猜价格方向，
而是为了更早发现“市场即将变得危险或值得重点关注”的时刻。

