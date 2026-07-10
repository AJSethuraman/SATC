import json, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .config import Settings
from .storage import CacheStore

RETRY_CODES={429,500,502,503,504}

class SECClient:
    def __init__(self, settings: Settings):
        if not settings.sec_user_agent.strip():
            raise ValueError('SEC_USER_AGENT is required. Set SEC_USER_AGENT="Your Name your.email@example.com" in environment.')
        self.settings=settings
        self.cache=CacheStore()
        self._last=0.0

    @staticmethod
    def normalize_accession(accession_number:str)->str:
        return accession_number.replace('-','').strip()

    @staticmethod
    def pad_cik(cik:str)->str:
        return str(cik).strip().zfill(10)

    @staticmethod
    def unpad_cik(cik:str)->str:
        return str(int(str(cik).strip()))

    def _rate_limit(self):
        min_interval=max(0.1,self.settings.rate_limit_seconds)
        delta=time.time()-self._last
        if delta<min_interval:
            time.sleep(min_interval-delta)
        self._last=time.time()

    def _fetch_bytes(self,url:str,accept:str='application/json',retries:int=4)->bytes:
        cached=self.cache.get_bytes(url)
        if cached is not None:
            return cached
        err=None
        for i in range(retries+1):
            try:
                self._rate_limit()
                req=Request(url,headers={'User-Agent':self.settings.sec_user_agent,'Accept':accept})
                with urlopen(req,timeout=self.settings.request_timeout) as r:
                    body=r.read()
                self.cache.set_bytes(url,body,'json' if 'json' in accept else 'txt')
                return body
            except HTTPError as e:
                err=e
                if e.code not in RETRY_CODES or i==retries:
                    raise RuntimeError(f'SEC HTTP error {e.code} for {url}')
            except (URLError, TimeoutError) as e:
                err=e
                if i==retries:
                    raise RuntimeError(f'SEC request failed for {url}: {e}')
            time.sleep(0.4*(2**i))
        raise RuntimeError(f'SEC request failed for {url}: {err}')

    def get_json(self,url:str):
        return json.loads(self._fetch_bytes(url,'application/json').decode('utf-8'))

    def get_text(self,url:str):
        return self._fetch_bytes(url,'text/html, text/plain').decode('utf-8',errors='ignore')

    def download_filing_document(self,cik:str,accession_number:str,primary_document:str)->tuple[str,str]:
        cik_u=self.unpad_cik(cik)
        acc=self.normalize_accession(accession_number)
        url=f'https://www.sec.gov/Archives/edgar/data/{cik_u}/{acc}/{primary_document}'
        return url, self.get_text(url)
