# Codex Handoff：IFC 双向规范合规完整平台

> 给新 Codex 对话的执行说明。请完整阅读后直接工作，不要只输出方案或待办清单。

## 0. 一句话任务

在 `product/full-platform` 分支上，把当前可运行的 IFC 合规 MVD 迭代成一个可复现、可研究验证、可供团队直接 clone 运行的完整产品：包含多模型与检查历史、可追溯规则执行、完整中英双语、直观的 3D 协同工作区、可审计的中英文自然语言查询、报告/BCF 交换、自动化测试和真实浏览器验证。

这不是建筑审批、法律意见或官方认证软件。界面、报告和文档必须持续保留这一边界。

---

## 1. 开始工作前

### 1.1 Git 边界

- 目标分支：`product/full-platform`
- 远端分支：`origin/product/full-platform`
- 起点提交：`375a7b3f7f79551812863ac2b38c8ea3771d43b7`
- 远端仓库：<https://github.com/ralin0225/ifc-bidirectional-compliance-mvd>
- 不要在 `main` 上实现，不要重写或强推 `main`。
- 开始时先运行：

```text
git branch --show-current
git status --short --branch
git log -5 --oneline --decorate
git remote -v
```

若当前目录不是目标分支的工作树，先定位正确工作树；不要在错误目录继续。

### 1.2 自主权限与持续目标

- 用户已批准本项目范围内的一切正常编辑、安装、测试、浏览器验证、commit 和 push，不要反复询问编辑许可。
- 所有新工具和依赖都必须项目局部安装、版本锁定且可删除；禁止污染系统级 Python、Node 或 PATH。
- 用户要求持续优化至 Codex 周额度约剩余 8%。如果运行环境提供可信的额度读取能力，建立 active goal 并在约 8% 时安全收尾；如果不能读取，绝不猜测或伪造百分比，改为以本 handoff 的验收标准为完成条件，并在最终报告中说明额度不可见。
- 每个实质里程碑应形成小而清晰的 commit，并 push 到 `origin/product/full-platform`。
- 不要为了制造提交数量拆分没有意义的 commit。

### 1.3 公开仓库安全

任何 tracked 文件、Git 提交、测试快照、报告和日志中都不得出现：

- 用户或开发机的本地绝对路径；
- token、cookie、密码、API key、会话、GitHub credential；
- `.env`、虚拟环境、`node_modules`、运行数据库、上传缓存；
- 版权受限的完整 IBC PDF；
- 未确认再分发许可的大型 IFC 模型；
- 浏览器配置、个人账户信息或机器标识。

文档和代码必须只使用仓库相对路径、环境变量或运行时生成路径。每次 push 前执行路径、secret、大文件和许可证扫描。

---

## 2. 已实现基线：不要重复造轮子

基线是一个可工作的研究 MVD，不是空项目。当前事实如下：

- Python 3.11–3.13、FastAPI、IfcOpenShell 0.8.3、IfcTester 0.8.3。
- 2021 IBC 三条人工复核规则：
  - §1010.1.1 疏散门净宽；
  - §1010.1.1 疏散门净高；
  - §1003.2 疏散空间净高。
- buildingSMART IDS 1.0 用于信息质量/可检查性。
- 确定性状态：`PASS`、`FAIL`、`NOT_APPLICABLE`、`NOT_CHECKABLE`；数据模型已经预留 `MANUAL_REVIEW_REQUIRED`。
- rule → elements 与 element → rules 双向 REST API。
- `GlobalId` 对齐 API、结果表、证据、关系图和三维 mesh。
- 无 CDN 的原生 WebGL viewer，支持状态着色、筛选、拾取、证据面板和局部 provenance graph。
- 可重建的约 14 KB IFC4 合成夹具，10 个构件、15 个 ground-truth 结果。
- `reports/acceptance.md` 记录的基线结果为 `18 passed`，并记录了 clean-clone 和浏览器验收。
- Windows/macOS/Linux 启动脚本会在仓库内创建 `.venv`；核心运行不要求 Node、Docker、Neo4j、IBC PDF 或 API key。

主要入口：

