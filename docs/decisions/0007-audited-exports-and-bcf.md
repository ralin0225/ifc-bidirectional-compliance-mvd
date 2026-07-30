# ADR 0007：运行输出以审计结果为唯一来源

- 状态：Accepted
- 日期：2026-07-30

## 背景

完整平台需要 JSON、CSV、HTML/打印和 BCF 3.0 输出。不同 exporter 若重新计算结果，可能与浏览器、API 和历史记录漂移；BCF/ZIP 和 HTML/CSV 还引入路径穿越、解压炸弹、脚本与公式注入风险。

## 决策

所有输出只读取 SQLite 中已完成的 check run，不重新执行 checker。四种格式都保留 run id、execution id、model id、rule id、GlobalId 和 evidence：

- JSON 是完整、版本化的机器可读审计 payload；
- CSV 将 evidence details 序列化为 JSON，并转义电子表格公式前缀；
- HTML 使用转义后的本地内容和打印 CSS，不加载外部资源或脚本；
- BCF 3.0 为每个失败、不可检查或人工复核结果生成 topic 和 viewpoint，selection 使用 IFC `GlobalId`。

BCF UUID、ZIP 顺序和时间戳确定化，使相同运行得到相同字节。导入检查使用 `defusedxml` 并拒绝不安全 ZIP 成员、过大解压内容和悬空 viewpoint。

## 限制

当前 camera 是稳定的通用透视视点，不是用户浏览器中的实时 camera；没有 snapshot、comment workflow 或 BCF 回写。后续 viewer camera/visibility/section state 持久化后再替换为用户实际 viewpoint。
