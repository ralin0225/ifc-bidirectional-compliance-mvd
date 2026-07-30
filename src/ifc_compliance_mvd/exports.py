from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import datetime
from html import escape
from pathlib import PurePosixPath
from xml.etree import ElementTree

from defusedxml import ElementTree as SafeElementTree

BCF_VERSION = "3.0"
BCF_NAMESPACE = uuid.UUID("322de99d-5a32-4ca5-9fee-d2bf655f76da")
EXPORTABLE_STATUSES = {"FAIL", "NOT_CHECKABLE", "MANUAL_REVIEW_REQUIRED"}


class UnsafeBcfArchive(ValueError):
    pass


def report_payload(run: dict) -> dict:
    return {
        "format_version": "1.0",
        "disclaimer": (
            "Research and teaching output; not a building approval, official "
            "certification, or legal opinion."
        ),
        "run": {key: value for key, value in run.items() if key != "results"},
        "results": run["results"],
    }


def json_report(run: dict) -> bytes:
    return json.dumps(
        report_payload(run),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def csv_report(run: dict) -> bytes:
    output = io.StringIO(newline="")
    fields = [
        "run_id",
        "execution_id",
        "model_id",
        "rule_id",
        "rule_version",
        "element_guid",
        "element_name",
        "ifc_class",
        "status",
        "measured_value",
        "operator",
        "required_value",
        "unit",
        "reason",
        "evidence_source",
        "evidence_details",
        "checker_version",
        "clause",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for result in run["results"]:
        writer.writerow(
            {
                **{
                    key: _csv_safe(value)
                    for key, value in result.items()
                    if key != "evidence_details"
                },
                "run_id": run["run_id"],
                "execution_id": run["execution_id"],
                "evidence_details": json.dumps(
                    result["evidence_details"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
    return output.getvalue().encode("utf-8-sig")


def _csv_safe(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def html_report(run: dict, *, locale: str = "en") -> bytes:
    chinese = locale == "zh-CN"
    title = "IFC 合规检查报告" if chinese else "IFC compliance check report"
    disclaimer = (
        "研究与教学输出；不是建筑审批、官方认证或法律意见。"
        if chinese
        else "Research and teaching output; not a building approval, official certification, or legal opinion."
    )
    labels = (
        ("状态", "构件", "规则", "实测", "要求", "证据来源")
        if chinese
        else ("Status", "Element", "Rule", "Measured", "Required", "Evidence source")
    )
    rows = []
    for result in run["results"]:
        measured = (
            "—"
            if result["measured_value"] is None
            else f'{result["measured_value"]} {result["unit"]}'
        )
        rows.append(
            "<tr>"
            f'<td><span class="status status-{escape(result["status"])}">{escape(result["status"])}</span></td>'
            f'<td><strong>{escape(result["element_name"])}</strong><code>{escape(result["element_guid"])}</code></td>'
            f'<td><strong>{escape(result["rule_id"])}</strong><small>IBC {escape(result["clause"])}</small></td>'
            f"<td>{escape(measured)}</td>"
            f'<td>{escape(result["operator"])} {escape(str(result["required_value"]))} {escape(result["unit"])}</td>'
            f'<td>{escape(result["evidence_source"] or "—")}<small>{escape(result["reason"])}</small></td>'
            "</tr>"
        )
    html = f"""<!doctype html>
<html lang="{escape(locale)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · {escape(run["run_id"])}</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #14262d; }}
    body {{ margin: 32px; }} h1 {{ margin-bottom: 4px; }}
    .disclaimer {{ border-left: 4px solid #d44d3f; padding: 8px 12px; background: #fff4f2; }}
    .meta {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 22px 0; }}
    .meta div {{ border-top: 1px solid #c8d7d9; padding-top: 6px; }}
    .meta small, td small, td code {{ display: block; color: #60747b; font-size: 11px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #c8d7d9; padding: 9px; text-align: left; vertical-align: top; }}
    th {{ background: #f2f7f7; }} .status {{ font: 700 10px monospace; }}
    .status-FAIL {{ color: #b62f25; }} .status-PASS {{ color: #12704f; }}
    @media print {{ body {{ margin: 12mm; }} .disclaimer {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <p>IFC ↔ IBC</p>
  <h1>{escape(title)}</h1>
  <p class="disclaimer">{escape(disclaimer)}</p>
  <section class="meta">
    <div><small>Run ID</small>{escape(run["run_id"])}</div>
    <div><small>Execution ID</small>{escape(run["execution_id"])}</div>
    <div><small>Model ID</small>{escape(run["model_id"])}</div>
    <div><small>Checker</small>{escape(run["checker_version"])}</div>
  </section>
  <table>
    <thead><tr>{''.join(f"<th>{escape(label)}</th>" for label in labels)}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>"""
    return html.encode("utf-8")


def _xml_bytes(root: ElementTree.Element) -> bytes:
    return ElementTree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    )


def _add_point(parent: ElementTree.Element, name: str, values: tuple[float, float, float]):
    point = ElementTree.SubElement(parent, name)
    for axis, value in zip(("X", "Y", "Z"), values, strict=True):
        ElementTree.SubElement(point, axis).text = str(value)


def _markup_xml(run: dict, result: dict, topic_guid: str, viewpoint_guid: str) -> bytes:
    root = ElementTree.Element("Markup")
    header = ElementTree.SubElement(root, "Header")
    ElementTree.SubElement(header, "Files")
    topic = ElementTree.SubElement(
        root,
        "Topic",
        {
            "Guid": topic_guid,
            "TopicStatus": "OPEN",
            "TopicType": "ERROR" if result["status"] == "FAIL" else "WARNING",
        },
    )
    ElementTree.SubElement(topic, "Title").text = (
        f'{result["status"]}: {result["element_name"]}'
    )
    labels = ElementTree.SubElement(topic, "Labels")
    for label in (result["status"], result["rule_id"], f'IBC {result["clause"]}'):
        ElementTree.SubElement(labels, "Label").text = label
    ElementTree.SubElement(topic, "CreationDate").text = run["started_at"]
    ElementTree.SubElement(topic, "CreationAuthor").text = (
        "ifc-compliance@localhost.invalid"
    )
    ElementTree.SubElement(topic, "Description").text = (
        f'Run {run["run_id"]}; rule {result["rule_id"]}; '
        f'IFC GlobalId {result["element_guid"]}. {result["reason"]}'
    )
    ElementTree.SubElement(topic, "DocumentReferences")
    ElementTree.SubElement(topic, "RelatedTopics")
    ElementTree.SubElement(topic, "Comments")
    viewpoints = ElementTree.SubElement(topic, "Viewpoints")
    viewpoint = ElementTree.SubElement(viewpoints, "ViewPoint", {"Guid": viewpoint_guid})
    ElementTree.SubElement(viewpoint, "Viewpoint").text = (
        f"viewpoint-{viewpoint_guid}.bcfv"
    )
    return _xml_bytes(root)


def _viewpoint_xml(result: dict, viewpoint_guid: str) -> bytes:
    root = ElementTree.Element("VisualizationInfo", {"Guid": viewpoint_guid})
    components = ElementTree.SubElement(root, "Components")
    selection = ElementTree.SubElement(components, "Selection")
    ElementTree.SubElement(
        selection,
        "Component",
        {"IfcGuid": result["element_guid"]},
    )
    visibility = ElementTree.SubElement(
        components,
        "Visibility",
        {"DefaultVisibility": "true"},
    )
    ElementTree.SubElement(
        visibility,
        "ViewSetupHints",
        {
            "SpacesVisible": "true",
            "SpaceBoundariesVisible": "false",
            "OpeningsVisible": "false",
        },
    )
    ElementTree.SubElement(visibility, "Exceptions")
    ElementTree.SubElement(components, "Coloring")
    camera = ElementTree.SubElement(root, "PerspectiveCamera")
    _add_point(camera, "CameraViewPoint", (18.0, -18.0, 12.0))
    _add_point(camera, "CameraDirection", (-0.64, 0.64, -0.42))
    _add_point(camera, "CameraUpVector", (0.0, 0.0, 1.0))
    ElementTree.SubElement(camera, "FieldOfView").text = "60.0"
    ElementTree.SubElement(camera, "AspectRatio").text = "1.7777777778"
    ElementTree.SubElement(root, "Lines")
    ElementTree.SubElement(root, "ClippingPlanes")
    ElementTree.SubElement(root, "Bitmaps")
    return _xml_bytes(root)


def _zip_write(
    archive: zipfile.ZipFile,
    name: str,
    data: str | bytes,
    timestamp: tuple[int, int, int, int, int, int],
) -> None:
    info = zipfile.ZipInfo(name, date_time=timestamp)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    archive.writestr(info, data)


def bcf_report(run: dict) -> bytes:
    output = io.BytesIO()
    started = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00"))
    timestamp = (
        max(1980, started.year),
        started.month,
        started.day,
        started.hour,
        started.minute,
        started.second,
    )
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _zip_write(
            archive,
            "bcf.version",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Version VersionId="3.0"/>',
            timestamp,
        )
        for result in run["results"]:
            if result["status"] not in EXPORTABLE_STATUSES:
                continue
            topic_guid = str(
                uuid.uuid5(
                    BCF_NAMESPACE,
                    f'{run["run_id"]}:{result["rule_id"]}:{result["element_guid"]}',
                )
            )
            viewpoint_guid = str(uuid.uuid5(BCF_NAMESPACE, f"{topic_guid}:viewpoint"))
            folder = f"{topic_guid}/"
            _zip_write(
                archive,
                f"{folder}markup.bcf",
                _markup_xml(run, result, topic_guid, viewpoint_guid),
                timestamp,
            )
            _zip_write(
                archive,
                f"{folder}viewpoint-{viewpoint_guid}.bcfv",
                _viewpoint_xml(result, viewpoint_guid),
                timestamp,
            )
    payload = output.getvalue()
    inspect_bcfzip(payload)
    return payload


def inspect_bcfzip(payload: bytes) -> dict:
    topics = []
    total_size = 0
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as error:
        raise UnsafeBcfArchive("BCF payload is not a valid ZIP archive.") from error
    with archive:
        infos = archive.infolist()
        if len(infos) > 1000:
            raise UnsafeBcfArchive("BCF archive contains too many files.")
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in info.filename
                or info.file_size > 5_000_000
            ):
                raise UnsafeBcfArchive(f"Unsafe BCF archive member: {info.filename}")
            total_size += info.file_size
            if total_size > 50_000_000:
                raise UnsafeBcfArchive("BCF archive is too large after decompression.")
            if info.filename.endswith("/markup.bcf"):
                root = SafeElementTree.fromstring(archive.read(info))
                topic = root.find("Topic")
                if topic is None:
                    raise UnsafeBcfArchive("BCF markup is missing a Topic.")
                topics.append(
                    {
                        "guid": topic.attrib.get("Guid"),
                        "title": topic.findtext("Title"),
                        "viewpoints": [
                            node.findtext("Viewpoint")
                            for node in topic.findall("./Viewpoints/ViewPoint")
                        ],
                    }
                )
        if "bcf.version" not in archive.namelist():
            raise UnsafeBcfArchive("BCF archive is missing bcf.version.")
        version = SafeElementTree.fromstring(archive.read("bcf.version"))
        if version.attrib.get("VersionId") != BCF_VERSION:
            raise UnsafeBcfArchive("Only BCF 3.0 archives are supported.")
        names = set(archive.namelist())
        for topic in topics:
            folder = f'{topic["guid"]}/'
            for viewpoint in topic["viewpoints"]:
                if (
                    not viewpoint
                    or PurePosixPath(viewpoint).name != viewpoint
                    or f"{folder}{viewpoint}" not in names
                ):
                    raise UnsafeBcfArchive("BCF viewpoint reference is missing or unsafe.")
    return {
        "version": BCF_VERSION,
        "topic_count": len(topics),
        "topics": topics,
        "uncompressed_size": total_size,
    }
