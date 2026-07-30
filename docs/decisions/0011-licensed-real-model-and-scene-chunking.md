# ADR 0011：许可现实模型与 scene 分块方向

- 状态：Accepted
- 日期：2026-07-30

## 背景

14 KiB 合成夹具不能验证 IFC2X3 异构性或现实规模。候选资产必须有原作者/官方来源、固定版本、可核验许可、checksum 和 offline fallback，且不能让核心 CI 依赖网络。

## 决策

1. 登记 buildingSMART Community Medical-Dental Clinic architectural IFC。其 README 称该资产为脱敏真实建筑，仓库和 dataset 说明均给出 CC BY 4.0。
2. 只提交 JSON manifest 和安全下载器；13.0 MB 模型写入 ignored runtime。URL 固定完整 commit，下载必须通过 HTTPS、20 MiB、exact byte size、SHA-256 和 STEP envelope 校验。
3. tracked 14 KiB IFC4 继续作为完全离线 fallback 和 deterministic unit fixture。
4. 现实模型单列性能报告与宽松预算，不复用合成夹具阈值。
5. 1.66 MB 单 scene payload 虽可运行，但现实模型首屏和 long-task 数据支持下一步改为 manifest + bounded chunks；旧 `/api/scene` 保持兼容直到前端迁移。
6. 当前现实模型产生的 777 项 `NOT_CHECKABLE` 保持原义：缺少 mapping/required information，不得转成 FAIL。

## 结果

IFC2X3、3,298 products、523 个门/空间的真实资产链现在可复现，且不扩大 clone 或核心启动依赖。下一步优化有了实际测量目标；代价是网络下载只在显式命令执行，CI 不能自行重验 13 MB 本体。
