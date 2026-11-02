"""The local web front door: a standard-library WSGI app, so nothing has to be installed to run it.

Every request names who is signed in through a signed cookie; the service decides what that person may do.
Routes that change something are POSTs; a refusal comes back as a message on the page, never as a silent no-op.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import secrets
import tempfile
import threading
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote

from . import outputs, ui
from .engine import EntryError
from .service import Refused, Studio

LOCK = threading.RLock()


class App:
    def __init__(self, studio: Studio, secret: bytes):
        self.st, self.secret = studio, secret

    # session -------------------------------------------------------
    def sign(self, user):
        mac = hmac.new(self.secret, user.encode(), hashlib.sha256).hexdigest()[:24]
        return quote(f"{user}|{mac}")

    def who(self, environ):
        c = SimpleCookie(environ.get("HTTP_COOKIE", ""))
        if "ws_user" not in c:
            return None
        raw = unquote(c["ws_user"].value)
        user, _, mac = raw.rpartition("|")
        good = hmac.new(self.secret, user.encode(), hashlib.sha256).hexdigest()[:24]
        return user if hmac.compare_digest(mac, good) and user in self.st.users else None

    # plumbing ------------------------------------------------------
    def __call__(self, environ, start):
        method, path = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "/")
        query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
        form = {}
        if method == "POST":
            n = int(environ.get("CONTENT_LENGTH") or 0)
            form = {k: v[0] for k, v in parse_qs(environ["wsgi.input"].read(n).decode("utf-8"), keep_blank_values=True).items()}
        user = self.who(environ)
        try:
            with LOCK:
                status, headers, body = self.route(method, path, query, form, user)
        except KeyError:
            status, headers, body = "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], b"Not found."
        start(status, headers)
        return [body]

    @staticmethod
    def html(text, status="200 OK", extra=()):
        return status, [("Content-Type", "text/html; charset=utf-8"), *extra], text.encode("utf-8")

    @staticmethod
    def redirect(to, extra=()):
        return "303 See Other", [("Location", to), *extra], b""

    @staticmethod
    def json(obj, status="200 OK"):
        return status, [("Content-Type", "application/json")], json.dumps(obj).encode()

    def flash_to(self, to, msg):
        sep = "&" if "?" in to else "?"
        return self.redirect(f"{to}{sep}msg={quote(msg)}")

    # routes --------------------------------------------------------
    def route(self, method, path, q, f, user):
        st = self.st
        if path == "/signin":
            if method == "POST":
                if f.get("user") not in st.users:
                    return self.html(ui.signin(st.users), "400 Bad Request")
                nxt = f.get("next") or "/"
                return self.redirect(nxt if nxt.startswith("/") else "/", [("Set-Cookie", f"ws_user={self.sign(f['user'])}; Path=/; HttpOnly; SameSite=Strict")])
            return self.html(ui.signin(st.users, q.get("next", "/")))
        if user is None:
            if path.startswith("/api/"):
                return self.json({"error": "Sign in first."}, "401 Unauthorized")
            return self.redirect("/signin?next=" + quote(path))
        msg = q.get("msg", "")
        if path == "/":
            cases = [st.case(cid) for cid in st.case_ids()]
            return self.html(ui.home(st, user, cases, msg))
        if path == "/settings":
            if method == "POST":
                try:
                    p = st.published()[f["tool"]]
                    pk = st.stored_pack(p["fingerprint"])
                    b = next(b for _, b in pk.calcs() if b["id"] == f["calc"])
                    raw = f.get("limit", "").replace("%", "").replace("$", "").replace(",", "").strip()
                    v = float(raw)
                    v = v / 100 if b["method"] in ("dti", "devrate") else v
                    st.confirm_limit(user, f["tool"], f["calc"], v)
                    return self.flash_to("/settings", "")
                except (Refused, ValueError) as e:
                    return self.html(ui.settings_page(st, user, str(e) if isinstance(e, Refused) else "Enter the limit as a number."), "400 Bad Request")
            return self.html(ui.settings_page(st, user, msg))
        if path == "/tools":
            return self.html(ui.tools_page(st, user, msg))
        if path.startswith("/tools/") and method == "GET":
            name = path.split("/", 2)[2]
            good, _ = st.pack_files()
            p = next(p for p in good if p.file == name) if any(p.file == name for p in good) else None
            if p is None:
                raise KeyError(name)
            return self.html(ui.pack_page(st, user, p))
        if path in ("/tools/propose", "/tools/approve") and method == "POST":
            try:
                if path.endswith("propose"):
                    st.propose(user, f["file"])
                else:
                    st.approve_pack(user, f["fp"])
                return self.redirect("/tools")
            except Refused as e:
                return self.html(ui.tools_page(st, user, str(e)), "403 Forbidden")
        if path == "/case/new" and method == "POST":
            try:
                cid = st.new_case(user, f["tool"])
                return self.redirect(f"/case/{cid}")
            except Refused as e:
                return self.html(ui.home(st, user, [st.case(x) for x in st.case_ids()], str(e)), "403 Forbidden")
        if path.startswith("/api/case/"):
            _, _, _, cid, act = path.split("/", 4)
            return self.api(user, cid, act, f)
        if path.startswith("/case/"):
            parts = path.split("/")
            cid = parts[2]
            c = st.case(cid)
            sub = parts[3] if len(parts) > 3 else ""
            if method == "POST":
                return self.case_action(user, c, sub, f)
            if sub == "":
                screen = q.get("screen", "Workpaper")
                text = ui.case_page(st, user, c, screen, msg)
                if q.get("print"):
                    text = text.replace("</body>", "<script>addEventListener('load',()=>print())</script></body>")
                return self.html(text)
            if sub == "check":
                return self.html(ui.check_page(st, user, c, msg))
            if sub == "history":
                return self.html(ui.history_page(st, user, c))
            if sub == "outputs":
                return self.html(ui.outputs_page(st, user, c))
            if sub == "draft":
                return self.draft(c, parts[4])
            if sub == "file":
                name = parts[4]
                if name not in {o["name"] for o in st.released_outputs(cid)}:
                    raise KeyError(name)
                data = (st.out_dir / cid / name).read_bytes()
                ct = mimetypes.guess_type(name)[0] or "application/octet-stream"
                return "200 OK", [("Content-Type", ct), ("Content-Disposition", f'attachment; filename="{name}"')], data
        raise KeyError(path)

    def draft(self, c, name):
        fd = outputs.feed(c)
        fd["draft"] = True
        if name == "feed.json":
            return "200 OK", [("Content-Type", "application/json"), ("Content-Disposition", f'attachment; filename="{c["id"]}-DRAFT.feed.json"')], json.dumps(fd, indent=1).encode()
        if name == "feed.csv":
            return "200 OK", [("Content-Type", "text/csv"), ("Content-Disposition", f'attachment; filename="{c["id"]}-DRAFT.feed.csv"')], outputs.feed_csv(fd).encode()
        if name == "workbook.xlsx":
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "draft.xlsx"
                outputs.workbook(c, p)
                data = p.read_bytes()
            return "200 OK", [("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                              ("Content-Disposition", f'attachment; filename="{c["id"]}-DRAFT.xlsx"')], data
        raise KeyError(name)

    def case_action(self, user, c, act, f):
        st, cid = self.st, c["id"]
        back = f"/case/{cid}/check" if act in ("approve", "release", "submit") else f"/case/{cid}"
        try:
            if act == "submit":
                st.submit(user, cid)
            elif act == "return":
                st.return_case(user, cid)
            elif act == "approve":
                st.approve(user, cid)
            elif act == "release":
                st.release(user, cid)
                back = f"/case/{cid}/outputs"
            elif act == "point":
                st.raise_point(user, cid, f.get("section", ""), f.get("text", ""))
            elif act == "reply":
                st.reply_point(user, cid, f.get("id", ""), f.get("text", ""))
            elif act == "clear":
                st.clear_point(user, cid, f.get("id", ""))
            elif act == "exception":
                st.record_exception(user, cid, f.get("calc", ""), f.get("reason", ""), f.get("note", ""))
            elif act == "ack":
                st.acknowledge(user, cid, f.get("id", ""))
            else:
                raise KeyError(act)
            return self.redirect(back if act not in ("point", "reply", "clear", "exception", "ack") else self._screen_for(c, act, f))
        except Refused as e:
            return self.flash_to(back if act in ("approve", "release", "submit") else self._screen_for(c, act, f), str(e))

    def _screen_for(self, c, act, f):
        if act == "exception" or act == "ack":
            for s, b in c["pack"].blocks():
                if b["kind"] == "calc":
                    return f'/case/{c["id"]}?screen={quote(s.get("screen", "Workpaper"))}'
        if act == "point":
            s = next((s for s in c["pack"].sections if s["id"] == f.get("section")), {})
            return f'/case/{c["id"]}?screen={quote(s.get("screen", "Workpaper"))}'
        if act in ("reply", "clear"):
            p = c["points"].get(f.get("id", ""))
            s = next((s for s in c["pack"].sections if p and s["id"] == p["section"]), {})
            return f'/case/{c["id"]}?screen={quote(s.get("screen", "Workpaper"))}'
        return f'/case/{c["id"]}'

    def api(self, user, cid, act, f):
        st = self.st
        c = st.case(cid)
        screen = "Workpaper"
        path = f.get("path", "")
        if path:
            sec = ui._section_of(c, path) if path.startswith(("f/", "g/")) else {}
            screen = sec.get("screen", "Workpaper")
        try:
            if act == "set":
                c = st.set(user, cid, path, f.get("value", ""))
            elif act == "mark":
                c = st.mark(user, cid, path, f.get("state") or None, f.get("reason", ""))
            else:
                raise KeyError(act)
            return self.json({"ok": True, "main": ui.case_main(st, user, c, screen)})
        except (Refused, EntryError) as e:
            status = "403 Forbidden" if isinstance(e, Refused) else "422 Unprocessable Entity"
            return self.json({"ok": False, "error": str(e), "main": ui.case_main(st, user, st.case(cid), screen, str(e))}, status)


def make_app(data_dir, packs_dir, users=None):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    sec = data_dir / "secret"
    if not sec.exists():
        sec.write_bytes(secrets.token_bytes(32))
    st = Studio(data_dir / "studio.db", packs_dir, users)
    return App(st, sec.read_bytes())


def serve(app, host="127.0.0.1", port=5077):
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    class Quiet(WSGIRequestHandler):
        def log_message(self, *a):
            pass

    class Threaded(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    srv = make_server(host, port, app, server_class=Threaded, handler_class=Quiet)
    print(f"Workpaper Studio on http://{host}:{port}  (Ctrl+C to stop)")
    srv.serve_forever()
