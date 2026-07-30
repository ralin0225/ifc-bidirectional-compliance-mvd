import json
import re
from xml.etree import ElementTree

from ifc_compliance_mvd.paths import FRONTEND_PATH, IDS_PATH
from ifc_compliance_mvd.rules import load_rule_collection


def test_locale_catalogs_have_identical_keys():
    catalogs = json.loads((FRONTEND_PATH / "i18n.json").read_text(encoding="utf-8"))
    assert set(catalogs) == {"zh-CN", "en"}
    assert set(catalogs["zh-CN"]) == set(catalogs["en"])
    assert all(value.strip() for catalog in catalogs.values() for value in catalog.values())


def test_static_and_script_translation_keys_exist():
    catalogs = json.loads((FRONTEND_PATH / "i18n.json").read_text(encoding="utf-8"))
    known = set(catalogs["en"])
    html = (FRONTEND_PATH / "index.html").read_text(encoding="utf-8")
    script = (FRONTEND_PATH / "app.js").read_text(encoding="utf-8")

    static_keys = set(
        re.findall(r'data-i18n(?:-aria|-placeholder)?="([^"]+)"', html)
    )
    script_keys = set(re.findall(r'\bt\("([^"]+)"', script))

    assert static_keys <= known
    assert script_keys <= known


def test_ui_shell_declares_locale_and_non_certification_boundary():
    html = (FRONTEND_PATH / "index.html").read_text(encoding="utf-8")
    assert 'id="localeSelect"' in html
    assert 'data-i18n="app.disclaimer"' in html
    assert 'data-i18n="runs.heading"' in html


def test_every_published_rule_and_ids_specification_has_bilingual_copy():
    catalogs = json.loads((FRONTEND_PATH / "i18n.json").read_text(encoding="utf-8"))
    for rule in load_rule_collection()["rules"]:
        title_key = f'rules.{rule["rule_id"]}.title'
        interpretation_key = f'rules.{rule["rule_id"]}.interpretation'
        assert all(title_key in catalog for catalog in catalogs.values())
        assert all(interpretation_key in catalog for catalog in catalogs.values())

    root = ElementTree.parse(IDS_PATH).getroot()
    identifiers = {
        element.attrib["identifier"]
        for element in root.iter()
        if element.tag.endswith("specification") and "identifier" in element.attrib
    }
    for identifier in identifiers:
        assert all(f"ids.{identifier}" in catalog for catalog in catalogs.values())
