"""Full-text search over extracted filing sections (SQLite FTS5).

The FTS index is a derived structure: it is rebuilt from FilingSection rows,
never written directly. SQLite-only for now — on another backend, search
degrades to a plain LIKE scan (documented Phase 8 work)."""

from dataclasses import dataclass

from sqlalchemy import text as sql_text
from sqlmodel import Session

from stock_helper.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class SearchHit:
    chunk_id: str
    section_name: str
    filing_id: int
    snippet: str


def _is_sqlite(session: Session) -> bool:
    return session.get_bind().dialect.name == "sqlite"


def rebuild_fts(session: Session) -> int:
    """(Re)build the FTS index from FilingSection. Returns indexed row count."""
    if not _is_sqlite(session):
        log.info("FTS rebuild skipped: non-SQLite backend")
        return 0
    session.exec(sql_text(
        "CREATE VIRTUAL TABLE IF NOT EXISTS filingsection_fts "
        "USING fts5(chunk_id UNINDEXED, section_name UNINDEXED, "
        "filing_id UNINDEXED, text)"
    ))
    session.exec(sql_text("DELETE FROM filingsection_fts"))
    session.exec(sql_text(
        "INSERT INTO filingsection_fts (chunk_id, section_name, filing_id, text) "
        "SELECT chunk_id, section_name, filing_id, text FROM filingsection"
    ))
    count = session.exec(sql_text("SELECT count(*) FROM filingsection_fts")).one()[0]
    session.commit()
    log.info("FTS index rebuilt rows=%d", count)
    return count


def search_sections(session: Session, query: str, limit: int = 20) -> list[SearchHit]:
    """Rank-ordered FTS matches with highlighted snippets.

    Falls back to a LIKE scan on non-SQLite backends or if the index is
    missing (call rebuild_fts after ingesting documents)."""
    query = query.strip()
    if not query:
        return []
    if _is_sqlite(session):
        try:
            rows = session.exec(
                sql_text(
                    "SELECT chunk_id, section_name, filing_id, "
                    "snippet(filingsection_fts, 3, '**', '**', '…', 24) "
                    "FROM filingsection_fts WHERE filingsection_fts MATCH :q "
                    "ORDER BY rank LIMIT :n"
                ),
                params={"q": query, "n": limit},
            ).all()
            return [
                SearchHit(chunk_id=r[0], section_name=r[1], filing_id=int(r[2]), snippet=r[3])
                for r in rows
            ]
        except Exception as exc:  # missing index / bad FTS syntax → fallback
            log.debug("FTS query failed (%s); falling back to LIKE", exc)
    like = f"%{query}%"
    rows = session.exec(
        sql_text(
            "SELECT chunk_id, section_name, filing_id, substr(text, 1, 240) "
            "FROM filingsection WHERE text LIKE :q LIMIT :n"
        ),
        params={"q": like, "n": limit},
    ).all()
    return [
        SearchHit(chunk_id=r[0], section_name=r[1], filing_id=int(r[2]), snippet=r[3])
        for r in rows
    ]
