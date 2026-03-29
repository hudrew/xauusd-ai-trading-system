# 本地 MT5 终端手工联调说明

## 适用场景

适用于当前这种情况：

- 你的本地机器已经装了 MT5 终端
- 但当前 Python 环境还不能直接跑 `MetaTrader5` 模块
- 你仍然希望先做一轮手工联调，确认交易账户、品种、点差和下单链路没有明显问题

这条路径的目标不是替代正式执行宿主机，而是先把终端层面的问题排干净。

## 这条路径能做什么

- 确认 MT5 终端能正常登录
- 确认 `XAUUSD` 可见且有实时行情
- 确认账户是否允许交易
- 确认手工小单能否正常成交
- 确认终端里的交易参数与项目配置是否一致

## 这条路径不能做什么

- 不能直接验证当前仓库的 `MT5 Python` 执行适配器
- 不能替代 `host-check`
- 不能替代 `preflight`
- 不能作为最终生产联调依据

## 最短手工联调流程

### 1. 终端登录

在 MT5 终端里确认：

- 已登录到正确的 demo 或 live 账户
- 连接状态正常
- `XAUUSD` 已加入 `Market Watch`

### 2. 行情检查

确认：

- `XAUUSD` 的 bid / ask 持续跳动
- 点差没有长期异常扩张
- 图表周期里能看到稳定的 `M1` K 线

建议记录：

- 常见时段点差范围
- 新闻前后点差变化
- 你准备交易的券商符号名是否真的是 `XAUUSD`

### 3. 交易权限检查

在终端层面确认：

- 账户允许交易
- 终端没有被券商限制下单
- 自动交易相关权限没有被禁用

如果 MT5 日志里出现：

- `trading has been disabled - disabled on server`

说明：

- 登录已经成功
- 行情同步也可能已经成功
- 但账户在服务器侧被禁止交易，当前不能继续做下单联调

这时候应该优先处理：

- 联系券商或后台确认账户权限
- 换一个允许交易的 demo / paper 账户
- 不要把这个问题误判成网络问题或 MT5 客户端故障

### 4. 手工小单检查

先在 demo 环境做一笔最小风险手工单，确认：

- 能正常开仓
- 能正常平仓
- 止损止盈能正常设置
- 手续费、滑点、点差表现是否符合预期

### 5. 参数对齐

把终端里确认过的信息对齐到项目配置：

- `XAUUSD_AI_MT5_SERVER`
- `XAUUSD_AI_MT5_PATH`
- `XAUUSD_AI_MT5_SYMBOL`
- `execution.mt5.deviation`
- `risk.max_spread_ratio`

### 6. 与项目决策联调

当前这台机器即使不能直接跑 MT5 Python，也可以先跑：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli smoke
PYTHONPATH=src ./.venv/bin/python examples/replay_csv.py /path/to/xauusd_m1.csv
```

这样你可以先确认：

- 策略信号生成逻辑
- 高波动预警输出
- 风控拦截是否符合预期

然后再拿执行宿主机去验证：

- `host-check`
- `preflight`
- `paper loop`

## 建议的职责划分

当前推荐这样用：

- 本地 MT5 终端：做手工观察与账户层面检查
- 当前 Mac 开发机：做研发、回放、文档、规则验证
- Windows 执行宿主机：做 MT5 Python 真实联调与生产运行

## 什么时候可以进入下一步

满足以下条件后，再切到执行宿主机联调：

- 本地 MT5 终端登录稳定
- `XAUUSD` 行情正常
- 手工小单没有权限或品种层面的异常
- 你已经确认券商侧的 symbol / spread / trade mode 没问题
- 日志里没有 `trading has been disabled - disabled on server`

然后按 [mt5_execution_host_runbook.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/mt5_execution_host_runbook.md) 继续。
