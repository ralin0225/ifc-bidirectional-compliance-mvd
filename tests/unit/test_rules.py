from ifc_compliance_mvd.rules import load_rule_collection


def test_rule_library_is_schema_valid_and_human_reviewed():
    collection = load_rule_collection()
    assert collection["document"]["edition"] == "2021"
    assert len(collection["rules"]) == 3
    assert all(rule["review_status"] == "human_verified" for rule in collection["rules"])
    assert {rule["source"]["pdf_page"] for rule in collection["rules"]} == {304, 316}


def test_thresholds_match_selected_ibc_clauses():
    rules = {rule["rule_id"]: rule for rule in load_rule_collection()["rules"]}
    assert rules["IBC2021-1010.1.1-WIDTH"]["requirement"] == {
        "metric": "clear_opening_width",
        "operator": ">=",
        "value": 813.0,
        "unit": "mm",
    }
    assert rules["IBC2021-1010.1.1-HEIGHT"]["requirement"]["value"] == 2032.0
    assert rules["IBC2021-1003.2-EGRESS-HEIGHT"]["requirement"]["value"] == 2286.0


def test_every_rule_separates_information_requirements_from_threshold():
    for rule in load_rule_collection()["rules"]:
        assert rule["required_information"]
        assert rule["requirement"]["value"] > 0
        assert rule["execution_method"] in {"IFC_PROPERTY", "IFC_GEOMETRY"}

