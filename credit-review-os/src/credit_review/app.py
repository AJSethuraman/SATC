"""Review Room — the local working surface (``credit-review ui``).

Localhost-only Flask app in the ``satc_system`` mold: loopback bind, a
Host-header guard against DNS rebinding, single operator, nothing leaves the
machine. The reviewer works one file at a time; entries persist in the
encrypted engagement store; the Excel workbook — the source of truth — is
generated on demand through the existing deterministic builder.
"""

from __future__ import annotations

from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template_string,
    request,
    url_for,
)

from credit_review import crypto
from credit_review.config import ConfigError
from credit_review.evaluate import evaluate_file
from credit_review.store import EngagementStore
from credit_review.workbook import build_engagement_workbook, workbook_bytes

_ALLOWED_HOSTS = ("127.0.0.1", "localhost", "[::1]")

_BASE = """<!doctype html><html><head><meta charset="utf-8">
<title>Review Room · {{ store.engagement.engagement_id }}</title>
<style>
 :root{--ink:#0A0908;--red:#CC0000;--paper:#FFF;--canvas:#F4F1EC;--mist:#E4DFD5;
  --slate:#57534B;--crimson:#960019;--green:#1E7A47}
 body{margin:0;background:var(--paper);color:#16130F;
  font:15px/1.5 -apple-system,"Segoe UI",Arial,sans-serif}
 header{background:var(--ink);border-bottom:3px solid var(--red);padding:14px 22px}
 header a{color:#FFF;text-decoration:none;font-weight:800;font-size:17px}
 header span{color:#B9B4AC;margin-left:12px;font-size:13px}
 main{max-width:880px;margin:0 auto;padding:20px 22px 80px}
 h2{font:700 14px/1 Arial;letter-spacing:.04em;background:var(--ink);color:#FFF;
  padding:8px 12px;margin:28px 0 12px}
 table{border-collapse:collapse;width:100%;font-size:14px}
 th{text-align:left;background:var(--ink);color:#FFF;font-size:12px;padding:6px 10px}
 td{padding:6px 10px;border-bottom:1px solid var(--mist)}
 .num{text-align:right;font-variant-numeric:tabular-nums}
 a{color:var(--crimson)}
 .btn{display:inline-block;background:var(--ink);color:#FFF;border:none;
  border-bottom:3px solid var(--red);padding:9px 16px;font:600 13px Arial;
  cursor:pointer;text-decoration:none}
 .field{margin:10px 0}
 .field label{display:block;font:700 11px Arial;letter-spacing:.06em;
  text-transform:uppercase;color:var(--slate);margin-bottom:3px}
 .field input,.field select{font:15px inherit;padding:7px 9px;
  background:var(--canvas);border:1px solid var(--mist);width:230px}
 .tests{margin-top:6px}
 .test{display:flex;align-items:center;gap:10px;padding:7px 9px;
  border-bottom:1px solid var(--mist)}
 .test .name{flex:1}
 .test .verdict{font-weight:700;width:60px;text-align:center}
 .verdict.fail{color:var(--crimson);background:#F7DEDE}
 .verdict.pass{color:var(--green)}
 .badge{font:700 11px Arial;letter-spacing:.05em;padding:3px 8px;
  background:#F7DEDE;color:var(--crimson)}
 .err{background:#F7DEDE;color:var(--crimson);padding:9px 12px;margin:12px 0}
 .ok{background:#E4EFE7;color:var(--green);padding:9px 12px;margin:12px 0}
 .kbd{font:12px Consolas,monospace;background:var(--canvas);padding:1px 5px}
</style></head><body>
<header><a href="{{ url_for('board') }}">Review Room</a>
<span>{{ store.engagement.client_name }} · {{ store.engagement.engagement_id }}</span>
</header><main>{{ body }}</main></body></html>"""

