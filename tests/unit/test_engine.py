import csv
import hashlib
import runpy

from ifc_compliance_mvd.paths import MODEL_PATH, ROOT


def test_results_match_manual_ground_truth(engine):
    expected_path = ROOT / "tests" / "expected" / "ground_truth.csv"
    with expected_path.open(encoding="utf-8", newline="") as stream:
        expected = {
            (row["element_guid"], row["rule_id"]): row["expected_status"]
            for row in csv.DictReader(stream)
        }
    actual = {
        (result["element_guid"], result["rule_id"]): result["status"]
        for result in engine.ensure_results()
    }
    assert actual == expected


def test_each_rule_has_pass_fail_not_checkable_boundary_and_not_applicable(engine):
    for rule_id in engine.rules:
        results = [result for result in engine.ensure_results() if result["rule_id"] == rule_id]
        statuses = {result["status"] for result in results}
        assert {"PASS", "FAIL", "NOT_CHECKABLE", "NOT_APPLICABLE"} <= statuses
        boundary = next(
            result
            for result in results
            if result["measured_value"] == result["required_value"]
        )
        assert boundary["status"] == "PASS"


def test_missing_information_is_never_reported_as_design_failure(engine):
    not_checkable = [
        result for result in engine.ensure_results() if result["status"] == "NOT_CHECKABLE"
    ]
    assert len(not_checkable) == 3
    assert all(result["measured_value"] is None for result in not_checkable)
    assert all("missing" in result["reason"].lower() for result in not_checkable)


def test_geometry_rule_uses_computed_world_bbox(engine):
    results = [
        result
        for result in engine.ensure_results()
        if result["rule_id"] == "IBC2021-1003.2-EGRESS-HEIGHT"
        and result["status"] in {"PASS", "FAIL"}
    ]
    assert {result["measured_value"] for result in results} == {2400.0, 2286.0, 2200.0}
    for result in results:
        measurement = result["evidence_details"]["measurement"]
        assert measurement["algorithm"] == "world-coordinate axis-aligned bounding-box Z extent"
        assert measurement["triangle_count"] == 12


def test_repeated_runs_are_semantically_identical(engine):
    first = engine.run(persist=False)
    second = engine.run(persist=False)
    assert first == second


def test_fixture_generation_is_byte_for_byte_reproducible():
    generator = runpy.run_path(str(ROOT / "scripts" / "generate_fixture.py"))["generate"]
    generator()
    first_hash = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    generator()
    second_hash = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    assert first_hash == second_hash


def test_ids_detects_exactly_the_three_missing_information_cases(engine):
    report = engine.ids_report()
    assert report["standard"] == "buildingSMART IDS 1.0"
    assert {spec["identifier"] for spec in report["specifications"]} == {
        "IDS-DOOR-CLEAR-WIDTH",
        "IDS-DOOR-CLEAR-HEIGHT",
        "IDS-EGRESS-SPACE-GEOMETRY",
    }
    assert all(spec["failed_count"] == 1 for spec in report["specifications"])
