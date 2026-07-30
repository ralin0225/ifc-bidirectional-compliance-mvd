from __future__ import annotations

import argparse
import json
import os
from collections import Counter

import uvicorn

from .engine import ComplianceEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="IFC bidirectional compliance MVD")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Start the API and browser demonstrator")
    serve.add_argument("--host", default=os.getenv("IFC_MVD_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.getenv("IFC_MVD_PORT", "8000")))

    check = subparsers.add_parser("check", help="Run deterministic checks and write JSON")
    check.add_argument("--json", action="store_true", help="Print the complete result payload")

    subparsers.add_parser("ids", help="Validate IDS information requirements")

    args = parser.parse_args()
    if args.command == "serve":
        uvicorn.run("ifc_compliance_mvd.api:app", host=args.host, port=args.port)
        return

    engine = ComplianceEngine()
    if args.command == "check":
        results = engine.run(persist=True)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            counts = Counter(result["status"] for result in results)
            print(f"{engine.execution_id}: {len(results)} results")
            print(" ".join(f"{status}={count}" for status, count in sorted(counts.items())))
            print(f"Wrote {engine.results_path}")
        return
    print(json.dumps(engine.ids_report(), indent=2))


if __name__ == "__main__":
    main()

