# ADR 0012：代表性规则必须保留证据边界

- 状态：Accepted
- 日期：2026-07-30

## 背景

前三条规则只覆盖 IFC property 与受控 geometry 阈值，不能证明平台能诚实处理跨构件关系、疏散拓扑或必须由人判断的要求。直接把项目自定义布尔值当作完整法规结论会隐藏数据来源，也容易把模型缺失误报为设计 FAIL。

## 决策

加入三个不同执行边界：

1. §1010.1.2.1 从 `IfcDoor.ProvidesBoundaries` 找到关联空间，以显式 occupant load / `IfcRelAssociatesClassification` Group H 判断适用性，再核对门摆向。证据保存空间、classification 与边界关系 GlobalId。
2. §1003.6 在 `IfcSpace ↔ IfcDoor` 边界图上做 BFS。只有 `TopologyCoverageComplete=true` 时，无 exit-discharge 路径才可 FAIL；缺少关系或完整性声明时为 `NOT_CHECKABLE`。
3. §1010.2 不自动判断“readily openable”。适用门返回 `MANUAL_REVIEW_REQUIRED` 并携带现场检查清单。

关系与拓扑结果继续用数值 1/0 表示规则内的有限判断，方便现有查询和导出保持稳定；其含义、算法和路径必须写入 evidence，不能声称覆盖整个条款。

## 后果

- 受控夹具从 15 条扩展为 30 条 ground truth，覆盖属性、几何、关系、拓扑和人工判断。
- IDS 继续只检查可检查性；跨对象语义和法规比较仍由确定性引擎执行。
- 真实 IFC 若没有受控映射会产生更多 `NOT_CHECKABLE`，这是信息不足的诚实结果。
- 生产化仍需合格人员复核当地采用版本、例外、模型交换要求和人工审批责任链。
