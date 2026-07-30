# ADR 0009：本地 IFC 导入使用持久化轻量 job

- 状态：Accepted
- 日期：2026-07-30

## 背景

完整平台需要导入多个 IFC、在重启后保留模型和诊断，并让较慢的解析过程有明确状态。引入 Redis/Celery 会破坏零服务启动；直接把用户文件名拼入路径、仅检查扩展名或在请求事务里静默解析则不满足公开仓库和不可信上传边界。

## 决策

- `POST /api/import-jobs` 接收单个 raw IFC body。`filename`、来源和许可是受长度限制的 metadata；不用 multipart，因而不新增上传解析依赖。
- API 在写盘前同时限制声明和实际 body 为 20 MiB，并检查 `.ifc`、允许的 media type、`ISO-10303-21`、`FILE_SCHEMA` 和完整 STEP terminator。
- 原文件名永不成为目录。暂存路径只使用服务端生成的 `import-<uuid>`，最终模型 ID 为完整 `model-<sha256>`，最终路径只由该 ID 构造。
- SQLite schema v3 保存 `import_jobs`、模型导入 metadata 和规范化 element index；v4 把查询历史关联到 model id。
- Starlette `BackgroundTasks` 在应用内线程执行导入，不需要外部 broker。job 使用原子 `QUEUED → VALIDATING` claim；只有尚未 claim 的 job 可以安全取消。重启时未完成 job 明确转为 `FAILED / PROCESS_RESTARTED`。
- IfcOpenShell 成功解析且 schema 为 IFC2X3 或 IFC4 系列后，索引所有带 `GlobalId` 的 `IfcProduct`，保存 class、name、pset 和空间路径。相同 SHA-256 复用已有模型，不覆盖原文件。
- 检查引擎接收显式 `model_id`；scene、IDS、rules/results、NL query 和 check run 都可绑定模型。默认仍是可重建夹具，保持旧 URL/API 可用。

## 安全边界

公开 API 不返回内部 `stored_path`。解析失败只返回稳定错误码和无路径公开文案。IFC names、properties、source 和 licence 都是不可信显示数据，前端继续经过 HTML escaping。

当前 20 MiB 限制可以约束内存和常见滥用，但应用内 IfcOpenShell 仍不是 OS 级资源沙箱，不能强杀卡死的 native parser。对公开互联网开放前必须把 parse/index 放入带 wall-clock、CPU、memory 和文件系统限制的 worker process；这不需要改变 job API。

## 影响

优点是 clone 后仍零配置、job 与模型可审计、重复内容确定性去重。代价是单进程吞吐有限、只有 queued cancellation、没有上传分块/续传和模型版本 UI。数据库与上传目录均在被 Git 忽略的 runtime 根下。
