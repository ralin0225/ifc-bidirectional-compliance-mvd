# 规则编写与人工复核

## 从条文到规则

一条规则只有在完成以下复核后才能设为 `human_verified`：

1. 确认法规文件、版本、章节、条款、PDF 页码和印刷页码。
2. 只保存足以识别阈值的短摘录，避免重新分发受版权保护的规范。
3. 分开写 `target`、`applicability`、`exceptions`、`requirement`。
4. 明确需要哪些 IFC 信息；缺失时必须返回 `NOT_CHECKABLE`。
5. 指定 IFC 属性/关系/几何的主要映射，说明拒绝了哪些不等价 fallback。
6. 记录测量单位、比较符、边界值语义和几何假设。
7. 为 PASS、FAIL、NOT_CHECKABLE、边界值和适用时的 NOT_APPLICABLE 建 ground truth。

## 为什么不把所有内容写成 Python `if`

阈值、来源和映射放在 `data/regulations/ibc_2021_rules.json`，执行器只实现有限的、经过测试的 metric。这样可以：

- 在 code review 中直接比较条款解释；
- 用 JSON Schema 阻止漏写来源或审核状态；
- 从同一规则派生 IDS 信息要求；
- 让未来的规则编辑器或 LLM 只生成候选 JSON，而不是直接给出法律结论。

## 本 MVD 的映射决策

### 门净宽/净高

IBC 说的是 clear opening，不是门洞名义宽高。因此规则读取自定义且语义明确的：

```text
Pset_ComplianceMeasurements.ClearOpeningWidth
Pset_ComplianceMeasurements.ClearOpeningHeight
```

`IfcDoor.OverallWidth` / `OverallHeight` 不做 fallback，因为它们不能保证代表门扇打开到规定角度后的净尺寸。对真实项目，应将企业属性名、类型属性、门五金或几何算法映射到同一概念，并给每个 fallback 单独的置信与证据标签。

### 疏散空间净高

MVD 对正交合成空间使用世界坐标 bbox 的 Z 向尺寸。这个算法仅用于证明几何闭环，不覆盖斜顶、梁、局部突出物、楼梯、坡道或条款例外。

### 门—空间关系与疏散拓扑

门开启方向先从 `IfcDoor.ProvidesBoundaries` 找到相关空间，再读取显式人数，并通过 `IfcRelAssociatesClassification` 读取 occupancy group；项目属性只在 classification 缺失时作为显式 fallback。疏散连续性对 `IfcSpace.BoundedBy ↔ IfcDoor.ProvidesBoundaries` 图做 BFS。两者都保存实际关系 GlobalId；关系缺失不得退化为 FAIL。

拓扑无路径只有在 `Pset_ComplianceTopology.TopologyCoverageComplete=true` 时才表示设计失败。缺少该声明代表信息不充分。

### 人工判定

`automation_level: manual_judgement` 的规则在确认适用后直接进入 `MANUAL_REVIEW_REQUIRED`。规则必须提供人工检查清单，且不得借用一个看似相关的 IFC 属性制造自动 PASS。

## 增加规则

1. 在规则 JSON 中添加对象并运行 `python -m pytest tests/unit/test_rules.py`。
2. 如需新 IFC 信息，更新 `scripts/generate_ids.py`。
3. 如需新 metric，在 `ComplianceEngine._measure` 添加确定性实现和 provenance。
4. 更新 `scripts/generate_fixture.py` 与 `tests/expected/ground_truth.csv`。
5. 添加边界、缺失和不适用测试。
6. 只有人工复核后才能写 `review_status: human_verified`。

## 当前条款复核记录

| Rule ID | 2021 IBC | PDF 页 | 阈值 | 审核结论 |
|---|---|---:|---:|---|
| `IBC2021-1010.1.1-WIDTH` | §1010.1.1 | 316 | 813 mm | 已核对原文；未实现例外和 occupant load |
| `IBC2021-1010.1.1-HEIGHT` | §1010.1.1 | 316 | 2032 mm | 已核对原文；未实现高度例外 |
| `IBC2021-1003.2-EGRESS-HEIGHT` | §1003.2 | 304 | 2286 mm | 已核对原文；受控正交空间，未实现八项例外 |
| `IBC2021-1010.1.2.1-SWING` | §1010.1.2.1 | 316 | binary = 1 | 已核对原文；关联空间上下文与摆向为受控映射 |
| `IBC2021-1003.6-EGRESS-CONTINUITY` | §1003.6 | 305 | binary = 1 | 已核对原文；仅检查声明完整的边界图连通 |
| `IBC2021-1010.2-DOOR-OPERATIONS` | §1010.2 | 318 | manual | 已核对原文；只生成现场复核任务 |
