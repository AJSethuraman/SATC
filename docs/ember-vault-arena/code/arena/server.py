from __future__ import annotations

import json
import mimetypes
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .demo import PROJECT_ROOT, load_manifests
from .engine import ArenaEngine
from .models import AgentManifest, ValidationError
from .providers import provider_from_name
from .storage import ArenaStore


WEB_ROOT = PROJECT_ROOT / "web"
MAX_REQUEST_BYTES = 64 * 1024


class ArenaHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: ArenaStore, *, stream_interval: float = 1.0):
        super().__init__(address, ArenaHandler)
        self.store = store
        self.stream_interval = stream_interval  # how often the round stream looks at the store


class ArenaHandler(BaseHTTPRequestHandler):
    server: ArenaHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[arena] {self.address_string()} {format % args}")

    def _json(self, value: Any, status: int = 200) -> None:
        encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("request body must be 1..65536 bytes")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                self._json({"ok": True, "service": "ember-vault-arena"})
                return
            if path == "/api/matches":
                self._json({"matches": self.server.store.list_matches()})
                return
            if path == "/api/agents":
                self._json({"agents": self.server.store.list_agents()})
                return
            if path == "/api/leaderboard":
                self._json({"leaderboard": self.server.store.leaderboard()})
                return
            if path.startswith("/api/matches/") and path.endswith("/replay"):
                match_id = path.split("/")[3]
                self._json(self.server.store.replay_bundle(match_id))
                return
            if path.startswith("/api/matches/") and path.endswith("/audit"):
                match_id = path.split("/")[3]
                self._json(self.server.store.verify_audit(match_id))
                return
            # ---- the live page (PRD §5.35–38): loopback by default, one round behind ----
            if path.startswith("/live/"):
                match_id = path.split("/")[2]
                self._html(self._live_page(match_id))
                return
            if path.startswith("/api/matches/") and path.endswith("/board"):
                match_id = path.split("/")[3]
                after = int((parse_qs(parsed.query).get("after") or ["0"])[0])
                self._json(self._board_data(match_id, after))
                return
            if path.startswith("/api/matches/") and path.endswith("/live"):
                match_id = path.split("/")[3]
                self._round_stream(match_id)
                return
            self._serve_static(path)
        except KeyError:
            self._error(HTTPStatus.NOT_FOUND, "resource not found")
        except Exception as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._body()
            if path == "/api/agents":
                manifest = AgentManifest.from_dict(body)
                self.server.store.register_agent(manifest)
                self._json(
                    {
                        "agent": manifest.public_dict(reveal_secret=True),
                        "saved": True,
                    },
                    HTTPStatus.CREATED,
                )
                return
            if path == "/api/demo":
                seed = int(body.get("seed", 20260724))
                provider_name = str(body.get("provider", "mock"))
                manifests = load_manifests()
                match_id = ArenaEngine(
                    self.server.store,
                    provider_from_name(provider_name),
                ).run(manifests, seed)
                self._json(
                    {
                        "match_id": match_id,
                        "replay_url": f"/api/matches/{match_id}/replay",
                    },
                    HTTPStatus.CREATED,
                )
                return
            if path == "/api/matches":
                agent_ids = body.get("agent_ids")
                if not isinstance(agent_ids, list) or not 4 <= len(agent_ids) <= 8:
                    raise ValueError("agent_ids must contain four to eight IDs")
                seed = int(body.get("seed", 20260724))
                provider_name = str(body.get("provider", "mock"))
                manifests = self.server.store.get_manifests(
                    [str(agent_id) for agent_id in agent_ids]
                )
                match_id = ArenaEngine(
                    self.server.store,
                    provider_from_name(provider_name),
                ).run(manifests, seed)
                self._json(
                    {
                        "match_id": match_id,
                        "replay_url": f"/api/matches/{match_id}/replay",
                    },
                    HTTPStatus.CREATED,
                )
                return
            self._error(HTTPStatus.NOT_FOUND, "route not found")
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except KeyError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except Exception as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def _html(self, page: str, status: int = 200) -> None:
        encoded = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _board_data(self, match_id: str, after: int) -> dict[str, Any]:
        """The board's frames, cards and story for the completed rounds after
        ``after`` (PRD §5.36). Unredacted: this is the audience's page and it
        is served on the operator's own machine (PRD §5.24, §5.38)."""
        from tools import replay_board  # the page builder lives with the tools; imported when asked for
        bundle = self.server.store.replay_bundle(match_id, reveal=True)
        return replay_board.live_data(bundle, after)

    def _live_page(self, match_id: str) -> str:
        from tools import replay_board
        bundle = self.server.store.replay_bundle(match_id, reveal=True)
        live = {"match_id": match_id, "board": f"/api/matches/{match_id}/board", "sse": f"/api/matches/{match_id}/live", "poll_ms": 5000}
        return replay_board.build(bundle, live=live)

    def _round_stream(self, match_id: str) -> None:
        """Server-Sent Events (PRD §5.36): a ``round`` event each time a
        round's end snapshot lands, ``done`` when the match completes. The
        page pulls the board data on each; the stream carries no beat itself,
        so a slow call never reaches the screen before its round has ended."""
        store = self.server.store
        last = store.rounds_complete(match_id)
        status = store.match_status(match_id)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def send(event: str, data: dict[str, Any]) -> None:
            self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
            self.wfile.flush()

        try:
            send("round", {"rounds_complete": last, "status": status})
            waited = 0.0
            while status != "completed":
                time.sleep(self.server.stream_interval)
                waited += self.server.stream_interval
                now, status = store.rounds_complete(match_id), store.match_status(match_id)
                if now > last or status == "completed":
                    last = now
                    send("round", {"rounds_complete": last, "status": status})
                    waited = 0.0
                elif waited >= 15.0:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    waited = 0.0
            send("done", {"rounds_complete": last, "status": status})
        except (BrokenPipeError, ConnectionResetError):
            return

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
            self._error(HTTPStatus.FORBIDDEN, "invalid path")
            return
        if not candidate.is_file():
            candidate = WEB_ROOT / "index.html"
        data = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; img-src 'self' data:",
        )
        self.end_headers()
        self.wfile.write(data)


def serve(store: ArenaStore, host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ArenaHTTPServer((host, port), store)
    print(f"Ember Vault Arena: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping arena.")
    finally:
        server.server_close()
