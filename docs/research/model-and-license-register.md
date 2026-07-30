# 模型与许可登记

- 更新日期：2026-07-30
- 原则：只有来源和再分发许可可核查的模型才能进入 Git；本地上传 metadata 不是平台替用户完成的法律判断。

## Tracked 模型

| 模型 | Schema | 大小 | SHA-256 | 来源与 provenance | 许可 | 用途 |
|---|---:|---:|---|---|---|---|
| `data/models/generated/ibc_egress_demo.ifc` | IFC4 | 14,120 bytes | `743f344f6f1bddd273f896fd99865189aff06dca90697b2576572d51846a583f` | `scripts/generate_fixture.py` 确定性生成；IFC header 标记非认证设计 | 仓库 MIT；生成器与 header 均明确 | 单元、边界、浏览器和导入去重测试 |

该模型是受控合成数据，不是现实项目，也不能作为真实作者工具兼容性或性能证据。

## Runtime 本地模型

用户通过 UI/API 导入的 IFC 只进入 `data/runtime/imports/`（或 `IFC_COMPLIANCE_DATA_DIR` 指定根），不进入 Git。系统记录：

- 原文件名（只作为 metadata）；
- 完整 SHA-256 和 hash-derived model id；
- schema、byte size、unit scale、产品数和 IFC class counts；
- 用户提供的 source 和 licence/usage-rights note；
- import job、诊断与时间。

默认 licence note 是“user-provided; redistribution not granted”。这有意阻止把“能够本地检查”误解为“能够重新分发”。平台不会从文件内容自动推定版权或许可。

## 尚缺的验证资产

handoff 要求的许可证明确现实 IFC 尚未登记。引入前必须记录官方/原作者 URL、版本或 commit、明确许可文本、下载日期、原始 checksum、是否允许仓库再分发，以及离线 fallback。大模型若不宜入库，只提交固定 checksum 的下载脚本和小型离线 fallback。没有这些证据时不把网络模型复制到仓库。
