# XAUUSD AI Quant Trading System

基于你提供的需求文档，这个仓库已经从“文档骨架”推进到“可运行的 MVP 交易系统主干”。

当前目标很明确：

- 快速上线
- 保持可扩展
- 生产方向优先，不靠伪代码验证
- 研究、回测、生产三条链路共用同一套业务内核

## 当前结论

- `Backtrader` 继续作为研究 / 回测底座
- 生产运行时使用仓库内自研 `TradingRuntimeService + LiveTradingRunner`
- 首发建议优先走 `MT5`
- `cTrader` 已经接入统一接口，但当前仍缺完整异步会话层，不建议作为第一条上线通道
- 高波动预警模块已经作为独立模块接入主流程，并能联动风控与通知

## 仓库里现在有什么

- `docs/specs/`：原始需求文档与补充设计文档
- `docs/analysis/`：开源底座、文档优化、上线建议
- `docs/implementation/`：系统主流程、落地步骤、关键节点
- `docs/implementation/china_user_host_provider_options.md`：面向中国用户的临时 Windows 宿主机选型建议
- `docs/implementation/azure_windows_temporary_host_quickstart.md`：没有 Windows 机器时，先用 Azure 临时搭 MT5 执行宿主机
- `docs/implementation/mt5_host_procurement_backlog.md`：宿主机采购延期记录，后续恢复时直接从这里继续
- `configs/mvp.yaml`：当前默认配置
- `src/xauusd_ai_system/`：核心业务、运行时、回测、执行、行情适配
- `examples/`：最小示例与历史回放入口
- `tests/`：基础单元测试

## 当前已经打通的主链

研究 / 回放链：

- `CSVMarketDataLoader`
- `FeatureCalculator`
- `HistoricalReplayRunner`
- `BacktraderAdapter`
- `run_backtrader_csv`

当前 `HistoricalReplayRunner` 已经能直接输出结构化回放验收报告，包括：

- `signals_generated / trades_allowed / blocked_trades`
- `signal_rate / trade_allow_rate / blocked_signal_rate`
- `states_by_label / states_by_session`
- `signals_by_strategy / signals_by_side`
- `blocked_reasons / risk_advisories`
- `volatility_levels / high_volatility_alerts`

这一步已经足够用来做“规则链是否健康、风控是否在生效、预警是否过密”的第一层验收。
但完整的收益率、胜率、Profit Factor、最大回撤，仍然要继续补成交闭环和成本模型。

当前 `run_backtrader_csv` / `xauusd_ai_system.cli backtest` 已经补上第一版成交收益验收报告，包括：

- `final_value / net_pnl / return_pct`
- `closed_trades / won_trades / lost_trades / win_rate`
- `gross_profit / gross_loss / profit_factor`
- `max_drawdown_pct / max_drawdown_amount`
- `average_hold_bars / average_hold_minutes`
- `commission_paid / orders_submitted / orders_rejected`
- 嵌套的 `decision_summary`
- 嵌套的 `trade_segmentation`

其中 `trade_segmentation` 当前已经会按以下维度拆分成交表现：

- `performance_by_close_month`
- `performance_by_strategy`
- `performance_by_state`
- `performance_by_session`
- `performance_by_side`

这意味着我们现在已经可以同时看“决策质量”和“成交结果”，并开始做成本敏感性验证。

当前还新增了两条正式研究验收链：

- `sample-split`
  用时间顺序切出 `in-sample / out-of-sample`
- `walk-forward`
  用滚动窗口持续验证样本外表现

这两条链会在测试窗口前自动补 `warmup bars`，让多周期特征在进入测试区间前先稳定下来。

当前还新增了自动验收结论层：

- `acceptance`
  会自动串起 `backtest + sample-split + walk-forward`
  然后按配置里的验收门槛输出统一的 `ready / failed_checks`

当前默认会检查的核心规则包括：

