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

## 单位与边界

结构化规则统一使用毫米。比较符为 `>=`，因此 813、2032、2286 的精确边界值都应 PASS。测试夹具为每条规则包含一个等于阈值的案例。