```text
README.md
reports/acceptance.md
docs/architecture.md
docs/limitations.md
docs/decisions/
src/ifc_compliance_mvd/
frontend/
data/regulations/
data/ids/
data/models/generated/
tests/
```

首先阅读这些文件并实际运行测试。新工作树最初没有 `.venv`；直接调用未安装依赖的系统 Python 报缺少 `pytest` 是正常现象，不代表基线损坏。

建议首次验证：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install -e . --no-deps
.\.venv\Scripts\python -m pytest
```

macOS/Linux 使用 `.venv/bin/python`。不要把 `.venv` 提交。

---

## 3. 产品原则

以下原则不可因技术重构而删除：

1. 法规来源、版本、条款、结构化解释、适用性、例外、信息需求、执行方法和结果必须可追溯。
2. IDS/信息质量与法规合规判定必须分离。
3. 运行时最终状态必须由可测试、可重复的确定性查询或计算产生；LLM 不得直接宣布合规。
4. 同时支持 `rule → elements` 和 `element → rules`，并将二者做成真实的协调交互。
5. 每个结果都要展示证据、算法、输入、单位、阈值、版本和失败/未知原因。
6. 缺失信息不能当成 `FAIL`；无法可靠自动化的情况应进入 `NOT_CHECKABLE` 或 `MANUAL_REVIEW_REQUIRED`。
7. IFC `GlobalId` 继续作为跨后端、前端、BCF 和报告的主要构件标识。
8. 默认安装和演示必须零外部服务、零 API key、零手工建库。
9. 所有新能力必须提供自动化测试、真实浏览器验证或明确的人工验收证据。
10. 功能深度优先于首页堆叠；实现一个可靠的产品闭环，再扩大规则和模型数量。

---

## 4. 目标产品信息架构

最终界面应至少具有以下产品级区域；可以调整导航名称，但能力不能丢失：

### 4.1 项目与模型

- 创建/打开本地项目；
- 导入一个或多个 IFC；
- 模型元数据、schema、单位、hash、许可证/来源和导入诊断；
- IFC2X3、IFC4，条件允许时覆盖 IFC4.3；
- 空间结构、楼层、类别、类型和属性索引；
- 模型版本与联邦模型概念；
- 原始模型与生成/变异模型 provenance。

### 4.2 检查运行

- 选择模型、规则集和参数后创建检查运行；
- 运行历史、状态、耗时、checker/rule/model 版本；
- 两次运行或两个模型版本的结果差异；
- 可恢复的错误与部分成功状态；
- 稳定的 run URL；
- JSON、CSV、HTML/打印报告，合适时导出 BCF 3.0 `.bcfzip`。

### 4.3 规则目录

- 条款、规则、适用性、例外、信息要求、自动化等级、review 状态；
- IDS 结果与法规结果分栏显示；
- 规则版本和人工复核记录；
- 从规则定位构件、从构件返回规则；
- 不要把规则全部硬编码进 Python 分支。

### 4.4 3D 合规工作区

- 3D 视图是核心分析工作区，不是装饰性模型预览；
- 模型树/空间层级、结果列表、属性/证据、规则详情与 3D 选择必须双向联动；
- 详细要求见第 7 节。

### 4.5 自然语言查询

- 用户可用简体中文或英语提问；
- 每个回答都通过结构化查询和确定性数据检索得到；
- 显示解析意图、可编辑查询、证据和不确定性；
- 详细要求见第 8 节。

### 4.6 设置与帮助

- 全局语言切换；
- 颜色和可访问性选项；
- 数据、隐私、可选 LLM adapter 状态；
- 版本、许可证、局限和“非认证工具”声明；
- 示例工作流与快捷键。

---

## 5. 推荐运行时架构

先写 ADR 再做不可逆重构。推荐演进方向如下，但若研究和原型数据支持更好的方案，可以调整：

```text
IFC / generated fixtures
  → import + validation + normalized index
  → versioned project/model store
  → IDS information-quality layer
  → applicability layer
  → deterministic property/relation/geometry/topology checkers
  → versioned results + evidence + provenance
  → SQLite query/read model
  → FastAPI/OpenAPI
  → localized product UI + coordinated 3D workspace
  → deterministic NL query DSL
  → reports / BCF / comparison