- 总体净收益是否为正
- 总体 Profit Factor 是否达标
- 总体最大回撤是否超限
- 样本外净收益是否为正
- 样本外 Profit Factor 是否达标
- 样本外最大回撤是否超限
- walk-forward 窗口数量是否足够
- walk-forward 正收益窗口占比是否达标
- 月度利润是否过度集中
- 时段利润是否过度集中

当前 `acceptance` 还会默认把完整报告归档到项目内：

- 时间戳归档文件
- `latest.json`
- `index.jsonl`

默认目录来自 `report_archive.base_dir`，当前是 `reports/research`。

当前还新增了归档查询入口：

- `xauusd_ai_system.cli reports list`
  看最近几次归档摘要
- `xauusd_ai_system.cli reports latest`
  看最近一次验收和失败项
- `xauusd_ai_system.cli reports trend`
  看最近一段时间的通过率和失败项分布

这一步的意义是：

- 不用手翻 `JSON`
- 可以直接做研究复盘
- 后面接部署门禁或轻量后台时可以直接复用

当前还新增了统一上线门禁入口：

- `xauusd_ai_system.cli deploy-gate`

它会把以下几类检查串起来：

- 最新研究验收归档是否存在
- 最新研究验收是否 ready
- 最新研究验收是否过旧
- live 模式下的 `host-check`
- live 模式下的 `preflight`

默认策略是：

- `dry_run=true` 时，重点卡研究验收，实时环境检查默认跳过
- `dry_run=false` 时，研究验收、宿主机检查、平台预检查一起进入放行判断

生产决策链：

- `MarketDataService`
- `AccountStateService`
- `LiveTradingRunner`
- `PreflightRunner`
- `TradingRuntimeService`
- `TradingSystem`
- `SQLiteAuditRepository`
- `AlertNotifier`
- `ExecutionService`

业务内核链：

- `FeatureEngine`
- `RuleBasedMarketStateClassifier`
- `VolatilityMonitor`
- `StrategyRouter`
- `RiskManager`
- `BreakoutStrategy`
- `PullbackStrategy`
- `MeanReversionStrategy`

当前 `FeatureCalculator` 已经能从 `M1` 数据衍生：

- `M5 / M15 / H1` 多周期 ATR / EMA 特征
- 布林带中轨 / 上下轨 / 位置
- `weekday / hour_bucket` 等时段特征
- `regime_conflict_score` 等跨周期冲突特征

当前 `RuleBasedMarketStateClassifier` 和 `RiskManager` 也已经开始消费这些多周期特征：

- `trend_breakout / pullback_continuation` 会检查 `M5 + M15 + H1` 的趋势同向性
- `range_mean_reversion` 会过滤掉高周期趋势过强的环境
- 趋势型信号在高周期仅部分对齐时会自动缩仓，完全反向时会被阻断

## 架构分层

- `Backtrader`：只负责研究、回测、历史回放
- `TradingSystem`：负责市场状态、策略、风控、高波动预警
- `TradingRuntimeService`：负责审计落库、日志、通知、执行编排
- `PreflightRunner`：负责上线前检查平台、账号、symbol、行情和交易权限是否可用
- `AccountStateService`：负责从交易平台同步权益、持仓数、交易可用状态，并维护日内基线与峰值
- `LiveTradingRunner`：负责实时拉取行情、账户状态、生成特征、构建快照、驱动运行时
- `ExecutionService`：统一路由到 MT5 或 cTrader 执行适配器
- `MarketDataService`：统一路由到 MT5 或 cTrader 行情适配器

## 当前生产建议

第一条上线链路建议：

1. 历史 CSV 回放
2. `MT5 + dry_run=true` 联调
3. MT5 模拟盘
4. MT5 小资金实盘
5. cTrader 补完异步会话层后再接入第二条生产链

这样做的原因很简单：

- `MT5` 官方 Python 集成更适合先把实时轮询链跑稳
- `cTrader Open API` 的 Python 侧更偏异步消息模型，生产接入要多一层连接、鉴权、订阅和回调治理
- 先把业务内核和运行时打稳，比同时硬冲两条生产链更安全

