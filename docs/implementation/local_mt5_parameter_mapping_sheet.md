# 本地 MT5 观察项与项目配置映射表

## 使用方式

你在 MT5 终端里观察到一个信息，就按下面的表回填到项目配置。

优先更新：

- `.env.mt5.local`
- `configs/mt5_paper.yaml`

确认稳定后，再决定是否同步到：

- `configs/mt5_prod.yaml`

---

## 1. 账户与服务器

### 终端里看什么

- 登录账号
- 服务器名
- 账户类型：`demo / live`

### 回填到哪里

- `XAUUSD_AI_MT5_LOGIN`
- `XAUUSD_AI_MT5_SERVER`
- `XAUUSD_AI_ENV`

### 如何判断

- 如果当前只是联调，先保持 `XAUUSD_AI_ENV=paper`
- 只有在连续稳定后，再切 `prod`

---

## 2. 终端路径

### 终端里看什么

- MT5 应用实际启动路径

### 回填到哪里

- `XAUUSD_AI_MT5_PATH`

### 如何判断

- 路径必须是你后续执行宿主机也能使用的真实路径

---

## 3. 品种名

### 终端里看什么

- `Market Watch` 中实际显示的黄金品种名

常见情况：

- `XAUUSD`
- `XAUUSD.`
- `XAUUSDm`
- `GOLD`

### 回填到哪里

- `XAUUSD_AI_MT5_SYMBOL`
- `market_data.mt5.symbol`
- `execution.mt5.symbol`

### 如何判断

- 一定不要想当然写 `XAUUSD`
- 必须以券商真实品种名为准

---

## 4. 点位精度

### 终端里看什么

- 价格小数位数
- 一跳最小变动单位

### 回填到哪里

当前仓库还没有单独配置这个字段，但你需要把它记录在联调报告里。

现在也可以通过环境变量覆盖：

- `XAUUSD_AI_RISK_CONTRACT_SIZE`

### 如何判断

- 如果点位精度与预期不一致，后续要调整止损距离和滑点容忍

---

## 5. 最小手数 / 手数步长

### 终端里看什么

- 最小下单手数
- 手数步长
- 最大手数

### 回填到哪里

当前仓库还没有单独建这组配置字段，先记入联调报告。

### 如何判断

- 如果系统算出的仓位经常低于最小手数，后面需要补“最小手数归整”逻辑

---

## 6. 止损止盈最小距离

### 终端里看什么

- 下单面板或品种规范中的最小止损 / 止盈距离

### 回填到哪里

当前仓库还没有单独配置这个字段，先记入联调报告。

### 如何判断

- 如果券商限制太大，当前策略里的结构止损可能会被拒
- 后续需要把最小止损距离纳入执行前检查

---

## 7. 点差

### 终端里看什么

- 常规时段点差
- 欧盘 / 美盘时段点差
- 新闻时段点差

### 回填到哪里

- `risk.max_spread_ratio`
- `state_thresholds.spread_ratio_max`
- `volatility_monitor.spread_ratio_trigger`
- `XAUUSD_AI_RISK_MAX_SPREAD_RATIO`
- `XAUUSD_AI_STATE_SPREAD_RATIO_MAX`
- `XAUUSD_AI_VOLATILITY_SPREAD_RATIO_TRIGGER`

### 如何判断

如果你观察到：

- 正常时段点差很低：当前阈值可保守保持不动
- 活跃时段偶尔放大：保持 `paper` 阶段先观测
- 新闻时段明显扩张：后续要优先依赖高波动预警与风控拦截

默认参考：

- `mt5_paper.yaml`
  - `risk.max_spread_ratio = 1.40`
  - `state_thresholds.spread_ratio_max = 1.50`
  - `volatility_monitor.spread_ratio_trigger = 1.20`
- `mt5_prod.yaml`
  - `risk.max_spread_ratio = 1.35`
  - `state_thresholds.spread_ratio_max = 1.45`
  - `volatility_monitor.spread_ratio_trigger = 1.18`

---

## 8. 滑点

### 终端里看什么

- 手工小单的实际成交价与点击价的差值

### 回填到哪里

- `execution.mt5.deviation`
- `XAUUSD_AI_MT5_DEVIATION`

### 如何判断

- 如果手工小单很少滑点，可保持当前值
- 如果经常被拒单或成交偏移明显，需要适当调大 `deviation`

当前默认：

- `mt5_paper.yaml`：`deviation = 30`
- `mt5_prod.yaml`：`deviation = 30`

---

## 8.1 合约量

### 终端里看什么

- 品种规格中的 `合约量`

### 回填到哪里

- `risk.contract_size`
- `XAUUSD_AI_RISK_CONTRACT_SIZE`

### 如何判断

- 对当前 `XAUUSD`，你本地观察值已经确认 `合约量 = 100`
- 这个值如果写错，会直接导致风险金额和下单手数被放大或缩小
- 当前仓库默认已按 `100` 处理，`preflight` 也会校验配置值是否与券商规格一致

---

## 9. 交易权限

### 终端里看什么

- 账户是否允许交易
- 自动交易是否被禁用
- 是否有品种层面的交易限制

### 回填到哪里

这部分主要影响你是否可以进入下一阶段，不需要直接写进 YAML。

### 如何判断

- 如果手工单都下不了，就不要继续考虑 `paper/prod`

---

## 10. 交易时段

### 终端里看什么

- 品种交易时段
- 是否有日切或短暂停牌

### 回填到哪里

当前仓库还没有单独做交易时段配置，先记入联调报告。

### 如何判断

- 如果存在固定不可交易时段，后续要补交易时段过滤器

---

## 11. 建议你先填的最小参数集

先把以下字段填对，就能显著降低后面联调成本：

- `XAUUSD_AI_MT5_LOGIN`
- `XAUUSD_AI_MT5_PASSWORD`
- `XAUUSD_AI_MT5_SERVER`
- `XAUUSD_AI_MT5_PATH`
- `XAUUSD_AI_MT5_SYMBOL`
- `execution.mt5.deviation`
- `risk.max_spread_ratio`

---

## 12. 当前阶段怎么用这张表

建议顺序：

1. 先跑 `bash scripts/local_mt5_smoke.sh`
2. 打开 MT5 终端做观察
3. 用这张表把终端观察项映射到配置
4. 记录到 `local_mt5_debug_report_template.md`
5. 等执行宿主机就绪后，再把这些结果迁移到 `paper/prod`
