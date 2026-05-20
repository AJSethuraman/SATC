from .models import FinancialPeriod

FIELD_TAGS={
'revenue':['Revenues','RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet'],
'gross_profit':['GrossProfit'],'operating_income':['OperatingIncomeLoss'],'net_income':['NetIncomeLoss','ProfitLoss'],
'cash_and_equivalents':['CashAndCashEquivalentsAtCarryingValue','CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'],
'total_assets':['Assets'],'total_liabilities':['Liabilities'],
'stockholders_equity':['StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
'current_assets':['AssetsCurrent'],'current_liabilities':['LiabilitiesCurrent'],
'long_term_debt':['LongTermDebtNoncurrent','LongTermDebtAndFinanceLeaseObligationsNoncurrent','LongTermDebt'],
'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities'],'capex':['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'],
'shares_outstanding':['EntityCommonStockSharesOutstanding','WeightedAverageNumberOfDilutedSharesOutstanding']}

def _select_fact(usgaap,tag):
    node=usgaap.get(tag,{})
    units=node.get('units',{})
    vals=units.get('USD') or units.get('shares') or []
    vals=[v for v in vals if v.get('fy') and v.get('fp')=='FY']
    vals.sort(key=lambda v:((v.get('form')=='10-K'),bool(v.get('frame','').startswith('CY')),v.get('filed','')),reverse=True)
    return vals

def normalize_periods(client,cik:str,years:int=3):
    url=f"{client.settings.sec_base_facts}/CIK{client.pad_cik(cik)}.json"
    data=client.get_json(url)
    us=data.get('facts',{}).get('us-gaap',{})
    per={}
    for field,tags in FIELD_TAGS.items():
        for tag in tags:
            vals=_select_fact(us,tag)
            for v in vals:
                fy=int(v['fy'])
                per.setdefault(fy,{'fiscal_year':fy,'period':'FY','tag_map':{}})
                if field not in per[fy]:
                    val=v.get('val')
                    if field=='capex' and val is not None:
                        val=abs(val)
                    per[fy][field]=val
                    per[fy]['tag_map'][field]=tag
            if any(field in d for d in per.values()):
                break
    yrs=sorted(per)[-years:]
    return [FinancialPeriod(**per[y]) for y in yrs],url
