import pytest

from ifc_compliance_mvd.imports import (
    MAX_IFC_BYTES,
    ImportValidationError,
    validate_filename,
    validate_payload,
)


@pytest.mark.parametrize(
    "filename",
    ["../model.ifc", r"C:\model.ifc", "folder/model.ifc", "model.ifczip", ""],
)
def test_filename_validation_rejects_paths_and_non_ifc_extensions(filename):
    with pytest.raises(ImportValidationError):
        validate_filename(filename)


def test_payload_validation_rejects_size_before_parser():
    with pytest.raises(ImportValidationError) as error:
        validate_payload(b"x" * (MAX_IFC_BYTES + 1), "application/octet-stream")
    assert error.value.code == "UPLOAD_TOO_LARGE"
    assert error.value.status_code == 413


def test_payload_validation_requires_complete_step_envelope():
    with pytest.raises(ImportValidationError) as error:
        validate_payload(
            b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;",
            "application/x-step",
        )
    assert error.value.code == "TRUNCATED_IFC"
