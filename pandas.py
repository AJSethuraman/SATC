from __future__ import annotations
import csv, json, sqlite3
from datetime import datetime
from pathlib import Path

class Series(list):
    def value_counts(self):
        d={}
        for x in self: d[x]=d.get(x,0)+1
        return CountDict(d)
    def to_dict(self): return {i:v for i,v in enumerate(self)}
class CountDict(dict):
    def to_dict(self): return dict(self)
class Loc:
    def __init__(self,df): self.df=df
    def __getattr__(self,name):
        if name in self.columns: return self[name]
        raise AttributeError(name)
    def __getitem__(self,key):
        r,c=key; return self.df.rows[r].get(c)
class ILoc:
    def __init__(self,df): self.df=df
    def __getitem__(self,i): return Row(self.df.rows[i])
class Row(dict):
    def to_dict(self): return dict(self)
class DataFrame:
    def __init__(self, data=None, columns=None):
        if data is None: self.rows=[]
        elif isinstance(data, list) and data and isinstance(data[0], dict): self.rows=[dict(x) for x in data]
        elif isinstance(data, list): self.rows=[{columns[i]: row[i] for i in range(len(columns))} for row in data]
        elif isinstance(data, dict):
            keys=list(data.keys()); n=len(next(iter(data.values()),[])); self.rows=[{k:data[k][i] for k in keys} for i in range(n)]
        else: self.rows=[]
        self.columns=columns or (list(self.rows[0].keys()) if self.rows else [])
        self.loc=Loc(self); self.iloc=ILoc(self)
    @property
    def empty(self): return len(self.rows)==0
    def __len__(self): return len(self.rows)
    def __getattr__(self,name):
        if name in self.columns: return self[name]
        raise AttributeError(name)
    def __getitem__(self,key):
        if isinstance(key,str): return Series([r.get(key) for r in self.rows])
        if isinstance(key,list): return DataFrame([{k:r.get(k) for k in key} for r in self.rows])
        if isinstance(key, Series): return DataFrame([r for r,b in zip(self.rows,key) if b])
    def __setitem__(self,k,v):
        if not isinstance(v, list): v=[v]*len(self.rows)
        if not self.rows: self.rows=[{} for _ in range(len(v))]
        for r,val in zip(self.rows,v): r[k]=val
        if k not in self.columns: self.columns.append(k)
    def head(self,n=5): return DataFrame(self.rows[:n], self.columns)
    def iterrows(self):
        for i,r in enumerate(self.rows): yield i, Row(r)
    def apply(self, func, axis=1): return Series([func(Row(r)) for r in self.rows])
    def to_dict(self, orient=None): return [dict(r) for r in self.rows] if orient=='records' else {c:[r.get(c) for r in self.rows] for c in self.columns}
    def to_csv(self,path,index=False):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with open(path,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=self.columns or (list(self.rows[0].keys()) if self.rows else [])); w.writeheader(); w.writerows(self.rows)
    def to_excel(self,path,index=False): self.to_csv(path,index=index)
def read_csv(path):
    with open(path,newline='') as f: return DataFrame(list(csv.DictReader(f)))
def read_excel(path): return read_csv(path)
def isna(v): return v is None or v==''
def notnull(v): return not isna(v)
def to_datetime(v):
    class D:
        def __init__(self,d): self._d=d
        def date(self): return self._d.date()
    for fmt in ['%Y-%m-%d','%m/%d/%Y','%Y-%m-%d %H:%M:%S']:
        try: return D(datetime.strptime(str(v),fmt))
        except Exception: pass
    return D(datetime.fromisoformat(str(v)))
def read_sql_query(sql, conn, params=None):
    cur=conn.execute(sql, params or ())
    rows=[dict(r) if not isinstance(r,tuple) else {cur.description[i][0]:v for i,v in enumerate(r)} for r in cur.fetchall()]
    return DataFrame(rows)
