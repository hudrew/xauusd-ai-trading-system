# Pullback Sell V3 纸盘连续观察记录模板

记录日期：

- `YYYY-MM-DD`

记录人：

- ``

观察窗口：

- `asia / eu / overlap / us`

## 1. 基本状态

监控页地址：

- `http://<VPS-IP>/`

主任务状态：

- `Running / Ready / Failed`

监控任务状态：

- `serve:`
- `refresh:`

健康检查：

- `http://<VPS-IP>/health`
- 返回值：

## 2. 本轮检查命令

日常巡检：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check.ps1 .env.mt5.local
```

归档巡检结果：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_check_archive.ps1 .env.mt5.local
```

如需恢复监控：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mt5_pullback_sell_v3_daily_recover.ps1 .env.mt5.local
```

## 3. 巡检摘要

本轮是否正常：

- `是 / 否`

主任务是否持续刷新：

- `是 / 否`

监控页是否持续刷新：

- `是 / 否`

高波动预警是否异常暴增：

- `是 / 否`

是否出现明显 stale：

- `是 / 否`

## 4. 关键观察

最近决策时间：

- ``

最近高波动预警情况：

- `无 / 少量 / 频繁 / 异常`

最近执行尝试情况：

- `无 / 正常 / 异常`

风险拦截情况：

- `正常 / 偏多 / 异常`

日志是否出现失败关键词：

- `无 / 有`

## 5. 问题记录

是否发现问题：

- `否 / 是`

问题现象：

- ``

问题发生时间：

- ``

是否已恢复：

- `否 / 是`

恢复动作：

- ``

## 6. 本轮结论

本轮结论：

- `继续观察 / 需要恢复 / 需要重新拉主任务 / 需要研究排查`

下一步动作：

- ``

## 7. 巡检归档文件

建议把每次归档结果记录到：

- `var\xauusd_ai\ops_checks\paper\mt5-paper-pullback-sell-v3\`

建议同步记录：

- 本次归档文件路径
- 本次是否执行过恢复
- 本次结论
