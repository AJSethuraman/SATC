from .models import FinancialPeriod

def normalize_periods(client, cik: str, years: int = 3):
    url = f"{client.settings.sec_base_facts}/CIK{cik}.json"
    data = client.get_json(url)
    us = data.get('facts', {}).get('us-gaap', {})
    tags = {
        'revenue':'Revenues','gross_profit':'GrossProfit','operating_income':'OperatingIncomeLoss','net_income':'NetIncomeLoss',
        'cash_and_equivalents':'CashAndCashEquivalentsAtCarryingValue','total_assets':'Assets','total_liabilities':'Liabilities',
        'stockholders_equity':'StockholdersEquity','current_assets':'AssetsCurrent','current_liabilities':'LiabilitiesCurrent',
        'long_term_debt':'LongTermDebtNoncurrent','operating_cash_flow':'NetCashProvidedByUsedInOperatingActivities',
        'capex':'PaymentsToAcquirePropertyPlantAndEquipment','shares_outstanding':'EntityCommonStockSharesOutstanding'
    }
    years_map = {}
    for field, tag in tags.items():
        units = us.get(tag, {}).get('units', {})
        values = next(iter(units.values()), []) if units else []
        for v in values:
            fy = v.get('fy')
            if not fy: continue
            years_map.setdefault(fy, {'fiscal_year': fy, 'period': v.get('fp','FY')})
            years_map[fy][field] = v.get('val')
    rows = [FinancialPeriod(**years_map[y]) for y in sorted(years_map.keys())[-years:]]
    return rows, url
