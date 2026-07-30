# ADR 0011：许可现实模型与增量 scene 分块

- 状态：Accepted
- 日期：2026-07-30

## 背景

14 KiB 合成夹具不能验证 IFC2X3 异构性或现实规模。候选资产必须有原作者/官方来源、固定版本、可核验许可、checksum 和 offline fallback，且不能让核心 CI 依赖网络。

## 决策

1. 登记 buildingSMART Community Medical-Dental Clinic architectural IFC。其 README 称该资产为脱敏真实建筑，仓库和 dataset 说明均给出 CC BY 4.0。
2. 只提交 JSON manifest 和安全下载器；13.0 MB 模型写入 ignored runtime。URL 固定完整 commit，下载必须通过 HTTPS、20 MiB、exact byte size、SHA-256 和 STEP envelope 校验。
3. tracked 14 KiB IFC4 继续作为完全离线 fallback 和 deterministic unit fixture。
4. 现实模型单列性能报告与宽松预算，不复用合成夹具阈值。
5. 新增快速 manifest 和稳定 GlobalId 排序、每块最多 100 elements 的 chunk API；前端首块即初始化 viewer，剩余块依序追加，IDS 在完整 scene 后加载。旧 `/api/scene` 保持兼容。
6. imported model engine 采用 per-model single-flight lock，避免多个并发首屏 API 重复解析/check 同一 IFC。
7. 当前现实模型产生的 777 项 `NOT_CHECKABLE` 保持原义：缺少 mapping/required information，不得转成 FAIL。

## 结果

IFC2X3、3,298 products、523 个门/空间的真实资产链现在可复现，且不扩大 clone 或核心启动依赖。warm first-useful median 从 4,379.9 ms 降至 799.1 ms；代价是完整 scene 仍约 4.5 s，网络下载只在显式命令执行，CI 不能自行重验 13 MB 本体。
