from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .imports import MAX_IFC_BYTES, validate_payload
from .paths import LICENSED_MODEL_MANIFEST_PATH, LICENSED_MODELS_PATH

DOWNLOAD_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class LicensedModelManifest:
    model_id: str
    display_name: str
    description: str
    schema: str
    filename: str
    source_repository: str
    source_commit: str
    source_path: str
    download_url: str
    expected_bytes: int
    sha256: str
    license_spdx: str
    license_url: str
    attribution: str
    redistribution_allowed: bool
    download_verified_on: str
    repository_tracking: str
    offline_fallback: str


def load_licensed_model_manifest(
    path: Path = LICENSED_MODEL_MANIFEST_PATH,
) -> LicensedModelManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        manifest = LicensedModelManifest(**raw)
    except TypeError as error:
        raise ValueError(f"Invalid licensed-model manifest: {error}") from error
    if (
        len(manifest.source_commit) != 40
        or any(character not in "0123456789abcdef" for character in manifest.source_commit)
    ):
        raise ValueError("The licensed-model source commit must be a full lowercase SHA-1.")
    if (
        len(manifest.sha256) != 64
        or any(character not in "0123456789abcdef" for character in manifest.sha256)
    ):
        raise ValueError("The licensed-model checksum must be a lowercase SHA-256.")
    if manifest.source_commit not in manifest.download_url:
        raise ValueError("The download URL must be pinned to the registered source commit.")
    if urlparse(manifest.download_url).scheme != "https":
        raise ValueError("The licensed-model download URL must use HTTPS.")
    if not 0 < manifest.expected_bytes <= MAX_IFC_BYTES:
        raise ValueError("The licensed model must fit the platform upload boundary.")
    if not manifest.filename.lower().endswith(".ifc") or Path(manifest.filename).name != manifest.filename:
        raise ValueError("The licensed-model filename must be a plain .ifc basename.")
    if not manifest.redistribution_allowed or manifest.license_spdx != "CC-BY-4.0":
        raise ValueError("The registered model must have explicit redistribution permission.")
    return manifest


def licensed_model_path(
    manifest: LicensedModelManifest,
    root: Path = LICENSED_MODELS_PATH,
) -> Path:
    resolved_root = Path(root).resolve()
    target = (resolved_root / manifest.filename).resolve()
    if resolved_root not in target.parents:
        raise ValueError("The licensed-model destination escaped runtime storage.")
    return target


def file_digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(DOWNLOAD_CHUNK_BYTES), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def verify_licensed_model(path: Path, manifest: LicensedModelManifest) -> None:
    size, digest = file_digest(path)
    if size != manifest.expected_bytes:
        raise ValueError(
            f"Licensed-model size mismatch: received {size}, expected {manifest.expected_bytes}."
        )
    if digest != manifest.sha256:
        raise ValueError(
            f"Licensed-model SHA-256 mismatch: received {digest}, expected {manifest.sha256}."
        )
    validate_payload(Path(path).read_bytes(), "application/x-step")


def fetch_licensed_model(
    manifest: LicensedModelManifest,
    *,
    root: Path = LICENSED_MODELS_PATH,
    timeout_seconds: int = 120,
) -> tuple[Path, bool]:
    target = licensed_model_path(manifest, root)
    if target.exists():
        verify_licensed_model(target, manifest)
        return target, False

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f"{target.suffix}.part")
    if temporary.exists():
        temporary.unlink()
    request = urllib.request.Request(
        manifest.download_url,
        headers={"User-Agent": "ifc-bidirectional-compliance-mvd/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if urlparse(response.geturl()).scheme != "https":
                raise ValueError("The licensed-model download redirected away from HTTPS.")
            digest = hashlib.sha256()
            size = 0
            with temporary.open("wb") as stream:
                while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                    size += len(chunk)
                    if size > manifest.expected_bytes or size > MAX_IFC_BYTES:
                        raise ValueError("The licensed-model download exceeded its registered size.")
                    digest.update(chunk)
                    stream.write(chunk)
        if size != manifest.expected_bytes or digest.hexdigest() != manifest.sha256:
            raise ValueError("The licensed-model download failed size or SHA-256 verification.")
        validate_payload(temporary.read_bytes(), "application/x-step")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target, True
