# Azure 临时 Windows 宿主机快速落地

## 适用场景

这份文档针对当前项目的一个非常具体的目标：

- 你手里暂时没有 Windows 电脑
- 需要先把 `MT5` 生产执行宿主机跑起来
- 希望尽量压低前期成本
- 优先解决“能上线、能联调、能扩展”，不是长期基础设施最优解

如果你是中国用户，建议先结合下面这份文档一起看：

- `docs/implementation/china_user_host_provider_options.md`

这份补充文档会说明为什么当前中国用户未必一定优先选 Azure。

## 先说结论

- 真正长期免费的 `Windows VPS` 基本不现实
- 对当前项目最实用的方案，是先用 `Azure Free Account` 的试用额度搭一台临时 `Windows x64` 虚拟机
- 如果后面进入连续纸面盘 / 小资金实盘，再切到正式按量计费或迁移到长期宿主机

官方信息可参考：

- [Azure Free Account](https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account)
- [Create a Windows VM in Azure portal](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/quick-create-portal)
- [Azure VM Auto-shutdown](https://learn.microsoft.com/en-us/azure/virtual-machines/auto-shutdown-vm)

## 为什么当前优先选 Azure

对这个项目来说，Azure 现在更合适，原因是：

- 新账号有试用额度，适合先做临时宿主机
- Windows 虚拟机创建路径成熟，控制台操作直观
- `RDP`、自动关机、磁盘和网络配置都比较顺手
- 对我们当前这种“先把 MT5 跑通，再逐步上生产”的节奏更友好

## 区域建议

优先从这些区域里选一个离你更近、创建时配额更容易通过的：

- `Japan East`
- `Korea Central`
- `Southeast Asia`
- `East Asia`

说明：

- 以上区域都在 Azure 官方全球区域范围内
- 具体哪个更快，要以你本地网络、账号可用配额、当时库存为准
- 如果某个区域无法创建 Windows x64 机型，直接切到下一个，不要卡太久

## 机型建议

先不要追求大机器，优先让链路跑起来。

建议范围：

- 最低可用：`2 vCPU / 4 GB RAM`
- 更稳妥：`2 vCPU / 8 GB RAM`
- 系列优先：`B` 系列或其他通用型 `x64` 机型

选择原则：

- 必须是 `Windows x64`
- 不要选 `Arm`
- 不需要 GPU
- 磁盘先用系统盘即可，后续日志和审计库再单独扩

如果只是做当前阶段的：

- `host-check`
- `preflight`
- `live-once`
- 短时 `paper loop`

那么 `2 vCPU / 4 GB` 通常就够用。

## 15 分钟落地步骤

### 1. 开通 Azure 试用账号

入口：

- [Azure Free Account](https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account)

你需要关注的点：

- 试用额度是临时的，不是永久免费
- 用完额度或转为按量后会开始计费
- 当前阶段一定要同时打开自动关机和预算提醒

### 2. 创建 Windows 虚拟机

入口：

- [Azure Windows VM Quickstart](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/quick-create-portal)

创建时按下面选：

- Image: `Windows Server 2022` 的 `x64` 版本
- Authentication: 用户名 + 强密码
- Inbound port: 只开 `RDP (3389)`
- Region: 从上面推荐区域里选一个
- VM size: 先选 `2 vCPU / 4-8 GB`

当前项目不建议一开始就把 `80`、`443`、自定义管理端口都暴露出去。

### 3. 打开自动关机

入口：

- [Azure VM Auto-shutdown](https://learn.microsoft.com/en-us/azure/virtual-machines/auto-shutdown-vm)

建议：

- 每天固定关机，例如凌晨或你不盯盘的时段
- 打开关机前通知
- 如果只是临时联调，用完就手工关机，不要空转

### 4. 用 RDP 连上 Windows 宿主机

连接后先做三件事：

- 更新系统
- 安装浏览器
- 安装 Python `3.10+`

### 5. 安装 MT5 并手工登录

在这台 Windows 宿主机上：

- 安装 `MetaTrader 5`
- 用你的测试账号先手工登录
- 确认 `XAUUSD` 能看到报价
- 确认能手工开平最小单

这一点非常关键，因为它能把问题分成两类：

- 平台和网络问题
- 账号权限问题

如果手工都不能开单，先不要进入 Python 联调。

### 6. 拉项目并自举环境

在 Windows PowerShell 里执行：

```powershell
git clone https://github.com/hudrew/xauusd-ai-trading-system.git
cd xauusd-ai-trading-system
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_bootstrap.ps1
```

如果宿主机还要兼顾研究 / 回放：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_bootstrap.ps1 -WithResearch
```

### 7. 配置环境变量

复制模板：

```powershell
copy .env.mt5.example .env.mt5.local
```

至少填写这些值：

- `XAUUSD_AI_MT5_LOGIN`
- `XAUUSD_AI_MT5_PASSWORD`
- `XAUUSD_AI_MT5_SERVER`
- `XAUUSD_AI_MT5_PATH`

建议先这样配：

- `XAUUSD_AI_ENV=paper`
- `XAUUSD_AI_DRY_RUN=true`
- `XAUUSD_AI_MARKET_DATA_PLATFORM=mt5`
- `XAUUSD_AI_EXECUTION_PLATFORM=mt5`

### 8. 先跑宿主机检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_host_check.ps1 .env.mt5.local
```

通过标准：

- 是 `Windows x64`
- Python 版本满足要求
- `MetaTrader5` Python 模块可导入
- MT5 路径有效

### 9. 再跑平台预检

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_preflight.ps1 .env.mt5.local
```

重点看这些检查项：

- `initialize`
- `account_info`
- `terminal_info`
- `symbol_select`
- `contract_size_alignment`
- `latest_tick`
- `recent_bars`
- `trade_permission`

如果这里失败，不要直接跳过进入 `prod loop`。

### 10. 最后按这个顺序联调

单次联调：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_live_once.ps1 .env.mt5.local
```

短时纸面盘：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_paper_loop.ps1 .env.mt5.local --iterations 10
```

准备生产时：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_prod_loop.ps1 .env.mt5.local
```

## 当前项目建议的上线顺序

不要一上来就直接实盘连续跑，推荐顺序：

1. Windows 宿主机上完成 MT5 手工开平单验证
2. `host-check`
3. `preflight`
4. `live-once`
5. `paper loop`
6. 小资金实盘
7. 再补 `cTrader`

## 宿主机安全与成本控制

最少做这几件事：

- `RDP` 只在需要时开放，能限制源 IP 就限制
- 不在机器里保存无关资料
- `.env.mt5.local` 只放这台宿主机必需的凭据
- 开启 Azure 自动关机
- 每天看一次账单和资源状态
- 不用时直接停止或删除虚拟机

## 什么时候该从“临时宿主机”升级

出现下面任一情况，就该切正式宿主机了：

- 需要 24 小时连续跑纸面盘
- 开始实盘
- 要接入告警守护、进程拉起、自动重连和长期日志
- 要同时接 `MT5` 和 `cTrader`
- 要做多环境隔离，例如 `paper` / `prod`

## 与当前仓库的关系

当前仓库已经为 Windows MT5 宿主机准备好了这条路径：

- `scripts/mt5_bootstrap.ps1`
- `scripts/mt5_host_check.ps1`
- `scripts/mt5_preflight.ps1`
- `scripts/mt5_live_once.ps1`
- `scripts/mt5_paper_loop.ps1`
- `scripts/mt5_prod_loop.ps1`
- `docs/implementation/mt5_execution_host_runbook.md`

所以这份文档不是一套新的方案，而是把“没有 Windows 机器时如何先搭一台临时执行宿主机”单独整理出来，方便快速落地。

## 不推荐的误区

- 直接在当前这台 macOS 上强行做 MT5 Python 实盘执行
- 还没做 `preflight` 就直接跑生产循环
- 用真实账号登录成功后，就误以为一定有交易权限
- 不开自动关机，放任 Windows 宿主机空转计费
- 同时推进 `MT5` 和 `cTrader` 生产接入，导致上线链路变复杂
