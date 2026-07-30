from __future__ import annotations


def ego_graph(*, engine, rule_id: str | None = None, element_guid: str | None = None) -> dict:
    results = engine.ensure_results()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, kind: str, label: str, **data) -> None:
        nodes[node_id] = {"id": node_id, "kind": kind, "label": label, **data}

    if rule_id:
        rule = engine.rules[rule_id]
        clause_id = f'clause:{rule["source"]["section"]}'
        rule_node = f"rule:{rule_id}"
        add_node(clause_id, "Clause", f'IBC {rule["source"]["section"]}')
        add_node(rule_node, "Rule", rule["title"], rule_id=rule_id)
        edges.append({"source": clause_id, "target": rule_node, "type": "FORMALIZED_AS"})
        selected = [result for result in results if result["rule_id"] == rule_id]
    elif element_guid:
        element = engine.elements[element_guid]
        element_node = f"element:{element_guid}"
        add_node(element_node, "IfcElement", element.Name or element_guid, global_id=element_guid)
        selected = [result for result in results if result["element_guid"] == element_guid]
    else:
        raise ValueError("rule_id or element_guid is required")

    for result in selected:
        rule = engine.rules[result["rule_id"]]
        rule_node = f'rule:{result["rule_id"]}'
        element_node = f'element:{result["element_guid"]}'
        result_node = f'result:{result["rule_id"]}:{result["element_guid"]}'
        add_node(rule_node, "Rule", rule["title"], rule_id=result["rule_id"])
        add_node(
            element_node,
            "IfcElement",
            result["element_name"],
            global_id=result["element_guid"],
            ifc_class=result["ifc_class"],
        )
        add_node(result_node, "ComplianceResult", result["status"], status=result["status"])
        edges.extend(
            [
                {"source": rule_node, "target": element_node, "type": "APPLIES_TO"},
                {"source": rule_node, "target": result_node, "type": "PRODUCES"},
                {"source": result_node, "target": element_node, "type": "EVIDENCED_BY"},
            ]
        )
    return {"nodes": list(nodes.values()), "edges": edges}

