# 模型与许可登记

- 更新日期：2026-07-30
- 原则：只有来源和再分发许可可核查的模型才能进入 Git；本地上传 metadata 不是平台替用户完成的法律判断。

## Tracked 模型

| 模型 | Schema | 大小 | SHA-256 | 来源与 provenance | 许可 | 用途 |
|---|---:|---:|---|---|---|---|
| `data/models/generated/ibc_egress_demo.ifc` | IFC4 | 14,120 bytes | `743f344f6f1bddd273f896fd99865189aff06dca90697b2576572d51846a583f` | `scripts/generate_fixture.py` 确定性生成；IFC header 标记非认证设计 | 仓库 MIT；生成器与 header 均明确 | 单元、边界、浏览器和导入去重测试 |

该模型是受控合成数据，不是现实项目，也不能作为真实作者工具兼容性或性能证据。

## Manifest-only 现实模型

| 模型 | Schema | 大小 | SHA-256 | 固定来源 | 许可/署名 | 用途 |
|---|---:|---:|---|---|---|---|
| Medical-Dental Clinic — Architectural | IFC2X3 | 13,003,205 bytes | `2ac970ce065ecac4e0c9e5f453a257169e90d0067f419b7e33533a64ef837880` | buildingSMART Community `Community-Sample-Test-Files` commit `7ddf57a201f88a0c213d5322b02ed15e94a60a40`；完整路径和固定 media URL 见 manifest | CC BY 4.0；`BSI (2020) "Medical-Dental Test Files," buildingSMART International` | 现实规模 IFC2X3 import/index、checker、scene 和性能验证 |

模型 README 说明这是经过脱敏的真实两层 clinic，曾用于 COBie Challenge interoperability trials；README 和仓库根许可证均明确 CC BY 4.0。完整机读登记位于
`data/models/external/medical-dental-clinic-architectural.json`。

模型本体不进入 Git：

```text
python scripts/fetch_licensed_model.py
python scripts/fetch_licensed_model.py --check
```

下载器只写 `data/runtime/licensed-models/`，拒绝非 HTTPS、非固定 commit URL、超过平台 20 MiB 边界、byte size/SHA-256 不一致和无效 STEP envelope。离线 fallback 始终是 tracked 合成夹具，核心 UI、测试和 CI 不依赖网络。

2026-07-30 本地验证：

- IFC2X3；
- 3,298 个 `IfcProduct`；
- 523 个受检 `IfcDoor` / `IfcSpace`；
- scene 28,780 个三角形；
- import/index、全量 checker、SQLite、NL 和 scene payload 均完成，数据见 `reports/real-model-performance.md`。

## Runtime 本地模型

用户通过 UI/API 导入的 IFC 只进入 `data/runtime/imports/`（或 `IFC_COMPLIANCE_DATA_DIR` 指定根），不进入 Git。系统记录：

- 原文件名（只作为 metadata）；
- 完整 SHA-256 和 hash-derived model id；
- schema、byte size、unit scale、产品数和 IFC class counts；
- 用户提供的 source 和 licence/usage-rights note；
- import job、诊断与时间。

默认 licence note 是“user-provided; redistribution not granted”。这有意阻止把“能够本地检查”误解为“能够重新分发”。平台不会从文件内容自动推定版权或许可。
