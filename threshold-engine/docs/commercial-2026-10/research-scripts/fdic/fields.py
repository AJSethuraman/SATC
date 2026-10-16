CATS = [
 ("Construction & land dev (total)", "LNRECONS", ["DRRECONS","CRRECONS","NTRECONS"], ["DRRECONQ","CRRECONQ","NTRECONQ"], ["NTRECONQR","NTRECOQR","NTRECONSR","NTRECOSR"], "P3RECONS","P9RECONS","NARECONS"),
 ("Construction 1-4 family", "LNRECNFM", ["DRRECNFM","CRRECNFM","NTRECNFM"], [], [], "P3RECNFM","P9RECNFM","NARECNFM"),
 ("Construction other + land", "LNRECNOT", ["DRRECNOT","CRRECNOT","NTRECNOT"], [], [], "P3RECNOT","P9RECNOT","NARECNOT"),
 ("Multifamily", "LNREMULT", ["DRREMULT","CRREMULT","NTREMULT"], ["DRREMULQ","CRREMULQ","NTREMULQ"], ["NTREMULQR","NTREMUQR","NTREMULTR","NTREMULR"], "P3REMULT","P9REMULT","NAREMULT"),
 ("Nonfarm nonres (total)", "LNRENRES", ["DRRENRES","CRRENRES","NTRENRES"], ["DRRENRSQ","CRRENRSQ","NTRENRSQ"], ["NTRENRSQR","NTRENRQR","NTRENRESR","NTRENRSR"], "P3RENRES","P9RENRES","NARENRES"),
 ("Nonfarm nonres owner-occ", "LNRENROW", ["DRRENROW","CRRENROW","NTRENROW"], [], [], "P3RENROW","P9RENROW","NARENROW"),
 ("Nonfarm nonres other (non-OO)", "LNRENROT", ["DRRENROT","CRRENROT","NTRENROT"], [], [], "P3RENROT","P9RENROT","NARENROT"),
 ("Farmland", "LNREAG", ["DRREAG","CRREAG","NTREAG"], ["DRREAGQ","CRREAGQ","NTREAGQ"], ["NTREAGQR","NTREAGR"], "P3REAG","P9REAG","NAREAG"),
 ("C&I (total)", "LNCI", ["DRCI","CRCI","NTCI"], ["DRCIQ","CRCIQ","NTCIQ"], ["NTCIQR","NTCIR"], "P3CI","P9CI","NACI"),
 ("C&I non-U.S. addressees", "LNCINUS", ["DRCINUS","CRCINUS","NTCINUS"], ["DRCINUSQ","CRCINUSQ","NTCINUSQ"], ["NTCINUSQR"], "P3CINUS","P9CINUS","NACINUS"),
 ("Agricultural production", "LNAG", ["DRAG","CRAG","NTAG"], ["DRAGQ","CRAGQ","NTAGQ"], ["NTAGQR","NTAGR"], "P3AG","P9AG","NAAG"),
 ("Loans to depository insts", "LNDEP", ["DRDEP","CRDEP","NTDEP"], ["DRDEPQ","CRDEPQ","NTDEPQ"], ["NTDEPQR","NTDEPR"], "P3DEP","P9DEP","NADEP"),
 ("Loans to NDFIs (domestic offices)", "LNNDEPD", [], [], [], None,None,None),
 ("Loans to NDFIs (consolidated)", "LNNDEPC", [], [], [], None,None,None),
 ("NDFI + all other loans", "LNOTHER", ["DROTHER","CROTHER","NTOTHER"], ["DROTHQ","CROTHQ","NTOTHQ"], ["NTOTHQR","NTOTHERR"], "P3OTHLN","P9OTHLN","NAOTHLN"),
 ("Lease financing receivables", "LS", ["DRLS","CRLS","NTLS"], ["DRLSQ","CRLSQ","NTLSQ"], ["NTLSQR","NTLSR"], "P3LS","P9LS","NALS"),
]
EXTRA = ["LNSOTHER","LNOTHERF","LNCIFOR","LNDEPAOBK","LNDEPCB","LNDEPUS","LNDEPFC","LNOTCI","LSNUS","LSFOR",
         "NTALLOTHQR","NTALLOTHR","NTALLOTHNUM","NTALLOTHDEN",
         "UC","UCLN","UCCOMRE","UCCOMRES","UCCOMREU","UCOTHER","UCLOC","UCCRCD","UCSC","UCOVER1",
         "LNLSGR","LNLS","LNRE","LNCON","LNMUNI","LNFG","LNACOTH","LNRERES","LNCRCD","LNAUTO","LNCONOTH","LNCONRP",
         "P3LNLS","P9LNLS","NALNLS","NTLNLS","NTLNLSQ","NTRENREQ"]
def all_fields():
    out=[]
    for c in CATS:
        for f in [c[1]]+c[2]+c[3]+c[4]+[c[5],c[6],c[7]]:
            if f and f not in out: out.append(f)
    for f in EXTRA:
        if f not in out: out.append(f)
    return out
