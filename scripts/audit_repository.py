"""Fail closed when tracked public-repository hygiene drifts."""

from __future__ import annotations

import importlib.metadata
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
MAX_TRACKED_BYTES = 1024 * 1024

FORBIDDEN_PARTS = {".venv", "node_modules", "__pycache__"}
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub personal token": re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "assigned secret": re.compile(
        r"""(?i)(?:api[_-]?key|password)\s*[:=]\s*["'][^"']+["']"""
    ),
}
LOCAL_PATH_PATTERNS = {
    "Windows user profile": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
    "macOS user profile": re.compile(r"/Users/[^/\s]+/"),
    "Linux user profile": re.compile(r"/home/[^/\s]+/"),
}

EXPECTED_LICENSE_MARKERS = {
    "defusedxml": {"PSFL"},
    "fastapi": {"MIT"},
    "ifcopenshell": {"LGPL"},
    "ifctester": {"LGPL"},
    "jsonschema": {"MIT"},
    "uvicorn": {"BSD"},
    "bcf-client": {"GPL"},
    "httpx": {"BSD"},
    "packaging": {"Apache", "BSD"},
    "pytest": {"MIT"},
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def direct_requirements() -> list[Requirement]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    values = list(project["project"]["dependencies"])
    for group in project["project"].get("optional-dependencies", {}).values():
        values.extend(group)
    return [Requirement(value) for value in values]


def audit_dependencies(errors: list[str]) -> None:
    locked = {}
    for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        locked[canonicalize_name(requirement.name)] = requirement

    for requirement in direct_requirements():
        name = canonicalize_name(requirement.name)
        pins = [item for item in requirement.specifier if item.operator == "=="]
        if len(pins) != 1 or len(list(requirement.specifier)) != 1:
            errors.append(f"direct dependency is not exactly pinned: {requirement}")
        if name not in locked:
            errors.append(f"direct dependency is absent from requirements.lock: {name}")
            continue
        installed = importlib.metadata.version(requirement.name)
        if installed != pins[0].version:
            errors.append(
                f"installed {requirement.name}=={installed}, expected {pins[0].version}"
            )

        metadata = importlib.metadata.metadata(requirement.name)
        license_text = " ".join(
            filter(
                None,
                [
                    metadata.get("License-Expression"),
                    metadata.get("License"),
                    *(
                        classifier
                        for classifier in metadata.get_all("Classifier") or []
                        if classifier.startswith("License ::")
                    ),
                ],
            )
        )
        markers = EXPECTED_LICENSE_MARKERS.get(name)
        if markers and not any(marker.casefold() in license_text.casefold() for marker in markers):
            errors.append(
                f"license metadata for {requirement.name} lacks expected marker "
                f"{sorted(markers)}: {license_text or '<empty>'}"
            )


def audit_files(files: list[Path], errors: list[str]) -> None:
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if any(part in FORBIDDEN_PARTS for part in path.relative_to(ROOT).parts):
            errors.append(f"forbidden runtime directory is tracked: {relative}")
        if relative == ".env" or relative.startswith("data/runtime/"):
            errors.append(f"forbidden runtime artifact is tracked: {relative}")
        if path.stat().st_size > MAX_TRACKED_BYTES:
            errors.append(
                f"tracked file exceeds {MAX_TRACKED_BYTES} bytes: "
                f"{relative} ({path.stat().st_size})"
            )
        if path.resolve() == SELF or path.stat().st_size > MAX_TRACKED_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in LOCAL_PATH_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} appears in tracked file: {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} pattern appears in tracked file: {relative}")


def main() -> int:
    errors: list[str] = []
    files = tracked_files()
    audit_files(files, errors)
    audit_dependencies(errors)
    if errors:
        print("Repository audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"Repository audit passed: {len(files)} tracked files; "
        f"no forbidden runtime data, user paths, secret patterns, or >1 MiB files."
    )
    print(
        "Direct dependencies are exactly pinned, locked, installed at the expected "
        "versions, and expose the registered license markers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
