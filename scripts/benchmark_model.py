"""Measure a reproducible backend baseline for a selected IFC model.

The controlled fixture is the default. External model conclusions require a
separate provenance and license record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Callable

from ifc_compliance_mvd.engine import MODEL_ID, ComplianceEngine
from ifc_compliance_mvd.imports import ModelImportService
from ifc_compliance_mvd.nl_query import (
    NaturalLanguageQueryRequest,
    execute_query,
    parse_natural_language,
)
from ifc_compliance_mvd.paths import MODEL_PATH
from ifc_compliance_mvd.storage import DEFAULT_PROJECT_ID, ComplianceStore


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _summary(values: list[float]) -> dict[str, float | int]:
    return {
        "iterations": len(values),
        "min_ms": round(min(values), 3),
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(_percentile(values, 0.95), 3),
        "max_ms": round(max(values), 3),
    }


def _measure(action: Callable[[], object], iterations: int) -> dict[str, float | int]:
    action()
    values = []
    for _ in range(iterations):
        started = time.perf_counter()
        action()
        values.append((time.perf_counter() - started) * 1000)
    return _summary(values)


def _total_memory_bytes() -> int | None:
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong),
                    ("available_physical", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong),
                    ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.total_physical)
        except (AttributeError, OSError):
            return None
    try:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        return None


def _import_once(
    fixture: Path,
    fixture_engine: ComplianceEngine,
) -> float:
    payload = fixture.read_bytes()
    with tempfile.TemporaryDirectory(prefix="ifc-mvd-benchmark-") as directory:
        root = Path(directory)
        store = ComplianceStore(root / "audit.sqlite3")
        store.seed_fixture(
            model_id=MODEL_ID,
            model_name="benchmark project seed",
            schema_version=str(fixture_engine.model.schema),
            source="controlled benchmark seed",
            model_path=fixture,
            element_count=len(fixture_engine.elements),
        )
        # Keep the project row but remove the seed model so the exact fixture
        # exercises parse and semantic indexing instead of the dedupe path.
        with store.connect() as connection:
            connection.execute("DELETE FROM models WHERE model_id = ?", (MODEL_ID,))
        service = ModelImportService(store, root / "imports")

        started = time.perf_counter()
        job_id, _ = service.submit(
            payload=payload,
            filename=fixture.name,
            media_type="application/x-step",
            project_id=DEFAULT_PROJECT_ID,
        )
        service.process(
            job_id,
            source="controlled generated fixture",
            license_name="MIT; generated fixture",
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        job = store.get_import_job(job_id)
        if job is None or job["status"] != "COMPLETED" or job["deduplicated"]:
            raise RuntimeError(f"Benchmark import did not index the model: {job}")
        return elapsed_ms


def run_benchmark(fixture: Path, iterations: int, label: str | None = None) -> dict:
    fixture = fixture.resolve()
    fixture_engine = ComplianceEngine(model_path=fixture)
    fixture_engine.run(persist=False)
    scene = fixture_engine.serialised_elements(include_geometry=True)

    import_values = [_import_once(fixture, fixture_engine) for _ in range(iterations)]
    checker = _measure(lambda: fixture_engine.run(persist=False), iterations)
    scene_build = _measure(
        lambda: fixture_engine.serialised_elements(include_geometry=True),
        iterations,
    )
    query_request = NaturalLanguageQueryRequest(
        utterance="Show failed doors",
        locale="en",
    )

    def parse_and_query() -> object:
        parsed = parse_natural_language(query_request, fixture_engine)
        return execute_query(parsed, fixture_engine)

    natural_language = _measure(parse_and_query, iterations)

    with tempfile.TemporaryDirectory(prefix="ifc-mvd-query-benchmark-") as directory:
        store = ComplianceStore(Path(directory) / "audit.sqlite3")
        store.seed_fixture(
            model_id=MODEL_ID,
            model_name="IBC egress controlled fixture",
            schema_version=str(fixture_engine.model.schema),
            source="controlled generated fixture",
            model_path=fixture,
            element_count=len(fixture_engine.elements),
        )
        store.replace_model_elements(
            MODEL_ID,
            fixture_engine.serialised_elements(include_geometry=False),
        )
        run_id, _ = store.run_and_save(fixture_engine)
        sqlite_read = _measure(lambda: store.get_run(run_id), iterations)

    tracemalloc.start()
    memory_engine = ComplianceEngine(model_path=fixture)
    memory_engine.run(persist=False)
    memory_engine.serialised_elements(include_geometry=True)
    _, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    scene_document = {
        "model_id": MODEL_ID,
        "units": "m",
        "elements": scene,
    }
    scene_bytes = json.dumps(
        scene_document,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    triangle_count = sum(
        len(element["geometry"]["indices"]) // 3 for element in scene
    )
    processor = platform.processor().strip() or platform.machine()
    total_memory = _total_memory_bytes()
    controlled_fixture = fixture == MODEL_PATH.resolve()
    scope = (
        "controlled synthetic fixture smoke baseline; not representative of a real project"
        if controlled_fixture
        else label or "user-selected external IFC; provenance not asserted by this script"
    )
    return {
        "scope": scope,
        "environment": {
            "operating_system": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": processor,
            "logical_cpu_count": os.cpu_count(),
            "total_memory_bytes": total_memory,
            "python": platform.python_version(),
        },
        "model": {
            "name": fixture.name,
            "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "schema": str(fixture_engine.model.schema),
            "file_bytes": fixture.stat().st_size,
            "ifc_product_count": len(fixture_engine.model.by_type("IfcProduct")),
            "checked_element_count": len(fixture_engine.elements),
            "scene_element_count": len(scene),
            "triangle_count": triangle_count,
        },
        "measurements": {
            "ifc_import_and_semantic_index": _summary(import_values),
            "full_checker_batch": checker,
            "scene_build": scene_build,
            "sqlite_completed_run_read": sqlite_read,
            "natural_language_parse_and_query": natural_language,
            "scene_payload_bytes": len(scene_bytes),
            "scene_chunk_count": 1,
            "python_tracemalloc_peak_bytes": peak_python_bytes,
        },
        "limitations": [
            "Browser first-useful-render, interaction latency, FPS, and long tasks are measured separately.",
            "tracemalloc excludes native allocations made by IfcOpenShell and the graphics driver.",
            *(
                [
                    "The fixture is deliberately tiny and cannot support real-project performance conclusions."
                ]
                if controlled_fixture
                else [
                    "The caller is responsible for recording model provenance, license, and attribution."
                ]
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=MODEL_PATH,
        help="IFC file to benchmark (defaults to the generated fixture).",
    )
    parser.add_argument(
        "--label",
        help="Explicit provenance/scope label for a non-default IFC.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=7,
        help="Measured iterations per operation (default: 7).",
    )
    args = parser.parse_args()
    if args.iterations < 1 or args.iterations > 100:
        parser.error("--iterations must be between 1 and 100")
    print(json.dumps(run_benchmark(args.fixture, args.iterations, args.label), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
