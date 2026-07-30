from pathlib import Path

from ifc_compliance_mvd.engine import CHECKER_VERSION, MODEL_ID, ComplianceEngine
from ifc_compliance_mvd.storage import ComplianceStore, SCHEMA_VERSION


def seeded_store(tmp_path: Path, engine: ComplianceEngine) -> ComplianceStore:
    store = ComplianceStore(tmp_path / "runtime" / "compliance.db")
    store.seed_fixture(
        model_id=MODEL_ID,
        model_name="Fixture",
        schema_version=engine.model.schema,
        source="test fixture",
        model_path=engine.model_path,
        element_count=len(engine.elements),
    )
    return store


def test_migrations_and_seed_are_restart_safe(tmp_path, engine):
    store = seeded_store(tmp_path, engine)
    assert store.schema_version() == SCHEMA_VERSION
    assert store.list_projects()[0]["model_count"] == 1

    reopened = ComplianceStore(store.database_path)
    reopened.seed_fixture(
        model_id=MODEL_ID,
        model_name="Fixture",
        schema_version=engine.model.schema,
        source="test fixture",
        model_path=engine.model_path,
        element_count=len(engine.elements),
    )
    assert reopened.schema_version() == SCHEMA_VERSION
    assert len(reopened.list_models()) == 1


def test_runs_persist_results_and_compare_deterministically(tmp_path, engine):
    store = seeded_store(tmp_path, engine)
    results = engine.ensure_results()
    first = store.save_completed_run(
        execution_id=engine.execution_id,
        model_id=MODEL_ID,
        checker_version=CHECKER_VERSION,
        rule_count=len(engine.rules),
        results=results,
    )
    second = store.save_completed_run(
        execution_id=engine.execution_id,
        model_id=MODEL_ID,
        checker_version=CHECKER_VERSION,
        rule_count=len(engine.rules),
        results=results,
    )

    listing = store.list_runs(model_id=MODEL_ID, limit=1)
    assert listing["total"] == 2
    assert len(listing["items"]) == 1
    assert store.get_run(first)["result_count"] == 30
    assert store.compare_runs(first, second) == {
        "base_run_id": first,
        "target_run_id": second,
        "unchanged_count": 30,
        "change_count": 0,
        "changes": [],
    }


def test_query_history_round_trips_validated_dsl(tmp_path, engine):
    store = seeded_store(tmp_path, engine)
    query_id = store.save_query(
        original_utterance="哪些门没有通过净宽规则？",
        locale="zh-CN",
        dsl={"intent": "find_results", "filters": {"statuses": ["FAIL"]}},
        result_count=1,
        warnings=[],
        model_id=MODEL_ID,
    )
    history = store.list_queries()
    assert history["total"] == 1
    assert history["items"][0]["query_id"] == query_id
    assert history["items"][0]["dsl"]["filters"]["statuses"] == ["FAIL"]
    assert history["items"][0]["model_id"] == MODEL_ID


def test_queued_import_can_cancel_and_interrupted_import_fails_on_restart(
    tmp_path,
    engine,
):
    store = seeded_store(tmp_path, engine)
    cancelled_id = store.create_import_job(
        original_filename="cancel.ifc",
        file_size=100,
        source_sha256="a" * 64,
    )
    assert store.cancel_import_job(cancelled_id)["status"] == "CANCELLED"
    assert store.claim_import_job(cancelled_id) is False

    interrupted_id = store.create_import_job(
        original_filename="interrupted.ifc",
        file_size=100,
        source_sha256="b" * 64,
    )
    assert store.claim_import_job(interrupted_id) is True
    reopened = ComplianceStore(store.database_path)
    interrupted = reopened.get_import_job(interrupted_id)
    assert interrupted["status"] == "FAILED"
    assert interrupted["error"]["code"] == "PROCESS_RESTARTED"
