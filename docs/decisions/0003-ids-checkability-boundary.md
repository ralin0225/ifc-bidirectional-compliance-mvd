# ADR 0003：IDS 只负责可检查性

- 状态：Accepted
- 日期：2026-07-30

## 背景

IDS 能表达 IFC 对象、分类、属性、材料和数值的信息交付要求，但 IBC 条文还包含适用条件、例外、几何算法和法规阈值。把所有法规逻辑都称为 IDS 检查会混淆数据质量与设计合规。

## 决策

由结构化规则的 `required_information` 生成 IDS 1.0。运行时先确定适用性和信息完整性，信息缺失输出 `NOT_CHECKABLE`；信息充分后由确定性代码检查 IBC 阈值和几何。

## 优点

- 不会把缺属性误报为违法；
- IDS 文件可交给其他 buildingSMART 工具；
- 每个结果能说明失败发生在信息层还是法规层；
- 规则和 IDS 从同一概念源维护。

## 缺点

- 需要维护 IDS 与 checker 的对应测试；
- 一些工具用户可能预期 IDS 直接输出最终合规结论；
- IfcTester 0.8.3 读取 IDS 1.0 时不回填 specification identifier，报告层暂按稳定名称恢复。

## 迁移影响

升级 IfcTester 后删除 identifier 兼容映射。更复杂法规仍留在 checker/plugin 层，而不是扩大 IDS 的语义边界。

