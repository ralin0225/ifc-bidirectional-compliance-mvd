# 2024–2026 Web BIM viewer 选型核验

- 核验日期：2026-07-30
- 范围：用于本地优先 IFC 合规审查工作台的 viewer，而不是通用 CDE
- 方法：只采用产品官方文档、官方代码仓库和许可证文件；营销能力不视为本项目已验证性能

## 候选矩阵

| 方案 | IFC / 大模型路径 | 审查工具 | BCF / 视点 | 集成与运行约束 | 许可证判断 |
|---|---|---|---|---|---|
| 本项目原生 WebGL | IfcOpenShell 在服务端生成三角网格；目前一次性 JSON 传输 | 已实现 GUID 拾取、树、属性搜索、状态着色、隐藏/隔离/幽灵、正交、标准视图、单 Z 剖切、包围盒中心测距 | URL + localStorage 保存 camera、visibility、projection、section 和 selection；尚未写回 BCF exporter | 无 Node、WASM、CDN 或外部运行时；最容易保证离线与结果 GUID 对齐，但没有流式加载、材质、表面吸附和 section cap | 项目自身 MIT；无新增前端依赖 |
| That Open Engine Components | 官方 `IfcLoader` 用 Web-IFC 读取 IFC，并使用 Three.js/Fragments 路径 | 组件生态包含 BIM 选择、属性、测量和剖切所需原语 | 需要本项目实现与 BCF/run audit 的适配层 | 浏览器 WASM + npm 构建；可本地托管。最接近本项目的开放、离线目标，是扩大模型规模时首选 spike | `@thatopen/components` 官方 npm 元数据和仓库为 MIT |
| xeokit SDK v3 | 官方描述包含大模型批处理、流式、64 位坐标、IFC/XKT/XGF 等格式 | scene/data graph、picking、camera、section caps 和技术图等能力完整 | 官方列出 BCF Viewpoints | v3 仓库仍标为 alpha-status；技术匹配度高，但许可证会改变本 MIT Web 应用的分发/网络使用义务 | 官方仓库为 AGPL-3.0；未经法律与产品决策不集成 |
| Speckle Viewer / Server | 围绕 Speckle project/model/version 和 connectors 数据管线 | 官方 saved views 保存 camera、visibility、filters、section boxes 和 measurements | saved view 可分享、分组、设为 home；协作能力成熟 | 若只取 viewer 仍需适配 Speckle object 模型；完整方案带 server、身份和项目治理，超出本地单模型 checker 范围 | server 大部分 Apache-2.0，但 workspaces/gatekeeper 等目录采用 Enterprise license，必须按文件边界复核 |
| BIMData Viewer | 原生 viewer plugins 覆盖 IFC 3D/2D、DWG/DXF、点云等 | 官方 native plugins 有 structure/properties、search、projection、section、BCF；UI 可扩展 | BCF Manager 与 BIMData BCF API 集成 | 官方说明 viewer 绑定 BIMData API；Vue 3/plugin 架构适合其平台，但会把本项目引向另一套云 API 与对象状态 | 官方文档未给出足够明确的单一 SDK 许可结论；引入前需采购/法律复核 |
| Autodesk APS Viewer SDK | 支持多种设计格式，成熟的 Model Derivative / Viewer 路径 | 官方列出 section cuts、explode、measure、对象/图层显示、markup 和分享 | viewer state 与云端协作能力成熟 | Viewer JavaScript 和衍生数据依赖 Autodesk 托管服务、鉴权与计费；不符合当前离线、无外部运行时目标 | 专有服务条款；不是本项目 MIT 依赖的直接替代 |

## 直接来源

- That Open `IfcLoader`：[官方 API](https://thatopen.github.io/engine_past-docs/3.0.x/api/%40thatopen/components/classes/IfcLoader/)；[`@thatopen/components` 官方 npm 包](https://www.npmjs.com/package/@thatopen/components)；[官方仓库](https://github.com/ThatOpen/engine_components)。
- xeokit v3：[官方仓库及功能清单](https://github.com/xeokit/sdk)；[AGPL-3.0 许可证](https://github.com/xeokit/sdk/blob/develop/LICENSE.md)。
- Speckle：[Saved views 官方文档](https://docs.speckle.systems/3d-viewer/saved-views)；[server 许可证边界](https://github.com/specklesystems/speckle-server/blob/main/LICENSE)。
- BIMData：[Viewer 入门](https://developers.bimdata.io/viewer/)；[原生 plugins](https://developers.bimdata.io/viewer/reference/native_plugins.html)；[viewer plugin API](https://developers.bimdata.io/viewer/reference/viewer_plugins.html)。
- Autodesk APS：[Viewer SDK 官方概览](https://aps.autodesk.com/viewer-sdk)；[Viewer3D API](https://aps.autodesk.com/en/docs/viewer/v6/reference/Viewing/Viewer3D/)；[Measure extension](https://aps.autodesk.com/en/docs/viewer/v6/reference/Extensions/MeasureExtension/)。

## 结论

当前 10 构件受控样本不值得用新引擎换取依赖、许可证与数据管线风险。先补齐审查闭环，并保持 `GlobalId`、scene payload 和序列化 viewpoint 的边界。真实作者工具 benchmark 一旦证明一次性 JSON / 原生 WebGL 不满足交互和内存门槛，就对 That Open 做隔离 spike；迁移决策必须以同一批 IFC、同一浏览器、同一审查任务实测，不以 feature list 代替 benchmark。
