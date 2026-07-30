# 测试策略

## 测试分层

```text
JSON Schema / rule unit tests
        ↓
IFC property + geometry unit tests
        ↓
untrusted import + migration tests
        ↓
manual ground truth comparison
        ↓
IDS validation
        ↓
bidirectional API integration tests
        ↓
frontend contract + browser smoke test
```

运行：

```powershell
.\.venv\Scripts\python -m pytest
```

## 人工 ground truth

`tests/expected/ground_truth.csv` 包含 15 个 `(model, GlobalId, rule)` 判定。夹具和 ground truth 由脚本写出，但预期状态在脚本中逐例人工声明，不由检查器回填。

每条规则都有：

- 明显 PASS；
- 阈值相等的边界 PASS；
- 明显 FAIL；
- 适用但必要信息缺失的 NOT_CHECKABLE；
- 明确不适用的 NOT_APPLICABLE。

## 重要断言

- 规则库通过 JSON Schema，且三条规则均为 `human_verified`。
- 规则阈值与选定 IBC 条款的人工复核记录一致。
- `NOT_CHECKABLE` 的 `measured_value` 始终为空，不能变成 FAIL。
- 几何规则保存 bbox、顶点和三角形证据。
- IDS 对三个缺失信息夹具各识别一个失败实例。
- rule → elements 的实例能从 element → rules 反向查回同一规则。
- 三维 scene 的每个 mesh 都能通过 IFC `GlobalId` 对齐。
- scene manifest/chunks 保持稳定 GlobalId 顺序、每块上限、无重复/遗漏和越界 404。
- 并发首屏请求只构造一次 imported-model engine。
- 同一输入连续运行得到相同结果与 execution ID。
- 前端不包含 CDN 或外部运行依赖。
- 上传在 IfcOpenShell 之前拒绝路径文件名、非 IFC 扩展、错误 MIME、缺失 STEP envelope 和超限 body。
- import job、模型 metadata 和语义索引在 SQLite 重启后保留；中断 job 显式失败。

## 夹具再生的确定性

`scripts/generate_fixture.py` 固定 IFC header、产品 GlobalId、属性集和关系 GlobalId。对同一脚本与 IfcOpenShell 版本，重复生成应得到相同文件哈希。依赖版本锁在 `pyproject.toml` 中。

## 性能 smoke baseline

```text
python scripts/benchmark_model.py --iterations 7
```

脚本输出 JSON，覆盖导入/索引、整批 checker、scene build/payload、SQLite、NL 查询和 Python 托管内存。真实浏览器的 first-useful-render、选择/筛选到下一次绘制、主动 FPS 与 long task 由前端 runtime dataset 发布。基线、环境和只适用于受控夹具的预算记录在 `reports/performance-baseline.md`；这些数字不得外推为现实项目性能。

## 手工浏览器验收

自动化测试通过后，还应执行：

1. 启动 `ifc-mvd serve`。
2. 检查页面无控制台错误。
3. 逐条选择三条规则，确认目标类别与状态颜色更新。
4. 点击一个网格与一行结果，确认选中对象一致。
5. 旋转和缩放模型，确认拾取仍可用。
6. 切换状态过滤器，确认表格和三维视图同步。
7. 检查 NOT_CHECKABLE 的原因明确说明数据缺失。
8. 检查 ego graph 节点点击可以回到规则或构件。
9. 在窄屏宽度检查面板改为单列且没有横向溢出。
10. 通过 file chooser 导入许可明确的合成 IFC，确认 job 完成/去重、模型登记和 model-scoped run。
11. 打开登记的现实 clinic IFC，确认首 100 elements 可先交互、最终加载 523 elements，并恢复 late-chunk element 的 isolate/viewpoint。
