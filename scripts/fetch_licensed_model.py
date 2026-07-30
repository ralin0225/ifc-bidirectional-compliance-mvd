"""Fetch the registered CC BY 4.0 clinic IFC into ignored runtime storage."""

from __future__ import annotations

import argparse

from ifc_compliance_mvd.licensed_models import (
    fetch_licensed_model,
    licensed_model_path,
    load_licensed_model_manifest,
    verify_licensed_model,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify an existing cached file without network access.",
    )
    args = parser.parse_args()
    manifest = load_licensed_model_manifest()
    if args.check:
        path = licensed_model_path(manifest)
        if not path.is_file():
            parser.error(f"Licensed model is not cached: {path}")
        verify_licensed_model(path, manifest)
        downloaded = False
    else:
        path, downloaded = fetch_licensed_model(manifest)
    print(
        f"{'Downloaded' if downloaded else 'Verified'} {manifest.display_name}: "
        f"{manifest.expected_bytes} bytes, sha256={manifest.sha256}"
    )
    print(f"License: {manifest.license_spdx}; attribution: {manifest.attribution}")
    print(f"Runtime path: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
