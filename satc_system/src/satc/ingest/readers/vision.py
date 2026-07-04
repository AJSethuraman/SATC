"""Claude vision document reader.

Sends a document image to Claude with a structured-output schema derived from the
extraction config, and gets back each requested field's value (or null) plus the
fields the model was unsure about. The result is plain labeled fields that flow
through the normal MapExtractor + confirmation gate — Claude never writes directly
into a workpaper; the preparer still confirms.

Design notes:
  * The Anthropic SDK is imported lazily and the client is injectable, so this
    module imports cleanly without the SDK installed and is unit-testable with a
    fake client (no API key, no network).
  * Model defaults to ``claude-opus-4-8``.
  * PDFs are rasterized to an image first (first page by default) via ``pdftoppm``.
"""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from satc.ingest.readers.base import ReadResult

DEFAULT_MODEL = "claude-opus-4-8"

_PROMPT = (
    "You are a meticulous tax preparer's assistant extracting fields from a {doc_type}. "
    "Read the document in the image and return each requested field's value EXACTLY as "
    "printed. If a field is absent or illegible, return null — never guess a dollar amount "
    "or an identifier. Put the canonical field path as the key. List any fields you are not "
    "fully confident about (blurry, ambiguous, partially obscured) in 'uncertain_fields'."
)


def _media_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/png")


def _rasterize_pdf(pdf_path: Path, page: int) -> tuple[bytes, str]:
    """Rasterize one PDF page to PNG bytes via pdftoppm."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = str(Path(tmp) / "page")
        subprocess.run(["pdftoppm", "-png", "-r", "200", "-f", str(page), "-l", str(page),
                        str(pdf_path), prefix], check=True, capture_output=True)
        produced = sorted(Path(tmp).glob("page*.png"))
        if not produced:
            raise RuntimeError(f"Could not rasterize {pdf_path} page {page}")
        return produced[0].read_bytes(), "image/png"


class VisionDocumentReader:
    """Reads a document image/PDF into labeled fields using Claude vision."""

    def __init__(self, config: dict[str, Any], *, client: Any = None,
                 model: str = DEFAULT_MODEL, page: int = 1) -> None:
        self.doc_type = config.get("doc_type", "document")
        self.field_specs = config.get("fields", [])
        self.model = model
        self.page = page
        self._client = client  # injectable; lazily created if None

    # -- client -----------------------------------------------------------
    def _get_client(self) -> Any:
        if self._client is None:  # pragma: no cover - exercised only with a real key
            import anthropic  # imported lazily so the package works without the SDK
            self._client = anthropic.Anthropic()
        return self._client

    # -- schema / prompt --------------------------------------------------
    def _schema(self) -> dict[str, Any]:
        props: dict[str, Any] = {}
        for spec in self.field_specs:
            props[spec["field_path"]] = {
                "type": ["string", "null"],
                "description": spec.get("label", spec["field_path"]),
            }
        props["uncertain_fields"] = {"type": "array", "items": {"type": "string"}}
        return {
            "type": "object",
            "properties": props,
            "required": list(props.keys()),
            "additionalProperties": False,
        }

    def _path_to_label(self) -> dict[str, str]:
        return {spec["field_path"]: spec.get("label", spec["field_path"]) for spec in self.field_specs}

    # -- read -------------------------------------------------------------
    def _image_bytes(self, source: str) -> tuple[bytes, str]:
        path = Path(source)
        if path.suffix.lower() == ".pdf":
            return _rasterize_pdf(path, self.page)
        return path.read_bytes(), _media_type(path)

    def _call_model(self, image_b64: str, media_type: str) -> dict[str, Any]:
        client = self._get_client()
        resp = client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": _PROMPT.format(doc_type=self.doc_type)},
                ],
            }],
            output_config={"format": {"type": "json_schema", "schema": self._schema()}},
        )
        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
        return json.loads(text)

    @classmethod
    def classify_form(cls, source: str, labels: list[str], *, client: Any = None,
                      model: str = DEFAULT_MODEL, page: int = 1) -> str | None:  # pragma: no cover - needs a key
        """Name the form in ``source`` as one of ``labels`` (cheap classify-only call).

        Used as the last rung of the classification ladder when a document has no
        form fields and no text layer (a true scan). Returns the chosen label, or
        ``None`` if the model declines / errors.
        """
        reader = cls({"doc_type": "tax document", "fields": []},
                     client=client, model=model, page=page)
        image_bytes, media_type = reader._image_bytes(source)
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        schema = {
            "type": "object",
            "properties": {"doc_type": {"type": ["string", "null"], "enum": [*labels, None]}},
            "required": ["doc_type"],
            "additionalProperties": False,
        }
        prompt = ("Identify which tax document this image is. Choose exactly one of: "
                  f"{', '.join(labels)}. If none fit, return null. Do not guess wildly.")
        resp = reader._get_client().messages.create(
            model=model, max_tokens=200,
            messages=[{"role": "user", "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt}]}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
        return json.loads(text).get("doc_type")

    def read(self, source: str) -> ReadResult:
        image_bytes, media_type = self._image_bytes(source)
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        data = self._call_model(b64, media_type)

        path_to_label = self._path_to_label()
        uncertain_paths = set(data.get("uncertain_fields", []) or [])
        labeled: dict[str, str] = {}
        uncertain: set[str] = set()
        for field_path, label in path_to_label.items():
            value = data.get(field_path)
            if value is None or str(value).strip() == "":
                continue
            labeled[label] = str(value)
            if field_path in uncertain_paths:
                uncertain.add(label)
        return ReadResult(labeled_fields=labeled, uncertain_labels=uncertain,
                          backend=f"VisionDocumentReader[{self.model}]")
