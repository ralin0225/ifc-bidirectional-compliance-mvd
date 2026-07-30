from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "regulations" / "ibc_2021_rules.json"
RULE_SCHEMA_PATH = ROOT / "data" / "regulations" / "rule.schema.json"
MODEL_PATH = ROOT / "data" / "models" / "generated" / "ibc_egress_demo.ifc"
IDS_PATH = ROOT / "data" / "ids" / "ibc_egress_information_requirements.ids"
RESULTS_PATH = ROOT / "data" / "results" / "latest.json"
FRONTEND_PATH = ROOT / "frontend"

