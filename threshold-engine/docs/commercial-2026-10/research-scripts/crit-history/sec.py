import time, urllib.request, os, threading
import os; UA = os.environ["SEC_USER_AGENT"]  # SEC requires a contact; never stored
_lock = threading.Lock(); _last = [0.0]
def get(u, timeout=300):
    with _lock:
        w = 0.15 - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()
    for attempt in range(4):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            return urllib.request.urlopen(r, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code == 404: raise
            time.sleep(2 + attempt * 3)
        except Exception:
            time.sleep(2 + attempt * 3)
    raise RuntimeError("failed " + u)
CIKS = {"JPM":19617,"WFC":72971,"BAC":70858,"C":831001,"USB":36104,"PNC":713676,"TFC":92230,"COF":927628,
"KEY":91576,"FITB":35527,"HBAN":49196,"FCNCA":798941,"CFG":759944,"MTB":36270,"RF":1281761,"ZION":109380}
