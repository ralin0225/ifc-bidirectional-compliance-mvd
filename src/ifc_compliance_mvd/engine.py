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

CHECKER_VERSION = "0.2.0"
MODEL_ID = "ibc-egress-demo"
STATUSES = {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_CHECKABLE", "MANUAL_REVIEW_REQUIRED"}


class ComplianceEngine:
    checker_version = CHECKER_VERSION

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        ids_path: Path = IDS_PATH,
        results_path: Path = RESULTS_PATH,
        model_id: str = MODEL_ID,
    ) -> None:
        self.model_path = model_path
        self.ids_path = ids_path
        self.results_path = results_path
        self.model_id = model_id
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
    def _classification_context(element, system_name: str) -> list[dict[str, Any]]:
        records = []
        for association in tuple(getattr(element, "HasAssociations", ()) or ()):
            if not association.is_a("IfcRelAssociatesClassification"):
                continue
            reference = getattr(association, "RelatingClassification", None)
            if reference is None:
                continue
            source = getattr(reference, "ReferencedSource", None)
            source_name = getattr(source, "Name", None)
            if source_name != system_name:
                continue
            code = (
                getattr(reference, "Identification", None)
                or getattr(reference, "ItemReference", None)
                or getattr(reference, "Name", None)
            )
            if code is None:
                continue
            records.append(
                {
                    "code": str(code),
                    "name": getattr(reference, "Name", None),
                    "system": source_name,
                    "relationship_guid": association.GlobalId,
                    "reference_type": reference.is_a(),
                }
            )
        return sorted(records, key=lambda item: (item["code"], item["relationship_guid"]))

    @staticmethod
    def _applicability(rule: dict, element) -> tuple[str | None, str | None, dict]:
        details: dict[str, Any] = {}
        for condition in rule["applicability"]:
            if condition.get("kind") == "related_space_occupancy":
                boundaries = tuple(getattr(element, "ProvidesBoundaries", ()) or ())
                related_spaces = [
                    relation.RelatingSpace
                    for relation in boundaries
                    if relation.is_a("IfcRelSpaceBoundary")
                    and getattr(relation, "RelatingSpace", None) is not None
                ]
                key = "IfcRelSpaceBoundary.RelatingSpace occupancy context"
                contexts = []
                has_unknown_context = False
                applicable = False
                for space in related_spaces:
                    occupant_load = property_value(
                        space,
                        condition["occupant_load"]["property_set"],
                        condition["occupant_load"]["property"],
                    )
                    classification = ComplianceEngine._classification_context(
                        space,
                        condition["occupancy_group"]["classification_system"],
                    )
                    fallback = condition["occupancy_group"].get("fallback_property")
                    fallback_group = (
                        property_value(
                            space,
                            fallback["property_set"],
                            fallback["property"],
                        )
                        if fallback and not classification
                        else None
                    )
                    occupancy_groups = (
                        [record["code"] for record in classification]
                        if classification
                        else ([str(fallback_group)] if fallback_group is not None else [])
                    )
                    try:
                        numeric_occupant_load = (
                            float(occupant_load) if occupant_load is not None else None
                        )
                    except (TypeError, ValueError):
                        numeric_occupant_load = None
                    contexts.append(
                        {
                            "space_guid": space.GlobalId,
                            "space_name": space.Name or space.GlobalId,
                            "occupant_load": occupant_load,
                            "numeric_occupant_load": numeric_occupant_load,
                            "occupancy_groups": occupancy_groups,
                            "occupancy_group_source": (
                                "IFC_CLASSIFICATION"
                                if classification
                                else (
                                    f'{fallback["property_set"]}.{fallback["property"]}'
                                    if fallback_group is not None
                                    else None
                                )
                            ),
                            "classification": classification,
                        }
                    )
                    has_unknown_context = has_unknown_context or (
                        numeric_occupant_load is None or not occupancy_groups
                    )
                    applicable = applicable or (
                        numeric_occupant_load is not None
                        and numeric_occupant_load >= float(condition["minimum_occupant_load"])
                    ) or any(
                        group.upper() == condition["hazardous_group"].upper()
                        for group in occupancy_groups
                    )
                details[key] = {
                    "relationship_count": len(boundaries),
                    "related_spaces": contexts,
                }
                if not related_spaces or (not applicable and has_unknown_context):
                    return (
                        condition.get("missing_status", "NOT_CHECKABLE"),
                        "Applicability cannot be decided from a complete door-to-space occupancy context.",
                        details,
                    )
                if not applicable:
                    return (
                        "NOT_APPLICABLE",
                        "Related spaces have occupant loads below 50 and are not Group H occupancies.",
                        details,
                    )
                continue

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
                expected = requirement.get("expected_value")
                if value is None or (expected is not None and value != expected):
                    label = f'{requirement["property_set"]}.{requirement["property"]}'
                    if expected is not None:
                        label += f"={str(expected).lower()}"
                    missing.append(label)
            elif requirement["kind"] == "attribute":
                if getattr(element, requirement["attribute"], None) is None:
                    missing.append(f'Ifc attribute {requirement["attribute"]}')
            elif requirement["kind"] == "relationship":
                if not tuple(getattr(element, requirement["inverse_attribute"], ()) or ()):
                    missing.append(requirement["relationship"])
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
        if metric == "egress_swing_direction_conformance":
            path = "Pset_ComplianceRelationships.SwingDirection"
            raw_value = property_value(
                element,
                "Pset_ComplianceRelationships",
                "SwingDirection",
            )
            normalized = str(raw_value).strip().upper()
            if normalized not in {"EGRESS", "INGRESS"}:
                raise ValueError(
                    f"{path} must be one of EGRESS or INGRESS, received {raw_value!r}"
                )
            boundaries = tuple(getattr(element, "ProvidesBoundaries", ()) or ())
            return (
                1.0 if normalized == "EGRESS" else 0.0,
                "RELATIONSHIP",
                {
                    "property_path": path,
                    "raw_value": raw_value,
                    "normalized_value": normalized,
                    "relationship_type": "IfcRelSpaceBoundary",
                    "relationship_guids": sorted(
                        relation.GlobalId
                        for relation in boundaries
                        if relation.is_a("IfcRelSpaceBoundary")
                    ),
                    "related_space_guids": sorted(
                        relation.RelatingSpace.GlobalId
                        for relation in boundaries
                        if relation.is_a("IfcRelSpaceBoundary")
                        and getattr(relation, "RelatingSpace", None) is not None
                    ),
                },
            )
        if metric == "egress_path_to_exit_discharge":
            pending = [element]
            visited_spaces: set[str] = set()
            traversed_doors: set[str] = set()
            unclassified_doors: set[str] = set()
            relationship_guids: set[str] = set()
            exit_door_guid = None
            while pending:
                space = pending.pop(0)
                if space.GlobalId in visited_spaces:
                    continue
                visited_spaces.add(space.GlobalId)
                boundaries = tuple(getattr(space, "BoundedBy", ()) or ())
                for relation in boundaries:
                    if not relation.is_a("IfcRelSpaceBoundary"):
                        continue
                    relationship_guids.add(relation.GlobalId)
                    door = getattr(relation, "RelatedBuildingElement", None)
                    if door is None or not door.is_a("IfcDoor"):
                        continue
                    traversed_doors.add(door.GlobalId)
                    is_exit = property_value(
                        door,
                        "Pset_ComplianceTopology",
                        "IsExitDischarge",
                    )
                    if is_exit is None:
                        unclassified_doors.add(door.GlobalId)
                    if is_exit is True:
                        exit_door_guid = door.GlobalId
                        pending.clear()
                        break
                    for adjoining in tuple(getattr(door, "ProvidesBoundaries", ()) or ()):
                        adjoining_space = getattr(adjoining, "RelatingSpace", None)
                        if (
                            adjoining_space is not None
                            and adjoining_space.GlobalId not in visited_spaces
                        ):
                            pending.append(adjoining_space)
            if not relationship_guids:
                raise ValueError("No IfcRelSpaceBoundary topology is available for the space")
            if exit_door_guid is None and unclassified_doors:
                raise ValueError(
                    "Exit-discharge classification is missing for traversed door(s): "
                    + ", ".join(sorted(unclassified_doors))
                )
            return (
                1.0 if exit_door_guid else 0.0,
                "TOPOLOGY",
                {
                    "algorithm": "breadth-first traversal of IfcSpace–IfcDoor boundaries",
                    "visited_space_guids": sorted(visited_spaces),
                    "traversed_door_guids": sorted(traversed_doors),
                    "relationship_guids": sorted(relationship_guids),
                    "exit_discharge_door_guid": exit_door_guid,
                    "completeness_assertion": (
                        "Pset_ComplianceTopology.TopologyCoverageComplete"
                    ),
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
            "model_id": self.model_id,
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
            applicability_source = (
                "IFC_RELATIONSHIP"
                if "IfcRelSpaceBoundary.RelatingSpace occupancy context" in applicability
                else "IFC_PROPERTY"
            )
            result.update(
                status=status,
                reason=reason,
                evidence_source=applicability_source,
                evidence_details={"applicability": applicability},
            )
            return result

        if rule.get("automation_level") == "manual_judgement":
            result.update(
                status="MANUAL_REVIEW_REQUIRED",
                reason=(
                    "This requirement depends on field-observable door operation and "
                    "is not inferred from the available IFC representation."
                ),
                evidence_source="HUMAN_INSPECTION",
                evidence_details={
                    "applicability": applicability,
                    "manual_checklist": rule["mapping"]["manual_checklist"],
                },
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
                        item["ids_specification"]
                        for item in rule["required_information"]
                        if "ids_specification" in item
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
                evidence_source=rule["execution_method"],
                evidence_details={"error_type": type(error).__name__},
            )
            return result

        threshold = float(rule["requirement"]["value"])
        operator = rule["requirement"]["operator"]
        if operator == ">=":
            passed = measured >= threshold
        elif operator == "==":
            passed = measured == threshold
        else:
            raise ValueError(f"Unsupported comparison operator: {operator}")
        metric = rule["requirement"]["metric"]
        if metric == "egress_swing_direction_conformance":
            reason = (
                "Door swing is documented in the direction of egress travel."
                if passed
                else "Door swing is documented against the direction of egress travel."
            )
        elif metric == "egress_path_to_exit_discharge":
            reason = (
                "The modeled boundary graph contains a path to an exit-discharge door."
                if passed
                else "The asserted-complete boundary graph has no path to an exit-discharge door."
            )
        else:
            reason = (
                f"Measured {measured:.3f} mm is greater than or equal to {threshold:.3f} mm."
                if passed
                else f"Measured {measured:.3f} mm is below the required {threshold:.3f} mm."
            )
        result.update(
            status="PASS" if passed else "FAIL",
            measured_value=round(measured, 3),
            reason=reason,
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
                "model_id": self.model_id,
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
            "Doors expose an authored swing direction": "IDS-DOOR-SWING-DIRECTION",
            "Spaces declare topology export completeness": "IDS-EGRESS-SPACE-TOPOLOGY",
            "Spaces expose an IBC occupancy classification": (
                "IDS-SPACE-OCCUPANCY-CLASSIFICATION"
            ),
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

    def serialised_elements(
        self,
        include_geometry: bool = False,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict]:
        ordered = sorted(self.elements.values(), key=lambda item: item.GlobalId)
        selected = ordered[offset:] if limit is None else ordered[offset : offset + limit]
        return [
            serialise_element(element, include_geometry=include_geometry)
            for element in selected
        ]
