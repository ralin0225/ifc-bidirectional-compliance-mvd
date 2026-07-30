# 2024–2026 自然语言与 IFC 查询研究核验

- 核验日期：2026-07-30
- 范围：自然语言到 IFC/BIM 数据检索的表示、执行、安全和评估
- 用途：为本仓库的确定性 DSL 与可选 LLM 边界提供依据，不作为法规结论来源

## 一手来源

| 来源 | 状态 | 核验到的事实 | 对本项目的影响 |
|---|---|---|---|
| [Lin et al., *A natural-language-based approach to intelligent data retrieval and representation for cloud BIM*](https://arxiv.org/abs/2411.09951) | 2016 年 `Computer Aided Civil and Infrastructure Engineering` 期刊论文；2024-11-15 才上传 arXiv | 以 keyword / constraint 映射 IFC/IFD，并在 IFC schema 图上寻路；arXiv 页面明确列出 2016 journal reference | 支持“先把自然语言约束规范化，再执行结构化检索”。不能把它称为 2024 新研究 |
| [Ibba et al., *Enabling Natural Language Access to BIM Models with AI and Knowledge Graphs*](https://ceur-ws.org/Vol-3979/short3.pdf) | 2025 SemTech4STLD 同行评审 workshop short paper；卷页面说明 9 篇送审、7 篇录用，CC BY 4.0 | 将问题拆成子问题，匹配 KG class/property，生成最小 SPARQL 集合；用 28 个问题评估 | 说明可审计的中间查询和分解有价值；样本规模和 short-paper 状态不足以证明生产可靠性 |
| [Hellin et al., *BIM Information Extraction Through LLM-based Adaptive Exploration*](https://arxiv.org/abs/2605.01698) | 2026-05-03 arXiv v1 preprint；页面注明 submitted to *Automation in Construction* | ifc-bench v2 含 37 个 IFC 模型、21 个项目、1,027 个任务；论文认为异构模型下 adaptive exploration 优于固定静态查询 | 揭示当前小型固定词典对真实 IFC 异构性的外推风险；未来 benchmark 必须跨作者工具和项目，但不能因此允许任意代码执行 |
| [Lamsal et al., *IfcLLM: Natural Language Querying of IFC Models through Complementary Relational and Graph Representations*](https://arxiv.org/abs/2605.13236) | 2026-06-22 arXiv v2 preprint | 将属性/几何的关系表示与拓扑图表示结合；在 3 个模型、30 个场景上报告首次 93.3%–100% 准确率，失败由 fallback LLM 恢复 | 支持关系读模型与图投影并存；模型与场景数量有限，不能把报告数字移植成本项目准确率声明 |

## 结论

研究共同支持显式中间表示：自然语言不应直接变成合规结论。当前平台因此采用：

```text
Chinese / English utterance
  → locale-aware pattern parser
  → Pydantic-validated QueryDSL
  → deterministic in-memory / SQLite domain query
  → GlobalId-aligned evidence rows
```

当前实现故意不采用论文中的 LLM→SPARQL、fallback LLM 或任意代码 adaptive exploration：

- 核心演示必须无 API key、离线可运行；
- 合规查询需要可重复、可测试且能显示完整筛选；
- IFC 名称、属性和上传内容是不可信数据，不能成为执行指令；
- 现阶段只有一个受控小模型，尚不足以证明任一 LLM 方案的收益大于风险。

未来可选 LLM adapter 只能输出候选 `QueryDSL`，必须经过相同 Pydantic schema、domain identifier、复杂度和权限校验。不得输出 SQL、Python、shell、文件路径或最终合规状态。

## 尚未被证据支持的部分

- 现有来源没有证明中英文在同一 IFC corpus 上具有等价准确率；
- 2026 两篇 preprint 尚不能当成经同行评审的生产工程结论；
- 3 个模型或单一机场案例不能代表 IFC2X3/IFC4/IFC4.3 和主流作者工具差异；
- 当前 8 条 golden utterance 只验证产品垂直切片，不构成通用 BIM QA benchmark。
