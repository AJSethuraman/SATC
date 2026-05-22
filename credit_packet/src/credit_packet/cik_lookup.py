from .sec_client import SECClient

def ticker_to_identity(client: SECClient, ticker: str):
    data = client.get_json(client.settings.sec_ticker_url)
    t = ticker.upper()
    for _, row in data.items():
        if row.get('ticker', '').upper() == t:
            return t, str(row['cik_str']).zfill(10), row.get('title', t)
    raise ValueError(f'Ticker not found: {ticker}')
