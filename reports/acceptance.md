# MVD 验收报告

- 日期：2026-07-30
- 版本：0.1.0
- 模型：`data/models/generated/ibc_egress_demo.ifc`
- IFC schema：IFC4
- 规则数：3
- 构件数：10
- 结果数：15

## 自动化结果

```text
python -m pytest
18 passed

node --check frontend/app.js
exit code 0
```

覆盖：

- 规则 JSON Schema、IBC 阈值与人工复核状态；
- 每条规则的 PASS、FAIL、NOT_CHECKABLE、边界值、NOT_APPLICABLE；
- 15 条人工 ground truth；
- IfcOpenShell 属性和世界坐标几何 bbox；
- buildingSMART IDS 1.0 验证；
- rule → elements 与 element → rules；
- API 稳定结构和错误响应；
- GUID 与三维 mesh 对齐；
- 重复检查结果一致；
- 夹具重复生成 SHA-256 完全一致；
- 前端不依赖 CDN。

## 结果分布

| 状态 | 数量 |
|---|---:|
| PASS | 6 |
| FAIL | 3 |
| NOT_CHECKABLE | 3 |
| NOT_APPLICABLE | 3 |

## 浏览器验收

在 Chromium 内核浏览器对真实本地服务完成：

- 三条规则切换正确更新目标 IFC 类别和五个候选构件；
- WebGL 状态颜色、拖动旋转、滚轮缩放和颜色 ID picking 正常；
- 点击三维 mesh 后，证据面板与结果行通过同一 GlobalId 联动；
- 状态筛选同步控制结果表与三维场景；
- element ego graph 只保留局部 Rule / Result / Element 链；
- 390 × 844 移动端 viewport 使用单列布局，无横向溢出；
- 浏览器 console warning/error：0。

## 可移植性与公开安全

- 运行只需 Python 3.11–3.13；
- `run.ps1` / `run.sh` 自动创建仓库内 `.venv`；
- 已从本地 Git 提交创建全新 clone，在全新 `.venv` 中按 lock 安装、运行 18 项测试和 CLI 检查；结束时 tracked worktree 仍为空；
- 无 Neo4j、Docker、Node.js、CDN、IBC PDF 或外部 IFC 前置设置；
- 依赖完整解析在 `requirements.lock`；
- 受版权保护的 IBC PDF、用户原始 IFC、`.env`、虚拟环境和结果日志均不提交；
- 源码、IFC header、文档和配置经扫描，不含个人本机绝对路径；
- 未发现 token、private key 或硬编码密码。
