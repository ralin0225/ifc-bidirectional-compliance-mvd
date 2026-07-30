# 受控 IFC 夹具性能基线

- 日期：2026-07-30
- 目的：快速回归 smoke baseline，不代表现实项目
- 模型：`ibc_egress_demo.ifc`，IFC4，14,120 bytes，13 个 IfcProduct，10 个受检/场景构件，120 个三角形
- Python：CPython 3.12.10
- 机器：Windows 11、AMD64、Intel64 Family 6 Model 158、12 logical CPUs、31.8 GiB RAM
- 浏览器：本地 Chromium 内核 in-app browser，1265×720 CSS px，device pixel ratio 2

## 后端

命令：

```text
python scripts/benchmark_model.py --iterations 7
```

每项先 warm-up，再记录 7 次；P95 采用 nearest-rank。导入测试每次使用全新临时 SQLite 和导入目录，并强制走解析与语义索引而非去重路径。

| 指标 | Median | P95 | 当前受控夹具预算 |
|---|---:|---:|---:|
| IFC 校验、导入与语义索引 | 107.881 ms | 109.806 ms | ≤ 250 ms |
| 15 条结果整批 checker | 7.897 ms | 8.325 ms | ≤ 50 ms |
| 10 构件 scene build | 26.506 ms | 28.106 ms | ≤ 100 ms |
| SQLite 完整 run + 15 results 读取 | 2.005 ms | 2.715 ms | ≤ 20 ms |
| 英文 NL parse + deterministic query | 0.057 ms | 0.082 ms | ≤ 10 ms |

- 单 chunk scene JSON：9,359 bytes；预算 ≤ 25 KiB。
- engine load + checker + scene 的 Python `tracemalloc` peak：103,730 bytes；预算 ≤ 1 MiB。
- `tracemalloc` 不包含 IfcOpenShell 等 native allocation，也不包含图形驱动内存。

## 浏览器

前端在 `<html>` 的 runtime dataset 发布诊断值；首个可用画面与交互均记录到第二个 animation frame，FPS 样本在首屏完成后持续主动调用 viewer render 1 秒。以下为 5 次冷导航：

| 指标 | Median | P95 / lower bound | 当前受控夹具预算 |
|---|---:|---:|---:|
| first useful render | 188.4 ms | 216.7 ms P95 | ≤ 1,000 ms |
| element selection → next paint | 27.6 ms | 27.8 ms P95 | ≤ 100 ms |
| status filter → next paint | 25.9 ms | 27.2 ms P95 | ≤ 100 ms |
| active viewer render | 61.9 FPS | 61.5 FPS minimum | ≥ 50 FPS |
| long-task duration / 1 s sample | 0 ms median | 56 ms P95 | ≤ 200 ms |

5 次采样只有一次出现 long task（1 个、56 ms）；console warning/error 为 0。

## 解释边界

- 这些预算仅用于这个确定性小夹具的 gross-regression gate，不是现实模型 SLO。
- 首屏包含本地 API、SQLite 和 WebGL 初始化，但不模拟广域网。
- 现实模型仍证明当前 scene 是单 payload；分块方向见 ADR 0011。
- 现实模型的规模、后端和真实浏览器数据在 `real-model-performance.md` 单独记录，不能和本表混为一个 SLO。
