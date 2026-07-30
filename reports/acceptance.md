# 全平台验收报告

- 日期：2026-07-30
- 分支：`product/full-platform`
- 版本：`0.1.0`
- 受控模型：`data/models/generated/ibc_egress_demo.ifc`
- IFC schema：IFC4
- 规则：3
- 受检构件：10
- 确定性结果：15

本报告记录可核查的 MVD 证据，不声称完整覆盖 IBC、官方认证、法律可靠性或现实项目性能。

## 自动化与 CI

```text
python -m pytest
55 passed

node --check frontend/app.js
exit code 0

python scripts/audit_repository.py
passed
```

GitHub Actions 质量矩阵 run
[`30585095622`](https://github.com/ralin0225/ifc-bidirectional-compliance-mvd/actions/runs/30585095622)
在 Ubuntu CPython 3.11、3.12、3.13 和 Windows CPython 3.12 全部通过。每个作业从锁文件安装后执行
`pip check`、公开仓库审计、前端语法检查、自动化测试、确定性夹具/IDS 重建 diff 和 CLI 检查。

覆盖证据包括：

- SQLite schema v4 migration、restart persistence、run 保存/比较和 model-scoped query history；
- IFC 上传边界、签名/schema 校验、失败状态、取消、重启恢复、去重和语义索引；
- 规则 JSON Schema、PASS/FAIL/NOT_CHECKABLE/NOT_APPLICABLE、阈值边界和 15 条人工声明 ground truth；
- IfcOpenShell 属性与世界坐标 bbox，以及 buildingSMART IDS 1.0 信息要求分层；
- 中英文 NL → validated DSL → deterministic evidence golden corpus；
- JSON、CSV、HTML/打印和 BCF 3.0 导出及 BCF round-trip；
- rule → element 与 element → rule、API 合约、i18n 完整性和前端能力契约；
- GUID 与三维 mesh 对齐、重复执行一致、夹具与 IDS 重建 SHA-256 一致。

## 结果分布

| 状态 | 数量 |
|---|---:|
| PASS | 6 |
| FAIL | 3 |
| NOT_CHECKABLE | 3 |
| NOT_APPLICABLE | 3 |

## 真实浏览器验收

在本地真实 Chromium 内核浏览器完成：

- 简体中文与英文主流程、规则切换、结果/证据/图谱联动；
- 文件选择器导入受控 IFC，验证完成、内容去重、模型登记和 model-scoped run；
- 自然语言查询同步结果和 3D；
- run history/compare，以及 JSON、CSV、HTML 和 BCF 导出；
- 3D picking、状态 overlay、搜索、模型树、隐藏、隔离、ghost、正交/透视、标准视图、Z 剖切、bbox 中心点测量和 viewpoint URL 恢复；
- 现实模型通过 6 个稳定 scene chunks 增量加载；首块可用后继续加载，late-chunk element 的 isolate/viewpoint 保存恢复保持正确；
- 390×844 单列布局，无横向溢出；
- 性能采样期间 5 次冷导航及选择/筛选交互，console warning/error 为 0。
- 通过文件选择器导入登记的 13.0 MB CC BY 4.0 clinic IFC2X3，打开 523 构件工作区并保存 777-result run；现实模型浏览器指标和限制单独记录。

浏览器性能数字及限制见
[`performance-baseline.md`](performance-baseline.md)。

## 可移植性与公开安全

- 核心只需 Python 3.11–3.13；不要求 API key、Docker、数据库服务器、Node.js、CDN、用户 PDF 或外部 IFC；
- `run.ps1` / `run.sh` 自动建立仓库内 `.venv`；
- 运行时依赖和开发依赖均精确锁定；Python 3.11 的 NumPy 兼容分支已在隔离环境和 CI 验证；
- 审计拒绝 tracked runtime data、用户目录绝对路径、常见 secret/private-key 模式和超过 1 MiB 的文件；
- 用户原始 IFC、`.env`、虚拟环境、SQLite/WAL、导入暂存和结果日志不提交；
- 合成模型来源、SHA-256 和许可登记在
  [`model-and-license-register.md`](../docs/research/model-and-license-register.md)；
- 许可现实模型以固定 commit、13,003,205-byte exact size、SHA-256、CC BY 4.0 署名和 offline fallback 登记；模型本体留在 ignored runtime；
- 现实模型性能与 777 项 `NOT_CHECKABLE` mapping 限制见
  [`real-model-performance.md`](real-model-performance.md)。
