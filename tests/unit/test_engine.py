import csv
import hashlib
import runpy

import ifcopenshell

from ifc_compliance_mvd.engine import ComplianceEngine
from ifc_compliance_mvd.paths import IDS_PATH, MODEL_PATH, ROOT


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
    deterministic_rules = {
        rule_id
        for rule_id, rule in engine.rules.items()
        if rule["automation_level"] == "deterministic_mvd"
    }
    for rule_id in deterministic_rules:
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
    assert len(not_checkable) == 5
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


def test_swing_rule_uses_door_to_space_occupancy_relationships(engine):
    results = [
        result
        for result in engine.ensure_results()
        if result["rule_id"] == "IBC2021-1010.1.2.1-SWING"
    ]
    assert {result["status"] for result in results} == {
        "PASS",
        "FAIL",
        "NOT_CHECKABLE",
        "NOT_APPLICABLE",
    }
    boundary = next(
        result
        for result in results
        if result["element_name"].startswith("Door PASS - exact threshold")
    )
    contexts = boundary["evidence_details"]["applicability"][
        "IfcRelSpaceBoundary.RelatingSpace occupancy context"
    ]["related_spaces"]
    assert contexts[0]["occupant_load"] == 50.0
    assert contexts[0]["occupancy_groups"] == ["B"]
    assert contexts[0]["occupancy_group_source"] == "IFC_CLASSIFICATION"
    assert contexts[0]["classification"][0]["relationship_guid"]
    assert boundary["evidence_source"] == "IFC_RELATIONSHIP"
    assert boundary["evidence_details"]["measurement"]["relationship_guids"]

    group_h = next(
        result
        for result in results
        if result["element_name"].startswith("Door PASS - generous opening")
    )
    group_h_context = group_h["evidence_details"]["applicability"][
        "IfcRelSpaceBoundary.RelatingSpace occupancy context"
    ]["related_spaces"][0]
    assert group_h_context["numeric_occupant_load"] == 10.0
    assert group_h_context["occupancy_groups"] == ["H"]
    assert group_h["status"] == "PASS"


def test_continuity_rule_preserves_traversed_topology_evidence(engine):
    results = [
        result
        for result in engine.ensure_results()
        if result["rule_id"] == "IBC2021-1003.6-EGRESS-CONTINUITY"
    ]
    passed = next(result for result in results if result["status"] == "PASS")
    failed = next(result for result in results if result["status"] == "FAIL")
    pass_evidence = passed["evidence_details"]["measurement"]
    fail_evidence = failed["evidence_details"]["measurement"]
    assert passed["evidence_source"] == "IFC_TOPOLOGY"
    assert pass_evidence["exit_discharge_door_guid"]
    assert pass_evidence["relationship_guids"]
    assert fail_evidence["exit_discharge_door_guid"] is None
    assert fail_evidence["traversed_door_guids"]


def test_missing_exit_classification_cannot_be_reported_as_topology_failure(
    engine,
    tmp_path,
):
    model = ifcopenshell.open(str(engine.model_path))
    failed_space = next(
        space for space in model.by_type("IfcSpace") if "FAIL - 2200" in space.Name
    )
    door = failed_space.BoundedBy[0].RelatedBuildingElement
    topology_pset = next(
        relation.RelatingPropertyDefinition
        for relation in door.IsDefinedBy
        if relation.RelatingPropertyDefinition.Name == "Pset_ComplianceTopology"
    )
    exit_property = next(
        item for item in topology_pset.HasProperties if item.Name == "IsExitDischarge"
    )
    exit_property.NominalValue = None
    model_path = tmp_path / "missing-exit-classification.ifc"
    model.write(str(model_path))

    mutated = ComplianceEngine(
        model_path=model_path,
        ids_path=IDS_PATH,
        results_path=tmp_path / "results.json",
        model_id="missing-exit-classification",
    )
    result = next(
        item
        for item in mutated.run(persist=False)
        if item["rule_id"] == "IBC2021-1003.6-EGRESS-CONTINUITY"
        and item["element_guid"] == failed_space.GlobalId
    )
    assert result["status"] == "NOT_CHECKABLE"
    assert result["evidence_source"] == "IFC_TOPOLOGY"
    assert "classification is missing" in result["reason"]


def test_malformed_related_occupant_load_fails_closed(engine, tmp_path):
    model = ifcopenshell.open(str(engine.model_path))
    boundary_space = next(
        space for space in model.by_type("IfcSpace") if "exact 2286" in space.Name
    )
    door = boundary_space.BoundedBy[0].RelatedBuildingElement
    context_pset = next(
        relation.RelatingPropertyDefinition
        for relation in boundary_space.IsDefinedBy
        if relation.RelatingPropertyDefinition.Name == "Pset_ComplianceContext"
    )
    occupant_load = next(
        item for item in context_pset.HasProperties if item.Name == "ServedOccupantLoad"
    )
    occupant_load.NominalValue = model.createIfcLabel("not-a-number")
    model_path = tmp_path / "malformed-occupant-load.ifc"
    model.write(str(model_path))

    mutated = ComplianceEngine(
        model_path=model_path,
        ids_path=IDS_PATH,
        results_path=tmp_path / "results.json",
        model_id="malformed-occupant-load",
    )
    result = next(
        item
        for item in mutated.run(persist=False)
        if item["rule_id"] == "IBC2021-1010.1.2.1-SWING"
        and item["element_guid"] == door.GlobalId
    )
    assert result["status"] == "NOT_CHECKABLE"
    assert result["evidence_source"] == "IFC_RELATIONSHIP"
    assert "Applicability cannot be decided" in result["reason"]


def test_operational_requirement_is_never_auto_passed_or_failed(engine):
    results = [
        result
        for result in engine.ensure_results()
        if result["rule_id"] == "IBC2021-1010.2-DOOR-OPERATIONS"
    ]
    assert {result["status"] for result in results} == {
        "MANUAL_REVIEW_REQUIRED",
        "NOT_APPLICABLE",
    }
    reviews = [
        result for result in results if result["status"] == "MANUAL_REVIEW_REQUIRED"
    ]
    assert len(reviews) == 4
    assert all(result["measured_value"] is None for result in reviews)
    assert all(result["evidence_source"] == "HUMAN_INSPECTION" for result in reviews)
    assert all(result["evidence_details"]["manual_checklist"] for result in reviews)


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


def test_ids_detects_each_controlled_missing_information_case(engine):
    report = engine.ids_report()
    assert report["standard"] == "buildingSMART IDS 1.0"
    assert {spec["identifier"] for spec in report["specifications"]} == {
        "IDS-DOOR-CLEAR-WIDTH",
        "IDS-DOOR-CLEAR-HEIGHT",
        "IDS-EGRESS-SPACE-GEOMETRY",
        "IDS-DOOR-SWING-DIRECTION",
        "IDS-EGRESS-SPACE-TOPOLOGY",
        "IDS-SPACE-OCCUPANCY-CLASSIFICATION",
    }
    assert all(spec["failed_count"] == 1 for spec in report["specifications"])
