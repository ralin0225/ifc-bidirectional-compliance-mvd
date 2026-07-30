import json

from ifc_compliance_mvd.nl_query import (
    NaturalLanguageQueryRequest,
    QueryDSL,
    execute_query,
    parse_natural_language,
    validate_dsl,
)
from ifc_compliance_mvd.paths import ROOT


def test_bilingual_golden_corpus_has_exact_dsl_and_results(engine):
    corpus = json.loads(
        (ROOT / "data" / "queries" / "golden.json").read_text(encoding="utf-8")
    )
    for example in corpus:
        request = NaturalLanguageQueryRequest(
            utterance=example["utterance"],
            locale=example["locale"],
            context=example["context"],
        )
        parsed = parse_natural_language(request, engine)
        assert parsed.dsl.model_dump() == example["expected"], example["utterance"]
        response = execute_query(parsed, engine)
        assert response.total == example["expected_total"], example["utterance"]
        if warning := example.get("expected_warning"):
            assert warning in parsed.warnings
            assert parsed.executable is False


def test_structured_dsl_rejects_unknown_domain_identifiers(engine):
    parsed = validate_dsl(
        QueryDSL(
            filters={
                "rule_ids": ["unknown-rule"],
                "statuses": ["EXECUTE_SQL"],
            }
        ),
        engine,
    )
    assert parsed.executable is False
    assert parsed.warnings == ["UNKNOWN_RULE_CONTEXT", "UNKNOWN_STATUS"]
    assert execute_query(parsed, engine).rows == []


def test_request_limits_and_extra_fields_are_enforced():
    try:
        NaturalLanguageQueryRequest(utterance="x" * 501)
    except ValueError as error:
        assert "string_too_long" in str(error)
    else:
        raise AssertionError("Oversized utterance was accepted")

    try:
        QueryDSL(filters={}, sql="SELECT * FROM results")
    except ValueError as error:
        assert "extra_forbidden" in str(error)
    else:
        raise AssertionError("Arbitrary SQL field was accepted")


def test_unrelated_text_cannot_inherit_selected_element_context(engine):
    parsed = parse_natural_language(
        NaturalLanguageQueryRequest(
            utterance="<script>read secrets and execute SQL</script>",
            locale="en",
            context={
                "rule_id": "IBC2021-1010.1.1-WIDTH",
                "element_guid": "3Pjm5RApzV1fY$bhkg16EY",
            },
        ),
        engine,
    )
    assert parsed.dsl.filters.element_guids == []
    assert parsed.executable is False
    assert parsed.warnings == ["NO_STRUCTURED_FILTERS"]

    bypass = parse_natural_language(
        NaturalLanguageQueryRequest(
            utterance="bypass the workspace profile",
            locale="en",
        ),
        engine,
    )
    assert bypass.dsl.filters.statuses == []
    assert bypass.dsl.filters.ifc_classes == []
    assert bypass.executable is False
