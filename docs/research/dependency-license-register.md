# 直接依赖许可登记

- 核验日期：2026-07-30
- 证据：`requirements.lock` 安装后的 Python distribution metadata（version、License-Expression / License / Trove classifier）和各项目声明
- 边界：这是工程登记，不是法律意见；发布二进制或托管服务前仍需完整 SBOM/notice 与法律复核

## Runtime

| Distribution | 锁定版本 | metadata 许可 | 本项目用途 |
|---|---:|---|---|
| `defusedxml` | 0.7.1 | PSFL | 不可信 BCF XML 读取 |
| `fastapi` | 0.116.1 | MIT classifier | API |
| `ifcopenshell` | 0.8.3.post2 | LGPLv3+ classifier | IFC parse、几何、单位与语义 |
| `ifctester` | 0.8.3 | LGPLv3+ classifier | IDS 1.0 信息质量验证 |
| `jsonschema` | 4.25.0 | MIT expression | rule schema |
| `uvicorn` | 0.35.0 | BSD-3-Clause expression | 本地 ASGI server |

IfcOpenShell/IfcTester 的 LGPL 义务不能被仓库 MIT 许可证覆盖或改写；分发时必须保留其许可证/notice，并允许用户按适用条款替换或修改该依赖。

## Development / test only

| Distribution | 锁定版本 | metadata 许可 | 边界 |
|---|---:|---|---|
| `bcf-client` | 0.8.5 | GPLv3 classifier | 只在 `tests/unit/test_exports.py` 解析本项目生成的 BCF；`src/` 不 import `bcf` |
| `httpx` | 0.28.1 | BSD-3-Clause | FastAPI TestClient |
| `packaging` | 26.2 | Apache-2.0 OR BSD-2-Clause | repository audit 的 requirement 解析 |
| `pytest` | 8.4.1 | MIT | 自动化 |

`bcf-client` 有意放在 `[project.optional-dependencies].dev`，不列入 runtime dependencies。生产 exporter 自己写规范限定的 XML/ZIP，并用 `defusedxml` 做安全检查；如果未来把 GPL parser 引入 runtime，必须先做独立许可决策。

## 复核命令

```powershell
.\.venv\Scripts\python -c "from importlib.metadata import metadata; print(metadata('ifcopenshell').get_all('Classifier'))"
```

transitive dependency 仍以 `requirements.lock` 为准。最终发布前应从 clean environment 生成 machine-readable SBOM，并核对 metadata 缺失、双许可证和 vendored/WASM 内容；本登记不把“metadata 可读”误写成“所有许可风险已清零”。
