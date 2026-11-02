import openpyxl,sys,json
wb=openpyxl.load_workbook(sys.argv[1],read_only=True)
out={}
for ws in wb.worksheets:
    rows=list(ws.iter_rows(values_only=True))
    print(ws.title,len(rows),rows[:3])
    out[ws.title]=[[str(c) if c is not None else '' for c in r] for r in rows]
json.dump(out,open(sys.argv[2],'w'))
