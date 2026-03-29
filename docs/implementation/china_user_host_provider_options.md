# 中国用户临时宿主机选型建议

## 适用前提

这份文档针对的是下面这个场景：

- 你在中国
- 现在要先起一台 `Windows` 宿主机跑 `MT5`
- 目标是临时联调、快速上线，不是一步到位做长期基础设施

## 截止 2026-03-29 的结论

如果你是中国用户，我建议优先级这样排：

1. `阿里云 ECS` 试用或低配按量
2. `腾讯云 Lighthouse / CVM`
3. `Azure Global`
4. `Azure China (21Vianet)`

原因不是谁“技术更强”，而是谁更适合你现在这个项目阶段。

## 推荐顺序为什么这样排

### 1. 阿里云优先

对中国用户来说，阿里云当前最顺手。

官方页面显示：

- 阿里云 `ECS` 有免费试用入口
- 个人版试用总额度为 `300 元`
- 试用有效期为 `3 个月`
- 试用地域包含 `香港`
- 最高可试用到 `4 vCPU / 8 GiB`

参考：

- [阿里云 ECS 免费试用](https://free.aliyun.com/product/product/ecs/freetrial)
- [阿里云 ECS 产品页](https://www.aliyun.com/product/ecs)

对我们这个项目来说，它的优点是：

- 中国用户注册、实名认证、付款链路更顺
- 有官方试用额度
- 香港地域可选，适合先做海外交易链路验证
- `Windows` 宿主机和远程桌面运维都比较常规

### 2. 腾讯云次选

腾讯云也很适合中国用户，尤其是你想快速买一台轻量机器时。

官方页面显示：

- `Lighthouse` 是面向开发测试和轻量应用场景的云服务器产品
- 有“中国香港及其他境外地域”
- 当前页面写有“新用户免费体验 1 个月”
- 同时也给出了比较低门槛的入门型和进阶型套餐

参考：

- [腾讯云 Lighthouse 产品页](https://cloud.tencent.com/product/lighthouse)

它的优点是：

- 控制台和运维上手快
- 活动多，临时机器常有低价入口
- 香港地域对出海类应用通常更实用

要注意的是：

- 促销和试用活动时效性强
- 不要把某个活动价当成长期稳定成本

如果当前项目是为了跑 `MT5` 的 `Windows` 执行宿主机，建议优先这样选：

- 产品：`CVM`
- 地域：`中国香港`
- 实例族：`标准型 SA5`
- 起步规格：`2 vCPU / 4 GB`
- 更稳妥：`2 vCPU / 8 GB`
- 镜像：`Windows Server 2022 x64`

这样选的原因是：

- 腾讯云官方的实例选型文档把 `标准型` 定义为适合大多数常规业务
- 同一文档说明，`S` 和 `SA` 都属于标准型，`S` 单核更强，`SA` 性价比更高
- 腾讯云官方的 `SA5` 实例文档说明，它提供平衡、稳定的计算、内存和网络资源，适合作为通用型生产实例

参考：

- [腾讯云云服务器选型概述](https://intl.cloud.tencent.com/zh/document/product/213/41951)
- [腾讯云 SA5 实例规格](https://cloud.tencent.com/document/product/213/11518)

如果 `中国香港` 某个可用区没有 `SA5`，就按下面顺序降级：

1. `标准型 S5 / S6`
2. 仍然保持 `2 vCPU / 4 GB` 或 `2 vCPU / 8 GB`

不建议当前项目一开始就选：

- `BF1`

因为腾讯云官方文档明确提示，`BF1` 可能会随机部署到不同处理器平台，并且实例生命周期中也可能迁移到不同平台；如果业务对一致性有强诉求，建议购买标准型实例。

参考：

- [腾讯云 BF1 实例规格](https://cloud.tencent.com/document/product/213/11518)

### 3. Azure Global 作为国际化备选

如果你已经能正常使用国际版 Azure，那么它仍然适合做 `MT5` 临时宿主机。

官方页面显示：

- `Azure Free Account` 提供试用额度
- 全局 Azure 的 Windows VM 创建文档成熟

参考：

- [Azure Free Account](https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account)
- [Azure Windows VM Quickstart](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/quick-create-portal)

它的优点是：

- Windows VM 路径成熟
- 自动关机、RDP、监控、扩容都比较标准化
- 如果后面你要走更国际化的部署，会比较顺

### 4. Azure China 不作为当前首选

`Azure China` 不是全球 Azure 的简单镜像，而是单独运营的一套环境。

微软官方说明：

- `Azure operated by 21Vianet` 是位于中国、物理隔离的云实例
- 与全球 Azure 存在功能差异
- 中国区 Azure 是由 `21Vianet` 独立运营和交易
- Azure FAQ 里明确写了，全球平台的 `Azure Benefit` 不能直接用于中国区平台

参考：

- [Microsoft Azure operated by 21Vianet](https://learn.microsoft.com/en-us/azure/china/overview-operations)
- [Azure China FAQ](https://support.azure.cn/en-us/support/faq/)

所以对当前项目来说，`Azure China` 最大的问题不是不能用，而是：

- 和全球 Azure 不是同一套体系
- 功能存在差距
- 你现在是为了快速把 `MT5` 跑起来，不值得先增加平台分叉

## 中国用户该怎么选

### 情况 1：想尽量白嫖或低成本试错

优先：

- 阿里云 `ECS` 试用
- 腾讯云 `Lighthouse` 新用户试用或活动机

这是当前最务实的路径。

### 情况 2：后面可能会走国际化部署

优先：

- Azure Global

前提是你已经能顺利使用国际版 Azure。

### 情况 3：只想最快把 MT5 宿主机跑起来

优先：

- 阿里云香港
- 腾讯云香港

这里有一个经验性判断，不是厂商官方承诺：

- 如果你的券商服务器在海外，`香港 / 日本 / 新加坡` 一般会比中国内地地域更适合做交易执行宿主机

这条判断主要来自常见网络路径和实际部署经验，建议最终以你自己的：

- `MT5` 手工登录稳定性
- 报价刷新速度
- 手工下单响应
- `preflight` 结果

来决定。

## 对当前项目的直接建议

按你现在的情况，我建议这样走：

1. 先查阿里云 `ECS` 试用，优先看 `香港`
2. 如果试用没拿到，就看腾讯云 `Lighthouse` 香港或境外地域活动机
3. 如果你已经有国际版 Azure 可用，再用我们仓库现成的 Azure 文档落地

## 如果遇到“需要香港手机号验证”

这在实际购买路径里是一个常见阻塞点。

处理建议：

1. 先确认你是不是走到了阿里云国际站，而不是中国站
2. 如果当前路径仍然要求香港手机号，不要继续在这条链路上消耗时间
3. 直接切到腾讯云中国站购买 `中国香港` 的实例

这里有一个重要的官方信息：

- 腾讯云官方文档明确写了，使用腾讯云中国站账号，既可以购买中国地域实例，也可以购买其他国家或地区实例，无需分别申请中国站账号和国际站账号

参考：

- [腾讯云地域和可用区相关](https://cloud.tencent.com/document/product/213/17276)

如果你只是为了尽快拉起一台临时 `Windows MT5` 宿主机，那么从执行效率上看，遇到香港手机号验证时，直接切腾讯云通常更省时间。

## 配置建议

不管你选哪家，当前项目阶段都建议：

- `Windows x64`
- `2 vCPU / 4 GB` 起步
- 更稳妥是 `2 vCPU / 8 GB`
- 先装 `MT5`
- 先手工登录和手工开平最小单
- 再跑：
  - `mt5_host_check.ps1`
  - `mt5_preflight.ps1`
  - `mt5_live_once.ps1`

## 不建议的做法

- 一上来就买年付长期套餐
- 只看机器便宜，不看是否有 `Windows x64`
- 还没确认 `XAUUSD` 和账号权限，就直接部署自动交易循环
- 因为人在中国，就默认一定要上 `Azure China`
