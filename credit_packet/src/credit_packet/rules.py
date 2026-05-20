from .models import WatchlistFlag

def evaluate_rules(periods, metrics, excerpts):
    flags=[]
    for p,m in zip(periods,metrics):
        period=str(p.fiscal_year)
        if m.revenue_growth is not None and m.revenue_growth <= -0.10: flags.append(WatchlistFlag(code='REVENUE_DECLINE', severity='medium', description='YoY revenue decline <= -10%', metric='revenue_growth', threshold='<= -10%', observed_value=f'{m.revenue_growth:.2%}', period=period, source='metrics'))
        if m.cash_change_pct is not None and m.cash_change_pct <= -0.25: flags.append(WatchlistFlag(code='CASH_DECLINE', severity='medium', description='Cash decline >=25% YoY', metric='cash_change_pct', threshold='<= -25%', observed_value=f'{m.cash_change_pct:.2%}', period=period, source='metrics'))
        if m.debt_change_pct is not None and m.debt_change_pct >= 0.20: flags.append(WatchlistFlag(code='DEBT_INCREASE', severity='medium', description='Debt increase >=20% YoY', metric='debt_change_pct', threshold='>= 20%', observed_value=f'{m.debt_change_pct:.2%}', period=period, source='metrics'))
        if p.operating_cash_flow is not None and p.operating_cash_flow < 0: flags.append(WatchlistFlag(code='NEGATIVE_OPERATING_CASH_FLOW', severity='high', description='Operating cash flow below zero', metric='operating_cash_flow', threshold='< 0', observed_value=str(p.operating_cash_flow), period=period, source='facts'))
        if m.current_ratio is not None and m.current_ratio < 1.0: flags.append(WatchlistFlag(code='CURRENT_RATIO_BELOW_ONE', severity='high', description='Current ratio below 1.0', metric='current_ratio', threshold='< 1.0', observed_value=f'{m.current_ratio:.2f}', period=period, source='metrics'))
        if m.free_cash_flow is not None and m.free_cash_flow < 0: flags.append(WatchlistFlag(code='NEGATIVE_FREE_CASH_FLOW', severity='high', description='Free cash flow below zero', metric='free_cash_flow', threshold='< 0', observed_value=str(m.free_cash_flow), period=period, source='metrics'))
        if p.stockholders_equity is not None and p.stockholders_equity < 0: flags.append(WatchlistFlag(code='EQUITY_DEFICIT', severity='high', description='Stockholders equity below zero', metric='stockholders_equity', threshold='< 0', observed_value=str(p.stockholders_equity), period=period, source='facts'))
    for e in excerpts:
        if e.category=='material_weakness': flags.append(WatchlistFlag(code='MATERIAL_WEAKNESS_LANGUAGE', severity='high', description='Material weakness/internal control language', metric='excerpt_keyword', threshold='keyword match', observed_value=e.text[:80], period=e.filing_date, source=e.source_url))
        if e.category=='going_concern': flags.append(WatchlistFlag(code='GOING_CONCERN_LANGUAGE', severity='high', description='Going concern language', metric='excerpt_keyword', threshold='keyword match', observed_value=e.text[:80], period=e.filing_date, source=e.source_url))
        if e.category in {'covenant','default_or_waiver'}: flags.append(WatchlistFlag(code='COVENANT_OR_WAIVER_LANGUAGE', severity='medium', description='Covenant/default/waiver language', metric='excerpt_keyword', threshold='keyword match', observed_value=e.text[:80], period=e.filing_date, source=e.source_url))
    return flags
