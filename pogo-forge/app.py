"""
pogo-forge — a local Pokemon GO roster and planning tool.

Reads nothing from your Pokemon GO account. Everything here is data you enter.
Run:  python app.py
Then open http://<forge-tailscale-name>:8737 from your phone.
"""

import os
import sqlite3
import contextlib
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

import costs

ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("POGO_FORGE_DB", ROOT / "pogo-forge.db"))
SLOTS = ("attack", "guard", "spirit")

app = FastAPI(title="pogo-forge", docs_url="/api/docs")


# --------------------------------------------------------------- database --
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextlib.contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")
    with db() as conn:
        conn.executescript(schema)


# ----------------------------------------------------------------- models --
class Body(BaseModel):
    """Request bodies reject fields they do not recognise.

    Pydantic's default is to ignore an unknown key, which turns a client-side
    typo into a confident wrong answer rather than an error. Posting
    {"ivs": [9,12,15], "level": 20} to /api/cost — plausible names, neither of
    them the real one — was answered with a plan for a perfect 15/15/15 at
    level 1: every field defaulted, nothing said so, and the itemised dust
    figure looked exactly as trustworthy as a correct one.

    This is the same rule the rest of the codebase follows. The reader refuses
    rather than guessing when it cannot read a bar; a request that names a
    field we do not have is the same situation.
    """

    model_config = ConfigDict(extra="forbid")


class PokemonIn(Body):
    species: str
    nickname: str | None = None
    role: str = "attacker"
    max_form: str = "dynamax"
    fast_type: str | None = None
    cp: int | None = None
    iv_atk: int | None = Field(default=None, ge=0, le=15)
    iv_def: int | None = Field(default=None, ge=0, le=15)
    iv_hp: int | None = Field(default=None, ge=0, le=15)
    priority: int = Field(default=3, ge=1, le=5)
    notes: str | None = None


class MoveLevelIn(Body):
    slot: str
    level: int = Field(ge=0, le=3)


class ParticleIn(Body):
    delta: int
    reason: str
    pokemon_id: int | None = None
    slot: str | None = None


class CostIn(Body):
    species: str
    slot: str
    to_level: int = Field(ge=1, le=3)
    particles: int = Field(ge=0)
    candy: int = 0
    candy_xl: int = 0


class FilterIn(Body):
    name: str
    query: str
    note: str | None = None
    destructive: bool = False


# ------------------------------------------------------------------ roster --
def _hydrate(conn, row) -> dict:
    p = dict(row)
    moves = conn.execute(
        "SELECT slot, level FROM max_move WHERE pokemon_id = ?", (p["id"],)
    ).fetchall()
    p["moves"] = {s: 0 for s in SLOTS} | {m["slot"]: m["level"] for m in moves}
    ivs = (p["iv_atk"], p["iv_def"], p["iv_hp"])
    p["iv_pct"] = round(sum(ivs) / 45 * 100, 1) if None not in ivs else None
    return p


@app.get("/api/roster")
def list_roster(include_archived: bool = False):
    with db() as conn:
        sql = "SELECT * FROM pokemon"
        if not include_archived:
            sql += " WHERE archived = 0"
        sql += " ORDER BY priority ASC, species ASC"
        return [_hydrate(conn, r) for r in conn.execute(sql).fetchall()]


@app.post("/api/roster", status_code=201)
def add_pokemon(body: PokemonIn):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO pokemon
               (species, nickname, role, max_form, fast_type, cp,
                iv_atk, iv_def, iv_hp, priority, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (body.species.strip(), body.nickname, body.role, body.max_form,
             body.fast_type, body.cp, body.iv_atk, body.iv_def, body.iv_hp,
             body.priority, body.notes),
        )
        pid = cur.lastrowid
        # Every Dynamax Pokemon starts with Max Attack at level 1.
        start = 1 if body.max_form in ("dynamax", "gigantamax") else 0
        for slot in SLOTS:
            conn.execute(
                "INSERT INTO max_move (pokemon_id, slot, level) VALUES (?,?,?)",
                (pid, slot, start if slot == "attack" else 0),
            )
        row = conn.execute("SELECT * FROM pokemon WHERE id = ?", (pid,)).fetchone()
        return _hydrate(conn, row)


@app.patch("/api/roster/{pid}")
def update_pokemon(pid: int, body: PokemonIn):
    with db() as conn:
        cur = conn.execute(
            """UPDATE pokemon SET species=?, nickname=?, role=?, max_form=?,
               fast_type=?, cp=?, iv_atk=?, iv_def=?, iv_hp=?, priority=?, notes=?
               WHERE id=?""",
            (body.species.strip(), body.nickname, body.role, body.max_form,
             body.fast_type, body.cp, body.iv_atk, body.iv_def, body.iv_hp,
             body.priority, body.notes, pid),
        )
        if not cur.rowcount:
            raise HTTPException(404, "no such pokemon")
        row = conn.execute("SELECT * FROM pokemon WHERE id = ?", (pid,)).fetchone()
        return _hydrate(conn, row)


