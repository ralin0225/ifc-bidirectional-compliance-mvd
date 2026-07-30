# 已知限制

## 法规范围

- 只覆盖 2021 IBC 的三个数值规则。
- §1010.1.1 和 §1003.2 的例外没有自动推理。
- 未建模 occupant load、occupancy group、双扇门、门摆角、斜顶、梁和局部突出物。
- 短摘录仅用于研究追溯，不能替代合法取得的 IBC 正文。
- 系统不是审批、认证、法律意见或生命安全决策工具。

## IFC 与信息异构性

- 夹具是受控 IFC4，不代表 Revit、Archicad 或其他作者工具的全部导出差异。
- 门 clear opening 使用自定义 `Pset_ComplianceMeasurements`。真实模型需要受控映射表、单位转换、类型继承和来源置信。
- 当前适用性依赖 `Pset_ComplianceApplicability.IsMeansOfEgress`，没有从空间连通、疏散路径或房间功能自动推断。
- 缺失表示的空间在 viewer 中显示为低矮 placeholder；它只用于保持选择能力，明确不参与几何判定。

## 几何算法

- 世界坐标 axis-aligned bbox 只对受控正交空间等价于净高。
- 未做布尔运算、最小净高场、障碍投影、碰撞、路径或可达性分析。
- 未处理几何容差、损坏 B-rep、映射表示、布尔树和非常大的模型性能。

## IDS

- `.ids` 是有效 buildingSMART IDS 1.0，并由 IfcTester 执行。
- IDS 只表达“属性/表示是否存在且类型正确”，不编码 IBC 阈值和例外。
- IfcTester 0.8.3 读取 IDS 1.0 时没有把 XML 的 `identifier` 回填到对象；报告层按稳定 specification name 恢复 ID。ADR 记录了该兼容处理。

## 查询、图和界面

- 图是结果数据的内存投影，不是持久 Neo4j。
- 浏览器 viewer 是本项目实现的轻量 WebGL triangle renderer，不支持完整 IFC 材质、层级树、剖切和测量工具。
- API 单进程加载一个小模型，未做上传隔离、作业队列、鉴权或数据库并发。
- `data/results/latest.json` 是本地运行产物，故意不提交。

## 生产化之前必须补齐

- 由有资质人员确认条文、采用版本、当地修订和所有例外；
- 建立模型交换信息要求、命名映射、单位和可信度策略；
- 针对真实作者工具 IFC 建 benchmark；
- 对几何容差、性能、攻击性文件和审计日志做工程化；
- 让所有自动结论能由人工复查和覆盖，并保存审批责任链。

