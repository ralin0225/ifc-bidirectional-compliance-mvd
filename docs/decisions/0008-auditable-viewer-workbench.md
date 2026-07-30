# ADR 0008：原生 viewer 扩展为可审计审查工作台

- 状态：Accepted
- 日期：2026-07-30
- 扩展：ADR 0002

## 背景

只有旋转、缩放和拾取的画布不能支持合规人员复核。审查至少需要从 IFC 空间树定位构件、搜索属性、隐藏/隔离上下文、切换投影与标准视图、剖切、量测，并让视点可重复打开。同时，直接切换到成熟 BIM viewer 会引入前端构建、WASM、云数据管线或 AGPL 等新的产品边界。

候选核验记录在 `docs/research/2024-2026-viewer-landscape.md`。

## 决策

在当前受控模型阶段继续使用原生 WebGL，并建立以下稳定契约：

- `/api/scene` 为每个 mesh 返回 IFC `GlobalId`、属性和 Project → Site → Building → Storey 的 `spatial_path`；
- 模型树、结果表、关系图、证据面板与 canvas 只通过 `GlobalId` 协调选择；
- viewer state 明确保存 camera、projection、hidden GUID、isolation/ghost、Z section 和 selected GUID；
- state 使用 URL-safe 编码写入 `view` 查询参数，并备份到 localStorage；恢复时只接受有限数值和当前 scene 已知 GUID；
- shader 完成单 Z 平面 fail-safe clipping；颜色 picking 使用 24-bit mesh id；
- 当前测距明确是两个构件世界坐标 bbox center 的距离，不冒充表面吸附或规范净距。

不加载 CDN 或外部脚本。当前不引入新的 JavaScript package。

## 迁移门槛

保留原生实现不等于宣称它适合生产大模型。出现任一情况就使用真实作者工具 IFC 对 That Open Engine Components 做隔离 spike：

- 一次性 scene JSON 在目标浏览器产生不可接受的首屏、内存或交互性能；
- 需要 chunk/stream、几何实例化、材质、透明排序、多个剖切面或 section caps；
- 需要面/边/点吸附测量、markup 或多模型 federation；
- 16-bit geometry index、单 canvas picking 或服务端预三角化成为实际瓶颈。

spike 必须保持现有 `GlobalId` selection 和 viewer-state adapter，不允许 viewer 自己重新判定合规。xeokit 的 AGPL-3.0、BIMData/APS 的平台绑定，未经独立许可和部署决策不进入依赖树。

## 影响

审查人员可以从空间结构或属性搜索进入同一个证据闭环，并通过 URL 复现视点。代价是原生渲染代码增多，量测与剖切仍是受控能力。URL viewpoint 尚未写入 BCF exporter；这是 exporter/viewer 集成的下一步，而不是把稳定通用 BCF camera 误标成用户实际视点。
