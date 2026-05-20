from .models import FinancialPeriod, CalculatedMetric

def _div(a,b):
    if a is None or b in (None,0): return None
    return a/b

def _pct_change(cur, prev):
    if cur is None or prev in (None,0): return None
    return (cur-prev)/abs(prev)

def calculate_metrics(periods: list[FinancialPeriod]) -> list[CalculatedMetric]:
    out=[]
    for i,p in enumerate(periods):
        prev = periods[i-1] if i>0 else None
        fcf = None if p.operating_cash_flow is None or p.capex is None else p.operating_cash_flow - p.capex
        out.append(CalculatedMetric(
            fiscal_year=p.fiscal_year,
            revenue_growth=_pct_change(p.revenue, prev.revenue) if prev else None,
            gross_margin=_div(p.gross_profit, p.revenue),
            operating_margin=_div(p.operating_income, p.revenue),
            net_margin=_div(p.net_income, p.revenue),
            current_ratio=_div(p.current_assets, p.current_liabilities),
            debt_to_equity=_div(p.long_term_debt, p.stockholders_equity),
            operating_cash_flow_margin=_div(p.operating_cash_flow, p.revenue),
            free_cash_flow=fcf,
            free_cash_flow_margin=_div(fcf, p.revenue),
            cash_change_pct=_pct_change(p.cash_and_equivalents, prev.cash_and_equivalents) if prev else None,
            debt_change_pct=_pct_change(p.long_term_debt, prev.long_term_debt) if prev else None,
        ))
    return out
