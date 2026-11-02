# Signals data, committed (built 18 Oct 2026)

Public series the Signals tab draws that are not fetched at build: read once
from large sources or ones that need a contact, kept small, each with its
source in the file. `nmdb.json` (FHFA National Mortgage Database aggregates:
the share of outstanding mortgages with mark-to-market LTV over 90%, and the
share of new purchase mortgages with DTI 44% or more) and
`fico-under-660.json` (each holding company's share of scored card balances
with a refreshed FICO under 660, from its 10-Q XBRL where it cuts at 660;
KeyCorp from 2018). How each was made is in the file and in
`docs/early-warning-2026-10/record/`. The Run tab prints each file's SHA-256.

The rest of the tab's data is fetched by `peers signals-pull` (Philadelphia
Fed card balances and originations files; FRED `DRTSCLCC`) or computed from
the FDIC cache at build.
