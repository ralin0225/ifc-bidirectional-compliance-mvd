from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any

import ifcopenshell
from ifcopenshell.util.unit import calculate_unit_scale

from .ifc_adapter import serialise_element
from .paths import IMPORTS_PATH
from .storage import ComplianceStore

MAX_IFC_BYTES = 20 * 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    "application/octet-stream",
    "application/x-step",
    "model/ifc",
    "text/plain",
}
SAFE_JOB_ID = re.compile(r"^import-[0-9a-f]{32}$")


class ImportValidationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.status_code = status_code


def validate_filename(filename: str) -> str:
    candidate = filename.strip()
    if not candidate or len(candidate) > 255:
        raise ImportValidationError("INVALID_FILENAME", "The IFC filename is invalid.")
    if any(character in candidate for character in ("/", "\\", "\x00", ":")):
        raise ImportValidationError(
            "UNSAFE_FILENAME",
            "The filename must not contain a path or drive prefix.",
        )
    if Path(candidate).suffix.lower() != ".ifc":
        raise ImportValidationError("INVALID_EXTENSION", "Only .ifc files are accepted.")
    return candidate


def validate_payload(payload: bytes, media_type: str | None) -> None:
    if not payload:
        raise ImportValidationError("EMPTY_UPLOAD", "The uploaded IFC file is empty.")
    if len(payload) > MAX_IFC_BYTES:
        raise ImportValidationError(
            "UPLOAD_TOO_LARGE",
            f"The IFC upload exceeds the {MAX_IFC_BYTES // (1024 * 1024)} MiB limit.",
            status_code=413,
        )
    normalized_media_type = (media_type or "application/octet-stream").split(";", 1)[0].lower()
    if normalized_media_type not in ALLOWED_MEDIA_TYPES:
        raise ImportValidationError(
            "UNSUPPORTED_MEDIA_TYPE",
            "The content type is not allowed for IFC uploads.",
            status_code=415,
        )
    leading = payload[:65536].lstrip().upper()
    trailing = payload[-4096:].rstrip().upper()
    if not leading.startswith(b"ISO-10303-21;"):
        raise ImportValidationError(
            "INVALID_IFC_SIGNATURE",
            "The file does not start with an IFC STEP signature.",
        )
    if b"FILE_SCHEMA" not in leading:
        raise ImportValidationError(
            "MISSING_IFC_SCHEMA",
            "The IFC header does not declare FILE_SCHEMA.",
        )
    if not trailing.endswith(b"END-ISO-10303-21;"):
        raise ImportValidationError(
            "TRUNCATED_IFC",
            "The IFC STEP terminator is missing.",
        )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "is_a") and hasattr(value, "id"):
        return {"ifc_class": value.is_a(), "entity_id": value.id()}
    return str(value)


class ModelImportService:
    """Zero-service IFC import pipeline with persisted job transitions."""

    def __init__(
        self,
        store: ComplianceStore,
        imports_path: Path = IMPORTS_PATH,
    ) -> None:
        self.store = store
        self.imports_path = Path(imports_path)
        self.staging_path = self.imports_path / "staging"
        self.models_path = self.imports_path / "models"
        self.staging_path.mkdir(parents=True, exist_ok=True)
        self.models_path.mkdir(parents=True, exist_ok=True)

    def submit(
        self,
        *,
        payload: bytes,
        filename: str,
        media_type: str | None,
        project_id: str,
    ) -> tuple[str, str]:
        safe_filename = validate_filename(filename)
        validate_payload(payload, media_type)
        source_sha256 = hashlib.sha256(payload).hexdigest()
        job_id = self.store.create_import_job(
            original_filename=safe_filename,
            file_size=len(payload),
            source_sha256=source_sha256,
            project_id=project_id,
        )
        stage = self._stage_path(job_id)
        stage.write_bytes(payload)
        return job_id, source_sha256

    def _stage_path(self, job_id: str) -> Path:
        if not SAFE_JOB_ID.fullmatch(job_id):
            raise ValueError("Invalid import job identifier.")
        path = (self.staging_path / f"{job_id}.ifc").resolve()
        if self.staging_path.resolve() not in path.parents:
            raise ValueError("Import staging path escaped its root.")
        return path

    def process(
        self,
        job_id: str,
        *,
        source: str,
        license_name: str,
    ) -> None:
        job = self.store.get_import_job(job_id)
        if job is None:
            return
        stage = self._stage_path(job_id)
        try:
            if not self.store.claim_import_job(job_id):
                stage.unlink(missing_ok=True)
                return
            duplicate = self.store.find_model_by_hash(job["source_sha256"])
            if duplicate is not None:
                self.store.update_import_job(
                    job_id,
                    status="COMPLETED",
                    phase="deduplicated",
                    progress=100,
                    model_id=duplicate["model_id"],
                    deduplicated=True,
                )
                stage.unlink(missing_ok=True)
                return

            try:
                model = ifcopenshell.open(str(stage))
            except Exception:
                self._fail(
                    job_id,
                    "IFC_PARSE_FAILED",
                    "IfcOpenShell rejected the uploaded IFC file.",
                )
                return

            schema = str(model.schema)
            if schema != "IFC2X3" and not schema.startswith("IFC4"):
                self._fail(
                    job_id,
                    "UNSUPPORTED_SCHEMA",
                    f"The declared IFC schema {schema} is not supported.",
                )
                return

            self.store.update_import_job(
                job_id,
                status="INDEXING",
                phase="semantic-index",
                progress=55,
            )
            products = [
                element
                for element in model.by_type("IfcProduct")
                if getattr(element, "GlobalId", None)
            ]
            elements = [
                _json_safe(serialise_element(element, include_geometry=False))
                for element in products
            ]
            class_counts = dict(sorted(Counter(item["ifc_class"] for item in elements).items()))
            model_id = f"model-{job['source_sha256']}"
            relative_path = Path("models") / model_id / "source.ifc"
            final_path = (self.imports_path / relative_path).resolve()
            if self.imports_path.resolve() not in final_path.parents:
                raise RuntimeError("Import destination escaped its root.")
            final_path.parent.mkdir(parents=True, exist_ok=True)
            stage.replace(final_path)
            self.store.register_imported_model(
                model_id=model_id,
                project_id=job["project_id"],
                name=Path(job["original_filename"]).stem,
                schema_version=schema,
                source=source,
                source_sha256=job["source_sha256"],
                stored_path=relative_path.as_posix(),
                original_filename=job["original_filename"],
                file_size=job["file_size"],
                license_name=license_name,
                unit_scale_to_m=float(calculate_unit_scale(model)),
                diagnostics={
                    "global_id_product_count": len(elements),
                    "ifc_class_counts": class_counts,
                    "warnings": [],
                },
                elements=elements,
            )
            self.store.update_import_job(
                job_id,
                status="COMPLETED",
                phase="ready",
                progress=100,
                model_id=model_id,
            )
        except Exception:
            self._fail(
                job_id,
                "IMPORT_PIPELINE_FAILED",
                "The IFC import pipeline failed safely.",
            )

    def _fail(self, job_id: str, code: str, message: str) -> None:
        self.store.update_import_job(
            job_id,
            status="FAILED",
            phase="failed",
            progress=0,
            error={"code": code, "message": message},
        )
        self._stage_path(job_id).unlink(missing_ok=True)
