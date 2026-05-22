import json
from pathlib import Path
class Cell:
    def __init__(self,value=None,row=1,column=1): self.value=value; self.row=row; self.column=column; self.fill=None; self.font=None; self.alignment=None; self.border=None
class Dim:
    def __init__(self): self.width=None
class ColDims(dict):
    def __missing__(self,k):
        self[k]=Dim(); return self[k]
class Worksheet:
    def __init__(self,title): self.title=title; self.data=[]; self.column_dimensions=ColDims()
    def append(self,row): self.data.append([Cell(v,len(self.data)+1,i+1) for i,v in enumerate(row)])
    def __getitem__(self,key):
        if isinstance(key,str):
            col=ord(key[0].upper())-64; row=int(key[1:]);
            while len(self.data)<row: self.append([])
            while len(self.data[row-1])<col: self.data[row-1].append(Cell(None,row,len(self.data[row-1])+1))
            return self.data[row-1][col-1]
        if isinstance(key,int): return self.data[key-1]
        if isinstance(key,slice): return self.data[key]
    @property
    def columns(self):
        maxc=max((len(r) for r in self.data), default=0)
        return [[r[i] if i<len(r) else Cell(None, ri+1, i+1) for ri,r in enumerate(self.data)] for i in range(maxc)]
class Workbook:
    def __init__(self): self._sheets=[Worksheet('Sheet')]; self.active=self._sheets[0]
    def create_sheet(self,title):
        ws=Worksheet(title); self._sheets.append(ws); return ws
    @property
    def sheetnames(self): return [s.title for s in self._sheets]
    def __getitem__(self,name): return next(s for s in self._sheets if s.title==name)
    def save(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        Path(path).write_text(json.dumps({s.title:[[c.value for c in r] for r in s.data] for s in self._sheets}))
def load_workbook(path):
    data=json.loads(Path(path).read_text()); wb=Workbook(); wb._sheets=[]
    for title, rows in data.items():
        ws=Worksheet(title)
        for r in rows: ws.append(r)
        wb._sheets.append(ws)
    wb.active=wb._sheets[0]
    return wb
