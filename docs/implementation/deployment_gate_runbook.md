# 统一上线门禁说明

## 目标

在进入模拟盘或实盘前，用一条命令完成统一放行判断，避免以下情况：

- 研究验收没有通过，但已经开始联调
- MT5 宿主机不符合要求，但仍然继续部署
- 账号、symbol、行情或交易权限异常，但系统仍然启动

## 当前入口

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli --config configs/mt5_prod.yaml deploy-gate --strict
```

加上 `--strict` 后，如果门禁没有通过，命令会以退出码 `2` 结束。
说明：`--config` 是 CLI 全局参数，必须放在子命令前面。
这一步可以直接接到：

- 本地上线前自检
- CI/CD 脚本
- 运维发布脚本

## 当前检查内容

### 1. 研究验收归档

门禁会读取最新的 `acceptance` 归档，检查：

- 归档是否存在
- `ready` 是否为 `true`
- 报告时间是否超过 `deployment_gate.max_acceptance_report_age_hours`

如果执行宿主机本身不跑研究回测，而研究是在本地开发机或另一台机器完成的，当前标准做法是：

1. 在研究节点生成 `acceptance` 报告
2. 把生成出来的 `latest.json` 拷到执行宿主机
3. 在执行宿主机运行 `report-import`
4. 再执行 `deploy-gate`

### 2. 宿主机检查

在 `dry_run=false` 的 live 模式下，门禁默认会要求：

- `host-check`

这一步重点检查：

- 是否为合适的 MT5 宿主机平台
- Python 版本
- MetaTrader5 模块是否可用
- terminal 路径是否存在
- 登录凭证是否完整

### 3. 平台预检查

在 `dry_run=false` 的 live 模式下，门禁默认还会要求：

- `preflight`

这一步重点检查：

- MT5 初始化
- 账户信息
- terminal 信息
- symbol 选择
- symbol specification
- contract size 对齐
- 最新 tick
- recent bars
- 交易权限

## 默认策略

- `dry_run=true`
  默认只卡研究验收归档，宿主机和实时平台检查默认跳过
- `dry_run=false`
  默认同时要求研究验收、宿主机检查和平台预检查全部通过

当前还新增了一条自动衔接规则：

- `live-once`
- `live-loop`

当配置里 `dry_run=false` 时，这两个命令会在真正启动前自动先经过 `deploy-gate`。
也就是说，live 启动不再只依赖人工先手动跑门禁。

## 常用命令

只看门禁 JSON，不阻断：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli --config configs/mt5_prod.yaml deploy-gate
```

严格阻断：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli --config configs/mt5_prod.yaml deploy-gate --strict
```

覆盖验收归档目录：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli deploy-gate --report-dir reports/research
```

候选分支 `pullback sell v3` 使用独立归档目录时：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli --config configs/mt5_paper_pullback_sell_v3.yaml deploy-gate --report-dir reports/research_pullback_sell_v3
```

临时跳过实时检查：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli deploy-gate --skip-host-check --skip-preflight
```

在 dry run 中强制做实时检查：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli deploy-gate --require-host-check --require-preflight
```

在 dry run 中启动一次实时决策，但先强制走研究门禁：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli live-once --require-deploy-gate
```

在 dry run 中只强制做平台预检查：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli live-once --require-preflight
```

把别的机器生成的验收 JSON 导入当前宿主机：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-import C:/work/incoming/acceptance_latest.json --report-dir reports/research
```

先把当前机器里的最新验收归档导出成可传输文件：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-export ./tmp/acceptance_latest.json --report-dir reports/research
```

推荐顺序：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-import C:/work/incoming/acceptance_latest.json --report-dir reports/research
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli reports latest --report-dir reports/research
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli --config configs/mt5_prod.yaml deploy-gate --strict
```

候选分支 `pullback sell v3` 推荐顺序：

```bash
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-export ./tmp/research_pullback_sell_v3_acceptance_latest.json --report-dir reports/research_pullback_sell_v3
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli report-import C:/work/incoming/acceptance_latest.json --report-dir reports/research_pullback_sell_v3
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli reports latest --report-dir reports/research_pullback_sell_v3
PYTHONPATH=src ./.venv/bin/python -m xauusd_ai_system.cli --config configs/mt5_paper_pullback_sell_v3.yaml deploy-gate --report-dir reports/research_pullback_sell_v3 --strict
```

说明：

- `report-import` 同时支持直接导入 `acceptance` 命令输出的原始 JSON
- 也支持直接导入归档目录里的 `latest.json`
- `report-export` 会导出当前归档里的最新 envelope，适合从研究机带到执行宿主机
- 门禁新鲜度优先读取报告内部的 `checked_at`，不是导入时间
- 所以这一步适合“研究在 A 机执行，MT5 在 B 机执行”的正式分工

## 当前边界

当前门禁层已经适合第一版 MT5 上线流程，但还有几个后续增强点：

- cTrader preflight 还未补完，所以 cTrader live 仍不应作为首发生产通道
- 目前研究归档仍是文件索引，不是数据库查询
- 还没有把门禁结果自动回写到专门的运维表或发布记录表
