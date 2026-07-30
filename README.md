# IFC ↔ IBC 双向合规探索 MVD

这是一个正在向完整平台演进的教学与研究工具。它把 2021 IBC 的三条人工复核规则、buildingSMART IDS 1.0 信息要求、IFC4 构件、确定性检查结果和计算证据连成一条可双向查询的链：

```text
IBC document → clause → structured rule → IFC requirement/geometry
             → element (GlobalId) → result → evidence
```

它不是建筑审批或法律认证工具。MVD 的目标是证明闭环可行，并明确展示“数据缺失”和“设计不合规”是两件不同的事。

![状态](https://img.shields.io/badge/status-research%20MVD-147ea0)
![Python](https://img.shields.io/badge/python-3.11--3.13-14262d)
![IFC](https://img.shields.io/badge/IFC-IFC4-e95645)
![License](https://img.shields.io/badge/license-MIT-16805d)

## 已实现

- 2021 IBC §1010.1.1：疏散门净宽 `>= 813 mm`
- 2021 IBC §1010.1.1：疏散门净高 `>= 2032 mm`
- 2021 IBC §1003.2：疏散空间净高 `>= 2286 mm`
- buildingSMART IDS 1.0 对属性和几何表示的可检查性验证
- IfcOpenShell 属性读取与世界坐标几何包围盒计算
- `PASS`、`FAIL`、`NOT_APPLICABLE`、`NOT_CHECKABLE`
- rule → elements 与 element → rules 双向 REST API
- 自动迁移 SQLite，持久化项目、模型元数据、检查运行和逐项证据
- 唯一运行号、确定性执行号、分页历史和两次运行比较 API
- 简体中文 / English 全局切换与可分享的规则、构件、运行 URL
- 无 CDN 的 WebGL 三维视图、状态筛选、构件拾取、证据面板和局部 provenance graph
- 15 条人工 ground truth、边界值和端到端自动化测试

## 一条命令启动

前提只有 Python 3.11、3.12 或 3.13。仓库不要求 Neo4j、Docker、Node.js、IBC PDF 或任何本机路径。

Windows PowerShell：

```powershell
.\run.ps1
```

macOS / Linux：

```bash
sh run.sh
```

脚本会在仓库内部创建 `.venv`、安装锁定版本的依赖并启动服务。打开 <http://127.0.0.1:8000>。

手动安装方式：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install -e . --no-deps
.\.venv\Scripts\ifc-mvd.exe serve
```

## 演示路线

1. 在左侧选择一条 IBC 规则。
2. 中央 IFC 三维视图会按结果着色所有候选构件。
3. 点击三维构件或结果行。
4. 右侧显示该构件的条款、实测、阈值、原因、IFC 路径和几何 provenance。
5. 底部关系图显示 `Clause → Rule → Result → Element` 局部链。
6. 选择另一个构件时，界面会显示该构件涉及的全部候选规则。
7. 选择 `NOT_CHECKABLE` 可确认缺失数据没有被误报为 `FAIL`。

## 命令行

```powershell
# 执行检查并写入 data/results/latest.json（该运行产物不提交）
.\.venv\Scripts\ifc-mvd.exe check

# 输出 buildingSMART IDS 信息质量报告
.\.venv\Scripts\ifc-mvd.exe ids

# 运行全部测试
.\.venv\Scripts\python -m pytest

# 重建公开的小型 IFC 和 IDS 夹具
.\.venv\Scripts\python scripts\generate_fixture.py
.\.venv\Scripts\python scripts\generate_ids.py
```

## API 摘要

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/models` | 模型列表 |
| GET | `/api/projects` | 本地项目与模型/运行计数 |
| GET | `/api/check-runs` | 分页检查历史 |
| GET | `/api/check-runs/{run_id}` | 可审计运行与逐项结果 |
| GET | `/api/check-runs/{base}/compare/{target}` | 两次运行的逐项差异 |
| GET | `/api/rules` | 规则与状态计数 |
| GET | `/api/rules/{rule_id}/elements` | rule → elements |
| GET | `/api/elements/{guid}/rules` | element → rules |
| GET | `/api/elements/{guid}/results` | 构件的检查结果 |
| GET | `/api/scene` | GUID 对齐的三角网格 |
| GET | `/api/graph/ego` | 局部 provenance graph |
| GET | `/api/ids/report` | IDS 可检查性报告 |
| POST | `/api/checks/run` | 重跑确定性检查 |

交互式 OpenAPI 文档位于 <http://127.0.0.1:8000/docs>。

## 仓库内容

```text
data/regulations/   人工复核的结构化 IBC 规则与 JSON Schema
data/ids/           由规则信息要求生成的 IDS 1.0
data/models/        可公开、可重建的小型 IFC4
src/                检查器、IFC 适配、API、图查询
frontend/           零构建步骤的原生 WebGL 协调界面
scripts/            IFC 和 IDS 生成器
tests/              单元、集成、ground truth
docs/               架构、规则编写、研究对应、限制和 ADR
```

## 原始材料与版权

原始 2021 IBC PDF 不在仓库中，也不是运行依赖。仓库只保存定位复核所必需的短摘录、条款号、页码、阈值和人工计算解释。原始大型 IFC 同样没有复制；演示使用代码生成的 14 KB IFC4 夹具。

进一步阅读：

- [小白也能看懂的 Pipeline 解释](docs/小白也能看懂的Pipeline解释.md)
- [架构](docs/architecture.md)
- [规则编写与复核](docs/rule-authoring.md)
- [测试](docs/testing.md)
- [研究方向对应](docs/research-alignment.md)
- [已知限制](docs/limitations.md)
