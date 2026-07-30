# ADR 0001：MVD 使用内存关系投影，不要求 Neo4j

- 状态：Accepted
- 日期：2026-07-30

## 背景

handoff 优先考虑 Neo4j，但同时要求新同学 clone 后无需额外配置即可运行。三条规则、十个构件和十五个结果不需要独立数据库。

## 决策

以规则 JSON、IFC 和检查结果为 source of truth，按请求生成局部 `nodes` / `edges` ego graph。API 使用稳定的节点类型与关系名称，不存 B-rep。

## 优点

- 单命令启动，无 Docker、密码、volume 或环境变量；
- 图数据不会与规则和结果产生第二份漂移；
- 测试可以精确断言双向关系；
- 保持后续迁移到 Neo4j 的接口边界。

## 缺点

- 没有 Cypher、持久索引和跨模型大图查询；
- 每次进程启动都从源数据重建；
- 只适合 MVD 规模。

## 迁移影响

未来可以用相同 node/edge projection 写 Neo4j adapter，让 `/api/graph/ego` 的响应不变。IFC 几何仍不写入图数据库。

