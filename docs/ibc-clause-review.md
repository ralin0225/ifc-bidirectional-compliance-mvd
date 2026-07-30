# 2021 IBC 条款局部复核记录

## 来源

- 文档：2021 International Building Code
- Publisher：International Code Council
- 本地 PDF：833 页
- PDF metadata title：`2021_IBC_Book.book`
- 复核日期：2026-07-30

源 PDF 受版权限制，不提交到仓库。以下只保留识别阈值所必需的短摘录。

## §1003.2 Ceiling height

- PDF 页：304
- 印刷页：10-1
- 短摘录：“shall have a ceiling height of not less than 7 feet 6 inches (2286 mm) above the finished floor”
- MVD 解释：对明确标为 means of egress 的正交 `IfcSpace`，世界坐标几何 bbox 高度不得小于 2286 mm。
- 限制：原条款列出八项例外；MVD 不推断例外，不把算法外推到斜顶或局部突出物。

## §1010.1.1 Size of doors

- PDF 页：316
- 印刷页：10-13
- 净宽短摘录：“shall provide a minimum clear opening width of 32 inches (813 mm)”
- 净高短摘录：“minimum clear opening height of doors shall be not less than 80 inches (2032 mm)”
- MVD 解释：只读取语义明确的 clear opening 属性，不用 `OverallWidth` / `OverallHeight` 替代。
- 限制：occupant load、双扇门、Group I-2、门类型和条文例外没有自动处理。

## §1003.6 Means of egress continuity

- PDF 页：305
- 印刷页：10-2
- 短摘录：“The path of egress travel along a means of egress shall not be interrupted by a building element other than a means of egress component”
- MVD 解释：在导出方明确声明拓扑完整时，从 `IfcSpace` 经 `IfcRelSpaceBoundary` / `IfcDoor` 做 breadth-first traversal，到达标记的 exit-discharge door 记为 1。
- 限制：只证明受控边界图的连通性；不证明沿途无实际障碍，也不验证宽度或容量没有缩减。

## §1010.1.2.1 Direction of swing

- PDF 页：316
- 印刷页：10-13
- 短摘录：“shall swing in the direction of egress travel where serving a room or area containing an occupant load of 50 or more persons or a Group H occupancy”
- MVD 解释：门通过 `IfcRelSpaceBoundary` 关联空间；人数恰为 50 或 `IfcRelAssociatesClassification` 标为 Group H 时适用，受控 `SwingDirection=EGRESS` 记为 1。
- 限制：人数、occupancy group 和摆向来自显式项目映射；不推断复杂门型或自行计算 occupant load。

## §1010.2 Door operations

- PDF 页：318
- 印刷页：10-15
- 短摘录：“egress doors shall be readily openable from the egress side without the use of a key or special knowledge or effort”
- MVD 解释：这是一条现场操作/五金复核规则，适用时只能返回 `MANUAL_REVIEW_REQUIRED`。
- 限制：任何 IFC 属性都不被当作“readily openable”的自动通过证据。

## 单位与边界

长度规则统一使用毫米和 `>=`，因此 813、2032、2286 的精确边界值都应 PASS。关系与拓扑规则使用可审计的二值分数和 `== 1`；门方向适用性另覆盖 occupant load 恰为 50 的边界。人工判定规则没有自动边界结论。
