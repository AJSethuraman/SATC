from .models import FilingRecord

def get_recent_filings(client, cik: str):
    url = f"{client.settings.sec_base_submissions}/CIK{cik}.json"
    data = client.get_json(url)
    recent = data.get('filings', {}).get('recent', {})
    out = []
    forms = recent.get('form', [])
    for i, form in enumerate(forms):
        if form in {'10-K','10-Q','8-K'}:
            acc = recent['accessionNumber'][i].replace('-', '')
            primary = recent.get('primaryDocument', [''])[i]
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{primary}" if primary else None
            out.append(FilingRecord(
                accession_number=recent['accessionNumber'][i], form=form,
                filing_date=recent.get('filingDate',[None])[i], report_date=recent.get('reportDate',[None])[i],
                primary_document=primary, filing_url=filing_url, source=url
            ))
    return out[:12]
