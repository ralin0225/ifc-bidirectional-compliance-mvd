# 小白也能看懂的 Pipeline 解释

## 先说 MVD 是什么

MVD 在这里是 Minimum Viable Demonstrator，也就是“最小可行演示系统”。它不打算检查整本 IBC，而是用三条真实条文证明一条完整链路能跑通：

```text
法规说了什么
→ 电脑需要模型提供什么
→ IFC 里实际有什么
→ 怎样计算
→ 为什么是这个结果
→ 在三维模型里它是谁
```

## 用一扇门理解全部流程

2021 IBC §1010.1.1 对疏散门的净开口宽度给出 813 mm 的最低值。人读这句话很自然，电脑却需要先回答很多小问题：

- “门”对应 IFC 的 `IfcDoor` 吗？
- 这扇门是不是疏散门？
- 模型里的 900 mm 是门框名义宽度，还是门扇打开后的净宽？
- 单位是毫米还是米？
- 属性根本没填时，是违规，还是资料不够？

所以法规不能直接变成一句草率的 `width >= 813`。

## 结构化规则是什么

结构化规则是把条文拆成机器能逐项读取的卡片：

```text
目标：IfcDoor
适用条件：IsMeansOfEgress = true
需要的信息：ClearOpeningWidth
要求：ClearOpeningWidth >= 813 mm
来源：2021 IBC §1010.1.1
例外：本 MVD 尚未自动处理
```

规则仍然保留原条款、短摘录和人工解释，因此人可以倒查它从哪里来。

## IDS 是什么

IDS 是 buildingSMART 的 Information Delivery Specification。可以把它理解成“交作业之前的信息清单”。

IDS 能检查：

- 有没有 `IfcDoor`；
- 有没有规定的 property set 和 property；
- 数据类型是否正确；
- 空间有没有几何表示。

IDS 不负责：

- 判断 760 mm 是否小于 IBC 的 813 mm；
- 解释所有法规例外；
- 计算复杂疏散路径。

本项目先跑信息清单，再做法规检查。没有填 `ClearOpeningWidth` 时，结果是 `NOT_CHECKABLE`，不是 `FAIL`。

## IfcOpenShell 是什么

IFC 是开放的建筑信息交换格式。IfcOpenShell 是能读取 IFC 的开源工具库。它帮助程序：

- 按类找到所有 `IfcDoor` 和 `IfcSpace`；
- 用 `GlobalId` 稳定识别每个构件；
- 读取 property set；
- 生成三角网格；
- 把局部 placement 转换到世界坐标；
- 测量空间几何的包围盒。

## 为什么需要图

表格很擅长显示一行结果，却不容易回答关系问题：

- 这条规则影响哪些门？
- 这扇门同时被哪些规则检查？
- 这个 FAIL 属于哪条 IBC 条款？
- 这个数值来自哪个 IFC 属性？

项目把这些对象看成节点，把“来自、适用、产生、证据”看成边。MVD 不需要先安装 Neo4j，而是在内存里按选中对象生成小型 ego graph。以后数据变大时，接口可以迁移到 Neo4j。

## API 是什么

API 是前端和检查器之间约定的问答格式。例如：

```text
GET /api/rules/某个规则/elements
```

意思是“给我受这条规则影响的构件”。

```text
GET /api/elements/某个GlobalId/rules
```

意思是“给我这件构件涉及的规则”。这两个接口组成双向查询。

## 三维 viewer 做什么

浏览器从 `/api/scene` 得到每个 IFC 构件的三角网格和 `GlobalId`。WebGL 把它们画出来：

- 绿色：PASS；
- 红色：FAIL；
- 橙色：NOT_CHECKABLE；
- 灰色：NOT_APPLICABLE。

点击网格后，程序用同一个 `GlobalId` 找结果、规则和证据，所以三维高亮、表格和右侧面板不会认错对象。

## 五种状态不要混

| 状态 | 意思 |
|---|---|
| `PASS` | 已知适用、信息充分、测量满足要求 |
| `FAIL` | 已知适用、信息充分、测量不满足要求 |
| `NOT_APPLICABLE` | 已明确知道这条规则不适用于该构件 |
| `NOT_CHECKABLE` | 缺少适用性、属性、关系或几何，不能下结论 |
| `MANUAL_REVIEW_REQUIRED` | 信息存在，但例外或算法超出可靠自动化范围；MVD 保留这个状态但当前夹具未触发 |

## 一个 IFC 文件经历了什么

1. `ComplianceEngine` 打开 IFC。
2. 规则按 `IfcDoor` 或 `IfcSpace` 选择候选构件。
3. 适用性属性为 false 就返回 NOT_APPLICABLE。
4. IDS/前置检查发现缺数据就返回 NOT_CHECKABLE。
5. IfcOpenShell 读取属性或生成几何。
6. 确定性代码测量并比较阈值。
7. 结果保存条款、实测、阈值、原因和 evidence。
8. API 可从规则查构件，也可从构件查规则。
9. 浏览器用 `GlobalId` 协调三维、表格、条文与图。

## 怎样运行

Windows：

```powershell
.\run.ps1
```

macOS/Linux：

```bash
sh run.sh
```

打开 `http://127.0.0.1:8000`。左侧选规则，中央点构件，右侧看证据。

## 怎样测试

```powershell
.\.venv\Scripts\python -m pytest
```

测试会把程序输出与人工 ground truth 对比，还会检查边界值、缺数据、IDS、双向 API、三维 GUID 对齐和重复运行一致性。

