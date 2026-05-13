from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

PLACEHOLDER_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
SUPPORTED_DOCS = {".docx"}
SUPPORTED_EMAILS = {".txt", ".html", ".md"}

def is_optional_placeholder(name: str) -> bool:
    return name.strip().lower().startswith("optional:")

def display_field_name(name: str) -> str:
    stripped = name.strip()
    if is_optional_placeholder(stripped):
        return stripped.split(":", 1)[1].strip()
    return stripped

def normalize_field_name(name: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", display_field_name(name).strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned

def detect_placeholders_from_text(text: str) -> list[str]:
    found = []
    seen = set()
    for match in PLACEHOLDER_RE.findall(text or ""):
        label = match.strip()
        key = normalize_field_name(label)
        if key not in seen:
            seen.add(key)
            found.append(label)
    return found

def extract_docx_text(path: str | Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
    return "\n".join(texts)

def read_template_text(path: str | Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".docx":
        return extract_docx_text(path)
    return path.read_text(encoding="utf-8")

def scan_template(path: str | Path) -> dict:
    path = Path(path)
    text = read_template_text(path)
    return {
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "template_type": "email" if path.suffix.lower() in SUPPORTED_EMAILS else "document",
        "placeholders": detect_placeholders_from_text(text),
        "text": text,
    }

def list_templates(template_folder: str | Path, category: str) -> list[Path]:
    folder = Path(template_folder) / category
    exts = SUPPORTED_DOCS if category == "Documents" else SUPPORTED_EMAILS
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts])
