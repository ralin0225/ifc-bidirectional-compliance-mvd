"""Generate the small, deterministic IFC4 model used by the demonstrator.

The fixture is generated from code so its geometry, properties, applicability
flags, expected outcomes, and GlobalIds are reviewable and reproducible.
"""

from __future__ import annotations

import csv
import uuid
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data" / "models" / "generated" / "ibc_egress_demo.ifc"
GROUND_TRUTH_PATH = ROOT / "tests" / "expected" / "ground_truth.csv"

RULE_WIDTH = "IBC2021-1010.1.1-WIDTH"
RULE_HEIGHT = "IBC2021-1010.1.1-HEIGHT"
RULE_SPACE = "IBC2021-1003.2-EGRESS-HEIGHT"


def stable_guid(name: str) -> str:
    value = uuid.uuid5(uuid.NAMESPACE_URL, f"ifc-mvd.local/{name}")
    return ifcopenshell.guid.compress(value.hex)


def api(operation: str, model: ifcopenshell.file, **kwargs):
    return ifcopenshell.api.run(operation, model, **kwargs)


def set_guid(entity, name: str) -> None:
    entity.GlobalId = stable_guid(name)


def place(model: ifcopenshell.file, product, x_mm: float, y_mm: float, z_mm: float = 0.0) -> None:
    matrix = np.eye(4)
    matrix[0:3, 3] = [x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0]
    api("geometry.edit_object_placement", model, product=product, matrix=matrix, is_si=True)


def add_properties(model: ifcopenshell.file, product, name: str, properties: dict) -> None:
    pset = api("pset.add_pset", model, product=product, name=name)
    api("pset.edit_pset", model, pset=pset, properties=properties)


def add_box(
    model: ifcopenshell.file,
    product,
    body_context,
    *,
    x_mm: float,
    y_mm: float,
    z_mm: float,
) -> None:
    representation = api(
        "geometry.add_wall_representation",
        model,
        context=body_context,
        length=x_mm / 1000.0,
        thickness=y_mm / 1000.0,
        height=z_mm / 1000.0,
    )
    api("geometry.assign_representation", model, product=product, representation=representation)


def add_door(
    model: ifcopenshell.file,
    storey,
    body_context,
    *,
    key: str,
    name: str,
    x_mm: float,
    clear_width_mm: float | None,
    clear_height_mm: float | None,
    is_egress: bool,
) -> str:
    nominal_width = clear_width_mm or 900.0
    nominal_height = clear_height_mm or 2100.0
    door = api("root.create_entity", model, ifc_class="IfcDoor", name=name)
    set_guid(door, key)
    door.OverallWidth = nominal_width
    door.OverallHeight = nominal_height
    add_box(
        model,
        door,
        body_context,
        x_mm=nominal_width,
        y_mm=120.0,
        z_mm=nominal_height,
    )
    place(model, door, x_mm=x_mm, y_mm=0.0)
    api("spatial.assign_container", model, products=[door], relating_structure=storey)
    add_properties(
        model,
        door,
        "Pset_ComplianceApplicability",
        {"IsMeansOfEgress": is_egress},
    )
    measurements = {}
    if clear_width_mm is not None:
        measurements["ClearOpeningWidth"] = model.createIfcLengthMeasure(clear_width_mm)
    if clear_height_mm is not None:
        measurements["ClearOpeningHeight"] = model.createIfcLengthMeasure(clear_height_mm)
    if measurements:
        add_properties(model, door, "Pset_ComplianceMeasurements", measurements)
    return door.GlobalId


def add_space(
    model: ifcopenshell.file,
    storey,
    body_context,
    *,
    key: str,
    name: str,
    x_mm: float,
    height_mm: float | None,
    is_egress: bool,
) -> str:
    space = api("root.create_entity", model, ifc_class="IfcSpace", name=name)
    set_guid(space, key)
    if height_mm is not None:
        add_box(
            model,
            space,
            body_context,
            x_mm=2400.0,
            y_mm=1800.0,
            z_mm=height_mm,
        )
    place(model, space, x_mm=x_mm, y_mm=2500.0)
    api("aggregate.assign_object", model, products=[space], relating_object=storey)
    add_properties(
        model,
        space,
        "Pset_ComplianceApplicability",
        {"IsMeansOfEgress": is_egress},
    )
    add_properties(
        model,
        space,
        "Pset_DemoViewer",
        {
            "PlaceholderWidth": 2400.0,
            "PlaceholderDepth": 1800.0,
            "PlaceholderHeight": height_mm or 400.0,
        },
    )
    return space.GlobalId