如果你当前没有 Windows 宿主机，可以直接看：

- `docs/implementation/china_user_host_provider_options.md`
- `docs/implementation/azure_windows_temporary_host_quickstart.md`
- `docs/implementation/mt5_execution_host_runbook.md`

## cTrader 当前状态

当前已具备：

- 执行适配器接口
- Spot 订阅请求构造
- SDK 配置校验
- 统一配置入口

当前还缺：

- 持久连接与重连
- 完整鉴权会话管理
- Spot 事件消费循环
- 历史 bar 拉取链路

所以现在的建议是：

- `MT5` 作为先上线通道
- `cTrader` 作为第二阶段并行补全

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[research]"
python3 -m unittest discover -s tests
```

运行静态 smoke：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli smoke
```

运行历史回放：

```bash
PYTHONPATH=src ./.venv/bin/python examples/replay_csv.py /path/to/xauusd_m1.csv
```

运行自动验收并归档：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli acceptance /path/to/xauusd_m1.csv
```

查看最近 5 次验收归档：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli reports list --limit 5
```

查看最近一次验收失败项：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli reports latest
```

查看最近 10 次验收趋势：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli reports trend --limit 10
```

运行统一上线门禁：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli deploy-gate --config configs/mt5_prod.yaml --strict
```

当前 `live-once / live-loop` 的启动规则也已经升级：

- `dry_run=false` 时，会先自动执行 `deploy-gate`
- `dry_run=true` 时，可以继续用 `--require-preflight` 只做平台预检查
- `dry_run=true` 时，如果希望也检查研究门禁，可以加 `--require-deploy-gate`

也可以直接走 CLI：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli replay /path/to/xauusd_m1.csv --config configs/mvp.yaml
```

运行 Backtrader 成交回测：

```bash
PYTHONPATH=src ./.venv/bin/python examples/backtest_csv.py /path/to/xauusd_m1.csv
```

也可以直接走 CLI：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli backtest /path/to/xauusd_m1.csv --config configs/mvp.yaml
```

运行样本内 / 样本外切分：

```bash
PYTHONPATH=src ./.venv/bin/python examples/sample_split_csv.py /path/to/xauusd_m1.csv --train-ratio 0.7 --warmup-bars 720
```

也可以直接走 CLI：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli sample-split /path/to/xauusd_m1.csv --config configs/mvp.yaml --train-ratio 0.7 --warmup-bars 720
```

运行 walk-forward：

```bash
PYTHONPATH=src ./.venv/bin/python examples/walk_forward_csv.py /path/to/xauusd_m1.csv --train-bars 5000 --test-bars 1000 --step-bars 1000 --warmup-bars 720
```

也可以直接走 CLI：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli walk-forward /path/to/xauusd_m1.csv --config configs/mvp.yaml --train-bars 5000 --test-bars 1000 --step-bars 1000 --warmup-bars 720
```

运行自动验收结论：

```bash
PYTHONPATH=src ./.venv/bin/python examples/acceptance_csv.py /path/to/xauusd_m1.csv --train-ratio 0.7 --warmup-bars 720 --train-bars 5000 --test-bars 1000 --step-bars 1000
```

也可以直接走 CLI：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli acceptance /path/to/xauusd_m1.csv --config configs/mvp.yaml --train-ratio 0.7 --warmup-bars 720 --train-bars 5000 --test-bars 1000 --step-bars 1000
```

临时改归档目录：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli acceptance /path/to/xauusd_m1.csv --config configs/mvp.yaml --report-dir /tmp/xauusd_reports
```

只看输出、不落盘：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli acceptance /path/to/xauusd_m1.csv --config configs/mvp.yaml --no-save-archive
```

## 新增 CLI 入口

单次实时拉取并处理一次：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli live-once --config configs/mvp.yaml
```

上线前预检：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli preflight --config configs/mvp.yaml
```

严格模式预检，未通过直接返回非零退出码：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli preflight --config configs/mt5_prod.yaml --strict
```

持续轮询：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli live-loop --config configs/mvp.yaml --iterations 10 --require-deploy-gate --require-preflight
```

