from datetime import datetime, timezone

def _fmt(v):
    return 'Unavailable' if v is None else str(v)

def render_markdown(packet):
    lines=[f"# Credit Research Packet - {packet.company.ticker}", f"Generated: {datetime.now(timezone.utc).isoformat()}", "", f"CIK: {packet.company.cik}", f"Company: {packet.company.name}", "", "## Latest Filings", "|Form|Filing Date|Accession|URL|", "|---|---|---|---|"]
    for f in packet.filings: lines.append(f"|{f.form}|{_fmt(f.filing_date)}|{f.accession_number}|{_fmt(f.filing_url)}|")
    lines += ["", "## 3-Year Financial Trend Table", "|Year|Revenue|Net Income|OCF|LTDebt|", "|---|---|---|---|---|"]
    for p in packet.financial_periods: lines.append(f"|{p.fiscal_year}|{_fmt(p.revenue)}|{_fmt(p.net_income)}|{_fmt(p.operating_cash_flow)}|{_fmt(p.long_term_debt)}|")
    lines += ["", "## Watchlist Flags"]
    for flag in packet.watchlist_flags: lines.append(f"- [{flag.severity}] {flag.code}: {flag.description} (observed={flag.observed_value}; threshold={flag.threshold}; period={flag.period}; source={flag.source})")
    lines += ["", "## Debt and Liquidity Excerpts"] + [f"- ({e.category}) {e.text} [{e.source_url}]" for e in packet.excerpts]
    lines += ["", "## Filing Change Summary"] + [f"- {c.category}/{c.section}: {c.change_type} (similarity={c.similarity_score:.2f})" for c in packet.filing_changes]
    lines += ["", "## Questions for Human Review"] + [f"- {q}" for q in packet.review_questions]
    lines += ["", "## Memo Draft", packet.memo_draft, "", "Manual Credit Conclusion: Manual review required. No automated credit conclusion generated.", "", "## Source and Audit Trail"] + [f"- {a}" for a in packet.audit_log]
    return '\n'.join(lines)+'\n'
