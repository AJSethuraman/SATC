# Result: the book walkthrough

Excel 16.0, `C:\Users\ajish\SATC\threshold-engine\docs\walkthrough-book\out\walk.xlsx`. Each read: what the step expected, what Excel said.
**327 of 328 reads as expected.**

Differences:

- B1 sheets: expected ['Decide', 'Summary', 'Peers', 'Thresholds', 'Internal', 'Evidence', 'Backtest', 'Glossary', 'Sources', 'Run', 'Data', 'Peers data', 'Peers delinquency data', 'Internal data', 'Assess', 'Chart', 'Peers workings'], Excel said ['Decide', 'Summary', 'Peers', 'Thresholds', 'Evidence', 'Backtest', 'Glossary', 'Sources', 'Run', 'Data', 'Peers data', 'Peers delinquency data', 'Assess', 'Chart', 'Peers workings']


## B1 · Open the workbook as built: 8 of 9

It opens on Summary; the tabs in order; three slicers, each with one button picked; Decide shows the first series and nothing decided.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | active | Summary | Summary |
| **DIFFERS** | sheets | ['Decide', 'Summary', 'Peers', 'Thresholds', 'Internal', 'Evidence', 'Backtest', 'Glossary | ['Decide', 'Summary', 'Peers', 'Thresholds', 'Evidence', 'Backtest', 'Glossary', 'Sources' |
| ok | slicers | {'Product': 'Credit card', 'Measure': 'Net charge-offs', 'Source': 'Industry (every bank)' | {'Product': 'Credit card', 'Measure': 'Net charge-offs', 'Source': 'Industry (every bank)' |
| ok | visible_rows | [9] | [9] |
| ok | Decide!L1 | Decided: 0 of 105 · accepted 0 · rejected 0 | Decided: 0 of 105 · accepted 0 · rejected 0 |
| ok | Decide!B115 | Industry (every bank), net charge-offs, credit card: 4.01% in 2026Q2 | Industry (every bank), net charge-offs, credit card: 4.01% in 2026Q2 |
| ok | Decide!I115 | 3 Moderate | 3 Moderate |
| ok | links | [] | {} |
| ok | errors | 0 | 0 |

## B2 · Read Summary: 210 of 210

Every series' latest value and rating, 105 series.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Summary!I6 | 4.009514461690263 | 4.009514461690263 |
| ok | Summary!J6 | 3 Moderate | 3 Moderate |
| ok | Summary!G6 | 3.544345895397895 | 3.544345895397895 |
| ok | Summary!H6 | 3 Moderate | 3 Moderate |
| ok | Summary!D6 | 3.7557700716206863 | 3.755770071620686 |
| ok | Summary!E6 | Refused | Refused |
| ok | Summary!I7 | 5.194125778490533 | 5.194125778490533 |
| ok | Summary!J7 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!G7 | 4.459337486283432 | 4.459337486283432 |
| ok | Summary!H7 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!D7 | 4.5892741608892 | 4.5892741608892 |
| ok | Summary!E7 | Refused | Refused |
| ok | Summary!I8 | 1.369877603605913 | 1.369877603605913 |
| ok | Summary!J8 | 3 Moderate | 3 Moderate |
| ok | Summary!G8 | 1.3339203071816816 | 1.333920307181682 |
| ok | Summary!H8 | 3 Moderate | 3 Moderate |
| ok | Summary!D8 | 0.9203649082818812 | 0.9203649082818812 |
| ok | Summary!E8 | 2 Moderate-Low | 2 Moderate-Low |
| ok | Summary!I9 | 1.3597572332361343 | 1.359757233236134 |
| ok | Summary!J9 | 3 Moderate | 3 Moderate |
| ok | Summary!G9 | 1.3761444089041033 | 1.376144408904103 |
| ok | Summary!H9 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!D9 | 1.0086456886494444 | 1.008645688649444 |
| ok | Summary!E9 | 3 Moderate | 3 Moderate |
| ok | Summary!I10 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Summary!J10 | 1 Low | 1 Low |
| ok | Summary!G10 | 0.007185926941504787 | 0.007185926941504787 |
| ok | Summary!H10 | 1 Low | 1 Low |
| ok | Summary!D10 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Summary!E10 | 5 High | 5 High |
| ok | Summary!I11 | 2.810916225966142 | 2.810916225966142 |
| ok | Summary!J11 | 3 Moderate | 3 Moderate |
| ok | Summary!G11 | 2.7172506430272896 | 2.71725064302729 |
| ok | Summary!H11 | 3 Moderate | 3 Moderate |
| ok | Summary!D11 | 2.6198238917146655 | 2.619823891714665 |
| ok | Summary!E11 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!I12 | 1.441038622360229 | 1.441038622360229 |
| ok | Summary!J12 | 3 Moderate | 3 Moderate |
| ok | Summary!G12 | 1.3833303358456082 | 1.383330335845608 |
| ok | Summary!H12 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!D12 | 1.699458983432784 | 1.699458983432784 |
| ok | Summary!E12 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!I13 | 0.0034023275592908768 | 0.003402327559290877 |
| ok | Summary!J13 | Refused | Refused |
| ok | Summary!G13 | -0.0025743833456980635 | -0.002574383345698063 |
| ok | Summary!H13 | 1 Low | 1 Low |
| ok | Summary!D13 | -0.014683811346124514 | -0.01468381134612451 |
| ok | Summary!E13 | Refused | Refused |
| ok | Summary!I14 | 0.01680541154576976 | 0.01680541154576976 |
| ok | Summary!J14 | 1 Low | 1 Low |
| ok | Summary!G14 | 0.014503470405333936 | 0.01450347040533394 |
| ok | Summary!H14 | 1 Low | 1 Low |
| ok | Summary!D14 | 0.00901829163851567 | 0.00901829163851567 |
| ok | Summary!E14 | Refused | Refused |
| ok | Summary!I15 | 0.6021167144740369 | 0.6021167144740369 |
| ok | Summary!J15 | 1 Low | 1 Low |
| ok | Summary!G15 | 0.5947750534149762 | 0.5947750534149762 |
| ok | Summary!H15 | Refused | Refused |
| ok | Summary!D15 | 0.11323781597973155 | 0.1132378159797316 |
| ok | Summary!E15 | 1 Low | 1 Low |
| ok | Summary!I16 | 0.7090160674676405 | 0.7090160674676405 |
| ok | Summary!J16 | 1 Low | 1 Low |
| ok | Summary!G16 | 0.7012243205482663 | 0.7012243205482663 |
| ok | Summary!H16 | 1 Low | 1 Low |
| ok | Summary!D16 | 0.07287173365206458 | 0.07287173365206458 |
| ok | Summary!E16 | 3 Moderate | 3 Moderate |
| ok | Summary!I17 | 0.6896266904344225 | 0.6896266904344225 |
| ok | Summary!J17 | 1 Low | 1 Low |
| ok | Summary!G17 | 0.7994275825767806 | 0.7994275825767806 |
| ok | Summary!H17 | 2 Moderate-Low | 2 Moderate-Low |
| ok | Summary!D17 | 0.5848928248693543 | 0.5848928248693543 |
| ok | Summary!E17 | Refused | Refused |
| ok | Summary!I18 | 2.0007594723761 | 2.0007594723761 |
| ok | Summary!J18 | 1 Low | 1 Low |
| ok | Summary!G18 | 2.095426956540023 | 2.095426956540023 |
| ok | Summary!H18 | 1 Low | 1 Low |
| ok | Summary!D18 | 0.7710023745011505 | 0.7710023745011505 |
| ok | Summary!E18 | Refused | Refused |
| ok | Summary!I19 | 1.398642757902063 | 1.398642757902063 |
| ok | Summary!J19 | 1 Low | 1 Low |
| ok | Summary!G19 | 1.500651903125047 | 1.500651903125047 |
| ok | Summary!H19 | 1 Low | 1 Low |
| ok | Summary!D19 | 0.6577645585214189 | 0.6577645585214189 |
| ok | Summary!E19 | Refused | Refused |
| ok | Summary!I20 | -0.019378006304722882 | -0.01937800630472288 |
| ok | Summary!J20 | 1 Low | 1 Low |
| ok | Summary!G20 | -0.07696849626190862 | -0.07696849626190862 |
| ok | Summary!H20 | 1 Low | 1 Low |
| ok | Summary!D20 | 0.03257808684852553 | 0.03257808684852553 |
| ok | Summary!E20 | Refused | Refused |
| ok | Summary!I21 | 0.08750898529165822 | 0.08750898529165822 |
| ok | Summary!J21 | 1 Low | 1 Low |
| ok | Summary!G21 | 0.10526437222162137 | 0.1052643722216214 |
| ok | Summary!H21 | 1 Low | 1 Low |
| ok | Summary!D21 | 0.07719012006354721 | 0.07719012006354721 |
| ok | Summary!E21 | Refused | Refused |
| ok | Summary!I22 | 0.5204319093538794 | 0.5204319093538794 |
| ok | Summary!J22 | 1 Low | 1 Low |
| ok | Summary!G22 | 0.5326696605839647 | 0.5326696605839647 |
| ok | Summary!H22 | 1 Low | 1 Low |
| ok | Summary!D22 | 0.5338326102465549 | 0.5338326102465549 |
| ok | Summary!E22 | Refused | Refused |
| ok | Summary!I23 | 0.05413210722089782 | 0.05413210722089782 |
| ok | Summary!J23 | Refused | Refused |
| ok | Summary!G23 | 0.04595395835621955 | 0.04595395835621955 |
| ok | Summary!H23 | Refused | Refused |
| ok | Summary!D23 | 0.07072710329502283 | 0.07072710329502283 |
| ok | Summary!E23 | Refused | Refused |
| ok | Summary!I24 | 1.451503633202392 | 1.451503633202392 |
| ok | Summary!J24 | Refused | Refused |
| ok | Summary!G24 | 2.2210716603342027 | 2.221071660334203 |
| ok | Summary!H24 | Refused | Refused |
| ok | Summary!D24 | 1.8537532811982647 | 1.853753281198265 |
| ok | Summary!E24 | Refused | Refused |
| ok | Summary!I25 | 2.0260676497771692 | 2.026067649777169 |
| ok | Summary!J25 | Refused | Refused |
| ok | Summary!G25 | 2.799695279274387 | 2.799695279274387 |
| ok | Summary!H25 | Refused | Refused |
| ok | Summary!D25 | 2.4583129947398423 | 2.458312994739842 |
| ok | Summary!E25 | Refused | Refused |
| ok | Summary!I26 | 1.5056357404232898 | 1.50563574042329 |
| ok | Summary!J26 | Refused | Refused |
| ok | Summary!G26 | 2.2670256186904223 | 2.267025618690422 |
| ok | Summary!H26 | Refused | Refused |
| ok | Summary!D26 | 1.9244803844932874 | 1.924480384493287 |
| ok | Summary!E26 | Refused | Refused |
| ok | Summary!S6 | 1.6138446897622272 | 1.613844689762227 |
| ok | Summary!T6 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!Q6 | 1.337170043038558 | 1.337170043038558 |
| ok | Summary!R6 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!N6 | 1.05873659463189 | 1.05873659463189 |
| ok | Summary!O6 | Refused | Refused |
| ok | Summary!S7 | 2.0372465877364028 | 2.037246587736403 |
| ok | Summary!T7 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!Q7 | 1.7168395140183859 | 1.716839514018386 |
| ok | Summary!R7 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!N7 | 1.269580994403605 | 1.269580994403605 |
| ok | Summary!O7 | Refused | Refused |
| ok | Summary!S8 | 0.9530633219641633 | 0.9530633219641633 |
| ok | Summary!T8 | 3 Moderate | 3 Moderate |
| ok | Summary!Q8 | 0.9548722801044224 | 0.9548722801044224 |
| ok | Summary!R8 | Refused | Refused |
| ok | Summary!N8 | 0.6203355401492896 | 0.6203355401492896 |
| ok | Summary!O8 | Refused | Refused |
| ok | Summary!S9 | 0.18427413737016327 | 0.1842741373701633 |
| ok | Summary!T9 | 1 Low | 1 Low |
| ok | Summary!Q9 | 0.14375139105377918 | 0.1437513910537792 |
| ok | Summary!R9 | 1 Low | 1 Low |
| ok | Summary!N9 | 0.47005694520492464 | 0.4700569452049246 |
| ok | Summary!O9 | Refused | Refused |
| ok | Summary!S10 | 0.23128678890546345 | 0.2312867889054634 |
| ok | Summary!T10 | Refused | Refused |
| ok | Summary!Q10 | 0.2634243333599892 | 0.2634243333599892 |
| ok | Summary!R10 | Refused | Refused |
| ok | Summary!N10 | 0.10472064090822332 | 0.1047206409082233 |
| ok | Summary!O10 | 1 Low | 1 Low |
| ok | Summary!S11 | 1.3686242482397901 | 1.36862424823979 |
| ok | Summary!T11 | Refused | Refused |
| ok | Summary!Q11 | 1.3620480045181909 | 1.362048004518191 |
| ok | Summary!R11 | Refused | Refused |
| ok | Summary!N11 | 1.1951131262624375 | 1.195113126262437 |
| ok | Summary!O11 | Refused | Refused |
| ok | Summary!S12 | 0.41556092627562674 | 0.4155609262756267 |
| ok | Summary!T12 | 1 Low | 1 Low |
| ok | Summary!Q12 | 0.4071757244137684 | 0.4071757244137684 |
| ok | Summary!R12 | Refused | Refused |
| ok | Summary!N12 | 0.574777586113148 | 0.574777586113148 |
| ok | Summary!O12 | Refused | Refused |
| ok | Summary!S13 | 0.9878539701554716 | 0.9878539701554716 |
| ok | Summary!T13 | Refused | Refused |
| ok | Summary!Q13 | 0.8781912575766412 | 0.8781912575766412 |
| ok | Summary!R13 | Refused | Refused |
| ok | Summary!N13 | 0.09593421653723161 | 0.09593421653723161 |
| ok | Summary!O13 | Refused | Refused |
| ok | Summary!S14 | 1.7254849919194866 | 1.725484991919487 |
| ok | Summary!T14 | Refused | Refused |
| ok | Summary!Q14 | 1.5913437416124365 | 1.591343741612437 |
| ok | Summary!R14 | Refused | Refused |
| ok | Summary!N14 | 0.7781330896908787 | 0.7781330896908787 |
| ok | Summary!O14 | Refused | Refused |
| ok | Summary!S15 | 2.1170273837661813 | 2.117027383766181 |
| ok | Summary!T15 | Refused | Refused |
| ok | Summary!Q15 | 1.9638512469082074 | 1.963851246908207 |
| ok | Summary!R15 | Refused | Refused |
| ok | Summary!N15 | 0.4854368932038835 | 0.4854368932038835 |
| ok | Summary!O15 | 3 Moderate | 3 Moderate |
| ok | Summary!S16 | 0.017704651456628466 | 0.01770465145662847 |
| ok | Summary!T16 | 1 Low | 1 Low |
| ok | Summary!Q16 | 0.022406517616564536 | 0.02240651761656454 |
| ok | Summary!R16 | 1 Low | 1 Low |
| ok | Summary!N16 | 0.0369703594161898 | 0.0369703594161898 |
| ok | Summary!O16 | 3 Moderate | 3 Moderate |
| ok | Summary!S17 | 0.6418505967481973 | 0.6418505967481973 |
| ok | Summary!T17 | Refused | Refused |
| ok | Summary!Q17 | 0.5062199971159558 | 0.5062199971159558 |
| ok | Summary!R17 | Refused | Refused |
| ok | Summary!N17 | 0.5963479714524529 | 0.5963479714524529 |
| ok | Summary!O17 | Refused | Refused |
| ok | Summary!S18 | 2.776582631971007 | 2.776582631971007 |
| ok | Summary!T18 | Refused | Refused |
| ok | Summary!Q18 | 2.492477761640728 | 2.492477761640728 |
| ok | Summary!R18 | Refused | Refused |
| ok | Summary!N18 | 1.1187552240725263 | 1.118755224072526 |
| ok | Summary!O18 | 4 Moderate-High | 4 Moderate-High |
| ok | Summary!S19 | 0.6595552482048258 | 0.6595552482048258 |
| ok | Summary!T19 | Refused | Refused |
| ok | Summary!Q19 | 0.5286265147325203 | 0.5286265147325203 |
| ok | Summary!R19 | Refused | Refused |
| ok | Summary!N19 | 0.6333183308686428 | 0.6333183308686428 |
| ok | Summary!O19 | Refused | Refused |

## B3 · On Decide, click Credit card, Nonaccrual, KeyBank: 26 of 26

One row shows, KeyBank's; the screen speaks for it and sets it beside the industry and peers.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | visible_rows | [23] | [23] |
| ok | Decide!B115 | KeyBank, nonaccrual, credit card: 0.69% in 2026Q2 | KeyBank, nonaccrual, credit card: 0.69% in 2026Q2 |
| ok | Decide!I115 | 5 High | 5 High |
| ok | Decide!B116 | Check: OK, your settings fit this series. | Check: OK, your settings fit this series. |
| ok | Decide!M121 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Decide!M122 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Decide!M123 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Decide!M124 | 0.6295871211811148 | 0.629587121181115 |
| ok | Decide!N128 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Decide!M128 | 1 Low | 1 Low |
| ok | Decide!N129 | 0.007185926941504787 | 0.007185926941504787 |
| ok | Decide!M129 | 1 Low | 1 Low |
| ok | Decide!N130 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Decide!M130 | 5 High | 5 High |
| ok | Thresholds!E19 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Thresholds!F19 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Thresholds!G19 | 1.8086714674791118 | 1.808671467479112 |
| ok | Thresholds!L19 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Thresholds!H19 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Thresholds!I19 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Thresholds!J19 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Thresholds!K19 | 0.6295871211811148 | 0.629587121181115 |
| ok | Thresholds!Q19 | 5 | 5 |
| ok | Thresholds!R19 | High | High |
| ok | Thresholds!S19 |  |  |

## B4 · Type 3.5 under How rare High is (z), in the yellow row: 13 of 13

Only High's line moves; Thresholds and Summary follow.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Thresholds!E19 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Thresholds!F19 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Thresholds!G19 | 1.8086714674791118 | 1.808671467479112 |
| ok | Thresholds!L19 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Thresholds!H19 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Thresholds!I19 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Thresholds!J19 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Thresholds!K19 | 0.7685831667662775 | 0.7685831667662779 |
| ok | Thresholds!Q19 | 4 | 4 |
| ok | Thresholds!R19 | Moderate-High | Moderate-High |
| ok | Thresholds!S19 |  |  |
| ok | Summary!E10 | 4 Moderate-High | 4 Moderate-High |

## B5 · Leave out 2012Q3 to 2013Q4, the period Decide suggests, with a reason: 15 of 15

The lines move as the reference says; Assess lists the period, its Status whole.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!D139 | Leave out 2012Q3 to 2013Q4 | Leave out 2012Q3 to 2013Q4 |
| ok | Assess!N127 | Credit card - Nonaccrual - KeyBank | Credit card - Nonaccrual - KeyBank |
| ok | Assess!T127 | Left out: 6 quarters | Left out: 6 quarters |
| ok | Thresholds!E19 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Thresholds!F19 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Thresholds!G19 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Thresholds!L19 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Thresholds!H19 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Thresholds!I19 | 0.235387727674618 | 0.235387727674618 |
| ok | Thresholds!J19 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Thresholds!K19 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Thresholds!Q19 | 5 | 5 |
| ok | Thresholds!R19 | High | High |
| ok | Thresholds!S19 |  |  |

## B6 · Clear the reason: 1 of 1

The series is refused, saying why.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Thresholds!S19 | Refused: a period left out for this product is not whole; its Status on Assess says what i | Refused: a period left out for this product is not whole; its Status on Assess says what i |

## B6b · Type the reason back: 12 of 12

The lines are back as in B5.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Thresholds!E19 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Thresholds!F19 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Thresholds!G19 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Thresholds!L19 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Thresholds!H19 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Thresholds!I19 | 0.235387727674618 | 0.235387727674618 |
| ok | Thresholds!J19 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Thresholds!K19 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Thresholds!Q19 | 5 | 5 |
| ok | Thresholds!R19 | High | High |
| ok | Thresholds!S19 |  |  |

## B7 · Pick Accept these lines and write a note: 2 of 2

The count at the top.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!L1 | Decided: 1 of 105 · accepted 1 · rejected 0 | Decided: 1 of 105 · accepted 1 · rejected 0 |
| ok | Thresholds!O19 | Accept these lines | Accept these lines |

## B8 · Click Auto, Net charge-offs, KeyBank: 12 of 12

Life to date: 15 quarters, its lines shown and the Check in words; Summary agrees.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | visible_rows | [95] | [95] |
| ok | Decide!B115 | KeyBank, net charge-offs, auto: 0.10% in 2026Q2 | KeyBank, net charge-offs, auto: 0.10% in 2026Q2 |
| ok | Summary!O13 | Refused | Refused |
| ok | Decide!B116 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Decide!I116 | To fix:  | To fix: Lower How rare High is to 0.88 or less, or put back a period that went higher. |
| ok | Thresholds!E91 | 0.01034527350316824 | 0.01034527350316824 |
| ok | Thresholds!F91 | 0.048110295921705216 | 0.048110295921705175 |
| ok | Thresholds!G91 | 0.3152509896784223 | 0.3152509896784223 |
| ok | Thresholds!L91 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M91 | 0.09593421653723161 | 0.09593421653723161 |
| ok | Thresholds!Q91 |  |  |
| ok | Thresholds!S91 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |

## B9 · Click Mortgage, Net charge-offs, Industry: 10 of 10

Refused, with what to type.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!B116 | Refused: Moderate-Low would begin at or below zero | Refused: Moderate-Low would begin at or below zero |
| ok | Decide!I116 | To fix:  | To fix: Lower Moderate-Low begins to 0.99 or less. |
| ok | Decide!I115 | No rating: see the Check | No rating: see the Check |
| ok | Thresholds!E26 | 0.05926778269446801 | 0.05926778269446801 |
| ok | Thresholds!F26 | 0.05937714243884957 | 0.05937714243884953 |
| ok | Thresholds!G26 | 1.5285126504018145 | 1.528512650401814 |
| ok | Thresholds!L26 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M26 | 0.0034023275592908768 | 0.003402327559290877 |
| ok | Thresholds!Q26 |  |  |
| ok | Thresholds!S26 | Refused: Moderate-Low would begin at or below zero | Refused: Moderate-Low would begin at or below zero |

## B10 · Save (Ctrl+S), close Excel, open the file again: 18 of 18

Every decision and setting typed is still there, and the lines with them.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!H23 | 3.5 | 3.5 |
| ok | Decide!J23 | 2012Q3 | 2012Q3 |
| ok | Decide!E23 | Accept these lines | Accept these lines |
| ok | Decide!M23 | Walkthrough: accepted with z 3.5 | Walkthrough: accepted with z 3.5 |
| ok | Decide!L1 | Decided: 1 of 105 · accepted 1 · rejected 0 | Decided: 1 of 105 · accepted 1 · rejected 0 |
| ok | slicers | {'Product': 'Mortgage', 'Measure': 'Net charge-offs', 'Source': 'Industry (every bank)'} | {'Product': 'Mortgage', 'Measure': 'Net charge-offs', 'Source': 'Industry (every bank)'} |
| ok | Thresholds!E19 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Thresholds!F19 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Thresholds!G19 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Thresholds!L19 | 2026Q2 | 2026Q2 |
| ok | Thresholds!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Thresholds!H19 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Thresholds!I19 | 0.235387727674618 | 0.235387727674618 |
| ok | Thresholds!J19 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Thresholds!K19 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Thresholds!Q19 | 5 | 5 |
| ok | Thresholds!R19 | High | High |
| ok | Thresholds!S19 |  |  |