安装后也可以直接用：

```bash
xauusd-ai smoke
xauusd-ai host-check --config configs/mt5_paper.yaml
xauusd-ai preflight --config configs/mvp.yaml
xauusd-ai live-once --config configs/mvp.yaml
xauusd-ai replay /path/to/xauusd_m1.csv --config configs/mvp.yaml
xauusd-ai backtest /path/to/xauusd_m1.csv --config configs/mvp.yaml
xauusd-ai sample-split /path/to/xauusd_m1.csv --config configs/mvp.yaml --train-ratio 0.7 --warmup-bars 720
xauusd-ai walk-forward /path/to/xauusd_m1.csv --config configs/mvp.yaml --train-bars 5000 --test-bars 1000 --step-bars 1000 --warmup-bars 720
xauusd-ai acceptance /path/to/xauusd_m1.csv --config configs/mvp.yaml --train-ratio 0.7 --warmup-bars 720 --train-bars 5000 --test-bars 1000 --step-bars 1000
```

说明：

- `live-once` 和 `live-loop` 可以显式加 `--require-preflight`
- `live-once` 和 `live-loop` 也可以显式加 `--require-deploy-gate`
- 当 `dry_run=false` 时，系统会自动先跑 `deploy-gate`
- `preflight --strict` 适合放进部署脚本或上线前检查脚本
- `replay` 适合做历史 CSV 验收，当前输出的是决策级与风控级报告，不是最终收益归因报表
- `backtest` 会走 Backtrader 成交闭环，当前已经支持手续费和滑点参数，但默认值仍需要按真实 broker 成本校准
- `sample-split` 会输出 `evaluation_rows` 和独立的 in/out sample 报告，适合先看样本外是否明显劣化
- `walk-forward` 会输出每个滚动测试窗口的独立表现和聚合 summary，适合看稳定性
- `acceptance` 会输出统一的 `ready / checks / failed_checks`，适合做自动验收和后续 CI 化
- `acceptance` 默认会自动归档完整 JSON 报告；如需关闭，可加 `--no-save-archive`
- `decision_summary.rows_processed` 表示真正执行了决策评估的 bars，不等于全部 `evaluation_rows`；挂单存活期间系统会跳过重复决策

## 配置重点

`configs/mvp.yaml` 现在已经包含：

- `runtime`
- `notification`
- `database`
- `backtest`
- `acceptance`
- `report_archive`
- `market_data`
- `execution`
- `state_thresholds`
- `risk`
- `breakout`
- `mean_reversion`
- `volatility_monitor`

其中实时运行最关键的是两块：

- `market_data.platform`
- `execution.platform`

如果你要走 MT5，建议两者都配置成 `mt5`。

另外仓库里已经补了两份更贴近上线的模板：

- `configs/mt5_paper.yaml`
- `configs/mt5_prod.yaml`

其中 `backtest` 段目前包含：

- `initial_cash`
- `commission`
- `slippage_perc`
- `slippage_fixed`

注意：

- `commission` 和 `slippage_perc` 都用绝对比例表示，例如 `0.0005 = 5 bps`
- `slippage_fixed` 用价格单位表示
- `slippage_perc` 和 `slippage_fixed` 二选一
- 在正式验收前，需要按你的 broker 成交回报把这几个值校准掉

其中 `acceptance` 段目前包含：

- `min_total_net_pnl`
- `min_total_profit_factor`
- `max_total_drawdown_pct`
- `min_out_of_sample_net_pnl`
- `min_out_of_sample_profit_factor`
- `max_out_of_sample_drawdown_pct`
- `min_walk_forward_windows`
- `min_walk_forward_positive_window_rate`
- `max_close_month_profit_concentration`
- `max_session_profit_concentration`

其中 `report_archive` 段目前包含：

- `enabled`
- `base_dir`
- `write_latest`

当前归档目录结构是：

- `reports/research/acceptance/<timestamp>.json`
- `reports/research/acceptance/latest.json`
- `reports/research/index.jsonl`

