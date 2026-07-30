from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.geom
from ifcopenshell.util.element import get_psets
from ifcopenshell.util.placement import get_local_placement


@dataclass(frozen=True)
class GeometryEvidence:
    height_mm: float
    bbox_min: list[float]
    bbox_max: list[float]
    vertex_count: int
    triangle_count: int


def open_model(path: Path):
    return ifcopenshell.open(str(path))


def element_psets(element) -> dict[str, dict[str, Any]]:
    return get_psets(element, psets_only=True)


def property_value(element, property_set: str, property_name: str):
    return element_psets(element).get(property_set, {}).get(property_name)


def _settings():
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    return settings


def geometry_payload(element) -> dict:
    shape = ifcopenshell.geom.create_shape(_settings(), element)
    # IfcOpenShell geometry output is normalized to SI metres even when the
    # project declares millimetres. IFC property values remain in project
    # units and are handled separately by the rule mappings.
    vertices = [round(float(value), 6) for value in shape.geometry.verts]
    triangles = [int(value) for value in shape.geometry.faces]
    xs, ys, zs = vertices[0::3], vertices[1::3], vertices[2::3]
    return {
        "positions": vertices,
        "indices": triangles,
        "bbox": {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        },
        "placeholder": False,
    }


def geometry_evidence(element) -> GeometryEvidence:
    payload = geometry_payload(element)
    bbox_min = payload["bbox"]["min"]
    bbox_max = payload["bbox"]["max"]
    return GeometryEvidence(
        height_mm=round((bbox_max[2] - bbox_min[2]) * 1000.0, 3),
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        vertex_count=len(payload["positions"]) // 3,
        triangle_count=len(payload["indices"]) // 3,
    )


def _box_mesh(origin: list[float], dimensions: list[float]) -> dict:
    x, y, z = origin
    width, depth, height = dimensions
    vertices = [
        x, y, z,
        x + width, y, z,
        x + width, y + depth, z,
        x, y + depth, z,
        x, y, z + height,
        x + width, y, z + height,
        x + width, y + depth, z + height,
        x, y + depth, z + height,
    ]
    triangles = [
        0, 1, 2, 0, 2, 3,
        4, 6, 5, 4, 7, 6,
        0, 4, 5, 0, 5, 1,
        1, 5, 6, 1, 6, 2,
        2, 6, 7, 2, 7, 3,
        3, 7, 4, 3, 4, 0,
    ]
    return {
        "positions": vertices,
        "indices": triangles,
        "bbox": {"min": origin, "max": [x + width, y + depth, z + height]},
        "placeholder": True,
    }


def scene_geometry(element) -> dict:
    if getattr(element, "Representation", None):
        return geometry_payload(element)
    psets = element_psets(element)
    demo = psets.get("Pset_DemoViewer", {})
    matrix = get_local_placement(getattr(element, "ObjectPlacement", None))
    origin = [
        round(float(matrix[0][3]) / 1000.0, 6),
        round(float(matrix[1][3]) / 1000.0, 6),
        round(float(matrix[2][3]) / 1000.0, 6),
    ]
    dimensions = [
        float(demo.get("PlaceholderWidth", 1000.0)) / 1000.0,
        float(demo.get("PlaceholderDepth", 1000.0)) / 1000.0,
        float(demo.get("PlaceholderHeight", 400.0)) / 1000.0,
    ]
    return _box_mesh(origin, dimensions)


def serialise_element(element, include_geometry: bool = False) -> dict:
    payload = {
        "global_id": element.GlobalId,
        "ifc_class": element.is_a(),
        "name": element.Name or element.GlobalId,
        "properties": {
            name: {key: value for key, value in values.items() if key != "id"}
            for name, values in element_psets(element).items()
        },
    }
    if include_geometry:
        payload["geometry"] = scene_geometry(element)
    return payload