_BOARD = """
{% if message %}<div class="ok">{{ message }}</div>{% endif %}
{% for pid, p in progress.items() %}
<h2>{{ pid }}</h2>
<table><tr><th>Segment</th><th>Method / stratum</th>
<th class="num">Planned</th><th class="num">Done</th><th></th></tr>
{% for seg in p.segments %}
<tr><td>{{ seg.id }}</td>
<td>{{ seg.method }}{% if seg.stratum %} — {% for k,v in seg.stratum.items() %}{{ k }}: {{ v }}{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}</td>
<td class="num">{{ seg.size }}</td><td class="num">{{ seg.done }}</td>
<td><a href="{{ url_for('file_card', product_id=pid) }}?segment={{ seg.id }}">add file</a></td></tr>
{% endfor %}</table>
<p>{% for f in files[pid] %}<a href="{{ url_for('file_card', product_id=pid) }}?loan={{ f.loan_number }}">{{ f.loan_number }}</a>{% if not loop.last %} · {% endif %}{% endfor %}</p>
{% endfor %}
<h2>Build workbook</h2>
<form method="post" action="{{ url_for('build') }}">
 <div class="field"><label>Write to</label>
  <input name="path" value="{{ default_out }}"></div>
 <div class="field"><label><input type="checkbox" name="plain" value="1"
  style="width:auto"> plain xlsx (synthetic work only)</label></div>
 <button class="btn">Build</button></form>
"""

_CARD = """
{% if error %}<div class="err">{{ error }}</div>{% endif %}
<h2>{{ product.label }} — file</h2>
<form method="post" id="card">
 <div class="field"><label>Loan number</label>
  <input name="loan_number" value="{{ entry.loan_number or '' }}" required autofocus></div>
 <div class="field"><label>Segment</label>
  <select name="segment">{% for s in segments %}
   <option value="{{ s.id }}" {% if entry.segment==s.id %}selected{% endif %}>{{ s.id }} — {{ s.method }}</option>
  {% endfor %}</select></div>
 {% for a in product.attributes %}
 <div class="field"><label>{{ a.label }}</label>
  <input name="attr_{{ a.id }}" value="{{ entry.get(a.id, '') }}"
   inputmode="decimal" data-attr="{{ a.id }}" required></div>
 {% endfor %}
 <h2>Checklist <span style="float:right;font-weight:400">keys: <span class="kbd">p</span>
 <span class="kbd">f</span> <span class="kbd">n</span>, <span class="kbd">Enter</span> next</span></h2>
 <div class="tests">
 {% for t in product.tests %}
  <div class="test"><span class="name">{{ t.label }}</span>
  {% if t.kind == 'attestation' %}
   <select name="test_{{ t.id }}" class="att">
    <option value=""></option>
    {% for v in ['pass','fail','na'] %}
    <option value="{{ v }}" {% if entry.get(t.id)==v %}selected{% endif %}>{{ v }}</option>
    {% endfor %}</select>
  {% else %}
   <span class="verdict" data-test="{{ t.id }}">·</span>
  {% endif %}</div>
 {% endfor %}
 </div>
 <span class="badge" id="fringe" style="display:none">FRINGE</span>
 <div class="field"><label>Note</label>
  <input name="note" value="{{ entry.get('note','') }}" style="width:100%"></div>
 <p><button class="btn">Save file</button>
 <a href="{{ url_for('board') }}">back</a></p>
</form>
<script>
const attrs=document.querySelectorAll('[data-attr]');
async function preview(){
  const a={};let ready=true;
  attrs.forEach(el=>{if(el.value==='')ready=false;a[el.dataset.attr]=el.value;});
  if(!ready)return;
  const r=await fetch('{{ url_for("preview", product_id=product.id) }}',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({attributes:a})});
  if(!r.ok)return;
  const d=await r.json();
  document.querySelectorAll('[data-test]').forEach(el=>{
    const v=d.tests[el.dataset.test]||'·';
    el.textContent=v;el.className='verdict '+v;});
  document.getElementById('fringe').style.display=d.fringe?'inline-block':'none';
}
attrs.forEach(el=>el.addEventListener('input',preview));
preview();
document.querySelectorAll('select.att').forEach(sel=>{
  sel.addEventListener('keydown',e=>{
    const m={p:'pass',f:'fail',n:'na'}[e.key];
    if(m){sel.value=m;e.preventDefault();
      const all=[...document.querySelectorAll('select.att')];
      const next=all[all.indexOf(sel)+1];
      if(next)next.focus();}
  });
});
</script>
"""


