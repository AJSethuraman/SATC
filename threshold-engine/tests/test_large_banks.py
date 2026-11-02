"""peers.large_banks: the Philadelphia Fed's credit card balances file, read as
filed and written as a series with its fingerprint in the notes."""
import hashlib

import pytest

from threshold_engine.cli import main
from threshold_engine.peers import large_banks as LB
from threshold_engine.workbook import read_notes, read_series

HEAD = ("YRQTR,Total Balances ($Billions),Share of Accounts Making the Minimum Payment,"
        "Utilization (Active Accounts Only) (50th percentile)\n")
BODY = ("2024Q3,$1000.00,11.01 %,9.4 %\n2024Q4,$1050.50,null,9.1 %\n2025Q1,$1100.00,10.15 %,8.9 %\n"
        "Source: Federal Reserve Bank of Philadelphia,,,\nEmail: Phil.LargeBankData@phil.frb.org,,,\n")


def test_file_name_and_url_follow_the_philadelphia_feds_pattern():
    assert LB.file_name("2026Q2") == "26Q2-CreditCardBalances.csv"
    assert LB.url("2026Q2") == ("https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/Y14/2026/Q2/"
                                "26Q2-CreditCardBalances.csv")
    with pytest.raises(ValueError):
        LB.file_name("2026-Q2")


def test_read_takes_every_column_as_filed_and_a_null_as_no_value(tmp_path):
    f = tmp_path / "26Q2-CreditCardBalances.csv"
    f.write_text("﻿" + HEAD + BODY, encoding="utf-8")
    cols = LB.read(f)
    assert cols["Share of Accounts Making the Minimum Payment"] == {"2024Q3": 11.01, "2024Q4": None, "2025Q1": 10.15}
    assert cols["Total Balances ($Billions)"]["2024Q4"] == 1050.5
    assert LB.series(f, "Share paying only the minimum") == [("2024Q3", 11.01), ("2024Q4", None), ("2025Q1", 10.15)]
    with pytest.raises(ValueError):
        LB.series(f, "Utilization")
    bad = tmp_path / "bad.csv"
    bad.write_text("Quarter,x\n2024Q3,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YRQTR"):
        LB.read(bad)


def test_write_puts_the_files_fingerprint_and_the_gap_in_the_notes(tmp_path):
    f = tmp_path / "26Q2-CreditCardBalances.csv"
    f.write_text(HEAD + BODY, encoding="utf-8")
    out = tmp_path / "series"
    made = LB.write(f, out, say=lambda s: None)
    assert made == [(("Credit card", "Share paying only the minimum", "Large banks (Philadelphia Fed)"),
                     out / "credit-card_large-banks_share-paying-only-the-minimum_quarter-end.csv")]
    pts = read_series(made[0][1])
    assert [(p.date, p.value) for p in pts] == [("2024-09-30", 11.01), ("2025-03-31", 10.15)]
    notes = read_notes(made[0][1])
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    texts = [t for _, t in notes]
    assert any(sha in n and "26Q2-CreditCardBalances.csv" in n for n in texts)
    assert any("No value in the file for 2024Q4" in n for n in texts)
    assert any(n.startswith("Share paying only the minimum: of the active consumer credit card accounts") for n in texts)


def test_pull_fetches_once_and_refuses_a_file_without_the_column(tmp_path, capsys):
    calls = []

    def fetch(u):
        calls.append(u)
        return (HEAD + BODY).encode("utf-8")
    p = LB.pull(tmp_path, "2026Q2", fetch=fetch)
    assert p == tmp_path / "large-banks" / "26Q2-CreditCardBalances.csv" and p.read_text(encoding="utf-8") == HEAD + BODY
    LB.pull(tmp_path, "2026Q2", fetch=fetch)
    assert len(calls) == 1
    LB.pull(tmp_path, "2026Q2", fetch=fetch, refresh=True)
    assert len(calls) == 2
    with pytest.raises(ValueError, match="does not carry"):
        LB.pull(tmp_path, "2026Q3", fetch=lambda u: b"YRQTR,Other\n2024Q3,1\n")
    assert not (tmp_path / "large-banks" / "26Q3-CreditCardBalances.csv").exists()


def test_the_cli_names_the_command_and_refuses_a_bad_quarter(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(LB, "_get", lambda u: (HEAD + BODY).encode("utf-8"))
    assert main(["peers", "large-banks-pull", "--cache", str(tmp_path), "--quarter", "2026Q2"]) == 0
    assert (tmp_path / "large-banks" / "26Q2-CreditCardBalances.csv").exists()
    assert main(["peers", "large-banks-pull", "--cache", str(tmp_path), "--quarter", "2026-2"]) == 2
    assert "REFUSED" in capsys.readouterr().err
