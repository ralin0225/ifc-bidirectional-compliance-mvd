# 与 2025–2026 ACC 研究方向的对应

本项目选择“AI 辅助作者阶段 + 确定性运行阶段”的混合路线。MVD 本身不调用 LLM；这是有意的边界：候选规则可以由模型辅助生成，但进入正式规则库前必须通过 schema、测试与人工确认，运行时结论只来自 IFC 数据和确定性算法。

## 研究依据与实现对应

### 1. 规则形式化需要 human-in-the-loop

Fuchs 等人的法规神经语义解析研究指出，模型可学习逻辑结构并辅助自动补全，但质量不足以完全自动化，适合识别需要人工复核的规则。2024 年对 LLM 解释建筑法规的研究同样把歧义、上下文和形式表示作为核心问题。

本 MVD 因此保存 `review_status: human_verified`、原文短摘录、计算解释、例外和版本；不会让 LLM 在运行时直接给 PASS/FAIL。

- Fuchs et al., *Neural Semantic Parsing of Building Regulations for Compliance Checking*, 2022. [DOI](https://doi.org/10.1088/1755-1315/1101/9/092022)
- Fuchs et al., *Using Large Language Models for the Interpretation of Building Regulations*, 2024. [arXiv](https://arxiv.org/abs/2407.21060)
- Hettiarachchi et al., *CODE-ACCORD*, 2024：人工标注法规实体与关系，为可评估的规则生成提供 ground truth。[arXiv](https://arxiv.org/abs/2403.02231)

### 2. 信息质量必须与设计合规分开

buildingSMART 将 IDS 定义为 IFC 信息要求的计算机可解释表示。它可规定对象、分类、材料、属性和值应如何交付；这不等于完整法规推理。

本项目先用 IDS 判定 clear opening 属性或 `Representation` 是否可用，再运行 IBC 阈值。IDS 失败变成 `NOT_CHECKABLE`，不是 `FAIL`。

- buildingSMART, *Information Delivery Specification v1.0*. [官方标准页面](https://www.buildingsmart.org/standards/bsi-standards/information-delivery-specification-ids/)
- buildingSMART, *IDS 1.0 schema and implementer resources*. [官方 GitHub](https://github.com/buildingSMART/IDS)

### 3. IFC 与法规之间需要语义桥

2025 年的 Semantic Web + IFC 研究把法规查询模板、领域对象本体和 IfcOWL 映射作为桥梁，并强调人机协同检查。本项目在更小范围内以显式 rule target、information requirement、property/geometry mapping 和局部图完成同一类语义对齐。

- Jia et al., *A Semantic Web and IFC-Based Framework for Automated BIM Compliance Checking*, 2025. [DOI](https://doi.org/10.3390/buildings15152633)

### 4. 图适合多跳检索，但几何不应全部塞进图数据库

IFC Whisperer 将 IFC 信息转换为知识图，再用结构化图查询处理多跳问题。MVD 采用相同的“语义投影”思想，但只把 Clause、Rule、Element、Result、Evidence 关系投影为 ego graph；三角网格继续由 IFC/IfcOpenShell 处理。

- Tung et al., *IFC Whisperer: Querying Building Information Models with Large Language Models and IFC-based Knowledge Graphs*, 2025. [DOI](https://doi.org/10.1088/1742-6596/3140/16/162007)

### 5. 回答或结论必须带来源

Joffe 等人的规范问答框架强调，工程问题的回答应伴随支持它的具体规范引用。MVD 将这一原则落实为每个结果的条款、PDF 页、IFC `GlobalId`、属性路径或几何算法、实测值、阈值和 reason。

- Joffe et al., *The Framework and Implementation of Using Large Language Models to Answer Questions about Building Codes and Standards*, 2025. [DOI](https://doi.org/10.1061/JCCEE5.CPENG-6037)

## 这个 MVD 有意没有夸大的地方

- 六条代表性规则不能代表整本 IBC。
- 合成 IFC 的正确率不能外推到真实项目。
- bbox 高度算法不能替代任意空间净高分析。
- 可解释 evidence 不等于法律上充分的审批记录。
- 图查询可证明双向关系，但不是完整法规知识图谱。

## 下一阶段可研究的问题

1. 把 LLM 候选规则与人工修订版并列保存，量化实体、关系、例外与数值的修订成本。
2. 在多个作者工具导出的真实 IFC 上建立信息映射 benchmark，分别报告 IDS 可检查率与设计合规率。
3. 将空间连接、门方向、障碍物和 path graph 引入疏散检查，并给几何误差设容差与可复核中间产物。
