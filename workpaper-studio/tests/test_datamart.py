"""The data mart: every answer of every released case, with its state and source, and the master-table shape as a
view over it that cannot drift."""
import csv
import io
import json
import sqlite3

import pytest

from conftest import fill
from workpaper_studio import datamart, demo, sources


def release_credit(st, packs, d):
    demo.write(d)
    rep = st.load_work("M. Okafor", "Credit file review", sources.configured(d), d)
    cid = dict(rep["loaded"])["L-1001"]
    ex = json.loads(json.dumps(packs["credit-file-review"].data["example"]))
    for k in ("tester", "reviewer", "borrower", "security", "newmoney", "quarter", "scope", "facilities"):
        ex.pop(k, None)
    ex["qs1"]["6.01"] = {"r": "Effective"}
    ex["summary"] = "Synthetic summary."
    fill(st, cid, "A. Rivera", ex, packs["credit-file-review"])
    st.set("A. Rivera", cid, "g/facilities/1/out", "23750")           # a correction to the master's value
    st.record_exception("A. Rivera", cid, "calc_dti", "Compensating strength documented", "Liquidity (synthetic).")
    st.submit("A. Rivera", cid)
    st.acknowledge("D. Patel", cid, "E1")
    st.approve("D. Patel", cid)
    st.release("D. Patel", cid)
    return cid


def test_every_answer_is_in_the_mart_with_its_state_and_source(studio, packs, tmp_path):
    cid = release_credit(studio, packs, tmp_path)
    db = sqlite3.connect(studio.mart_path)
    n_q = len(packs["credit-file-review"].grid("qs1")["rows"]["items"])
    ratings = db.execute("SELECT question, state, value_text FROM answers WHERE case_id=? AND path LIKE 'g/qs1/%/r'", (cid,)).fetchall()
    assert len(ratings) == n_q                                      # every question, answered or not
    assert ("2.02", "entered", "Not effective") in ratings
    comments = dict(db.execute("SELECT question, state FROM answers WHERE case_id=? AND path LIKE 'g/qs1/%/c'", (cid,)).fetchall())
    assert comments["1.02"] == "blank" and comments["2.02"] == "entered"
    fac = db.execute("SELECT value_num, source, changed_from_master, master_value FROM answers WHERE case_id=? AND path='g/facilities/1/out'", (cid,)).fetchone()
    assert fac == (23750.0, "master", 1, "22500")
    assert db.execute("SELECT verdict FROM results WHERE case_id=?", (cid,)).fetchone()[0] == "Above limit"
    assert db.execute("SELECT reason, acknowledged_by FROM exceptions WHERE case_id=?", (cid,)).fetchone() == ("Compensating strength documented", "D. Patel")
    assert db.execute("SELECT COUNT(*) FROM actions WHERE case_id=?", (cid,)).fetchone()[0] == len(studio.events(cid))


def test_the_wide_view_is_the_master_table_shape_and_matches_the_released_row(studio, packs, tmp_path):
    cid = release_credit(studio, packs, tmp_path)
    db = sqlite3.connect(studio.mart_path)
    view = [v for v in datamart.views(db) if v.startswith("wide_credit_file_review")][0]
    names, rows = datamart.rows(db, f'SELECT * FROM "{view}" WHERE case_id=?', (cid,))
    row = dict(zip(names, rows[0]))
    assert row["line_id"] == "L-1001" and row["q2_02_r"] == "Not effective" and row["calc_dti_verdict"] == "Above limit"
    assert row["facilities_2_out"] == "23750" and row["borrower_name"].startswith("H")
    released = list(csv.reader(io.StringIO((studio.out_dir / cid / f"{cid}.answers-row.csv").read_text())))
    assert released[0] == names and released[1] == [("" if v is None else str(v)) for v in rows[0]]


def test_the_mart_is_de_identified_and_append_only(studio, packs, tmp_path):
    cid = release_credit(studio, packs, tmp_path)
    blob = (studio.mart_path).read_bytes()
    assert b"Harbor Millwork" not in blob
    db = sqlite3.connect(studio.mart_path)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("UPDATE answers SET value_text='x'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("DELETE FROM cases")


def test_root_cause_questions_answer_from_the_mart(studio, packs, tmp_path):
    release_credit(studio, packs, tmp_path)
    db = sqlite3.connect(studio.mart_path)
    worst = db.execute("""SELECT a.question, a.value_text, COUNT(*) FROM answers a WHERE a.path LIKE 'g/qs1/%/r'
                          AND a.value_text IN ('Not effective','Partially effective') GROUP BY a.question, a.value_text ORDER BY a.question""").fetchall()
    assert ("2.02", "Not effective", 1) in worst
    why = db.execute("""SELECT c.value_text FROM answers r JOIN answers c ON c.case_id=r.case_id AND c.question=r.question AND c.path LIKE '%/c'
                        WHERE r.value_text='Not effective' AND r.path LIKE '%/r'""").fetchall()
    assert why and "industry code" in why[0][0]
