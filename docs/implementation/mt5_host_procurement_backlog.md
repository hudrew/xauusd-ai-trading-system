# MT5 宿主机采购延期待办

## 状态

- 当前状态：延期处理
- 最后更新：`2026-03-29`
- 原因：当前优先继续推进系统功能与落地实现，宿主机采购放到后续单独执行

## 这条任务是做什么的

目标不是单纯买一台机器，而是为本项目补齐一台可用于：

- `MT5 + Python`
- `Windows x64`
- 后续 `paper / prod` 联调

的真实执行宿主机。

## 已经沉淀下来的结论

### 1. 当前本地开发机的边界

- 当前 macOS 开发机适合做文档、研发、回放、手工 MT5 联调
- 当前 macOS 开发机不适合作为正式 `MT5 Python` 执行宿主机

## 2. 已验证的 MT5 事实

- 本地 `MT5` 登录链路已经打通
- `TradeMaxGlobal-Live` 可成功授权登录
- 测试账号已完成最小手数手工开平单验证
- 问题不在“能不能连上 MT5”，而在后续“宿主机选型、支付方式、上线方式”

## 3. 已记录的宿主机方案分支

已单独写入这些文档：

- `docs/implementation/mt5_execution_host_runbook.md`
- `docs/implementation/azure_windows_temporary_host_quickstart.md`
- `docs/implementation/china_user_host_provider_options.md`

这些文档已经覆盖了：

- 中国用户下的国内云厂商路线
- Azure 临时 Windows 宿主机路线
- 宿主机部署、联调、上线前检查

## 4. 已经发现的现实限制

### 国内云厂商

- 阿里云某些香港购买路径可能会卡在手机号验证
- 腾讯云 `CVM` 更偏正式生产，但月付和半年付价格相对高
- 腾讯云 `Lighthouse` / 轻量方案更便宜，但更适合临时验证，不一定是最终生产形态

### 海外通用云厂商

- 一些海外云支持 `Alipay`
- 但不一定支持 `Windows`
- 或不一定适合作为 `MT5` 的交易执行宿主机

### 传统 Forex / MT5 专用 VPS

- `FXVM`
- `ForexVPS`
- `FXVPS`

这类更接近交易型宿主机，但主流官方页面里未确认 `Alipay` 支持普遍可用。

### 支付方式相关结论

- `FXVPS` 官方 FAQ 当前写的是 `PayPal` 和 `bitcoin`
- 未找到其官方明确支持 `Alipay` 或香港银行卡直刷的说明
- 需要 `Alipay` 时，更接近可行路线的是支持 `Alipay` 的 VPS 厂商，而不是传统专用 Forex VPS 品牌

## 5. 关于 `TradeMaxGlobal-Live` 的已知线索

### 本地日志线索

本地 `MT5` 日志显示：

- 登录曾通过 `Access Server-SZ1`
- 本地观测 ping 约为 `250.05 ms`

参考：

- `/Users/kyrie/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/logs/20260329.log`

### 外部线索

- `TMGM / TradeMax` 官方账户页面提到服务器 `New York NY4`

这说明：

- 接入层可能离中国更近
- 但最终交易服务器大概率更偏向 `New York / NY4`
- 后续选宿主机时，不能只看“你连 VPS 是否顺畅”，还要看“VPS 到 broker 的实际延迟”

这里的 `New York / NY4` 判断是基于已查到的公开页面和交易 VPS 延迟页做出的工程判断，后续仍要以真实 MT5 登录后的实测为准。

## 恢复这条任务时的优先顺序

后续重新开始时，按下面顺序推进：

1. 明确本次优先级：`最低成本`、`最快落地`、还是 `更贴近生产`
2. 明确支付方式约束：`支付宝`、`PayPal`、`香港银行卡`、还是其他
3. 在候选宿主机里只保留满足 `Windows x64 + RDP + 可安装 MT5 + 可安装 Python` 的方案
4. 优先试 `Hong Kong / Singapore / Tokyo / New York`
5. 上机后先做 `MT5` 手工登录和最小手工单验证
6. 再跑：
   - `mt5_host_check.ps1`
   - `mt5_preflight.ps1`
   - `mt5_live_once.ps1`
7. 通过后再决定是否进入 `paper loop` 或长期宿主机采购

## 恢复时的最小验收标准

只要满足下面这些，就算宿主机采购任务完成：

- 可远程登录 Windows 宿主机
- 可安装并登录 `MT5`
- 可看到 `XAUUSD`
- 可完成最小手工单开平验证
- 可通过 `host-check`
- 可通过 `preflight`
- 可完成一次 `live-once`

## 当前建议

这条任务暂时不要继续消耗时间，先把精力放回：

- 系统功能实现
- 特征与策略落地
- 回放 / 预警 / 风控链路完善

等需要正式执行宿主机时，再回到这份待办继续。