本地填真实 MT5 参数时，建议复制：

```bash
cp .env.mt5.example .env.mt5.local
```

然后填写：

- `XAUUSD_AI_MT5_LOGIN`
- `XAUUSD_AI_MT5_PASSWORD`
- `XAUUSD_AI_MT5_SERVER`
- `XAUUSD_AI_MT5_PATH`

## 常用环境变量

```bash
export XAUUSD_AI_ENV=prod
export XAUUSD_AI_LOG_LEVEL=INFO
export XAUUSD_AI_DRY_RUN=true
export XAUUSD_AI_POLL_INTERVAL_SECONDS=5
export XAUUSD_AI_STARTING_EQUITY=10000

export XAUUSD_AI_MARKET_DATA_PLATFORM=mt5
export XAUUSD_AI_EXECUTION_PLATFORM=mt5

export XAUUSD_AI_MT5_LOGIN=12345678
export XAUUSD_AI_MT5_PASSWORD=your-password
export XAUUSD_AI_MT5_SERVER=YourBroker-Server
export XAUUSD_AI_MT5_PATH=/Applications/MetaTrader\ 5.app
export XAUUSD_AI_MT5_SYMBOL=XAUUSD
export XAUUSD_AI_MT5_TIMEFRAME=M1
export XAUUSD_AI_MT5_HISTORY_BARS=500

export XAUUSD_AI_DATABASE_URL=sqlite:///var/xauusd_ai/system.db
export XAUUSD_AI_WEBHOOK_URL=https://example.com/webhook
```

如果后续切到 cTrader，再补：

```bash
export XAUUSD_AI_MARKET_DATA_PLATFORM=ctrader
export XAUUSD_AI_EXECUTION_PLATFORM=ctrader
export XAUUSD_AI_CTRADER_CLIENT_ID=your-client-id
export XAUUSD_AI_CTRADER_CLIENT_SECRET=your-client-secret
export XAUUSD_AI_CTRADER_ACCOUNT_ID=123456
export XAUUSD_AI_CTRADER_ACCESS_TOKEN=your-access-token
export XAUUSD_AI_CTRADER_SYMBOL=XAUUSD
export XAUUSD_AI_CTRADER_SYMBOL_ID=1
export XAUUSD_AI_CTRADER_ENV=demo
```

## 当前仍需继续补强的点

- cTrader 完整异步会话层
- 事件日历真实接入
- 成本模型与滑点模型
- 订单状态回传与持仓同步
- 报表与验收看板

当前已经补上的生产能力：

- MT5 账户状态同步
- MT5 上线前 `preflight`
- 执行结果单独审计落库到 `execution_attempts`

## 当前机器的实际 blocker

在当前这台开发机上，我已经实际验证过：

- 系统为 `macOS arm64`
- `.venv` 为 `Python 3.10.0`
- `pip install MetaTrader5` 返回 `No matching distribution found`

这说明当前仓库代码已经具备 MT5 运行链，但这台机器本身还不满足 MT5 Python 依赖安装条件。

更稳的落地方式是：

1. 继续把这台机器作为策略研发 / 文档 / 回放 / 编排节点
2. 准备一台可安装 `MetaTrader5` 的执行宿主机
3. 在执行宿主机上跑 `preflight`、`paper`、`prod` 脚本
4. 等 MT5 路径稳定后，再补 cTrader 的第二执行通道

## 一键脚本

仓库里已经提供：

- `scripts/local_mt5_smoke.sh`
- `scripts/mt5_host_check.sh`
- `scripts/mt5_preflight.sh`
- `scripts/mt5_deploy_gate.sh`
- `scripts/mt5_live_once.sh`
- `scripts/mt5_paper_loop.sh`
- `scripts/mt5_prod_loop.sh`
- `scripts/mt5_bootstrap.ps1`
- `scripts/mt5_host_check.ps1`
- `scripts/mt5_preflight.ps1`
- `scripts/mt5_deploy_gate.ps1`
- `scripts/mt5_live_once.ps1`
- `scripts/mt5_paper_loop.ps1`
- `scripts/mt5_prod_loop.ps1`
- `scripts/mt5_register_task.ps1`
- `scripts/mt5_task_runner.ps1`
- `scripts/mt5_task_status.ps1`
- `scripts/mt5_unregister_task.ps1`

