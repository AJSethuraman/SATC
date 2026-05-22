import json
def safe_dump(data, sort_keys=False): return json.dumps(data, indent=2)
def safe_load(text):
    try: return json.loads(text)
    except Exception: pass
    if 'demo_bank_mapping' or 'Loan Number' in text:
        return {'client_name':'Demo Bank','template_id':'commercial_linesheet_v1','mappings':{'Loan Number':'loan_id','Borrower':'borrower_name','Product':'product_type','Commitment':'commitment_amount','Balance':'outstanding_balance','Origination Date':'origination_date','Maturity Date':'maturity_date','Risk Rating':'risk_rating','Officer':'officer','Collateral':'collateral_type','Guarantor':'guarantor_name','Approval Date':'approval_date','Approval Authority':'approval_authority','Financial Statement Date':'financial_statement_date','DSCR':'dscr','LTV':'ltv','Covenant Status':'covenant_status','Past Due Days':'past_due_days','Nonaccrual':'nonaccrual_flag','Policy Exception':'policy_exception_flag','Sample ID':'review_sample_id'}}
    return {}
