import csv
import io
import json
import zipfile
from copy import deepcopy

import pytest
from bcf.v3.bcfxml import BcfXml

from ifc_compliance_mvd.engine import CHECKER_VERSION, MODEL_ID
from ifc_compliance_mvd.exports import (
    UnsafeBcfArchive,
    bcf_report,
    csv_report,
    html_report,
    inspect_bcfzip,
    json_report,
)
from ifc_compliance_mvd.storage import ComplianceStore


@pytest.fixture
def audited_run(tmp_path, engine):
    store = ComplianceStore(tmp_path / "exports" / "compliance.db")
    store.seed_fixture(
        model_id=MODEL_ID,
        model_name="Fixture",
        schema_version=engine.model.schema,
        source="test fixture",
        model_path=engine.model_path,
        element_count=len(engine.elements),
    )
    run_id = store.save_completed_run(
        execution_id=engine.execution_id,
        model_id=MODEL_ID,
        checker_version=CHECKER_VERSION,
        rule_count=len(engine.rules),
        results=engine.ensure_results(),
    )
    return store.get_run(run_id)


def test_json_and_csv_preserve_audit_identifiers(audited_run):
    payload = json.loads(json_report(audited_run))
    assert payload["run"]["run_id"] == audited_run["run_id"]
    assert payload["results"][0]["element_guid"]
    assert payload["results"][0]["rule_id"]
    assert payload["disclaimer"].startswith("Research and teaching")

    rows = list(
        csv.DictReader(io.StringIO(csv_report(audited_run).decode("utf-8-sig")))
    )
    assert len(rows) == 30
    assert {row["run_id"] for row in rows} == {audited_run["run_id"]}
    assert all(row["element_guid"] and row["rule_id"] for row in rows)
    assert json.loads(rows[0]["evidence_details"])

    malicious = deepcopy(audited_run)
    malicious["results"][0]["element_name"] = "=HYPERLINK(\"bad\")"
    protected_rows = list(
        csv.DictReader(io.StringIO(csv_report(malicious).decode("utf-8-sig")))
    )
    assert protected_rows[0]["element_name"].startswith("'=")


def test_html_report_is_printable_localized_and_escaped(audited_run):
    malicious = deepcopy(audited_run)
    malicious["results"][0]["element_name"] = '<script>alert("x")</script>'
    html = html_report(malicious, locale="zh-CN").decode("utf-8")
    assert "<h1>IFC 合规检查报告</h1>" in html
    assert "@media print" in html
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert audited_run["run_id"] in html


def test_bcf_30_round_trip_preserves_topics_selection_and_is_deterministic(
    audited_run, tmp_path
):
    first = bcf_report(audited_run)
    second = bcf_report(audited_run)
    assert first == second

    inspection = inspect_bcfzip(first)
    assert inspection["version"] == "3.0"
    assert inspection["topic_count"] == 14
    assert all(topic["viewpoints"] for topic in inspection["topics"])
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        names = archive.namelist()
        assert names[0] == "bcf.version"
        assert sum(name.endswith("/markup.bcf") for name in names) == 14
        viewpoint_xml = archive.read(
            next(name for name in names if name.endswith(".bcfv"))
        ).decode("utf-8")
        assert 'IfcGuid="' in viewpoint_xml
        assert "<PerspectiveCamera>" in viewpoint_xml

    archive_path = tmp_path / "audit.bcfzip"
    archive_path.write_bytes(first)
    parsed = BcfXml.load(archive_path)
    assert parsed is not None
    assert len(parsed.topics) == 14


def test_bcf_inspection_rejects_path_traversal_and_zip_bombs():
    traversal = io.BytesIO()
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("bcf.version", '<Version VersionId="3.0"/>')
        archive.writestr("../outside.txt", "unsafe")
    with pytest.raises(UnsafeBcfArchive, match="Unsafe BCF archive member"):
        inspect_bcfzip(traversal.getvalue())

    oversized = io.BytesIO()
    with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bcf.version", '<Version VersionId="3.0"/>')
        archive.writestr("large.bin", b"0" * 5_000_001)
    with pytest.raises(UnsafeBcfArchive, match="Unsafe BCF archive member"):
        inspect_bcfzip(oversized.getvalue())
