#!/usr/bin/awk -f
# The independent road: the loan extract, read with awk and nothing else. No PocketBook code.
#
#   awk -f by-hand.awk "Consumer book Q3.csv"
#
# Columns in the extract: 1 LOAN_NBR, 2 FICO, 3 CHANNEL, 4 ORIG_BAL, 5 BAD_FLAG, 6 GCO_AMT, 7 RANR_AMT,
# 8 ASSET_CLASS, 9 REV_DEBT, 10 ORIG_DATE. No field in the file is quoted, so a plain comma split is exact.
#
# The rules below are the ones the workbook itself states (Record rows 16 and 68-72, Columns rows 14-18):
#   FICO -9999 is a code for missing (the analyst answered Treat as: Missing), and a blank FICO is blank.
#   FICO bands start at 654, 686, 712, 746; the lowest band is every real score under 654.
#   Charge-offs leave out a loan whose GCO_AMT is not a number or whose ORIG_BAL is blank.
#   Bad loans leave out a loan whose BAD_FLAG is neither 0 nor 1.

function band(f) {
    if (f == "") return "(blank)"
    if (f == -9999) return "(marked missing)"
    if (f < 654) return "1  <654"
    if (f < 686) return "2  654-685"
    if (f < 712) return "3  686-711"
    if (f < 746) return "4  712-745"
    return "5  746+"
}

BEGIN {
    FS = ","
    nbands = split("1  <654|2  654-685|3  686-711|4  712-745|5  746+|(blank)|(marked missing)", bands, "|")
    nchans = split("Branch|Broker|Online", chans, "|")      # the three channels the extract carries
}
NR == 1 { next }
{
    rows++
    b = band($2); ch = $3
    booked = ($4 == "") ? 0 : $4
    gco_ok = ($6 ~ /^[0-9]+(\.[0-9]+)?$/) && ($4 != "")
    flag_ok = ($5 == "0" || $5 == "1")

    # ---- Figure 2: the FICO x CHANNEL grid, every loan in exactly one cell
    n[b, ch]++; nb[b]++; nc[ch]++
    bk[b, ch] += booked; bkall += booked

    # ---- Figure 1: the lowest FICO band, Broker against the rest of the band
    if (b == "1  <654") {
        side = (ch == "Broker") ? "pocket" : "rest"
        loans[side]++
        if (flag_ok) { tested[side]++; bad[side] += $5 }
        if (gco_ok)  { co_loans[side]++; co_gco[side] += $6; co_bk[side] += $4 }
        if (lo == "" || $2 + 0 < lo) lo = $2 + 0
        if (hi == "" || $2 + 0 > hi) hi = $2 + 0
    }
}
END {
    printf "rows read: %d\n\n", rows

    print "FIGURE 1 -- FICO under 654 (lowest score seen " lo ", highest " hi "), Broker vs the rest of the band"
    for (i = 1; i <= 2; i++) {
        s = (i == 1) ? "pocket" : "rest"
        printf "  %-6s loans %4d | flag 0/1 %4d, bad %3d, bad rate %.10f\n", s, loans[s], tested[s], bad[s], bad[s] / tested[s]
        printf "         charge-off loans %4d, GCO %.2f, booked %.2f, GCO/booked %.10f\n", \
            co_loans[s], co_gco[s], co_bk[s], co_gco[s] / co_bk[s]
    }
    rp = co_gco["pocket"] / co_bk["pocket"]; rr = co_gco["rest"] / co_bk["rest"]
    printf "  charge-offs:  multiple = %.10f / %.10f = %.10f\n", rp, rr, rp / rr
    printf "  its share at the rest's rate = %.2f x %.10f = %.4f\n", co_bk["pocket"], rr, co_bk["pocket"] * rr
    printf "  above its share = %.2f - %.4f = %.4f\n", co_gco["pocket"], co_bk["pocket"] * rr, co_gco["pocket"] - co_bk["pocket"] * rr
    bp = bad["pocket"] / tested["pocket"]; br = bad["rest"] / tested["rest"]
    printf "  bad loans:    multiple = %.10f / %.10f = %.10f\n", bp, br, bp / br
    printf "  bad loans above share = %d - %d x %.10f = %.6f\n\n", bad["pocket"], tested["pocket"], br, bad["pocket"] - tested["pocket"] * br

    print "FIGURE 2 -- the FICO x CHANNEL grid: loans in each cell (booked dollars beneath)"
    printf "  %-18s", "FICO band"
    for (j = 1; j <= nchans; j++) printf "%16s", chans[j]
    printf "%16s\n", "All"
    for (i = 1; i <= nbands; i++) {
        printf "  %-18s", bands[i]
        for (j = 1; j <= nchans; j++) printf "%16d", n[bands[i], chans[j]]
        printf "%16d\n", nb[bands[i]]
        printf "  %-18s", ""
        for (j = 1; j <= nchans; j++) printf "%16.2f", bk[bands[i], chans[j]]
        printf "\n"
    }
    printf "  %-18s", "All"
    for (j = 1; j <= nchans; j++) printf "%16d", nc[chans[j]]
    printf "%16d\n", rows
    printf "  booked dollars, every loan: %.2f\n", bkall
}