```

### 5.1 数据持久化

使用仓库启动时自动创建的 SQLite 或同等级嵌入式方案，至少支持：

- projects；
- models 与 model_versions；
- elements 与 spatial/semantic indexes；
- rule_sets、rules、rule_versions；
- check_runs、results、evidence；
- provenance nodes/edges；
- saved queries 或 recent queries；
- issues/BCF mappings。

数据库 schema 必须有 migration；启动时自动初始化。默认数据库和上传内容是 runtime data，不进入 Git。当前内存 graph 可以保留为投影层，但不得继续作为全部历史的唯一存储。

### 5.2 后台任务

小模型可以同步执行；真实模型的导入、网格转换和检查应具备明确 job 状态、进度、取消/失败处理。不要为了“企业感”立即引入 Redis/Celery 等外部服务。优先使用应用内、可持久化、可测试且零配置的任务机制，并用 ADR 记录未来扩展边界。

### 5.3 插件边界

为 checker、metric extractor、exporter 和可选 NL provider 设计稳定接口。规则数据、适用性、计算器和展示文本不能相互缠绕。

---

## 6. 规则、法规和模型

### 6.1 规则扩展

在现有三条规则外构造一个“代表性而非假装完整”的规则集，至少覆盖：

- entity/type；
- attribute/property；
- classification；
- relationship；
- geometry；
- spatial/topology；
- path/egress；
- 需要人工判断的规则。

每条规则必须有：

- 稳定 `rule_id` 与语义版本；
- 法规文档、edition、chapter/section/page；
- 合理限度内的短摘录；
- 本项目采用的计算解释；
- target、applicability、exceptions；
- required information；
- unit、operator、threshold 或计算表达；
- fallback 和异构 IFC 映射；
- automation level；
- `human_verified`、`candidate` 或等价 review 状态；
- 已知误报/漏报风险。

不要声称覆盖完整 IBC。读取受版权保护 PDF 时只提取完成规则复核必需的局部信息，不提交原 PDF。

### 6.2 模型策略

- 保留现有合成 IFC 作为稳定单元/边界测试夹具。
- 至少增加一个许可证明确、来源可核查的现实 IFC 模型作为集成/性能验证。
- 大模型若不适合进 Git，可提供固定 URL、checksum、许可证、下载脚本和离线 fallback；核心演示仍必须不依赖下载。
- 若修改模型，生成 original → mutation 的 manifest，记录改动元素、预期状态和脚本版本。
- 不能覆盖用户原始 IFC。
- 为 IFC2X3/IFC4 命名、类型继承、property fallback 和单位差异建立测试。

### 6.3 评估

每条已发布规则至少有：

- PASS；
- FAIL；
- NOT_CHECKABLE；
- 阈值边界；
- 适用时的 NOT_APPLICABLE；
- 适用时的 MANUAL_REVIEW_REQUIRED。

建立人工可读 ground truth、mutation benchmark、混淆统计和案例级误差说明。ground truth 不能由生成 checker 的同一模型无复核地产生。

---

## 7. 3D Visualization：研究后重做

### 7.1 先研究，不要先换库

研究 2024–2026 的实际产品、官方文档和源码，形成：

```text
docs/research/2024-2026-viewer-landscape.md
docs/decisions/NNNN-viewer-architecture.md
```

至少比较：

- 当前原生 WebGL；
- That Open Engine / Components；
- xeokit；
- Speckle Viewer；
- BIMData Viewer；
- Autodesk Platform Services Viewer 作为交互基准；
- BCF/issue viewer 的问题定位模式。

比较维度至少包括：

- IFC 直接加载与预转换；
- 大模型/流式加载；
- 模型树和语义数据；
- 选择、框选、筛选、着色；
- hide/isolate/ghost；
- 剖切、楼层、测量；
- 多模型、坐标精度；
- BCF viewpoint；
- 移动端、键盘和可访问性；
- 包体、离线能力、维护状态；
- 开源许可证与本仓库 MIT 兼容性；
- Python 后端集成复杂度；
- 测试能力和长期维护风险。

不要仅因某库功能多就迁移；用小型 spike、性能数据、许可证和维护风险做决定。

### 7.2 必须实现的交互

- 空间层级：Project → Site → Building → Storey → Space/Element；
- 按楼层、IFC 类别、规则、状态筛选；
- select、hover、框选；
- fit selection / fit model；
- hide、isolate、show all、ghost context；
- 正交/透视和标准相机方向；
- 至少一个实用剖切面；
- 距离测量；面积/角度可根据技术选型追加；
- 属性、type、pset、classification、关系与合规证据面板；
- 状态 overlay，不只依赖红绿；图例必须含文本/形状或纹理；
- 问题列表点击定位、3D 点击反向选择列表；
- 搜索 GlobalId、名称、类别、属性；
- 清楚的 loading、progress、empty、error、WebGL unavailable 状态；
- 渐进加载或至少避免主线程长期无响应；
- 键盘焦点、可见 focus、ARIA 文本和 reduced-motion；
- 保存/恢复 camera + visibility + selection，供稳定 URL/BCF viewpoint 使用。

### 7.3 视觉设计

使用 `frontend-design` 指导视觉系统，使用真实浏览器反复截图验证。界面应像一个专注的 BIM 分析工作台：

- 信息密度高但层级清晰；
- 关键操作靠近 3D 工作区；
- 不堆叠无作用的统计卡片；
- desktop 与窄屏都无横向溢出；
- 深浅主题不是硬要求，但对比度和状态可读性是硬要求；
- 不以颜色作为唯一语义；
- loading 期间保持布局稳定。

---

## 8. 中英文自然语言查询

### 8.1 核心设计

采用：

```text
Chinese/English utterance
  → locale-aware parser
  → validated query DSL
  → deterministic SQLite/domain query
  → cited result rows/evidence
  → localized explanation
