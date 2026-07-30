from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ifcopenshell
from ifctester import ids

from .ifc_adapter import (
    element_psets,
    geometry_evidence,
    open_model,
    property_value,
    serialise_element,
)
from .paths import IDS_PATH, MODEL_PATH, RESULTS_PATH
from .rules import index_rules, load_rule_collection

CHECKER_VERSION = "0.1.0"
MODEL_ID = "ibc-egress-demo"
STATUSES = {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_CHECKABLE", "MANUAL_REVIEW_REQUIRED"}


class ComplianceEngine:
    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        ids_path: Path = IDS_PATH,
        results_path: Path = RESULTS_PATH,
    ) -> None:
        self.model_path = model_path
        self.ids_path = ids_path
        self.results_path = results_path
        self.collection = load_rule_collection()
        self.rules = index_rules(self.collection)
        self.model = open_model(model_path)
        self.elements = {
            element.GlobalId: element
            for ifc_class in ("IfcDoor", "IfcSpace")
            for element in self.model.by_type(ifc_class)
        }
        self.results: list[dict[str, Any]] = []
        self.execution_id = self._execution_id()

    def _execution_id(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.model_path.read_bytes())
        digest.update(json.dumps(self.collection, sort_keys=True).encode())
        digest.update(CHECKER_VERSION.encode())
        return f"run-{digest.hexdigest()[:16]}"

    @staticmethod
    def _applicability(rule: dict, element) -> tuple[str | None, str | None, dict]:
        details: dict[str, Any] = {}
        for condition in rule["applicability"]:
            value = property_value(element, condition["property_set"], condition["property"])
            key = f'{condition["property_set"]}.{condition["property"]}'
            details[key] = value
            if value is None:
                return (
                    condition.get("missing_status", "NOT_CHECKABLE"),
                    f"Applicability cannot be decided because {key} is missing.",
                    details,
                )
            if condition["operator"] == "is_true" and value is not True:
                return "NOT_APPLICABLE", f"{key} is explicitly false.", details
        return None, None, details

    @staticmethod
    def _missing_information(rule: dict, element) -> list[str]:
        missing = []
        for requirement in rule["required_information"]:
            if requirement["kind"] == "property":
                value = property_value(
                    element,
                    requirement["property_set"],
                    requirement["property"],
                )
                if value is None:
                    missing.append(f'{requirement["property_set"]}.{requirement["property"]}')
            elif requirement["kind"] == "attribute":
                if getattr(element, requirement["attribute"], None) is None:
                    missing.append(f'Ifc attribute {requirement["attribute"]}')
        return missing

    @staticmethod
    def _measure(rule: dict, element) -> tuple[float, str, dict]:
        metric = rule["requirement"]["metric"]
        if metric == "clear_opening_width":
            path = "Pset_ComplianceMeasurements.ClearOpeningWidth"
            value = property_value(element, "Pset_ComplianceMeasurements", "ClearOpeningWidth")
            return float(value), "PROPERTY", {"property_path": path, "raw_value": float(value)}
        if metric == "clear_opening_height":
            path = "Pset_ComplianceMeasurements.ClearOpeningHeight"
            value = property_value(element, "Pset_ComplianceMeasurements", "ClearOpeningHeight")
            return float(value), "PROPERTY", {"property_path": path, "raw_value": float(value)}
        if metric == "geometry_bounding_height":
            evidence = geometry_evidence(element)
            return (
                evidence.height_mm,
                "GEOMETRY",
                {
                    "algorithm": "world-coordinate axis-aligned bounding-box Z extent",
                    "bbox_min_m": evidence.bbox_min,
                    "bbox_max_m": evidence.bbox_max,
                    "vertex_count": evidence.vertex_count,
                    "triangle_count": evidence.triangle_count,
                    "controlled_fixture_assumption": "orthogonal floor and ceiling",
                },
            )
        raise ValueError(f"Unsupported metric: {metric}")

    def _base_result(self, rule: dict, element) -> dict:
        return {
            "execution_id": self.execution_id,
            "rule_id": rule["rule_id"],
            "rule_version": rule["version"],
            "element_guid": element.GlobalId,
            "element_name": element.Name or element.GlobalId,
            "ifc_class": element.is_a(),
            "model_id": MODEL_ID,
            "status": None,
            "measured_value": None,
            "required_value": rule["requirement"]["value"],
            "operator": rule["requirement"]["operator"],
            "unit": rule["requirement"]["unit"],
            "reason": None,
            "evidence_source": None,
            "evidence_details": {},
            "checker_version": CHECKER_VERSION,
            "clause": rule["source"]["section"],
        }

    def evaluate(self, rule: dict, element) -> dict:
        result = self._base_result(rule, element)
        status, reason, applicability = self._applicability(rule, element)
        if status:
            result.update(
                status=status,
                reason=reason,
                evidence_source="IFC_PROPERTY",
                evidence_details={"applicability": applicability},
            )
            return result

        missing = self._missing_information(rule, element)
        if missing:
            result.update(
                status="NOT_CHECKABLE",
                reason="Required information is missing; this is not evidence of design non-compliance.",
                evidence_source="IDS_INFORMATION_REQUIREMENT",
                evidence_details={
                    "missing": missing,
                    "ids_specifications": [
                        item["ids_specification"] for item in rule["required_information"]
                    ],
                    "applicability": applicability,
                },
            )
            return result

        try:
            measured, source, details = self._measure(rule, element)
        except (RuntimeError, ValueError) as error:
            result.update(
                status="NOT_CHECKABLE",
                reason=f"Measurement could not be computed: {error}",
                evidence_source="IFC_GEOMETRY",
                evidence_details={"error_type": type(error).__name__},
            )
            return result

        threshold = float(rule["requirement"]["value"])
        passed = measured >= threshold
        result.update(
            status="PASS" if passed else "FAIL",
            measured_value=round(measured, 3),
            reason=(
                f"Measured {measured:.3f} mm is greater than or equal to {threshold:.3f} mm."
                if passed
                else f"Measured {measured:.3f} mm is below the required {threshold:.3f} mm."
            ),
            evidence_source=f"IFC_{source}",
            evidence_details={"measurement": details, "applicability": applicability},
        )
        return result

    def run(self, persist: bool = True) -> list[dict]:
        results: list[dict] = []
        for rule in self.collection["rules"]:
            for element in self.model.by_type(rule["target"]["ifc_class"]):
                result = self.evaluate(rule, element)
                if result["status"] not in STATUSES:
                    raise AssertionError(f"Invalid status {result['status']}")
                results.append(result)
        self.results = sorted(results, key=lambda item: (item["rule_id"], item["element_guid"]))
        if persist:
            self.results_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "execution_id": self.execution_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model_id": MODEL_ID,
                "checker_version": CHECKER_VERSION,
                "results": self.results,
            }
            self.results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.results

    def ensure_results(self) -> list[dict]:
        return self.results or self.run(persist=False)

    def ids_report(self) -> dict:
        specification_file = ids.open(str(self.ids_path))
        specification_file.validate(self.model)
        identifier_by_name = {
            "Doors expose a clear opening width": "IDS-DOOR-CLEAR-WIDTH",
            "Doors expose a clear opening height": "IDS-DOOR-CLEAR-HEIGHT",
            "Spaces expose a geometric representation": "IDS-EGRESS-SPACE-GEOMETRY",
        }
        specifications = []
        for specification in specification_file.specifications:
            specifications.append(
                {
                    # IfcTester 0.8.3 validates the identifier in XML but does
                    # not hydrate it when reading IDS 1.0; preserve it by the
                    # stable specification name until that parser is upgraded.
                    "identifier": specification.identifier
                    or identifier_by_name.get(specification.name),
                    "name": specification.name,
                    "status": specification.status,
                    "applicable_count": len(specification.applicable_entities),
                    "passed_count": len(specification.passed_entities),
                    "failed_count": len(specification.failed_entities),
                    "failed_element_guids": sorted(
                        element.GlobalId for element in specification.failed_entities
                    ),
                }
            )
        return {
            "standard": "buildingSMART IDS 1.0",
            "purpose": "Information quality/checkability only; regulatory threshold evaluation is separate.",
            "specifications": specifications,
        }

    def serialised_elements(self, include_geometry: bool = False) -> list[dict]:
        return [
            serialise_element(element, include_geometry=include_geometry)
            for element in sorted(self.elements.values(), key=lambda item: item.GlobalId)
        ]
