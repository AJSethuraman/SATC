import re, sys, zlib
raw=open(sys.argv[1],'rb').read()
blobs=[raw]
for m in re.finditer(rb'stream\r?\n', raw):
    s=m.end(); e=raw.find(b'endstream', s)
    if e<0: continue
    try: blobs.append(zlib.decompress(raw[s:e]))
    except Exception: pass
seen=set()
for b in blobs:
    for t in re.findall(rb'[\x20-\x7e]{12,}', b):
        s=t.decode('ascii')
        if s not in seen:
            seen.add(s); print(s)
