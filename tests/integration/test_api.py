from fastapi.testclient import TestClient

from ifc_compliance_mvd.api import app

client = TestClient(app)


def test_health_and_models():
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["rule_count"] == 3
    assert health.json()["element_count"] == 10
    assert client.get("/api/models").json()[0]["schema"] == "IFC4"


def test_rule_to_elements_and_element_to_rules_are_bidirectional():
    rule_id = "IBC2021-1010.1.1-WIDTH"
    rule_elements = client.get(f"/api/rules/{rule_id}/elements").json()
    assert len(rule_elements) == 5
    guid = rule_elements[0]["global_id"]
    element_rules = client.get(f"/api/elements/{guid}/rules").json()
    assert rule_id in {rule["rule_id"] for rule in element_rules}
    assert all(rule["result"]["element_guid"] == guid for rule in element_rules)


def test_scene_is_guid_addressable_and_contains_real_geometry():
    scene = client.get("/api/scene").json()
    assert len(scene["elements"]) == 10
    assert len({element["global_id"] for element in scene["elements"]}) == 10
    geometries = [element["geometry"] for element in scene["elements"]]
    assert all(geometry["positions"] and geometry["indices"] for geometry in geometries)
    assert sum(geometry["placeholder"] for geometry in geometries) == 1


def test_check_endpoint_is_deterministic_and_structured():
    first = client.post("/api/checks/run")
    second = client.post("/api/checks/run")
    assert first.status_code == second.status_code == 200
    assert first.json()["execution_id"] == second.json()["execution_id"]
    assert first.json()["results"] == second.json()["results"]
    assert first.json()["status_counts"] == {
        "FAIL": 3,
        "NOT_APPLICABLE": 3,
        "NOT_CHECKABLE": 3,
        "PASS": 6,
    }


def test_ego_graph_is_local_and_traceable():
    graph = client.get(
        "/api/graph/ego",
        params={"rule_id": "IBC2021-1003.2-EGRESS-HEIGHT"},
    ).json()
    kinds = {node["kind"] for node in graph["nodes"]}
    edge_types = {edge["type"] for edge in graph["edges"]}
    assert {"Clause", "Rule", "IfcElement", "ComplianceResult"} <= kinds
    assert {"FORMALIZED_AS", "APPLIES_TO", "PRODUCES", "EVIDENCED_BY"} <= edge_types


def test_unknown_ids_return_404():
    assert client.get("/api/rules/unknown").status_code == 404
    assert client.get("/api/elements/unknown/rules").status_code == 404

