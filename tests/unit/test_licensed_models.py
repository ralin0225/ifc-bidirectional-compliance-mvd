import io

import pytest

from ifc_compliance_mvd.imports import MAX_IFC_BYTES
from ifc_compliance_mvd.licensed_models import (
    LicensedModelManifest,
    fetch_licensed_model,
    licensed_model_path,
    load_licensed_model_manifest,
)


def test_committed_licensed_model_manifest_is_pinned_and_redistributable():
    manifest = load_licensed_model_manifest()
    assert manifest.schema == "IFC2X3"
    assert manifest.license_spdx == "CC-BY-4.0"
    assert manifest.redistribution_allowed is True
    assert manifest.source_commit in manifest.download_url
    assert manifest.expected_bytes < MAX_IFC_BYTES
    assert licensed_model_path(manifest).name == "Clinic_Architectural.ifc"


class FakeResponse(io.BytesIO):
    def geturl(self):
        return "https://example.test/model.ifc"

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def test_fetch_rejects_content_that_does_not_match_manifest(tmp_path, monkeypatch):
    payload = b"ISO-10303-21;\nFILE_SCHEMA(('IFC4'));\nEND-ISO-10303-21;"
    manifest = LicensedModelManifest(
        model_id="test",
        display_name="Test",
        description="Test",
        schema="IFC4",
        filename="test.ifc",
        source_repository="https://example.test/repo",
        source_commit="a" * 40,
        source_path="test.ifc",
        download_url=f"https://example.test/{'a' * 40}/test.ifc",
        expected_bytes=len(payload) + 1,
        sha256="0" * 64,
        license_spdx="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution="Test",
        redistribution_allowed=True,
        download_verified_on="2026-07-30",
        repository_tracking="manifest-only",
        offline_fallback="fixture.ifc",
    )
    monkeypatch.setattr(
        "ifc_compliance_mvd.licensed_models.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(payload),
    )
    with pytest.raises(ValueError, match="size"):
        fetch_licensed_model(manifest, root=tmp_path)
    assert not (tmp_path / "test.ifc").exists()
    assert not (tmp_path / "test.ifc.part").exists()
