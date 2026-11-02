# Economic Data as a Fourth Helper: Proposal

14 Oct 2026. Copied from the Claude Doc the firm reads
(https://claude.ai/code/artifact/1e9a8201-71b5-47bd-bc8f-80a48109b3e4). The two
charts there are drawn from the files in `data/`.

**Recommendation: use economic data as a stress scenario (option C below).** The firm names a recession by how far unemployment rises. The tool then applies how far each product's losses rose per point of unemployment in past recessions, as a fourth suggestion for where rating 5 begins, beside KeyBank's history, the industry and the peers. Applying past recessions' card rates to the Fed's 2026 severely adverse rise in unemployment (+5.5 points), from the middle of the card history the tool keeps (3.76%), gives 7.5–10.6%. Unemployment has the strongest record; house prices matter for mortgage and home equity, but on one episode. National figures are enough for now. Nothing has been built.

**Terms used throughout.** *Rating 5* is High, the worst of the tool's five ratings. *Kept quarters* are the ones the tool uses, after any left out on purpose. *Rehearsal settings* are the practice settings agreed on 7 Oct 2026, not final ones; under them, rating 5 for cards begins at 5.98%. A *negative correlation* means the two series move in opposite directions. KeyCorp is the holding company of KeyBank.

| Decision waiting on the firm | Recommended | Answer |
| --- | --- | --- |
| Which option to build: A (a warning beside the chart), B (a level of unemployment read as a level of losses), C (a stress scenario), or none | C. Not B: the public data does not support it | |
| How big a recession C uses | The Fed's severely adverse rise, 5.5 points this year, updated when the Fed publishes. On cards this puts C's suggestion for rating 5 at 7.5–10.6%, above the rehearsal line of 5.98% | |
| Which past recessions C shows | All four, 1990, 2001, 2008 and 2020, with 2020 marked as the one that broke. The firm picks which to use | |
| Where C starts from | The middle of the kept history (3.76% for cards). The alternatives are today's rate, or the low before each recession | |
| Add the rise in points, or scale it in proportion | Show both (on cards: 7.5–10.6% added, 8.3–11.1% scaled); the firm picks | |
| Should rating 5 begin at about a 2001-sized recession, as the rehearsal card line does now, or at a smaller or larger one | The firm's call; the tool shows each | |
| Products in the first build | Cards, on unemployment. Other consumer including auto, on unemployment, marked as following it less closely. Residential mortgage and home equity, on house prices and unemployment, marked "one episode only" | |
| Auto on its own (the firm said on 13 Oct to set auto thresholds) | Public auto losses start in 2011, so C can only borrow other consumer's rates for auto. Whether that is acceptable is the firm's call | |
| Add A, the warning, later | Yes, as context only. It needs a rise in unemployment, set by the firm, to warn on | |

## Candidate series: unemployment carries the published evidence

Unemployment has the strongest published record: the Federal Reserve builds its stress-test consumer loss models on it, adding house prices for mortgage and home equity. On the public data, card lending standards, claims and the debt service ratio also track card losses some quarters later, but none has a published test as an early warning of losses.

| Series | Source, frequency, history | Published evidence | On the public data here |
| --- | --- | --- | --- |
| Unemployment rate, national | BLS; monthly; from 1948 (seen on FRED) | The Fed's card loss model: "The key macroeconomic variable that enters the model is the unemployment rate," taken from the previous quarter. A 2025 Fed note: a 1-point rise in unemployment "is associated with about a 45 basis point increase" (0.45 points) in card delinquency. | Card losses rose 0.68–1.25 points per point of unemployment in 1990, 2001 and 2008, measured from the low to the peak; not in 2020 |
| Unemployment, state and county | BLS Local Area Unemployment Statistics; monthly; states from 1976 (seasonally adjusted), counties mostly from 1990 (not seasonally adjusted) | The Fed's card and home equity models use state rates. Chicago Fed, on one lender's direct auto loans, mostly in the Northeast: a 1% rise in county unemployment raised default risk "by as much as 9 percent". | Weighted to KeyBank's deposits, it moves almost exactly with the national rate (see Geography) |
| Initial jobless claims | Labor Department; weekly; from 1967 | One of ten parts of the Conference Board's leading index, which leads business-cycle turning points by about seven months. No official or peer-reviewed link to consumer losses was found. | Its closest match is card losses six quarters later (correlation 0.66, to 2019); broke in 2020 |
| House prices | FHFA: quarterly from 1975 (sales and refinance appraisals), monthly from 1991 (purchases only); Case-Shiller from 1987 (seen on FRED) | The Fed's first-lien and home equity models use house prices and unemployment together: "both factors are often needed to cause default." Boston Fed: "negative equity is a necessary but not a sufficient condition for foreclosure." | Rising prices matched lower residential losses three quarters later and lower home equity losses four quarters later (correlation −0.85, −0.88, to 2019), on one fall only, 2007–12. The unemployment level matched them as closely, in the same quarter (0.87, 0.89) |
| Household debt service ratio | Federal Reserve; quarterly; current method from 2005, old method 1980–2024 | Linked to default in a 2003 Fed Bulletin article, which did not test it; no test was found. The 2025 Fed note tried debt-to-income instead and found those models fit worse than its preferred one. | Its closest match is card losses ten quarters later (correlation 0.66, to 2019, old method); it also held in 2020–26 (0.70, 17 quarters) |
| Consumer credit growth | Fed G.19 consumer credit; monthly; revolving credit from 1968 | Card delinquency is highest about two years after an account opens (Gross and Souleles). For mortgages, which G.19 leaves out, fast credit growth in some zip codes in 2001–05 was followed by defaults there in 2005–07 (Mian and Sufi). | No lead on card losses: growth falls as losses rise |
| Card lending standards | Fed Senior Loan Officer Opinion Survey (SLOOS); quarterly; cards from 1996 | The 2025 Fed note lags it four quarters and reads the link as banks that "tighten as delinquencies begin to rise". | Its closest match is card losses five quarters later (correlation 0.74, to 2019; 0.18 in the same quarter). Delinquency comes before charge-offs, so this may be banks reacting to delinquency |
| Real disposable income | BEA; monthly; from 1959 (seen on FRED) | None found. In Gross and Souleles, state income was not significant. | Not pulled: needs a BEA or FRED key |
| Delinquency, as a lead on charge-offs | Fed and FDIC, already in the tool; NY Fed transitions into delinquency from 2003 | Mechanical: regulators charge off revolving loans such as cards at 180 days past due, and installment loans at 120. | Card 30+ delinquency peaked in 2009Q2, card losses in 2010Q2 |

## Which product each fits: unemployment for cards and other consumer, house prices with unemployment for residential

Cards have the clearest public record. Other consumer, whose public series includes auto, rose as much as cards relative to where it started, but follows unemployment less closely quarter by quarter. Auto alone has too little history. Residential mortgage and home equity follow house prices and unemployment, on one episode.

| Product | Series | Net charge-off rate | 30+ days late, including nonaccrual | 90+ days late, including nonaccrual |
| --- | --- | --- | --- | --- |
| Credit card | Unemployment | Rose with it in 1990, 2001 and 2008: 0.68–1.25 points per point of unemployment, or +53%, +53% and +195% of its starting level. Not in 2020 | Fed series from 1991; peaked in 2009Q2, a year before losses | Public only from 2006 (FDIC, in the tool); not tested |
| Other consumer, including auto (FDIC series) | Unemployment | 0.27 and 0.40 points per point in 2001 and 2008, which was +59% and +195% of its starting level, as much as cards. Quarter by quarter, almost no fit | Fed series from 1991; correlation 0.47 with the unemployment level in the same quarter | Not tested |
| Auto | Unemployment; the Fed's model adds house prices and used-car prices | Public auto series start in 2011, so only 2020 to test | Same | Same |
| Residential mortgage (Fed series: 1–4 family, including home equity lines) | House prices with unemployment | +2.4 points from 2005Q4 to 2010Q1; +0.2 in 2001; the series starts too late for 1990 | Fed series from 1991 | The tool compares mortgage on nonaccrual and charge-offs instead, because 90+ includes rebooked GNMA loans (government-guaranteed loans bought back from Ginnie Mae pools) |
| Home equity (FDIC series: lines) | House prices with unemployment | +3.1 points from 2005Q4 to 2010Q1; +0.1 in 2001; the series starts too late for 1990 | No separate public series before 2006 | Not tested |

"Nonaccrual" means loans on which the bank has stopped booking interest. The card and residential series here are the Federal Reserve's, from 1985 and 1991, because the tool's FDIC pull starts in 2006 and these figures need the earlier recessions. The firm's rule (13 Oct) is FDIC for every industry series, with the Fed as a cross-check; this proposal uses the Fed only for history the FDIC pull does not reach. Home equity and other consumer are the FDIC's, from 1992. All are the public series already bundled with the tool.

## Three ways it could feed the thresholds

**A. A warning shown beside the loss series.** The tool would draw the change in unemployment under each product's chart and say, in words, when it has risen by more than an amount the firm sets. It moves no line. On the public data it reads like this:

> Chart: *Card losses rose with unemployment in 1990, 2001 and 2008, but not in 2020.* Federal Reserve card charge-off rate (CORCCACBS), four-quarter mean; change over four quarters in the BLS unemployment rate (quarterly average); 1986Q1–2026Q2; NBER recession quarters shaded. Data: `data/card_losses_and_unemployment_change.csv`. From 2010Q1 an accounting change brought securitized cards onto bank books; its effect on this Fed series is not checked here.

In 1990, 2001 and 2008, card losses started rising within two quarters of unemployment. Over 1985–2019 the yearly rise in unemployment matched card losses most closely four quarters later: correlation 0.83, the best of 13 lags tried, 0.58 before 2008 and 0.94 after. In 2020 the largest rise on record was followed by falling losses. And card losses began rising in 2022Q3 while unemployment was still falling (1.5 points lower than a year earlier). The yearly change turned positive only in 2023Q3 and peaked at +0.5 points, so the warning would have come late and small.

**B. "This level of unemployment has gone with this level of losses."** The tool would read, from history, what card losses followed each unemployment rate, to suggest where rating 5 begins. On the public data the levels do not line up:

> Chart: *The same unemployment rate has gone with card losses about 3 to 7 points apart.* Federal Reserve card net charge-off rate (four-quarter mean) in 1985Q1–2019Q4, grouped by the BLS unemployment rate four quarters earlier: lowest, middle and highest; the line for rating 5 is the rehearsal settings' (LOG.md, 7 Oct 2026). Data: `data/unemployment_bands_card_losses_1985_2019.csv`.

At 6.5–7.5% unemployment, card losses a year later ran anywhere from 2.4% to 9.4%. The relation has also shifted between decades. Unemployment of 3.9–5.2% in 1997–2000 went with card losses of 4.3–5.4% a year later; unemployment of 3.6–4.9% in 2016–2019 went with 3.3–3.8%. Every band crosses the current line for rating 5, so a level of unemployment cannot place it.

**C. A stress scenario: "a recession of this size would take losses here."** The firm states a rise in unemployment. The tool applies past recessions' rise in losses per point of unemployment, from a starting point the firm chooses, as a fourth suggestion for where rating 5 begins, beside KeyBank's history, the industry and the peers. On cards, with the Fed's 2026 severely adverse scenario (unemployment up 5.5 points, from 4.5% to a 10% peak) and starting from the middle of the kept card history (3.76%):

| Card losses would reach about | Using the rise in losses per point of unemployment in |
| --- | --- |
| 7.5% | 1990–92 (0.68) |
| 9.4% | 2001–03 (1.03) |
| 10.6% | 2007–10 (1.25) |
| no rise | 2020 (losses fell) |

These add points to the starting level; scaling it in proportion instead gives 8.3–11.1%. The 2007–10 rate is measured from 2006Q4, when card losses were at their lowest of that decade; measured from 2004Q4 or 2007Q2 it is 1.21–1.22. That rise also crosses 2010Q1, when an accounting change brought securitized cards back onto bank books. The comparability tie-out found that break in the FDIC series; this Fed series probably has it too, which is not checked here.

The Fed's own projection for KeyCorp's cards in this scenario is 17.4% over nine quarters, 7.7% a year on average. The Fed does not publish the worst single year, so this cannot be set against the range above.

Read the other way, it explains the line already drawn for cards. The rehearsal line for rating 5, 5.98%, comes from a statistical rule (the middle plus 2.5 times the spread of past levels), not from a recession. On 2001's rate, it sits where a 2.2-point rise in unemployment would take card losses, about the size of the 2001 recession. On 1990's rate it needs 3.3 points; on 2008's, 1.8. Whether rating 5 should start there is the firm's call.

The Fed publishes KeyCorp's projected losses for every consumer book in the same scenario (house prices also fall 30%):

| Book | KeyCorp, nine quarters | A year, on average | Industry's worst year, 2009–10 |
| --- | --- | --- | --- |
| Credit card | 17.4% | 7.7% | 10.4% |
| Other consumer, including auto and student | 11.6% | 5.2% | 3.3% (including auto) |
| First-lien mortgage | 1.6% | 0.7% | 2.5% (all residential, including home equity lines) |
| Home equity and junior liens | 3.7% | 1.6% | 3.1% (home equity lines) |

"A year, on average" is the nine-quarter rate times 4/9; the worst single year would be higher. The industry column is the tool's bundled public series at its 2009–10 peak, on a four-quarter basis.

**Recommendation: C.** Of the two options that place a line, it is the only one the public data supports, and it says what the line means in words a reader can test: a recession of a stated size. A is context, cheap to add later, but moves no line. B should not be built: levels of unemployment do not map to levels of losses. Under C, four settings are the firm's and have no default: the size of the recession, which past recessions' rates to use, where to start from, and whether to add or scale. Without them the tool refuses and names what it needs.

## Geography: national figures are enough for now

A footprint-weighted unemployment rate moves almost exactly with the national rate, so national figures are enough for now. Weighted by where KeyBank's deposits are booked (2025 weights, held fixed back to 1976), it correlates with the national rate at 0.981 in levels and 0.986 in year-on-year changes, monthly, 1976 to July 2026. With 2008's weights the figures are 0.984 and 0.989. Whether a footprint series would explain KeyBank's losses better than national was not tested.

| Recession | Footprint peak | National peak |
| --- | --- | --- |
| 1990–91 | 7.7% (Aug 1992) | 7.8% (Jun 1992) |
| 2001 | 6.4% (Jun 2003) | 6.3% (Jun 2003) |
| 2007–09 | 10.0% (Jan 2010) | 10.0% (Oct 2009) |
| 2020 | 15.5% (Apr 2020) | 14.8% (Apr 2020) |

The largest gap was 1.6 points, in January 1983. Since 2000 the gap has stayed between −0.6 and +0.7 points; the +0.7 was April 2020.

**Weights used:** the FDIC Summary of Deposits for KeyBank (FDIC certificate 17534), 30 June 2025: 955 branches, $152.0bn. Ohio 45.2%, New York 20.6%, Washington 7.4%, Pennsylvania 4.8%, Oregon 3.9%, Connecticut 3.4%, Colorado 3.1%, Indiana 2.6%, Utah 2.4%, Maine 1.8%, six more under 1.1% each. State rates are the repository's verified BLS series (`credit-suite/verified-data/`).

**Two limits on those weights.** Deposits are not loans: the largest single branch, in Cuyahoga County, Ohio (Cleveland), books 34.6% of KeyBank's deposits (11.5% in 2008), so Ohio's share is inflated. Leaving that branch out gives 0.985 and 0.989. And not every book follows the branches: loans made online can come from anywhere in the country, and for those the national rate is the right comparison.

**If a footprint series is wanted later:** mortgage and home equity could be weighted by KeyBank's own lending by state, from the public mortgage lending records banks file under the Home Mortgage Disclosure Act (HMDA). Card and unsecured loans have no public geography; deposits are the only stand-in.

## Validation: it held in three recessions out of four, and broke in 2020

The test is recession by recession, because there are only four in the public loss data. Recession dates are the National Bureau of Economic Research's (NBER). For each, from the quarter unemployment was lowest to the quarter it peaked, and the same for card losses (Federal Reserve, all banks, four-quarter rate):

| Recession (NBER peak) | Unemployment rise | Card loss rise | Card loss rise per point |
| --- | --- | --- | --- |
| 1990Q3 | +2.4 pts (1989Q1 to 1992Q3) | +1.66 pts (1989Q3 to 1992Q2) | 0.68 |
| 2001Q1 | +2.2 pts (2000Q4 to 2003Q3) | +2.30 pts (2000Q4 to 2002Q3) | 1.03 |
| 2007Q4 | +5.5 pts (2006Q4 to 2009Q4) | +6.89 pts (2006Q4 to 2010Q2) | 1.25 |
| 2019Q4 | +9.4 pts (2019Q3 to 2020Q2) | none: losses fell from 3.76% (2020Q2) to 1.76% (2022Q2) | none |

In the first three, card losses started rising within two quarters of unemployment. They peaked between four quarters before unemployment did (2001) and two quarters after (2009–10). In 2020 the link broke: unemployment averaged 13.0% in 2020Q2 (14.8% at its April peak) and card losses fell. The Fed's card model documentation reports research that "attributed" this "to financial assistance provided to borrowers via government support programs". That is not tested here.

**Out of sample.** A model fitted quarter by quarter on 1985–2007, then run on 2008–2019, years it had not seen, got the direction right (correlation 0.77 two quarters ahead) but not the size: it forecast a rise of 2.6 points where the largest actual rise was 3.9; four quarters ahead it forecast 0.6. On 2020–2026 the two-quarter model's forecasts had almost no relation to what happened (correlation 0.11), and the four-quarter model's were wrong in sign (−0.27). The whole-recession rates miss at the edges too. The two rates known before 2008 (0.68, 1.03), applied to 2008's 5.5-point rise, give +3.7 to +5.7 points against an actual +6.9. Any of the three, applied to 2020's 9.4-point rise, gives +6.4 to +11.8 against an actual fall.

**Residential mortgage and home equity have one episode.** Since their loss series begin (1991–92), house prices fell nationally only once, from 2007Q4 to 2012Q2 on a four-quarter basis, so a house-price relationship has nothing to be tested on out of sample. In 2001 their losses rose by only 0.2 and 0.1 points; their series start too late to show 1990.

**KeyBank's own data can test it, mostly only on 2020.** Most internal series start in 2014, where the only recession is 2020, the one that broke. Those that reach back to 2008 can test it against one recession that held.

**What the tool does when it breaks.** It never refits quietly. It prints every recession's row, as above, wherever the helper is used, so a break shows as a row. If the latest recession broke, the helper's suggestion carries that in words, and the firm decides whether to use it. Watching live, if unemployment rises by an amount the firm states and losses have not followed within a number of quarters the firm states, the tool says so. Neither setting has a default; without them the tool refuses and names what it needs.

## What could not be verified, and the sources

None of the figures here has been tied out yet. Each was computed from public files and read back once; each will be tied to the publisher's own page before anything is built on it.

**Could not verify**

- **Agarwal and Liu (2003)** on card delinquency: the publisher blocked access. The finding is known only through the Fed's own description of it.
- **Lown and Morgan (2006)** on lending standards: could not be opened anywhere.
- **Four journal papers were read as working papers** (Gross and Souleles; Gerardi et al.; Foote, Gerardi and Willen; Elul et al.), because the journals blocked access.
- **Start dates seen only on FRED**, not at the publisher: national unemployment (1948), real income (1959), Case-Shiller (1987). The BLS website refuses automated requests.
- **Real disposable income was not pulled.** FRED's download stalled, and BEA needs a key, which is not set here.
- **No published test was found** linking claims, the debt service ratio, the saving rate or consumer sentiment directly to consumer losses. The only claims lead found, about 13 weeks, is in a sell-side note that could not be opened.
- **Why 2020 broke** is not tested here. The Fed's card model documentation reports research attributing it to government support programs.
- **The Fed's card rate before 2010** probably excludes securitized cards, as the FDIC industry series does (comparability tie-out, gap 3). Not checked here.
- **October 2025 has no unemployment rate** in the published series, so 2025Q4 is left out of every calculation, not filled in.
- **Whether a footprint series would explain KeyBank's losses** better than the national rate was not tested; only the two rates were compared.

**Sources**

- Loss and delinquency rates: [Federal Reserve charge-off and delinquency release](https://www.federalreserve.gov/releases/chargeoff/) (delinquency is "past due thirty days or more and still accruing interest as well as those in nonaccrual status"); FDIC BankFind, already in the tool.
- Economic series: [BLS unemployment via FRED](https://fred.stlouisfed.org/series/UNRATE); [Labor Department weekly claims](https://oui.doleta.gov/unemploy/claims.asp); [Fed debt service ratio](https://www.federalreserve.gov/releases/DSR/about.htm) and its [archived 1980–2024 series](https://www.federalreserve.gov/releases/housedebt/default.htm); [FHFA house prices](https://www.fhfa.gov/data/hpi); state rates from `credit-suite/verified-data/`, checked against BLS.
- Recession dates: [NBER](https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions).
- Footprint: [FDIC Summary of Deposits API](https://api.fdic.gov/banks/docs/).
- Stress test: [2026 scenarios](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf), [severely adverse variables](https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Severely_Adverse_Domestic.csv), [2026 results by bank](https://www.federalreserve.gov/supervisionreg/files/public_results_DFAST_2026.csv), [2025 methodology](https://www.federalreserve.gov/publications/files/2025-june-supervisory-stress-test-methodology.pdf), [Credit Risk Models](https://www.federalreserve.gov/supervisionreg/files/credit-risk-models.pdf).
- Research: [Barnes, Bopst and Driscoll (2025), FEDS Note](https://www.federalreserve.gov/econres/notes/feds-notes/predicting-credit-card-delinquency-rates-20250228.html); [Banerjee and Canals-Cerdá (2012), Philadelphia Fed](https://www.philadelphiafed.org/-/media/FRBP/Assets/working-papers/2012/wp12-18.pdf); [Agarwal, Ambrose and Chomsisengphet (2008), Chicago Fed](https://www.chicagofed.org/~/media/publications/economic-perspectives/2008/ep-3qtr2008-part2-agarwal-etal-pdf.pdf); [Gross and Souleles (2001), NBER](https://www.nber.org/papers/w8409); [Elul et al. (2010), Philadelphia Fed](https://www.philadelphiafed.org/-/media/frbp/assets/working-papers/2010/wp10-13.pdf); [Gerardi et al. (2015), Boston Fed](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/wp1513.pdf); [Foote, Gerardi and Willen (2008), Boston Fed](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/ppdp0803.pdf); [Mian and Sufi (2008), NBER](https://www.nber.org/papers/w13936); [Conference Board leading index](https://www.conference-board.org/topics/us-leading-indicators/); [Dynan, Johnson and Pence (2003), Fed Bulletin](https://www.federalreserve.gov/pubs/bulletin/2003/1003lead.pdf); [charge-off timing rule, Federal Register 2000](https://www.govinfo.gov/content/pkg/FR-2000-06-12/html/00-14704.htm).
- The scripts and data behind every figure here: this folder, `threshold-engine/docs/macro/`.
