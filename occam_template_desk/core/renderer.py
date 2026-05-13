from __future__ import annotations

import html
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from .template_scanner import PLACEHOLDER_RE, normalize_field_name


def render_text(text: str, values: dict[str, str]) -> str:
    norm = {normalize_field_name(k): v for k, v in values.items()}
    def repl(m):
        raw = m.group(1).strip()
        return str(values.get(raw, norm.get(normalize_field_name(raw), "")))
    return PLACEHOLDER_RE.sub(repl, text)

def parse_email_template(path: str | Path) -> tuple[str, str]:
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        return lines[0].split(":", 1)[1].strip(), "\n".join(lines[1:]).lstrip("\n")
    return "", text

def render_email_template(path: str | Path, values: dict[str, str], output_dir: str | Path, to_email: str = "", status: str = "Ready") -> dict:
    path = Path(path); output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    subject_t, body_t = parse_email_template(path)
    subject = render_text(subject_t, values)
    body = render_text(body_t, values)
    body_path = output_dir / f"generated_email{path.suffix.lower()}"
    body_path.write_text(body, encoding="utf-8")
    meta = {"to": to_email or values.get("Client Email", ""), "subject": subject, "body_path": str(body_path), "status": status, "format": path.suffix.lower().lstrip(".")}
    meta_path = output_dir / "email_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"subject": subject, "body": body, "body_path": str(body_path), "metadata_path": str(meta_path), "generated_files": [str(body_path), str(meta_path)]}

def _replace_docx_xml(xml_bytes: bytes, values: dict[str, str]) -> bytes:
    # Minimal formatter-preserving replacement for placeholders contained in a run.
    text = xml_bytes.decode("utf-8")
    return render_text(text, {k: html.escape(str(v)) for k, v in values.items()}).encode("utf-8")

def render_docx_template(path: str | Path, values: dict[str, str], output_dir: str | Path, output_name: str | None = None) -> dict:
    path = Path(path); output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / (output_name or f"{path.stem}_generated.docx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                data = _replace_docx_xml(data, values)
            zout.writestr(item, data)
    return {"document_path": str(out), "generated_files": [str(out)]}

def create_minimal_docx(path: str | Path, paragraphs: list[str]) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    p_xml = "".join(f"<w:p><w:r><w:t>{html.escape(p)}</w:t></w:r></w:p>" for p in paragraphs)
    document = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes'?><w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body>{p_xml}<w:sectPr/></w:body></w:document>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/><Default Extension='xml' ContentType='application/xml'/><Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/></Types>""")
        z.writestr("_rels/.rels", """<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='word/document.xml'/></Relationships>""")
        z.writestr("word/document.xml", document)
    return path
