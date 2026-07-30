"""Generate the buildingSMART IDS 1.0 information-requirement artifact."""

from pathlib import Path

import ifctester.ids

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "ids" / "ibc_egress_information_requirements.ids"


def add_specification(
    ids: ifctester.ids.Ids,
    *,
    identifier: str,
    name: str,
    entity: str,
    requirements: list,
) -> None:
    specification = ifctester.ids.Specification(
        name=name,
        identifier=identifier,
        ifcVersion=["IFC4"],
        minOccurs=0,
        maxOccurs="unbounded",
        description="Information prerequisite for a deterministic IBC MVD check; it does not itself decide regulatory compliance.",
    )
    specification.applicability.append(ifctester.ids.Entity(name=entity))
    specification.requirements.extend(requirements)
    ids.specifications.append(specification)


def generate() -> Path:
    ids = ifctester.ids.Ids(
        title="IBC 2021 egress MVD information requirements",
        version="1.0.0",
        description="Machine-readable checkability requirements derived from the structured rule library.",
        author="research@example.invalid",
        purpose="Minimum Viable Demonstrator",
    )
    add_specification(
        ids,
        identifier="IDS-DOOR-CLEAR-WIDTH",
        name="Doors expose a clear opening width",
        entity="IFCDOOR",
        requirements=[
            ifctester.ids.Property(
                propertySet="Pset_ComplianceMeasurements",
                baseName="ClearOpeningWidth",
                dataType="IFCLENGTHMEASURE",
                cardinality="required",
            )
        ],
    )
    add_specification(
        ids,
        identifier="IDS-DOOR-CLEAR-HEIGHT",
        name="Doors expose a clear opening height",
        entity="IFCDOOR",
        requirements=[
            ifctester.ids.Property(
                propertySet="Pset_ComplianceMeasurements",
                baseName="ClearOpeningHeight",
                dataType="IFCLENGTHMEASURE",
                cardinality="required",
            )
        ],
    )
    add_specification(
        ids,
        identifier="IDS-EGRESS-SPACE-GEOMETRY",
        name="Spaces expose a geometric representation",
        entity="IFCSPACE",
        requirements=[
            ifctester.ids.Attribute(
                name="Representation",
                cardinality="required",
            )
        ],
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not ids.to_xml(OUTPUT):
        raise RuntimeError("Generated IDS does not validate against the buildingSMART IDS schema")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return OUTPUT


if __name__ == "__main__":
    generate()

