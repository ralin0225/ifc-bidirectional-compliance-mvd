import re

from ifc_compliance_mvd.paths import FRONTEND_PATH


def test_frontend_has_no_external_runtime_dependency():
    html = (FRONTEND_PATH / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND_PATH / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"""(?:src|href)=["']https?://""", html)
    assert "cdn" not in html.lower()
    assert "/api/rules" in javascript
    assert "/api/scene" in javascript
    assert "/api/graph/ego" in javascript


def test_frontend_exposes_coordinated_views():
    html = (FRONTEND_PATH / "index.html").read_text(encoding="utf-8")
    for required_id in (
        'id="ruleList"',
        'id="viewer"',
        'id="evidencePanel"',
        'id="resultsBody"',
        'id="graph"',
    ):
        assert required_id in html
