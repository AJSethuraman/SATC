"""No network call and no model anywhere in the application: checked by reading its imports, not by trusting it."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "workpaper_studio"
FORBIDDEN = {"urllib.request", "http.client", "requests", "httpx", "aiohttp", "socket", "smtplib", "ftplib",
             "anthropic", "openai", "transformers", "llama_cpp", "ollama", "google.generativeai", "cohere", "mistralai"}
SERVER_ONLY = {"wsgiref.simple_server", "socketserver"}   # listening on the local machine, never calling out


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_no_outbound_network_or_model_imports():
    bad = []
    for p in SRC.rglob("*.py"):
        for m in imports(p):
            top = {m, m.split(".")[0]}
            if top & FORBIDDEN:
                bad.append(f"{p.name}: {m}")
            if m in SERVER_ONLY and p.name != "web.py":
                bad.append(f"{p.name}: {m} (server code outside web.py)")
    assert not bad, bad


def test_the_guard_can_fail(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("import urllib.request\nfrom anthropic import Anthropic\n")
    found = [m for m in imports(p) if {m, m.split('.')[0]} & FORBIDDEN]
    assert found == ["urllib.request", "anthropic"]
