from datetime import datetime, timezone
from .llm import guardrail_check

def _fmt(v,pct=False):
    if v is None: return 'Unavailable'
    return f"{v:.2%}" if pct else f"{v:,.2f}" if isinstance(v,(int,float)) else str(v)

def render_markdown(packet):
    lines=[f"# Credit Research Packet: {packet.company.name} ({packet.company.ticker})",f"Generated: {datetime.now(timezone.utc).isoformat()}",f"CIK: {packet.company.cik}","","## Important Limitation","This packet is decision support only. It does not assign a credit rating, recommend approval or decline, or provide investment advice. Manual review is required.","","## Latest Filing Activity","| Form | Filing Date | Report Date | Accession | Source |","|---|---|---|---|---|"]
    for f in packet.filings: lines.append(f"| {f.form} | {_fmt(f.filing_date)} | {_fmt(f.report_date)} | {f.accession_number} | {f.filing_url or f.source} |")
    lines += ["","## Annual Financial Trends","| FY | Revenue | Gross Profit | Operating Income | Net Income | Cash | Assets | Liabilities | Equity | Current Assets | Current Liabilities | LT Debt | OCF | Capex |","|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in packet.financial_periods: lines.append(f"| {p.fiscal_year} | {_fmt(p.revenue)} | {_fmt(p.gross_profit)} | {_fmt(p.operating_income)} | {_fmt(p.net_income)} | {_fmt(p.cash_and_equivalents)} | {_fmt(p.total_assets)} | {_fmt(p.total_liabilities)} | {_fmt(p.stockholders_equity)} | {_fmt(p.current_assets)} | {_fmt(p.current_liabilities)} | {_fmt(p.long_term_debt)} | {_fmt(p.operating_cash_flow)} | {_fmt(p.capex)} |")
    lines += ["","## Calculated Metrics","| FY | Revenue Growth | Gross Margin | Operating Margin | Net Margin | Cash Change | Current Ratio | Debt Change | Debt/Equity | OCF Margin | Free Cash Flow | FCF Margin |","|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in packet.calculated_metrics: lines.append(f"| {m.fiscal_year} | {_fmt(m.revenue_growth,True)} | {_fmt(m.gross_margin,True)} | {_fmt(m.operating_margin,True)} | {_fmt(m.net_margin,True)} | {_fmt(m.cash_change_pct,True)} | {_fmt(m.current_ratio)} | {_fmt(m.debt_change_pct,True)} | {_fmt(m.debt_to_equity)} | {_fmt(m.operating_cash_flow_margin,True)} | {_fmt(m.free_cash_flow)} | {_fmt(m.free_cash_flow_margin,True)} |")
    lines += ["","## Rule-Based Watchlist Flags","| Severity | Flag | Period/Filing | Observed | Threshold | Source |","|---|---|---|---|---|---|"]
    if packet.watchlist_flags:
        for f in packet.watchlist_flags: lines.append(f"| {f.severity} | {f.code} | {f.period} | {f.observed_value} | {f.threshold} | {f.source} |")
    else: lines.append("No rule-based watchlist flags triggered based on available data.")
    lines += ["","## Debt, Liquidity, and Risk Excerpts"]
    by={}
    for e in packet.excerpts: by.setdefault(e.category,[]).append(e)
    for c,arr in by.items():
        lines.append(f"### {c}")
        for e in arr[:6]: lines.append(f"- **{e.filing} {e.filing_date} | {e.section} | {', '.join(e.matched_keywords)}**: {e.text} ([source]({e.source_url}))")
    lines += ["","## Filing Language Changes"]
    for c in packet.filing_changes[:20]: lines.append(f"- {c.change_type} language for manual review ({c.category}, similarity={c.similarity_score:.2f})\n  - old: {c.old_excerpt[:240]}\n  - new: {c.new_excerpt[:240]}\n  - sources: {c.source_old} | {c.source_new}")
    lines += ["","## Questions for Human Review"] + [f"- {q}" for q in packet.review_questions]
    lines += ["","## Memo Shell","- Company overview: based on SEC identity and filings.","- Recent filing activity: see filing table above.","- Financial trend summary: use annual trends and calculated metrics above.","- Watchlist flags: list deterministic rule outputs only.","- Notable filing language: use excerpt and change sections above.","- Open questions: see human-review questions.","- Manual credit conclusion: Manual review required. No automated credit conclusion generated.","","## Source and Audit Trail"] + [f"- {a}" for a in packet.audit_log]
    md='\n'.join(lines)+'\n'
    guardrail_check(md)
    return md