@app.put("/api/roster/{pid}/move")
def set_move_level(pid: int, body: MoveLevelIn):
    if body.slot not in SLOTS:
        raise HTTPException(422, "bad slot")
    with db() as conn:
        cur = conn.execute(
            "UPDATE max_move SET level = ? WHERE pokemon_id = ? AND slot = ?",
            (body.level, pid, body.slot),
        )
        if not cur.rowcount:
            raise HTTPException(404, "no such pokemon or slot")
        row = conn.execute("SELECT * FROM pokemon WHERE id = ?", (pid,)).fetchone()
        return _hydrate(conn, row)


@app.delete("/api/roster/{pid}", status_code=204)
def archive_pokemon(pid: int):
    with db() as conn:
        conn.execute("UPDATE pokemon SET archived = 1 WHERE id = ?", (pid,))


# --------------------------------------------------------------- particles --
def _balance(conn) -> int:
    return conn.execute(
        "SELECT COALESCE(SUM(delta), 0) AS b FROM particle_entry"
    ).fetchone()["b"]


@app.get("/api/particles")
def particles(limit: int = 25):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM particle_entry ORDER BY at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return {"balance": _balance(conn), "entries": [dict(r) for r in rows]}


@app.post("/api/particles", status_code=201)
def log_particles(body: ParticleIn):
    with db() as conn:
        conn.execute(
            "INSERT INTO particle_entry (delta, reason, pokemon_id, slot) VALUES (?,?,?,?)",
            (body.delta, body.reason.strip(), body.pokemon_id, body.slot),
        )
        return {"balance": _balance(conn)}


# ------------------------------------------------------------------- costs --
@app.get("/api/costs")
def list_costs():
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM move_cost ORDER BY species, slot, to_level"
        ).fetchall()]


@app.post("/api/costs", status_code=201)
def upsert_cost(body: CostIn):
    with db() as conn:
        conn.execute(
            """INSERT INTO move_cost (species, slot, to_level, particles, candy, candy_xl)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(species, slot, to_level) DO UPDATE SET
                 particles = excluded.particles,
                 candy     = excluded.candy,
                 candy_xl  = excluded.candy_xl""",
            (body.species.strip().lower(), body.slot, body.to_level,
             body.particles, body.candy, body.candy_xl),
        )
        return {"ok": True}


# -------------------------------------------------------------------- plan --
@app.get("/api/plan")
def plan():
    """Rank the next Max Move step for every active Pokemon.

    Cost comes only from what you have entered in move_cost. A step with no
    recorded cost is reported as unknown rather than estimated.
    """
    with db() as conn:
        balance = _balance(conn)
        costs = {
            (r["species"], r["slot"], r["to_level"]): dict(r)
            for r in conn.execute("SELECT * FROM move_cost").fetchall()
        }
        steps = []
        for row in conn.execute(
            "SELECT * FROM pokemon WHERE archived = 0 AND max_form != 'none' "
            "ORDER BY id"   # explicit: SQLite row order is otherwise unspecified
        ).fetchall():
            p = _hydrate(conn, row)
            for slot in SLOTS:
                lvl = p["moves"][slot]
                if lvl >= 3:
                    continue
                target = lvl + 1
                c = costs.get((p["species"].lower(), slot, target))
                steps.append({
                    "pokemon_id": p["id"],
                    "species": p["species"],
                    "nickname": p["nickname"],
                    "priority": p["priority"],
                    "role": p["role"],
                    "slot": slot,
                    "from_level": lvl,
                    "to_level": target,
                    "action": "unlock" if lvl == 0 else "upgrade",
                    "particles": c["particles"] if c else None,
                    "candy": c["candy"] if c else None,
                    "candy_xl": c["candy_xl"] if c else None,
                    "affordable": (c is not None and c["particles"] <= balance),
                })

        # Role decides which slot matters: attackers want Attack, the tank
        # wants Guard, the healer wants Spirit. Everything else ranks below.
        wanted = {"attacker": "attack", "defender": "guard", "healer": "spirit"}
        def rank(s):
            on_role = 0 if wanted.get(s["role"]) == s["slot"] else 1
            return (s["priority"], on_role, s["particles"] is None,
                    s["particles"] or 10**6)

        steps.sort(key=rank)
        return {"balance": balance, "steps": steps}


# ----------------------------------------------------------------- filters --
@app.get("/api/filters")
def list_filters():
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM saved_filter ORDER BY destructive DESC, name"
        ).fetchall()]


