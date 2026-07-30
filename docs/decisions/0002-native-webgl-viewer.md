# ADR 0002：使用原生 WebGL viewer

- 状态：Accepted
- 日期：2026-07-30

## 背景

That Open Engine、IFC.js 或 Three.js 能提供成熟 viewer，但会引入 Node 构建步骤、较大依赖或 CDN。演示只需显示十个 IfcOpenShell 已三角化构件、状态着色、旋转、缩放与 GUID 拾取。

## 决策

后端用 IfcOpenShell 生成世界坐标三角网格，前端用约 300 行无依赖 WebGL 绘制。拾取通过同一场景的颜色 ID pass 完成，所选 mesh 的 metadata 直接携带 IFC `GlobalId`。

## 优点

- clone 后只需要 Python；
- 没有 CDN、前端构建或 wasm 下载；
- mesh 与合规结果使用同一个 GlobalId；
- 功能边界小，浏览器 contract 易测。

## 缺点

- 没有完整 IFC 层级、材质、剖切、测量、模型流式加载；
- 只适合小场景；
- 自维护矩阵与 picking 代码。

## 迁移影响

以后替换为 That Open/IFC.js 时，保留 `/api/scene` 或改为浏览器读取 IFC；协调选择仍以 `GlobalId` 为契约。

