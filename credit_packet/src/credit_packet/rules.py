from .models import WatchlistFlag

def evaluate_rules(periods,metrics,excerpts):
    flags=[]
    for p,m in zip(periods,metrics):
        per=str(p.fiscal_year)
        add=lambda code,sev,desc,metric,thr,obs,src: flags.append(WatchlistFlag(code=code,severity=sev,description=desc,metric=metric,threshold=thr,observed_value=str(obs),period=per,source=src))
        if m.revenue_growth is not None and m.revenue_growth<=-0.10: add('REVENUE_DECLINE','medium','Revenue decline >= 10% YoY','revenue_growth','<= -10%',f'{m.revenue_growth:.2%}','metrics')
        if m.cash_change_pct is not None and m.cash_change_pct<=-0.25: add('CASH_DECLINE','medium','Cash decline >= 25% YoY','cash_change_pct','<= -25%',f'{m.cash_change_pct:.2%}','metrics')
        if m.debt_change_pct is not None and m.debt_change_pct>=0.20: add('DEBT_INCREASE','medium','Debt increase >= 20% YoY','debt_change_pct','>= 20%',f'{m.debt_change_pct:.2%}','metrics')
        if p.operating_cash_flow is not None and p.operating_cash_flow<0: add('NEGATIVE_OPERATING_CASH_FLOW','high','Operating cash flow below zero','operating_cash_flow','< 0',p.operating_cash_flow,'facts')
        if m.free_cash_flow is not None and m.free_cash_flow<0: add('NEGATIVE_FREE_CASH_FLOW','high','Free cash flow below zero','free_cash_flow','< 0',m.free_cash_flow,'metrics')
        if m.current_ratio is not None and m.current_ratio<1.0: add('CURRENT_RATIO_BELOW_ONE','high','Current ratio below 1.0','current_ratio','< 1.0',round(m.current_ratio,2),'metrics')
        if p.stockholders_equity is not None and p.stockholders_equity<0: add('EQUITY_DEFICIT','high','Stockholders equity below zero','stockholders_equity','< 0',p.stockholders_equity,'facts')
    for e in excerpts:
        if e.category=='material_weakness': flags.append(WatchlistFlag(code='MATERIAL_WEAKNESS_LANGUAGE',severity='high',description='Material weakness language detected',metric='excerpt',threshold='keyword match',observed_value=','.join(e.matched_keywords),period=e.filing_date,source=e.source_url))
        if e.category=='going_concern': flags.append(WatchlistFlag(code='GOING_CONCERN_LANGUAGE',severity='high',description='Going concern language detected',metric='excerpt',threshold='keyword match',observed_value=','.join(e.matched_keywords),period=e.filing_date,source=e.source_url))
        if e.category in {'covenant','default_or_waiver'}: flags.append(WatchlistFlag(code='COVENANT_OR_WAIVER_LANGUAGE',severity='medium',description='Covenant/default/waiver language detected',metric='excerpt',threshold='keyword match',observed_value=','.join(e.matched_keywords),period=e.filing_date,source=e.source_url))
    return flags
