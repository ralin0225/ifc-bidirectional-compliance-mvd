# 已知限制

## 法规范围

- 只覆盖 2021 IBC 的三个数值规则。
- §1010.1.1 和 §1003.2 的例外没有自动推理。
- 未建模 occupant load、occupancy group、双扇门、门摆角、斜顶、梁和局部突出物。
- 短摘录仅用于研究追溯，不能替代合法取得的 IBC 正文。
- 系统不是审批、认证、法律意见或生命安全决策工具。

## IFC 与信息异构性

- 已验证受控 IFC4 和一项 Revit 2011/optimizer 生成的 CC BY 4.0 IFC2X3 clinic；单个现实模型仍不代表 Revit、Archicad 或其他作者工具/版本的全部导出差异。
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

- 项目、模型元数据、运行和结果已保存到可迁移 SQLite；元素语义索引、几何和关系图仍是当前模型的内存投影。
- 已支持 20 MiB 内 IFC2X3/IFC4 系列本地导入、持久化 job、hash 去重和语义索引；IfcOpenShell 解析仍在应用进程内，没有 OS 级 CPU/memory/wall-clock sandbox，不能直接暴露给不受信公网。
- 中英文 NL parser 是受控词典/模式垂直切片；当前 golden corpus 只有 8 条表达，不代表开放域语言理解。未识别输入会拒绝执行。
- 没有启用 LLM adapter；当前也不支持 storey/property 复杂条件和自然语言 run comparison。
- BCF 3.0 topic/selection 已可交换；浏览器可以把实时 camera、visibility、projection、section 和 selection 保存到 URL/localStorage，但 exporter 尚未接收该状态，BCF 仍使用稳定通用 camera，也没有 snapshot、导入或回写。
- 浏览器 viewer 是轻量 WebGL triangle renderer：已有空间树、隐藏/隔离、单 Z 剖切、bbox-center 测距和最多 100-element 的增量 scene chunks；13 MB 现实模型完整几何仍需约 4.5 秒，没有持久几何缓存、IFC 材质、section cap、表面吸附或 markup。
- API 可按 model id 运行检查和场景，但 UI 尚无模型版本关系、联邦坐标或跨模型 compare；job 是单进程 `BackgroundTasks`，只有 queued cancellation，没有独立 worker、鉴权或多 writer 并发。
- `data/results/latest.json` 是本地运行产物，故意不提交。

## 生产化之前必须补齐

- 由有资质人员确认条文、采用版本、当地修订和所有例外；
- 建立模型交换信息要求、命名映射、单位和可信度策略；
- 扩展到更多现实作者工具/版本和 mutation benchmark；
- 对几何容差、性能、攻击性文件和审计日志做工程化；
- 让所有自动结论能由人工复查和覆盖，并保存审批责任链。
