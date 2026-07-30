# ADR 0010：受控夹具性能仪表与回归预算

- 状态：Accepted
- 日期：2026-07-30

## 背景

没有可复现基线时，“快”无法审计；但 14 KiB 合成 IFC 的成绩也不能外推到现实模型。handoff 要求同时记录导入、scene、浏览器、checker、SQLite、内存和 NL latency。

## 决策

1. `scripts/benchmark_model.py` 默认对固定 IFC 进行 warm-up 后重复测量，也可接收有独立 provenance 登记的外部 IFC，输出机器可读 JSON。
2. 前端通过 User Timing 与 `<html>` runtime dataset 发布 first-useful-render、选择/筛选到下一次绘制、主动 viewer FPS 和 long-task 指标；不上传遥测。
3. `reports/performance-baseline.md` 保存一次明确环境的基线和只适用于受控夹具的宽松回归预算。
4. 预算采用 P95（FPS 采用 minimum）：
   - import/index ≤ 250 ms；
   - batch checker ≤ 50 ms；
   - scene build ≤ 100 ms，payload ≤ 25 KiB；
   - SQLite run read ≤ 20 ms；
   - NL parse/query ≤ 10 ms；
   - Python managed peak ≤ 1 MiB；
   - first useful render ≤ 1,000 ms；
   - selection/filter paint ≤ 100 ms；
   - active viewer ≥ 50 FPS；
   - 1 秒采样 long-task total ≤ 200 ms。
5. 现实模型预算必须在许可证、来源、checksum、模型规模和硬件/浏览器环境齐全后另立 ADR；不得复用上述阈值形成产品性能声明。

## 结果

回归有了可重复测量入口，浏览器性能可从真实 UI 读取且不引入第三方分析服务。代价是基线脚本增加少量维护面，浏览器数字仍受机器负载影响；因此预算故意留有余量并要求多次采样。
