"""Bulk universe fetch: many tickers, facts-only, resumable, failure-tolerant.

The SEC company_tickers.json file is ordered roughly by market capitalization,
so ``top=N`` approximates "the N largest U.S. filers" without needing market
data. This is a convenience ordering, not a guarantee — SEC does not promise
accuracy or scope for that file (see DATA_SOURCES.md).

Scale notes: at the client throttle (~6 req/s) each ticker costs two requests
(submissions + companyfacts), so 100 tickers ≈ 1 minute, 500 ≈ 4 minutes.
For a *full*-universe pipeline the right tools are the SEC Frames API
(cross-sections) and the bulk companyfacts.zip download — both roadmapped
(Phase 8); this command targets the hundreds-of-tickers research universe.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from stock_helper.connectors.sec import SecClient, TickerNotFoundError
from stock_helper.core.logging import get_logger
from stock_helper.ingestion.sec_ingest import fetch_and_store
from stock_helper.storage.models import Company, SecurityIdentifier

log = get_logger(__name__)


@dataclass
class UniverseFetchResult:
    fetched: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # fresh enough, not re-fetched
    failed: list[tuple[str, str]] = field(default_factory=list)  # (ticker, reason)

    @property
    def total(self) -> int:
        return len(self.fetched) + len(self.skipped) + len(self.failed)


def select_universe_tickers(
    client: SecClient,
    top: int | None = None,
    tickers: list[str] | None = None,
) -> list[str]:
    """Explicit tickers win; otherwise the first ``top`` entries of the SEC
    ticker map (approximately the largest filers)."""
    if tickers:
        return [t.strip().upper() for t in tickers if t.strip()]
    ticker_map = client.load_ticker_map()  # insertion order = file order ≈ mktcap
    universe = list(ticker_map)
    return universe[:top] if top else universe


def _is_fresh(session: Session, ticker: str, refresh_days: float) -> bool:
    identifier = session.exec(
        select(SecurityIdentifier).where(SecurityIdentifier.ticker == ticker)
    ).first()
    if identifier is None:
        return False
    company = session.get(Company, identifier.company_id)
    if company is None or company.retrieved_at is None:
        return False
    retrieved = company.retrieved_at
    if retrieved.tzinfo is None:  # SQLite drops tzinfo; stored values are UTC
        retrieved = retrieved.replace(tzinfo=UTC)
    return datetime.now(UTC) - retrieved < timedelta(days=refresh_days)


def fetch_universe(
    session: Session,
    client: SecClient,
    top: int | None = None,
    tickers: list[str] | None = None,
    refresh_days: float = 7.0,
    with_documents: bool = False,
    progress: Callable[[str, str, int, int], None] | None = None,
) -> UniverseFetchResult:
    """Fetch many tickers, committing per ticker so interruption loses nothing.

    - Resumable: tickers fetched within ``refresh_days`` are skipped.
    - Failure-tolerant: one bad ticker (delisted, missing facts, HTTP error)
      is recorded and the run continues.
    - ``progress(ticker, status, i, n)`` is called after each ticker for UIs.
    """
    universe = select_universe_tickers(client, top=top, tickers=tickers)
    result = UniverseFetchResult()
    n = len(universe)
    for i, ticker in enumerate(universe, start=1):
        status = "fetched"
        try:
            if _is_fresh(session, ticker, refresh_days):
                result.skipped.append(ticker)
                status = "skipped"
            else:
                fetch_and_store(ticker, session, client, with_documents=with_documents)
                result.fetched.append(ticker)
        except (
            TickerNotFoundError, httpx.HTTPError, ValueError, KeyError, SQLAlchemyError,
        ) as exc:
            # Roll back the failed ticker and keep going — one bad filer (DB
            # integrity error, malformed payload, network blip) must never abort
            # a hundreds-of-names run.
            session.rollback()
            reason = f"{exc.__class__.__name__}: {exc}"
            result.failed.append((ticker, reason))
            status = "failed"
            log.warning("universe fetch failed ticker=%s reason=%s", ticker, reason)
        if progress is not None:
            progress(ticker, status, i, n)
    log.info(
        "universe fetch done fetched=%d skipped=%d failed=%d",
        len(result.fetched), len(result.skipped), len(result.failed),
    )
    return result
