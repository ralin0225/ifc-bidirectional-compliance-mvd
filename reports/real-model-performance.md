# 许可现实模型集成与性能基线

- 日期：2026-07-30
- 模型：Medical-Dental Clinic — Architectural
- 性质：经过脱敏的真实两层建筑；COBie Challenge interoperability dataset
- 许可：CC BY 4.0
- 署名：`BSI (2020) "Medical-Dental Test Files," buildingSMART International`
- 来源：buildingSMART Community `Community-Sample-Test-Files`
- 固定 commit：`7ddf57a201f88a0c213d5322b02ed15e94a60a40`
- SHA-256：`2ac970ce065ecac4e0c9e5f453a257169e90d0067f419b7e33533a64ef837880`
- 环境：Windows 11、CPython 3.12.10、AMD64、Intel64 Family 6 Model 158、12 logical CPUs、31.8 GiB RAM
- 浏览器：本地 Chromium 内核 in-app browser，1265×720 CSS px，device pixel ratio 2

完整来源路径、下载 URL、byte size、许可 URL和 offline fallback 见
`data/models/external/medical-dental-clinic-architectural.json`。模型本体只存在于 ignored runtime。

## 模型规模

| 指标 | 数值 |
|---|---:|
| IFC schema | IFC2X3 |
| 文件大小 | 13,003,205 bytes |
| IfcProduct | 3,298 |
| IfcDoor + IfcSpace | 523 |
| scene 三角形 | 28,780 |
| 当前规则结果 | 777 |

777 个结果均为 `NOT_CHECKABLE`：现实模型没有当前规则要求的自定义
`Pset_ComplianceMeasurements` / applicability mapping。这证明导入、索引、渲染和审计链可工作，但不构成 777 项合规失败，也不证明现实模型已经可自动判定。

## 后端基线

```text
python scripts/fetch_licensed_model.py --check
python scripts/benchmark_model.py \
  --fixture data/runtime/licensed-models/Clinic_Architectural.ifc \
  --iterations 3 \
  --label "registered redacted real-building IFC2X3; CC-BY-4.0"
```

导入每次使用全新临时数据库并走完整 parse/index；其他项目先 warm-up 再记录 3 次。

| 指标 | Median | P95 / max | 初始现实模型预算 |
|---|---:|---:|---:|
| IFC 校验、导入与 3,298 产品语义索引 | 7,859.9 ms | 8,291.9 ms | ≤ 12 s |
| 777 条结果整批 checker | 689.8 ms | 690.8 ms | ≤ 1.5 s |
| 523 构件 scene build | 3,825.1 ms | 3,886.7 ms | ≤ 6 s |
| SQLite 完整 run + 777 results 读取 | 9.2 ms | 9.7 ms | ≤ 50 ms |
| 英文 NL parse + deterministic query | 0.149 ms | 0.272 ms | ≤ 10 ms |

- legacy `/api/scene` 单一 JSON：1,660,470 bytes；保留兼容但前端不再使用。
- manifest 将 523 个构件按稳定 GlobalId 顺序分为 6 块（最多 100 elements）；响应为
  235,228、208,835、285,188、404,621、424,106、103,382 bytes，最大 424,106 bytes。
- engine load + checker + scene Python `tracemalloc` peak：13,179,983 bytes；预算 ≤ 25 MiB。
- `tracemalloc` 不包含 IfcOpenShell native allocation 和 graphics driver。

## 真实浏览器

文件选择器导入完成并在模型表登记 IFC2X3、3,298 products 和完整 SHA-256；模型工作区显示 523 个树节点。

### 优化前：单 payload + IDS 阻塞

首次从未缓存 engine 激活：

| 指标 | 首次激活 |
|---|---:|
| first useful render | 8,594.5 ms |
| active viewer render | 54.2 FPS |
| long task total / 1 s | 407 ms / 3 tasks |
| element selection → next paint | 125.4 ms |
| status filter → next paint | 46.9 ms |

engine warm、页面冷导航 3 次：

| 指标 | Median | P95 / minimum | 初始现实模型预算 |
|---|---:|---:|---:|
| first useful render | 4,379.9 ms | 4,529.6 ms P95 | ≤ 6 s warm；≤ 12 s first activation |
| element selection → next paint | 112.6 ms | 134.2 ms P95 | ≤ 250 ms |
| status filter → next paint | 47.8 ms | 48.4 ms P95 | ≤ 150 ms |
| active viewer render | 57.5 FPS | 56.0 FPS minimum | ≥ 45 FPS |
| long-task duration / 1 s sample | 306 ms | 317 ms P95 | ≤ 750 ms |

### 优化后：single-flight + 增量 scene chunks + 延后 IDS

冷 engine 首次激活时，首个 100-element chunk 在 2,361.4 ms 可用（相对 8,594.5 ms 减少 72.5%）；523 elements 在 6,075.9 ms 完成，IDS 在 6,295.0 ms 完成。首屏 active render 为 56.5 FPS，1 秒内 long-task total 88 ms。

engine warm、页面冷导航 3 次：

| 指标 | Median | P95 / minimum | 当前现实模型预算 |
|---|---:|---:|---:|
| first useful render（首 100 elements） | 799.1 ms | 839.7 ms P95 | ≤ 1.5 s warm；≤ 4 s first activation |
| 完整 523-element scene | 4,479.7 ms | 4,567.6 ms P95 | ≤ 6 s |
| scene + IDS ready | 4,738.0 ms | 4,779.0 ms P95 | ≤ 7 s |
| active viewer render during loading | 55.1 FPS | 53.9 FPS minimum | ≥ 45 FPS |
| long-task duration / 1 s sample | 139 ms | 155 ms P95 | ≤ 300 ms |

完整加载后的 element selection / filter 单次复验为 142.7 / 49.3 ms，late-chunk element 的 isolate + viewpoint URL 保存/恢复成功。优化后的 warm first-useful median 相对旧路径减少 81.8%。

真实浏览器随后创建了一个 `COMPLETED` run：777 results，保存的 checker duration 585.09 ms。导入、载入、交互和 run 全程 console warning/error 为 0。

## 结论与下一步

- 20 MiB 上传边界覆盖此 13.0 MB 模型，IFC2X3 路径已被真实资产验证。
- legacy 1.66 MB payload 仍兼容；产品 UI 已迁移到 manifest + 最多 100-element chunks，并把 IDS 从 first useful render 的阻塞链移出。
- 分块显著改善感知首屏，但完整几何仍需约 4.5 s；后续可考虑持久几何缓存、byte/triangle-aware chunk 和压缩。
- 现实模型 property/type fallback 尚未实现；所有 777 个 `NOT_CHECKABLE` 是可检查性证据，不是法规结论。
- 当前只是一台机器、一个作者工具年代和一个模型；预算是回归 guardrail，不是产品 SLO。