@app.post("/api/filters", status_code=201)
def save_filter(body: FilterIn):
    with db() as conn:
        conn.execute(
            """INSERT INTO saved_filter (name, query, note, destructive)
               VALUES (?,?,?,?)
               ON CONFLICT(name) DO UPDATE SET
                 query = excluded.query,
                 note = excluded.note,
                 destructive = excluded.destructive""",
            (body.name.strip(), body.query.strip(), body.note,
             1 if body.destructive else 0),
        )
        return {"ok": True}


@app.post("/api/filters/{fid}/ran")
def mark_run(fid: int):
    with db() as conn:
        conn.execute(
            "UPDATE saved_filter SET last_run = datetime('now') WHERE id = ?", (fid,)
        )
        return {"ok": True}


@app.delete("/api/filters/{fid}", status_code=204)
def delete_filter(fid: int):
    with db() as conn:
        conn.execute("DELETE FROM saved_filter WHERE id = ?", (fid,))


# -------------------------------------------------------------------- cost --
class CostQuery(Body):
    species: str
    iv_atk: int = Field(default=15, ge=0, le=15)
    iv_def: int = Field(default=15, ge=0, le=15)
    iv_hp: int = Field(default=15, ge=0, le=15)
    from_level: float = 1.0
    goal: str = "max"                      # level | cp_cap | max
    target_level: float | None = None
    cp_cap: int | None = None
    evolve_to: str | None = None
    second_move: bool = False
    shadow: bool = False
    purified: bool = False


@app.post("/api/cost")
def cost(q: CostQuery):
    try:
        return costs.plan(
            q.species,
            ivs=(q.iv_atk, q.iv_def, q.iv_hp),
            from_level=q.from_level,
            goal=q.goal,
            target_level=q.target_level,
            cp_cap=q.cp_cap,
            evolve_to=q.evolve_to or None,
            second_move=q.second_move,
            shadow=q.shadow,
            purified=q.purified,
        )
    except costs.Unknown as e:
        # A thing we can't determine is a 200 with an explanation, not a crash.
        return {"error": str(e)}


@app.get("/api/species")
def species(q: str = "", limit: int = 8):
    """Type-ahead over the species we hold base stats for."""
    needle = costs.norm(q)
    if not needle:
        return []
    names = sorted(costs.SPECIES)
    hits = [n for n in names if n.startswith(needle)]
    hits += [n for n in names if needle in n and n not in hits]
    return [{"id": n, "name": n.replace("_", " ").title(),
             "evolves_to": [b["to"].replace("_", " ").title()
                            for b in costs.SPECIES[n].get("evolves_to") or []]}
            for n in hits[:limit]]


# --------------------------------------------------------------- appraise --
@app.post("/api/appraise")
async def appraise(image: UploadFile = File(...), species: str = Form(...),
                   cp: int | None = Form(None), hp: int | None = Form(None)):
    """Read exact IVs off an appraisal screenshot and prove them against CP/HP."""
    import io
    from PIL import Image
    import appraisal as A

    raw = await image.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(413, "image too large")
    try:
        img = Image.open(io.BytesIO(raw))
    except Exception:
        raise HTTPException(422, "could not open that file as an image")

    try:
        return A.appraise(img, species, cp=cp, hp=hp)
    except A.ReadFailed as e:
        return {"error": str(e)}
    except costs.Unknown as e:
        return {"error": str(e)}


# ----------------------------------------------------------------- triage --
@app.post("/api/triage")
async def triage_batch(files: list[UploadFile] = File(...),
                       species: str = Form(""), cap: int = Form(1500)):
    """Batch verdicts from screenshots or one screen recording.

    Send several images, or a single video of you swiping through the Appraise
    screen. `species` is an optional comma-separated list, in the same order;
    entries left blank get a shape-based verdict instead of an exact PvP rank.
    """
    import io
    import tempfile
    from pathlib import Path
    from PIL import Image
    import triage as T

    names = [s.strip() for s in species.split(",")] if species.strip() else []
    images: list[Image.Image] = []

    for f in files:
        raw = await f.read()
        if len(raw) > 200 * 1024 * 1024:
            raise HTTPException(413, "file too large")
        kind = (f.content_type or "").lower()
        if kind.startswith("video/") or (f.filename or "").lower().endswith(
                (".mp4", ".mov", ".m4v", ".webm")):
            with tempfile.NamedTemporaryFile(suffix=Path(f.filename or "v.mp4").suffix,
                                             delete=False) as tmp:
                tmp.write(raw)
                path = Path(tmp.name)
            try:
                images.extend(T.frames_from_video(path))
            except ValueError as e:
                return {"error": str(e)}
            finally:
                path.unlink(missing_ok=True)
        else:
            try:
                images.append(Image.open(io.BytesIO(raw)).convert("RGB"))
            except Exception:
                return {"error": f"could not open {f.filename!r} as an image"}

    if not images:
        return {"error": "nothing readable was uploaded"}
    return T.triage(images, species=names, cap=cap)


# ------------------------------------------------------------------ static --
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8737)))
