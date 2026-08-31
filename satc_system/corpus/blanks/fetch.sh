#!/usr/bin/env bash
# Fetch the IRS's own blank fillable forms for the classifier corpus.
#
# WHY THESE AND NOT MORE SYNTHETIC PAGES. Everything else in the corpus is text
# this repository generated, and generated text proves almost nothing: a page
# reading "Form W-2 / 1 Wages, tips, other compensation" classifies as a W-2 and
# always will. A real blank carries the REAL AcroForm field names, the REAL
# layout, and the REAL text-layer reading order -- the three things that actually
# decide the answer, and the three things that were wrong in the field while the
# synthetic tests stayed green.
#
# These are public IRS documents. No client data goes in this folder, ever.
#
# ⚠ THE URLS ARE UNVERIFIED FROM THE BUILD ENVIRONMENT. irs.gov is blocked here
# (403 on CONNECT), so this script has never been run end to end by the software
# that wrote it. The pattern -- https://www.irs.gov/pub/irs-pdf/<form>.pdf -- is
# the IRS's long-standing one, but a form that has been revised may have moved.
# The script reports each file it could not get BY NAME rather than failing
# silently, so a 404 is a thing you can see and search for, not a gap.
#
#   bash fetch.sh
set -u
cd "$(dirname "$0")"

FORMS=(
  fw2       # W-2        Wage and Tax Statement
  f1099int  # 1099-INT   Interest Income
  f1099div  # 1099-DIV   Dividends and Distributions
  f1099b    # 1099-B     Proceeds From Broker Transactions
  f1099nec  # 1099-NEC   Nonemployee Compensation
  f1099msc  # 1099-MISC  Miscellaneous Information
  f1099r    # 1099-R     Distributions From Pensions
  f1099g    # 1099-G     Certain Government Payments
  f1098     # 1098       Mortgage Interest Statement
  f1098t    # 1098-T     Tuition Statement
  f1095a    # 1095-A     Health Insurance Marketplace Statement
  f1040     # 1040       U.S. Individual Income Tax Return
  f1040sc   # Schedule C Profit or Loss From Business
  f1065sk1  # K-1 (1065) Partner's Share
  f1120ssk1 # K-1 (1120-S) Shareholder's Share
)

ok=0; missing=()
for form in "${FORMS[@]}"; do
  url="https://www.irs.gov/pub/irs-pdf/${form}.pdf"
  printf '  %-12s ' "$form"
  if curl -fsSL --max-time 45 -o "${form}.pdf" "$url" 2>/dev/null && [ -s "${form}.pdf" ]; then
    printf 'ok  (%s bytes)\n' "$(wc -c < "${form}.pdf" | tr -d ' ')"
    ok=$((ok+1))
  else
    rm -f "${form}.pdf"
    printf 'COULD NOT FETCH\n'
    missing+=("$form")
  fi
done

echo
echo "  $ok of ${#FORMS[@]} fetched."
if [ ${#missing[@]} -gt 0 ]; then
  echo
  echo "  Not fetched: ${missing[*]}"
  echo "  Search irs.gov for the form by name and drop the PDF in this folder"
  echo "  under the same base name. A missing form is not a failure -- the corpus"
  echo "  uses whatever is here."
fi
echo
echo "  Nothing else to do. Committing these is fine: they are public IRS forms"
echo "  and carry no client data."
