from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .paths import RULE_SCHEMA_PATH, RULES_PATH


def load_rule_collection(
    rules_path: Path = RULES_PATH,
    schema_path: Path = RULE_SCHEMA_PATH,
) -> dict:
    collection = json.loads(rules_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(collection)
    return collection


def index_rules(collection: dict) -> dict[str, dict]:
    return {rule["rule_id"]: rule for rule in collection["rules"]}

