"""Local vision reader via Ollama — runs entirely on localhost, no internet.

For scans/photos that local OCR can't read cleanly, a vision model running on the
practice's own machine (``ollama serve`` on ``localhost:11434``) reads the image.
The document never leaves the machine. The reader speaks Ollama's ``/api/chat`` API
over stdlib ``urllib`` (no extra dependency) and asks for JSON keyed by canonical
field path. As with every reader, output flows through the MapExtractor +
confirmation gate; the model never writes a workpaper value directly.

The HTTP transport is injectable, so this is unit-testable with a canned response
(no Ollama, no model, no network).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Callable

from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.vision import _rasterize_pdf


class OllamaVisionReader:
    """Reads a document image into labeled fields using a local Ollama vision model."""

    def __init__(self, config: dict[str, Any], *, host: str | None = None,
                 model: str | None = None, page: int = 1,
                 transport: Callable[[dict], dict] | None = None) -> None:
        from satc.settings import ollama_host, ollama_model

        self.doc_type = config.get("doc_type", "document")
        self.field_specs = config.get("fields", [])
        self.page = page
        self.host = host or ollama_host()
        self.model = model or ollama_model()
        self._transport = transport          # injectable: payload -> response dict

    def _image_b64(self, source: str) -> str:
        p = Path(source)
        data = _rasterize_pdf(p, self.page)[0] if p.suffix.lower() == ".pdf" else p.read_bytes()
        return base64.standard_b64encode(data).decode("utf-8")

    def _prompt(self) -> str:
        lines = "\n".join(f"- {s['field_path']}: {s.get('label', s['field_path'])}"
                          for s in self.field_specs)
        return (f"You are extracting fields from a {self.doc_type}. Return ONLY a JSON object "
                "whose keys are the field paths below and whose values are the EXACT printed "
                "text, or null if a field is absent or illegible. Never guess a dollar amount "
                f"or an identifier.\n{lines}")

    def _call(self, image_b64: str) -> dict:
        payload = {"model": self.model, "stream": False, "format": "json",
                   "messages": [{"role": "user", "content": self._prompt(), "images": [image_b64]}]}
        if self._transport is not None:
            return self._transport(payload)
        import urllib.request   # pragma: no cover - exercised only against a live Ollama

        req = urllib.request.Request(self.host.rstrip("/") + "/api/chat",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def read(self, source: str) -> ReadResult:
        data = self._call(self._image_b64(source))
        content = data.get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        labeled: dict[str, str] = {}
        for spec in self.field_specs:
            value = parsed.get(spec["field_path"])
            if value is None or str(value).strip() == "":
                continue
            labeled[spec.get("label", spec["field_path"])] = str(value)
        # A local model's reads are noisy too — flag everything for review.
        return ReadResult(labeled_fields=labeled, uncertain_labels=set(labeled),
                          backend=f"OllamaVisionReader[{self.model}]")