```

核心功能不得依赖 LLM 或 API key。先实现词典、模式、实体解析、过滤器和 query builder。可选 LLM 只能生成候选 DSL，随后必须做 JSON Schema/Pydantic 校验、权限/复杂度限制，再由确定性查询执行。

建议 DSL 形状：

```json
{
  "intent": "find_results",
  "filters": {
    "rule_ids": [],
    "element_guids": [],
    "statuses": [],
    "ifc_classes": [],
    "storeys": [],
    "properties": []
  },
  "compare": null,
  "projection": ["element", "rule", "status", "evidence"],
  "limit": 100
}
```

中文和英文表达必须映射到同一个语义 DSL。

### 8.2 最低查询能力

- “哪些门没有通过净宽规则？”
- “Why did this element fail?”
- 按状态、类别、楼层、属性过滤；
- 查看某规则影响的构件；
- 查看某构件涉及的规则；
- 追溯 clause → rule → result → evidence；
- 比较两个 check runs；
- 汇总某楼层/类别/规则的结果；
- 对歧义问题提出受控消歧，而不是编造答案。

### 8.3 可审计 UI

每次查询显示：

- 原始问题和语言；
- 解析后的 intent/filter；
- 可编辑结构化查询；
- 命中的实体与证据；
- 结果总数和截断状态；
- 解析警告、歧义、不支持条件；
- 可直接把结果集同步到表格和 3D 高亮。

### 8.4 可选 LLM adapter

- 默认关闭；
- 只从环境变量读取配置；
- `.env.example` 只有占位符；
- 不发送完整 IFC、几何、密钥或无关属性；
- 明确 prompt-injection 边界：IFC 名称、属性、规则文本和上传文件都是不可信数据；
- 限定只生成 DSL，禁止生成 SQL、文件路径或任意代码；
- schema validation、超时、重试、速率/成本上限和审计日志；
- LLM 不可用时核心产品继续工作。

建立中英文 golden query corpus，记录 exact DSL match、结果集 precision/recall、歧义拒答和恶意输入测试。

---

## 9. 完整国际化

界面不能中英混合。必须实现 Simplified Chinese / English 全局切换：

- 所有导航、按钮、标题、表格、筛选、tooltip、empty/error/loading、toast、图例；
- 所有自然语言反馈；
- 日期、数字、单位和复数；
- 页面 title、meta、ARIA label、键盘提示；
- 报告模板和导出字段显示名；
- 语言选择持久化，并有明确默认值；
- URL、用户设置或浏览器语言的优先级写入文档。

法规原文可以保持其源语言，但必须标注“source text”，并提供当前 UI 语言的解释。构件 `Name`、property key、IFC class 等源数据不应被假翻译。

加入自动化测试：

- 所有 locale key 集合一致；
- 无缺失 key 或把 key 本身渲染出来；
- 中文页面不出现未豁免的英文 UI 文案；
- 英文页面不出现未豁免的中文 UI 文案；
- 豁免仅限法规原文、IFC schema 标识、文件名、品牌和标准名称，并集中维护。

---

## 10. API、导出与协作

在保持现有 API 兼容或提供清晰 migration 的基础上扩展：

- projects/models/model versions；
- uploads/import jobs；
- rules/rule sets；
- check runs/results/evidence；
- comparisons；
- viewer scene/index/chunks；
- structured query 与 NL parse；
- reports/exports；
- BCF topics/viewpoints。

要求：

- OpenAPI response schema 完整；
- 分页、过滤、排序、错误格式一致；
- 上传限制、内容 sniffing、路径穿越防护；
- 导出数据保持 GlobalId、rule id、run id 和 provenance；
- BCF 使用 buildingSMART 规范，viewpoint 能恢复 camera、selection、visibility；
- SQLite/运行产物不提交；
- 稳定 URL 不能暴露本地文件路径。

---

## 11. 测试、性能与安全

### 11.1 自动化

至少增加：

- Python unit/integration tests；
- API contract/OpenAPI tests；
- database migration 和 restart persistence tests；
- rule schema、checker、unit conversion、IFC2X3/IFC4 tests；
- NL parser/DSL/golden-result tests；
- i18n completeness/mixed-language tests；
- 前端 unit tests；
- Playwright 或同等级 E2E；
- BCF round-trip tests；
- malicious upload/query tests；
- deterministic fixture regeneration hashes。

建立 CI，在 Windows 和 Linux 至少覆盖核心安装与测试。不要让 CI 依赖私有模型、用户 PDF 或 secrets。

### 11.2 浏览器验收

必须用真实浏览器完成并记录：

- 中文完整主流程；
- 英文完整主流程；
- 模型导入与运行；
- rule → element；
- element → rule；
- 3D 选择、筛选、隐藏/隔离、剖切、测量；
- NL 查询同步 3D；
- run compare；
- 报告/BCF 导出；
- 390×844 窄屏；
- console error/warning；
- 键盘与可访问性基本流程。

视觉重构要保留关键截图或可复现的截图测试，但不要提交包含本地路径或个人信息的浏览器画面。

### 11.3 性能

先建立硬件/浏览器/模型规模明确的基线，再用 ADR 设预算。至少记录：

- IFC 导入/索引时间；
- scene payload/chunk 大小；
- first useful render；
- 选择/筛选响应；
- 3D FPS 或长任务；
- 单条与整批 checker 时间；
- SQLite query latency；
- 内存峰值；
- NL parse/query latency。

合成夹具的快速成绩不能代表真实模型。性能结论必须注明模型、构件数、三角形数、机器和浏览器。

### 11.4 安全

- 限制上传大小、扩展名、MIME、解析时间和资源；
- 防止路径穿越、ZIP bomb、BCF 外部引用和 HTML 注入；
- 所有 IFC/规则/BCF 文本以不可信输入处理；
- 禁止任意 SQL、Python、shell 或模板执行；
- 前端使用安全 DOM API，必要时设置 CSP；
- optional LLM adapter 有数据最小化和 prompt-injection 测试；
- 执行 dependency、secret、license 和大文件扫描。

---

## 12. 研究与一手资料起点

新对话必须自行核验访问日期、版本、许可证和论文状态。以下是起点，不是可复制的结论。

### 12.1 规范与官方实现

- buildingSMART 技术标准入口：<https://technical.buildingsmart.org/>
- buildingSMART IDS 官方仓库：<https://github.com/buildingSMART/IDS>
- buildingSMART BCF 说明：<https://technical.buildingsmart.org/standards/bcf/>
- buildingSMART BCF-XML 官方仓库：<https://github.com/buildingSMART/BCF-XML>
- IFC 规范：<https://ifc43-docs.standards.buildingsmart.org/>
- IfcOpenShell / IfcTester：<https://docs.ifcopenshell.org/>

### 12.2 Viewer 官方资料与源码

- That Open 文档：<https://docs.thatopen.com/>
- That Open Components 源码：<https://github.com/ThatOpen/engine_components>
- xeokit SDK：<https://xeokit.github.io/sdk/>
- xeokit SDK 3 white paper：<https://xeokit.github.io/sdk/userguide/whitepaper/index.html>
- Speckle Viewer 文档：<https://docs.speckle.systems/developers/viewer/introduction>
- Speckle Viewer 源码：<https://github.com/specklesystems/speckle-server/tree/main/packages/viewer>
- BIMData Viewer 文档：<https://developers.bimdata.io/viewer/>
- Autodesk Viewer SDK：<https://aps.autodesk.com/developer/overview/viewer-sdk>

Autodesk 等商业/云产品可作为交互和能力基准，不代表应作为本项目依赖。优先保证本地可复现和开源许可兼容。

### 12.3 近年 NL/IFC 研究候选

- *A natural-language-based approach to intelligent data retrieval and representation for cloud BIM*（2024）：<https://arxiv.org/abs/2411.09951>
- *Enabling Natural Language Access to BIM Models with AI*（2025）：<https://ceur-ws.org/Vol-3979/short3.pdf>
- *MCP4IFC: IFC-Based Building Design Using Large Language Models*（2025）：<https://arxiv.org/abs/2511.05533>
- *Language Models as BIM Interpreters: Unlocking IFC Data for Automation in Construction Informatics*（2025 working paper）：<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5563440>
- *BIM Information Extraction Through LLM-based Adaptive Exploration*（2026 preprint，并提供 ifc-bench v2 方向）：<https://arxiv.org/abs/2605.01698>
- *A Hybrid Framework for Natural Language Querying of IFC Models with Relational and Graph Representations*（2026 preprint）：<https://arxiv.org/abs/2605.13236>

引用时明确区分 peer-reviewed paper、conference short paper、working paper 和 preprint。重大决策优先使用标准、正式论文、官方文档和可复现实验；产品营销页不能充当研究证据。

研究输出至少包括：

```text
docs/research/2024-2026-viewer-landscape.md
docs/research/2024-2026-natural-language-ifc.md
docs/research/model-and-license-register.md
```

每份文档列出访问日期、来源类型、关键发现、对本项目的影响和没有被证据支持的部分。

---

## 13. 分阶段实施顺序

不要等全部研究完成才写代码；每阶段都交付可运行的垂直切片。

### Phase 0：基线审计与决策

- 安装、测试、启动和浏览器复验 MVD；
- 列出现有技术债、路径耦合和产品缺口；
- viewer、frontend、persistence、job、i18n、NL DSL 写 ADR；
- 建立 CI、前端工具链和测试骨架。

### Phase 1：产品壳、持久化与双语

- 项目/模型/运行的 SQLite schema 与 migration；
- 产品导航、设置、完整中英资源；
- 现有 MVD 能力迁入新壳且测试不回退；
- clone 后一条命令仍可启动。

### Phase 2：多模型、运行历史与规则扩展

- import/index/jobs；
- check runs、比较、稳定 URL；
- 代表性规则、IFC2X3/IFC4、现实模型和 mutation benchmark；
- IDS/applicability/checker/manual-review 边界。

### Phase 3：3D 分析工作区

- 根据研究和 spike 选择 viewer；
- 模型树、筛选、选择、属性、证据和问题列表联动；
- isolate/ghost/section/measure/camera；
- 性能与可访问性；
- 真实浏览器截图迭代。

### Phase 4：自然语言查询

- 双语 parser、DSL、deterministic executor；
- 3D/results 同步；
- golden corpus 和评估；
- 可选、默认关闭的 LLM adapter。

### Phase 5：协作与输出

- run comparison；
- JSON/CSV/HTML/打印；
- BCF 3.0 viewpoint/topic；
- OpenAPI 和开发者文档。

### Phase 6：全面硬化

- E2E、性能、安全、许可证；
- Windows/Linux clean-clone；
- 路径/secret/大文件扫描；
- 文档、截图、演示脚本；
- 最终验收与限制报告。

每一阶段结束都应运行相关测试、更新研究/ADR、commit 并 push。

---

## 14. 完成定义

只有存在可核查证据时才能勾选：

### 产品能力

- [ ] 多模型导入、索引和持久化；
- [ ] 可查看和比较检查历史；
- [ ] 代表性规则覆盖属性、关系、几何、拓扑/路径和人工判断；
- [ ] IDS 与法规判定严格分层；
- [ ] rule ↔ element 双向链完整；
- [ ] 3D 工作区具备模型树、联动、隔离、剖切、测量和状态 overlay；
- [ ] 简体中文/英语完整切换，无非豁免混合文案；
- [ ] 中英文 NL → validated DSL → deterministic evidence；
- [ ] JSON、CSV、HTML/打印和 BCF 输出；
- [ ] 现实模型与许可/来源登记。

### 质量

- [ ] Windows/Linux 一条命令启动；
- [ ] 核心无 API key、Docker、数据库服务器或手工设置；
- [ ] migrations 自动运行；
- [ ] unit/integration/E2E/browser/security/performance tests；
- [ ] clean-clone 验证；
- [ ] 关键流程真实浏览器验证；
- [ ] console 无未解释错误；
- [ ] 路径、secret、license 和大文件扫描通过；
- [ ] 所有依赖锁定；
- [ ] OpenAPI、架构、规则编写、测试、限制、研究和 ADR 更新；
- [ ] tracked worktree 干净；
- [ ] 所有里程碑已 push 到 `origin/product/full-platform`。

### 诚实性

- [ ] 未声称完整覆盖 IBC；
- [ ] 未声称官方认证或法律可靠性；
- [ ] preprint/working paper 没有冒充同行评审论文；
- [ ] 小夹具性能没有冒充真实模型性能；
- [ ] LLM 没有直接决定合规状态；
- [ ] 未伪造 Codex 剩余额度。

---

## 15. 最终报告

最终不要只写“完成”。报告至少包含：

1. 分支、最终 commit 和远端状态；
2. 实际技术栈与关键 ADR；
3. 已实现产品功能；
4. 使用/生成的 IFC、schema、来源、许可证和 checksum；
5. 规则、条款、自动化等级与已知局限；
6. IDS、适用性、checker、manual review 的边界；
7. 几何/拓扑/路径算法与验证；
8. 数据模型、migration、API；
9. 中英 i18n 验证；
10. viewer 研究、选型、性能和浏览器截图验证；
11. NL DSL、查询能力、golden corpus 和评估；
12. JSON/CSV/HTML/BCF 输出；
13. 测试命令、数量、结果和 CI；
14. 性能数据及测量条件；
15. clean-clone、路径/secret/license/大文件扫描；
16. 与起点 MVD 的差异；
17. 未完成项、风险和最有价值的下一步；
18. 是否能真实读取 Codex 周额度；不能则明确写“不可见”，不要给估计值。

---

## 16. 新对话的第一轮动作

按以下顺序直接开始：

1. 确认目标 branch/worktree 和干净状态；
2. 完整阅读本 handoff、README、acceptance、architecture、limitations 和现有 ADR；
3. 建立 active goal；
4. 安装本地依赖并复跑基线测试；
5. 启动服务，用浏览器复验当前 MVD；
6. 输出简短的基线差距表和分阶段计划；
7. 立即实现 Phase 0/1 的第一个可运行垂直切片；
8. 测试、commit、push；
9. 按阶段持续迭代，不要停在研究报告、静态 mockup 或半成品 scaffold。

如果某项建议与实验证据冲突，允许改变方案，但必须写 ADR，记录原方案、证据、新方案、优缺点、迁移影响和复现方式。
