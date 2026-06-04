from __future__ import annotations
from pathlib import Path
import yaml
from .models import Template
from .rules_engine import evaluate_rule

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "configs" / "templates"

def load_template_yaml(path: str | Path) -> Template:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("Template YAML must define a mapping at the top level")
    template = Template.model_validate(data)
    validate_template_structure(template)
    return template

def validate_template_structure(template: Template) -> None:
    seen=set()
    for section in template.sections:
        for q in section.questions:
            if q.question_id in seen: raise ValueError(f'Duplicate question_id: {q.question_id}')
            seen.add(q.question_id)
            if not q.export_label: raise ValueError(f'Missing export_label for {q.question_id}')
            if not q.data_mart_field: raise ValueError(f'Missing data_mart_field for {q.question_id}')

def discover_templates(directory: str | Path | None = None) -> dict:
    """Scan a directory for template YAMLs -> {template_id: {name, version, path}}."""
    directory = Path(directory or TEMPLATES_DIR)
    out = {}
    for p in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(p.read_text())
            tid = data.get("template_id") if isinstance(data, dict) else None
            if tid:
                out[tid] = {"name": data.get("template_name", tid), "version": str(data.get("version", "")), "path": str(p)}
        except Exception:
            continue
    return out

def template_path_for(template_id: str, directory: str | Path | None = None) -> str | None:
    reg = discover_templates(directory)
    return reg[template_id]["path"] if template_id in reg else None

def load_template(template_id: str, directory: str | Path | None = None) -> Template:
    path = template_path_for(template_id, directory)
    if not path:
        raise ValueError(f"Unknown template_id: {template_id}")
    return load_template_yaml(path)

def loan_to_source(loan_record) -> dict:
    return loan_record.model_dump() if hasattr(loan_record,'model_dump') else dict(loan_record)

def get_applicable_questions(loan_record, template: Template):
    source=loan_to_source(loan_record); out=[]
    for sec in sorted(template.sections, key=lambda s:s.display_order):
        for q in sorted(sec.questions, key=lambda x:x.display_order):
            if q.applies_if and not evaluate_rule(q.applies_if, source=source): continue
            out.append((sec,q))
    return out
