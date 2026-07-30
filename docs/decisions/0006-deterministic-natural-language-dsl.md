# ADR 0006：自然语言只生成受控 DSL

- 状态：Accepted
- 日期：2026-07-30

## 背景

用户需要用简体中文或英文查询规则、构件、状态和证据。直接让 LLM 生成 SQL、执行代码或声明合规会破坏可重复性、安全边界和审计链；核心产品也不能依赖 API key。

## 决策

用 locale-aware 词典和模式把 utterance 解析成 Pydantic `QueryDSL`。DSL 只允许固定 intent、domain filter、projection 和 1–200 的结果上限。执行器只遍历已验证的 domain result，不接收 SQL、代码、模板或路径。

选中的规则/构件属于受控上下文，但只有问题明确使用“这个构件 / this element”等指代或解释意图时才继承构件，避免无关或恶意文本借上下文变成可执行查询。无法识别结构化条件时返回 `NO_STRUCTURED_FILTERS`，结果集为空。

每次执行保存原问题、locale、已校验 DSL、warning 和结果数到 SQLite `query_history`。界面同时显示原问题输入、DSL、警告和 GlobalId 对齐结果；点击结果会同步规则、表格、证据与 3D。

## 影响

当前词典覆盖代表性而非开放域问题。它提供可测试的产品闭环和未来 adapter 契约。可选 LLM 只能提出候选 DSL，并必须通过同一 schema、domain identifier 和复杂度校验；LLM 不得直接决定合规。