def create_app(store: EngagementStore) -> Flask:
    app = Flask(__name__)

    @app.before_request
    def _host_guard():
        host = (request.host or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "::1"):
            abort(403)

    def page(body_template: str, **ctx) -> str:
        body = render_template_string(body_template, store=store, **ctx)
        return render_template_string(_BASE, store=store, body=body, **ctx)

    @app.route("/")
    def board():
        return page(_BOARD, progress=store.progress(),
                    files={pid: store.files(pid)
                           for pid in (p["id"] for p in store.program.products)},
                    default_out=f"{store.engagement.engagement_id}.xlsx.enc",
                    message=request.args.get("m"))

    @app.route("/p/<product_id>/file", methods=["GET", "POST"])
    def file_card(product_id):
        product = store.product(product_id)
        segments = store.engagement.overlay_products[product_id]["sample_plan"]["segments"]
        error = None
        if request.method == "POST":
            entry = {"loan_number": request.form.get("loan_number", "").strip(),
                     "segment": request.form.get("segment", "")}
            for a in product["attributes"]:
                raw = request.form.get(f"attr_{a['id']}", "").strip()
                try:
                    entry[a["id"]] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    entry[a["id"]] = raw   # loader rejects with a clear error
            for t in product["tests"]:
                if t["kind"] == "attestation":
                    value = request.form.get(f"test_{t['id']}", "")
                    if value:
                        entry[t["id"]] = value
            note = request.form.get("note", "").strip()
            if note:
                entry["note"] = note
            try:
                store.upsert_file(product_id, entry)
                return redirect(url_for("file_card", product_id=product_id,
                                        segment=entry["segment"]))
            except ConfigError as exc:
                error = str(exc)
                current = entry
        else:
            loan = request.args.get("loan")
            current = (store.get_file(product_id, loan) if loan else None) or \
                {"loan_number": "", "segment": request.args.get("segment", "")}
        return page(_CARD, product=product, segments=segments,
                    entry=current, error=error)

    @app.route("/p/<product_id>/preview", methods=["POST"])
    def preview(product_id):
        product = store.product(product_id)
        payload = request.get_json(force=True, silent=True) or {}
        attributes = payload.get("attributes", {})
        try:
            attributes = {k: float(v) for k, v in attributes.items()}
            result = evaluate_file(product, attributes, {},
                                   store.engagement.thresholds)
        except (ConfigError, ValueError, KeyError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"tests": {k: v for k, v in result["tests"].items() if v},
                        "fringe": result["fringe"]})

    @app.route("/build", methods=["POST"])
    def build():
        try:
            samples = store.to_samples()
        except ConfigError as exc:
            return page(_BOARD, progress=store.progress(),
                        files={pid: store.files(pid)
                               for pid in (p["id"] for p in store.program.products)},
                        default_out=f"{store.engagement.engagement_id}.xlsx.enc",
                        message=f"Not ready: {exc}"), 409
        wb = build_engagement_workbook(store.program, store.engagement, samples)
        data = workbook_bytes(wb)
        out = Path(request.form.get("path") or
                   f"{store.engagement.engagement_id}.xlsx.enc")
        if request.form.get("plain"):
            out.write_bytes(data)
        else:
            key = crypto.load_or_create_key(store.key_dir)
            out.write_bytes(crypto.encrypt_bytes(data, key))
        return redirect(url_for("board", m=f"Built {out}"))

    return app
