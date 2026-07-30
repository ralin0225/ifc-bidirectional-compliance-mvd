import re

from ifc_compliance_mvd.paths import FRONTEND_PATH


def test_frontend_has_no_external_runtime_dependency():
    html = (FRONTEND_PATH / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND_PATH / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"""(?:src|href)=["']https?://""", html)
    assert "cdn" not in html.lower()
    assert "/api/rules" in javascript
    assert "/api/scene" in javascript
    assert "/api/scene/manifest" in javascript
    assert "/api/scene/chunks/" in javascript
    assert "/api/graph/ego" in javascript
    assert "/export?format=" in javascript


def test_frontend_exposes_coordinated_views():
    html = (FRONTEND_PATH / "index.html").read_text(encoding="utf-8")
    for required_id in (
        'id="ruleList"',
        'id="viewer"',
        'id="evidencePanel"',
        'id="resultsBody"',
        'id="graph"',
        'id="queryForm"',
        'id="queryResults"',
        'id="modelTree"',
        'id="modelSearch"',
        'id="toggleProjection"',
        'id="toggleSection"',
        'id="toggleMeasure"',
        'id="saveView"',
        'id="importForm"',
        'id="ifcFile"',
        'id="modelsBody"',
    ):
        assert required_id in html


def test_viewer_supports_auditable_review_tools():
    javascript = (FRONTEND_PATH / "app.js").read_text(encoding="utf-8")
    for capability in (
        "renderModelTree",
        "hideSelection",
        "isolateSelection",
        "orthographic",
        "uClipEnabled",
        "measurePoints",
        "encodeViewpoint",
        "restoreViewpoint",
        "append(elements)",
    ):
        assert capability in javascript


def test_frontend_publishes_browser_performance_diagnostics():
    javascript = (FRONTEND_PATH / "app.js").read_text(encoding="utf-8")
    for metric in (
        "firstUsefulRenderMs",
        "lastSelectionPaintMs",
        "lastFilterPaintMs",
        "viewerFps",
        "viewerLongTaskCount",
        "viewerLongTaskTotalMs",
    ):
        assert metric in javascript