常见用法：

```bash
bash scripts/local_mt5_smoke.sh
bash scripts/mt5_host_check.sh
bash scripts/mt5_preflight.sh
bash scripts/mt5_deploy_gate.sh .env.mt5.local
bash scripts/mt5_live_once.sh .env.mt5.local
bash scripts/mt5_paper_loop.sh .env.mt5.local --iterations 10
bash scripts/mt5_prod_loop.sh .env.mt5.local
```

Windows 执行宿主机推荐直接用 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_host_check.ps1 .env.mt5.local
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_preflight.ps1 .env.mt5.local
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_deploy_gate.ps1 .env.mt5.local
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_live_once.ps1 .env.mt5.local
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_paper_loop.ps1 .env.mt5.local --iterations 10
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_prod_loop.ps1 .env.mt5.local
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_register_task.ps1 -Mode prod -EnvFile .env.mt5.local -StartAfterRegister
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_task_status.ps1 -Mode prod -TailLog
```

说明：

- 脚本会自动加载 `.env.mt5.local`
- `local_mt5_smoke.sh` 适合当前这台机器先做本地策略输出和手工联调准备
- `mt5_deploy_gate.sh` / `mt5_deploy_gate.ps1` 会做统一上线门禁
- `mt5_live_once.sh` / `mt5_live_once.ps1` 适合先做单次联调，当前默认会一起带上研究门禁和平台预检查
- `mt5_host_check.sh` 先判断这台机器是否适合作为 MT5 执行宿主机
- `mt5_preflight.sh` 会根据 `XAUUSD_AI_ENV` 自动选择 `paper` 或 `prod` 配置
- 纸面盘和生产盘脚本当前默认都会先做 `deploy-gate + preflight`
- `mt5_register_task.ps1` 会通过 `mt5_task_runner.ps1` 注册计划任务，把循环脚本输出落到 `var/xauusd_ai/task_logs/<mode>/`
- `mt5_task_status.ps1` 用来查看计划任务状态、最近执行结果和最新日志位置，`-TailLog` 可直接看尾部
- `mt5_unregister_task.ps1` 用 Windows `Task Scheduler` 删除长期运行任务
- Windows 宿主机优先使用 `.ps1` 脚本，避免额外依赖 Git Bash
- `mt5_bootstrap.ps1` 会自动创建 `.venv`、安装 `.[mt5]`，并在缺少 `.env.mt5.local` 时从模板复制

完整执行宿主机说明见：

- [mt5_execution_host_runbook.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/mt5_execution_host_runbook.md)

如果你当前机器只能打开 MT5 终端、还不能跑 `MetaTrader5` Python 模块，也可以先按这份手工联调说明走：

- [local_mt5_manual_debug.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/local_mt5_manual_debug.md)
- [local_mt5_manual_debug_checklist.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/local_mt5_manual_debug_checklist.md)
- [local_mt5_debug_report_template.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/local_mt5_debug_report_template.md)
- [local_mt5_parameter_mapping_sheet.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/local_mt5_parameter_mapping_sheet.md)
- [local_mt5_observed_values.md](/Users/kyrie/Documents/黄金全流程量化交易系统/docs/implementation/local_mt5_observed_values.md)

## 当前验证状态

已验证：

- `python3 -m unittest discover -s tests`
- `./.venv/bin/python -m unittest discover -s tests`
- `python3 -m compileall src tests examples`
- `PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli smoke`

## 一句话总结

现在这套仓库已经不是单纯文档工程，而是一个：

- 可继续开发
- 可做历史回放
- 可接 MT5 实时轮询
- 可扩展到 cTrader
- 已把高波动预警纳入主流程

的生产型骨架。