def generate() -> tuple[Path, Path]:
    model = api("project.create_file", None, version="IFC4")
    model.header.file_name.name = "ibc_egress_demo.ifc"
    model.header.file_name.time_stamp = "2026-07-30T00:00:00Z"
    model.header.file_name.author = ("IFC compliance MVD",)
    model.header.file_name.organization = ("Open research demonstrator",)
    model.header.file_name.authorization = "MIT-licensed fixture; not a certified design"
    project = api("root.create_entity", model, ifc_class="IfcProject", name="IBC Egress Compliance Demo")
    set_guid(project, "project")
    api("unit.assign_unit", model)

    model_context = api("context.add_context", model, context_type="Model")
    body_context = api(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )

    site = api("root.create_entity", model, ifc_class="IfcSite", name="Synthetic Site")
    building = api("root.create_entity", model, ifc_class="IfcBuilding", name="Synthetic Building")
    storey = api("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Ground Floor")
    for entity, key in ((site, "site"), (building, "building"), (storey, "storey")):
        set_guid(entity, key)
    api("aggregate.assign_object", model, products=[site], relating_object=project)
    api("aggregate.assign_object", model, products=[building], relating_object=site)
    api("aggregate.assign_object", model, products=[storey], relating_object=building)

    truth: list[dict[str, str]] = []

    door_cases = [
        ("door-pass", "Door PASS - generous opening", 0.0, 900.0, 2100.0, True, "PASS"),
        ("door-boundary", "Door PASS - exact threshold", 1300.0, 813.0, 2032.0, True, "PASS"),
        ("door-fail", "Door FAIL - undersized", 2600.0, 760.0, 1980.0, True, "FAIL"),
        ("door-missing", "Door NOT_CHECKABLE - clear dimensions absent", 3900.0, None, None, True, "NOT_CHECKABLE"),
        ("door-non-egress", "Door NOT_APPLICABLE - service access", 5200.0, 700.0, 1900.0, False, "NOT_APPLICABLE"),
    ]
    for key, name, x, width, height, is_egress, expected in door_cases:
        guid = add_door(
            model,
            storey,
            body_context,
            key=key,
            name=name,
            x_mm=x,
            clear_width_mm=width,
            clear_height_mm=height,
            is_egress=is_egress,
        )
        for rule_id in (RULE_WIDTH, RULE_HEIGHT):
            truth.append(
                {
                    "model_id": "ibc-egress-demo",
                    "element_guid": guid,
                    "rule_id": rule_id,
                    "expected_status": expected,
                    "note": name,
                }
            )

    space_cases = [
        ("space-pass", "Egress Space PASS - 2400 mm", 0.0, 2400.0, True, "PASS"),
        ("space-boundary", "Egress Space PASS - exact 2286 mm", 3000.0, 2286.0, True, "PASS"),
        ("space-fail", "Egress Space FAIL - 2200 mm", 6000.0, 2200.0, True, "FAIL"),
        ("space-missing", "Egress Space NOT_CHECKABLE - no representation", 9000.0, None, True, "NOT_CHECKABLE"),
        ("space-non-egress", "Space NOT_APPLICABLE - storage", 12000.0, 2100.0, False, "NOT_APPLICABLE"),
    ]
    for key, name, x, height, is_egress, expected in space_cases:
        guid = add_space(
            model,
            storey,
            body_context,
            key=key,
            name=name,
            x_mm=x,
            height_mm=height,
            is_egress=is_egress,
        )
        truth.append(
            {
                "model_id": "ibc-egress-demo",
                "element_guid": guid,
                "rule_id": RULE_SPACE,
                "expected_status": expected,
                "note": name,
            }
        )

    # IfcOpenShell assigns random GlobalIds to relationships and property sets.
    # Replace them with deterministic values so repeated generation produces
    # byte-for-byte identical IFC and check execution identifiers.
    stable_product_classes = {
        "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcDoor", "IfcSpace"
    }
    for root in model.by_type("IfcRoot"):
        if root.is_a() not in stable_product_classes:
            root.GlobalId = stable_guid(f"root-{root.is_a()}-{root.id()}")

    # API helpers internally use sets for inverse-safe assignment. Canonicalize
    # aggregate ordering before serialization so the generated STEP file is
    # byte-for-byte reproducible, not only semantically equivalent.
    for assignment in model.by_type("IfcUnitAssignment"):
        assignment.Units = tuple(sorted(assignment.Units, key=lambda item: item.id()))
    for relation in model.by_type("IfcRelContainedInSpatialStructure"):
        relation.RelatedElements = tuple(
            sorted(relation.RelatedElements, key=lambda item: item.GlobalId)
        )
    for relation in model.by_type("IfcRelAggregates"):
        relation.RelatedObjects = tuple(
            sorted(relation.RelatedObjects, key=lambda item: item.GlobalId)
        )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.write(MODEL_PATH)
    # IfcOpenShell follows the host newline convention. Normalize generated
    # text to LF so Windows and Unix clones remain byte-identical.
    model_text = MODEL_PATH.read_text(encoding="utf-8")
    MODEL_PATH.write_text(
        model_text.replace("\r\n", "\n"),
        encoding="utf-8",
        newline="\n",
    )

    GROUND_TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GROUND_TRUTH_PATH.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["model_id", "element_guid", "rule_id", "expected_status", "note"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(truth)

    print(f"Wrote {MODEL_PATH.relative_to(ROOT)}")
    print(f"Wrote {GROUND_TRUTH_PATH.relative_to(ROOT)}")
    return MODEL_PATH, GROUND_TRUTH_PATH


if __name__ == "__main__":
    generate()
