import time, json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .config import Settings
from .storage import CacheStore

class SECClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = CacheStore()

    def get_json(self, url: str, retries: int = 3):
        cached=self.cache.get(url)
        if cached is not None:
            return cached
        err=None
        for i in range(retries):
            try:
                time.sleep(self.settings.rate_limit_seconds)
                req=Request(url, headers={'User-Agent':self.settings.sec_user_agent,'Accept':'application/json'})
                with urlopen(req, timeout=self.settings.request_timeout) as resp:
                    data=json.loads(resp.read().decode('utf-8'))
                self.cache.set(url,data)
                return data
            except HTTPError as e:
                if e.code==404: raise ValueError(f'Not found: {url}')
                err=e
            except (URLError, TimeoutError, json.JSONDecodeError) as e:
                err=e
            time.sleep(0.5*(2**i))
        raise RuntimeError(f'SEC request failed: {url} ({err})')
