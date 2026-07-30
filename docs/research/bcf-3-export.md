# BCF 3.0 文件交换核验

- 核验日期：2026-07-30
- 一手来源：[buildingSMART BCF 说明](https://technical.buildingsmart.org/standards/bcf/)、[buildingSMART/BCF-XML `release_3_0`](https://github.com/buildingSMART/BCF-XML/tree/release_3_0)

buildingSMART 将 BCF 定义为跨 BIM 应用交换模型问题的 openBIM 标准；官方说明明确指出 XML 问题数据通过 IFC GUID 引用模型构件。官方 `BCF-XML` 仓库的 `release_3_0` 分支包含 `Schemas/` 和 `Test Cases/v3.0/`。

本实现对以下官方 v3.0 样例进行了只读核验：

- `Markup/Minimum information`：ZIP 根包含 `bcf.version`，topic 目录包含 `markup.bcf`；
- `Visualization/Component selection`：`markup.bcf` 的 `ViewPoint` 引用同目录 `.bcfv`；
- `VisualizationInfo/Components/Selection/Component` 使用 `IfcGuid`；
- viewpoint 可包含 `PerspectiveCamera` 或 `OrthogonalCamera`。

没有把 buildingSMART XSD、测试 `.bcf` 或 `.bcfzip` 复制进本仓库。仓库只保存独立生成器与针对本项目生成文件的结构/安全 round-trip 测试。

## 本项目映射

- 每个 `FAIL`、`NOT_CHECKABLE` 或 `MANUAL_REVIEW_REQUIRED` 结果成为一个 topic；
- topic 和 viewpoint UUID 从 `run_id + rule_id + GlobalId` 确定性生成；
- topic description 保留 run、rule、GlobalId 和原因；
- viewpoint selection 使用原 IFC `GlobalId`，并附带可恢复的透视 camera；
- 当前不生成 snapshot，也不嵌入 IFC 或外部引用。

## 安全边界

读取 `.bcfzip` 时限制成员数、单成员和总解压大小，拒绝绝对路径、`..`、反斜杠路径、缺失 `bcf.version`、非 3.0 版本和悬空 viewpoint 引用。XML 使用 `defusedxml` 读取。当前仅提供生成与结构 round-trip，还没有把外部 BCF topic 写入数据库。

BCF 官方页面声明内容使用 CC BY-ND 4.0；本研究记录只概述结构并链接原始来源，不再分发官方规范或样例。
