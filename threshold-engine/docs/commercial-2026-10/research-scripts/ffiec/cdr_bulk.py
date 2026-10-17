import re, sys, html, requests
OUT = sys.argv[1]
URL = "https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def fields(t):
    f = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*>', t):
        n = re.search(r'name="([^"]+)"', m.group(0)); v = re.search(r'value="([^"]*)"', m.group(0))
        if n: f[n.group(1)] = html.unescape(v.group(1) if v else "")
    return f
def opts(t, name):
    m = re.search(r'<select[^>]*name="%s"[^>]*>(.*?)</select>' % re.escape(name), t, re.S)
    if not m: return []
    return re.findall(r'<option([^>]*)value="([^"]*)"[^>]*>([^<]*)', m.group(1))
r = s.get(URL); t = r.text
print("GET", r.status_code)
f = fields(t)
f.update({"__EVENTTARGET": "ctl00$MainContentHolder$ListBox1", "ctl00$MainContentHolder$ListBox1": "ReportingSeriesSinglePeriod"})
r = s.post(URL, data=f); t = r.text
print("POST listbox", r.status_code)
d = opts(t, "ctl00$MainContentHolder$DatesDropDownList")
print("dates", len(d), [x[2] for x in d[:6]], "...", [x[2] for x in d[-3:]])
want = [x for x in d if x[2].strip() in ("06/30/2026",)]
print("want", want)
if not want: sys.exit(2)
f = fields(t)
f.update({"__EVENTTARGET": "ctl00$MainContentHolder$TSVRadioButton", "ctl00$MainContentHolder$ListBox1": "ReportingSeriesSinglePeriod",
          "ctl00$MainContentHolder$DatesDropDownList": want[0][1], "ctl00$MainContentHolder$FormatType": "TSVRadioButton"})
r = s.post(URL, data=f); t = r.text
print("POST radio", r.status_code)
f = fields(t)
f.update({"ctl00$MainContentHolder$ListBox1": "ReportingSeriesSinglePeriod",
          "ctl00$MainContentHolder$DatesDropDownList": want[0][1], "ctl00$MainContentHolder$FormatType": "TSVRadioButton",
          "ctl00$MainContentHolder$TabStrip1$Download_0": "Download"})
r = s.post(URL, data=f, stream=True)
print("POST download", r.status_code, r.headers.get("Content-Type"), r.headers.get("Content-Disposition"))
with open(OUT, "wb") as fh:
    for c in r.iter_content(1 << 20): fh.write(c)
