# Result: the book walkthrough

Excel 16.0, `C:\Users\ajish\SATC\threshold-engine\docs\walkthrough-book\out\walk.xlsx`. Each read: what the step expected, what Excel said.
**2465 of 2465 reads as expected.**

No differences.


## B1 · Open the workbook as built: 49 of 49

It opens on Summary; the tabs in order; two slicers, each with one button picked; Decide shows the first product and measure, no source picked and nothing decided.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | active | Summary | Summary |
| ok | sheets | ['Summary', 'Decide', 'Signals', 'Peers', 'Thresholds', 'Internal', 'Lines by source', 'Pe | ['Summary', 'Decide', 'Signals', 'Peers', 'Thresholds', 'Internal', 'Lines by source', 'Pe |
| ok | hidden | ['Internal', 'Internal data', 'Peers data', 'Peers delinquency data', 'Assess', 'Chart', ' | ['Internal', 'Internal data', 'Peers data', 'Peers delinquency data', 'Assess', 'Chart', ' |
| ok | slicers | {'Product': 'Credit card', 'Measure': 'Net charge-offs'} | {'Product': 'Credit card', 'Measure': 'Net charge-offs'} |
| ok | visible_rows | [10] | [10] |
| ok | Decide!L1 | Decided: 0 of 56 · accepted 0 · rejected 0 | Decided: 0 of 56 · accepted 0 · rejected 0 |
| ok | Decide!B67 | Credit card, net charge-offs: no source picked to set the lines yet | Credit card, net charge-offs: no source picked to set the lines yet |
| ok | Decide!I67 | No rating: see the Check | No rating: see the Check |
| ok | Decide!B68 | Check: pick the source whose history sets the lines, under Lines set from. | Check: pick the source whose history sets the lines, under Lines set from. |
| ok | links | [] | {} |
| ok | errors | 0 | 0 |
| ok | Summary!B35 | Needs your attention · KeyBank rated 4 or 5 | Needs your attention · KeyBank rated 4 or 5 |
| ok | Summary!B36 | None rated 4 or 5. | None rated 4 or 5. |
| ok | Summary!R1 | Lines picked: 0 of 56 · KeyBank rated 4 or 5: 0 · refused: 0 | Lines picked: 0 of 56 · KeyBank rated 4 or 5: 0 · refused: 0 |
| ok | Thresholds!S1 | Lines picked: 0 of 56 · KeyBank rated 4 or 5: 0 · refused: 0 | Lines picked: 0 of 56 · KeyBank rated 4 or 5: 0 · refused: 0 |
| ok | Summary!N2 | Large banks (Philadelphia Fed) · Credit card · Share paying only the minimum ·  | Large banks (Philadelphia Fed) · Credit card · Share paying only the minimum ·  |
| ok | Summary!O2 | 10.15 | 10.15 |
| ok | Summary!P2 |  · 2026Q2 · rating — |  · 2026Q2 · rating — |
| ok | Summary!D17 | Large banks only | Large banks only |
| ok | Thresholds!D5 |  |  |
| ok | Thresholds!E5 |  |  |
| ok | Thresholds!F5 |  |  |
| ok | Thresholds!G5 |  |  |
| ok | Thresholds!H5 |  |  |
| ok | Thresholds!I5 |  |  |
| ok | Thresholds!J5 |  |  |
| ok | Thresholds!K5 |  |  |
| ok | Thresholds!R5 |  |  |
| ok | Thresholds!S5 |  |  |
| ok | Thresholds!Q5 |  |  |
| ok | Thresholds!P5 | 4.009514461690263 | 4.009514461690263 |
| ok | Thresholds!O5 |  |  |
| ok | Thresholds!N5 | 3.9545852353018254 | 3.9545852353018254 |
| ok | Thresholds!M5 |  |  |
| ok | Thresholds!L5 | 3.7557700716206863 | 3.755770071620686 |
| ok | Thresholds!AK5 |  |  |
| ok | Thresholds!AJ5 | 4.009514461690263 | 4.009514461690263 |
| ok | Peers!B14 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Peers!B39 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Peers!J39 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Decide!B91 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Signals!B6 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Peers!B9 | Pack | Pack |
| ok | Peers!B12 | Pack | Pack |
| ok | Peers!B8 | JPMorgan | JPMorgan |
| ok | Peers!B11 | Zions | Zions |
| ok | Sources!B191 | Reporting changes · 12 rows | Reporting changes · 12 rows, from reporting-changes.json |
| ok | Sources!B193 | Change | Change |
| ok | Sources!B194 | Construction, nonfarm and lease splits | Construction, nonfarm and lease splits |

## B2 · Read Summary, and every source's own lines on Lines by source: 1972 of 1972

Every series' latest value, and a dash where its rating goes: 164 series, each with its own lines on Lines by source.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Summary!H7 | 4.009514461690263 | 4.009514461690263 |
| ok | Summary!I7 | — | — |
| ok | Summary!F7 | 3.9545852353018254 | 3.9545852353018254 |
| ok | Summary!G7 | — | — |
| ok | Summary!C7 | 3.7557700716206863 | 3.755770071620686 |
| ok | Summary!D7 | — | — |
| ok | Summary!H8 | 5.194125778490533 | 5.194125778490533 |
| ok | Summary!I8 | — | — |
| ok | Summary!F8 | 5.1312227443145 | 5.1312227443145 |
| ok | Summary!G8 | — | — |
| ok | Summary!C8 | 4.5892741608892 | 4.5892741608892 |
| ok | Summary!D8 | — | — |
| ok | Summary!H9 | 1.369877603605913 | 1.369877603605913 |
| ok | Summary!I9 | — | — |
| ok | Summary!F9 | 1.3341908238105804 | 1.3341908238105804 |
| ok | Summary!G9 | — | — |
| ok | Summary!C9 | 0.9203649082818812 | 0.9203649082818812 |
| ok | Summary!D9 | — | — |
| ok | Summary!H10 | 1.3597572332361343 | 1.359757233236134 |
| ok | Summary!I10 | — | — |
| ok | Summary!F10 | 1.3752942515968747 | 1.3752942515968747 |
| ok | Summary!G10 | — | — |
| ok | Summary!C10 | 1.0086456886494444 | 1.008645688649444 |
| ok | Summary!D10 | — | — |
| ok | Summary!H11 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Summary!I11 | — | — |
| ok | Summary!F11 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Summary!G11 | — | — |
| ok | Summary!C11 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Summary!D11 | — | — |
| ok | Summary!H12 | 2.810916225966142 | 2.810916225966142 |
| ok | Summary!I12 | — | — |
| ok | Summary!F12 | 2.7167019777414856 | 2.7167019777414856 |
| ok | Summary!G12 | — | — |
| ok | Summary!C12 | 2.6198238917146655 | 2.619823891714665 |
| ok | Summary!D12 | — | — |
| ok | Summary!H13 | 1.441038622360229 | 1.441038622360229 |
| ok | Summary!I13 | — | — |
| ok | Summary!F13 | 1.3825111539309054 | 1.3825111539309054 |
| ok | Summary!G13 | — | — |
| ok | Summary!C13 | 1.699458983432784 | 1.699458983432784 |
| ok | Summary!D13 | — | — |
| ok | Summary!H19 | 0.0034023275592908768 | 0.003402327559290877 |
| ok | Summary!I19 | — | — |
| ok | Summary!F19 | -0.0024265883136588345 | -0.0024265883136588345 |
| ok | Summary!G19 | — | — |
| ok | Summary!C19 | -0.014683811346124514 | -0.01468381134612451 |
| ok | Summary!D19 | — | — |
| ok | Summary!H20 | 0.01680541154576976 | 0.01680541154576976 |
| ok | Summary!I20 | — | — |
| ok | Summary!F20 | 0.014506762667246017 | 0.014506762667246017 |
| ok | Summary!G20 | — | — |
| ok | Summary!C20 | 0.00901829163851567 | 0.00901829163851567 |
| ok | Summary!D20 | — | — |
| ok | Summary!H21 | 0.6021167144740369 | 0.6021167144740369 |
| ok | Summary!I21 | — | — |
| ok | Summary!F21 | 0.5950344128542266 | 0.5950344128542266 |
| ok | Summary!G21 | — | — |
| ok | Summary!C21 | 0.11323781597973155 | 0.1132378159797316 |
| ok | Summary!D21 | — | — |
| ok | Summary!H22 | 0.7090160674676405 | 0.7090160674676405 |
| ok | Summary!I22 | — | — |
| ok | Summary!F22 | 0.701161908282818 | 0.701161908282818 |
| ok | Summary!G22 | — | — |
| ok | Summary!C22 | 0.07287173365206458 | 0.07287173365206458 |
| ok | Summary!D22 | — | — |
| ok | Summary!H23 | 0.6896266904344225 | 0.6896266904344225 |
| ok | Summary!I23 | — | — |
| ok | Summary!F23 | 0.799356429758733 | 0.799356429758733 |
| ok | Summary!G23 | — | — |
| ok | Summary!C23 | 0.5848928248693543 | 0.5848928248693543 |
| ok | Summary!D23 | — | — |
| ok | Summary!H24 | 2.0007594723761 | 2.0007594723761 |
| ok | Summary!I24 | — | — |
| ok | Summary!F24 | 2.0955527508957776 | 2.0955527508957776 |
| ok | Summary!G24 | — | — |
| ok | Summary!C24 | 0.7710023745011505 | 0.7710023745011505 |
| ok | Summary!D24 | — | — |
| ok | Summary!H25 | 1.398642757902063 | 1.398642757902063 |
| ok | Summary!I25 | — | — |
| ok | Summary!F25 | 1.500518338041551 | 1.500518338041551 |
| ok | Summary!G25 | — | — |
| ok | Summary!C25 | 0.6577645585214189 | 0.6577645585214189 |
| ok | Summary!D25 | — | — |
| ok | Summary!H27 | -0.019378006304722882 | -0.01937800630472288 |
| ok | Summary!I27 | — | — |
| ok | Summary!F27 | -0.06631193529668558 | -0.06631193529668558 |
| ok | Summary!G27 | — | — |
| ok | Summary!C27 | 0.03257808684852553 | 0.03257808684852553 |
| ok | Summary!D27 | — | — |
| ok | Summary!H28 | 0.08750898529165822 | 0.08750898529165822 |
| ok | Summary!I28 | — | — |
| ok | Summary!F28 | 0.10262904527785062 | 0.10262904527785062 |
| ok | Summary!G28 | — | — |
| ok | Summary!C28 | 0.07719012006354721 | 0.07719012006354721 |
| ok | Summary!D28 | — | — |
| ok | Summary!H29 | 0.5204319093538794 | 0.5204319093538794 |
| ok | Summary!I29 | — | — |
| ok | Summary!F29 | 0.5326480276667482 | 0.5326480276667482 |
| ok | Summary!G29 | — | — |
| ok | Summary!C29 | 0.5338326102465549 | 0.5338326102465549 |
| ok | Summary!D29 | — | — |
| ok | Summary!H30 | 0.05413210722089782 | 0.05413210722089782 |
| ok | Summary!I30 | — | — |
| ok | Summary!F30 | 0.04595209206224703 | 0.04595209206224703 |
| ok | Summary!G30 | — | — |
| ok | Summary!C30 | 0.07072710329502283 | 0.07072710329502283 |
| ok | Summary!D30 | — | — |
| ok | Summary!H31 | 1.451503633202392 | 1.451503633202392 |
| ok | Summary!I31 | — | — |
| ok | Summary!F31 | 2.2209814576008475 | 2.2209814576008475 |
| ok | Summary!G31 | — | — |
| ok | Summary!C31 | 1.8537532811982647 | 1.853753281198265 |
| ok | Summary!D31 | — | — |
| ok | Summary!H32 | 2.0260676497771692 | 2.026067649777169 |
| ok | Summary!I32 | — | — |
| ok | Summary!F32 | 2.799581577329843 | 2.799581577329843 |
| ok | Summary!G32 | — | — |
| ok | Summary!C32 | 2.4583129947398423 | 2.458312994739842 |
| ok | Summary!D32 | — | — |
| ok | Summary!H33 | 1.5056357404232898 | 1.50563574042329 |
| ok | Summary!I33 | — | — |
| ok | Summary!F33 | 2.2669335496630945 | 2.2669335496630945 |
| ok | Summary!G33 | — | — |
| ok | Summary!C33 | 1.9244803844932874 | 1.924480384493287 |
| ok | Summary!D33 | — | — |
| ok | Summary!Q7 | 1.6138446897622272 | 1.613844689762227 |
| ok | Summary!R7 | — | — |
| ok | Summary!O7 | 1.550392085338516 | 1.550392085338516 |
| ok | Summary!P7 | — | — |
| ok | Summary!L7 | 1.05873659463189 | 1.05873659463189 |
| ok | Summary!M7 | — | — |
| ok | Summary!Q8 | 2.0372465877364028 | 2.037246587736403 |
| ok | Summary!R8 | — | — |
| ok | Summary!O8 | 2.0194451522005985 | 2.0194451522005985 |
| ok | Summary!P8 | — | — |
| ok | Summary!L8 | 1.269580994403605 | 1.269580994403605 |
| ok | Summary!M8 | — | — |
| ok | Summary!Q9 | 0.9530633219641633 | 0.9530633219641633 |
| ok | Summary!R9 | — | — |
| ok | Summary!O9 | 0.951295071676428 | 0.951295071676428 |
| ok | Summary!P9 | — | — |
| ok | Summary!L9 | 0.6203355401492896 | 0.6203355401492896 |
| ok | Summary!M9 | — | — |
| ok | Summary!Q10 | 0.18427413737016327 | 0.1842741373701633 |
| ok | Summary!R10 | — | — |
| ok | Summary!O10 | 0.14276586877115047 | 0.14276586877115047 |
| ok | Summary!P10 | — | — |
| ok | Summary!L10 | 0.47005694520492464 | 0.4700569452049246 |
| ok | Summary!M10 | — | — |
| ok | Summary!Q11 | 0.23128678890546345 | 0.2312867889054634 |
| ok | Summary!R11 | — | — |
| ok | Summary!O11 | 0.2631254521014802 | 0.2631254521014802 |
| ok | Summary!P11 | — | — |
| ok | Summary!L11 | 0.10472064090822332 | 0.1047206409082233 |
| ok | Summary!M11 | — | — |
| ok | Summary!Q12 | 1.3686242482397901 | 1.36862424823979 |
| ok | Summary!R12 | — | — |
| ok | Summary!O12 | 1.3571863925490586 | 1.3571863925490586 |
| ok | Summary!P12 | — | — |
| ok | Summary!L12 | 1.1951131262624375 | 1.195113126262437 |
| ok | Summary!M12 | — | — |
| ok | Summary!Q13 | 0.41556092627562674 | 0.4155609262756267 |
| ok | Summary!R13 | — | — |
| ok | Summary!O13 | 0.4058913208726307 | 0.4058913208726307 |
| ok | Summary!P13 | — | — |
| ok | Summary!L13 | 0.574777586113148 | 0.574777586113148 |
| ok | Summary!M13 | — | — |
| ok | Summary!Q18 | 0.9878539701554716 | 0.9878539701554716 |
| ok | Summary!R18 | — | — |
| ok | Summary!O18 | 0.8774784779654787 | 0.8774784779654787 |
| ok | Summary!P18 | — | — |
| ok | Summary!L18 | 0.09593421653723161 | 0.09593421653723161 |
| ok | Summary!M18 | — | — |
| ok | Summary!Q19 | 1.7254849919194866 | 1.725484991919487 |
| ok | Summary!R19 | — | — |
| ok | Summary!O19 | 1.5906160217009966 | 1.5906160217009966 |
| ok | Summary!P19 | — | — |
| ok | Summary!L19 | 0.7781330896908787 | 0.7781330896908787 |
| ok | Summary!M19 | — | — |
| ok | Summary!Q20 | 2.1170273837661813 | 2.117027383766181 |
| ok | Summary!R20 | — | — |
| ok | Summary!O20 | 1.9632802207272166 | 1.9632802207272166 |
| ok | Summary!P20 | — | — |
| ok | Summary!L20 | 0.4854368932038835 | 0.4854368932038835 |
| ok | Summary!M20 | — | — |
| ok | Summary!Q21 | 0.017704651456628466 | 0.01770465145662847 |
| ok | Summary!R21 | — | — |
| ok | Summary!O21 | 0.022395815868242422 | 0.022395815868242422 |
| ok | Summary!P21 | — | — |
| ok | Summary!L21 | 0.0369703594161898 | 0.0369703594161898 |
| ok | Summary!M21 | — | — |
| ok | Summary!Q22 | 0.6418505967481973 | 0.6418505967481973 |
| ok | Summary!R22 | — | — |
| ok | Summary!O22 | 0.5060268781190284 | 0.5060268781190284 |
| ok | Summary!P22 | — | — |
| ok | Summary!L22 | 0.5963479714524529 | 0.5963479714524529 |
| ok | Summary!M22 | — | — |
| ok | Summary!Q23 | 2.776582631971007 | 2.776582631971007 |
| ok | Summary!R23 | — | — |
| ok | Summary!O23 | 2.4917029147144873 | 2.4917029147144873 |
| ok | Summary!P23 | — | — |
| ok | Summary!L23 | 1.1187552240725263 | 1.118755224072526 |
| ok | Summary!M23 | — | — |
| ok | Summary!Q24 | 0.6595552482048258 | 0.6595552482048258 |
| ok | Summary!R24 | — | — |
| ok | Summary!O24 | 0.5284226939872708 | 0.5284226939872708 |
| ok | Summary!P24 | — | — |
| ok | Summary!L24 | 0.6333183308686428 | 0.6333183308686428 |
| ok | Summary!M24 | — | — |
| ok | Summary!Q26 | 1.174029706845404 | 1.174029706845404 |
| ok | Summary!R26 | — | — |
| ok | Summary!O26 | 1.4008357178877437 | 1.4008357178877437 |
| ok | Summary!P26 | — | — |
| ok | Summary!L26 | 0.27753507018220386 | 0.2775350701822039 |
| ok | Summary!M26 | — | — |
| ok | Summary!Q27 | 1.5790107692017183 | 1.579010769201718 |
| ok | Summary!R27 | — | — |
| ok | Summary!O27 | 1.8900182585795187 | 1.8900182585795187 |
| ok | Summary!P27 | — | — |
| ok | Summary!L27 | 0.3596378648739932 | 0.3596378648739932 |
| ok | Summary!M27 | — | — |
| ok | Summary!Q28 | 0.9714323513479108 | 0.9714323513479108 |
| ok | Summary!R28 | — | — |
| ok | Summary!O28 | 1.0024414376176916 | 1.0024414376176916 |
| ok | Summary!P28 | — | — |
| ok | Summary!L28 | 0.26060423415177053 | 0.2606042341517705 |
| ok | Summary!M28 | — | — |
| ok | Summary!Q29 | 0.7101545779643433 | 0.7101545779643433 |
| ok | Summary!R29 | — | — |
| ok | Summary!O29 | 0.7677750430897722 | 0.7677750430897722 |
| ok | Summary!P29 | — | — |
| ok | Summary!L29 | 0.1637746480448366 | 0.1637746480448366 |
| ok | Summary!M29 | — | — |
| ok | Summary!Q30 | 0.5541971976675089 | 0.5541971976675089 |
| ok | Summary!R30 | — | — |
| ok | Summary!O30 | 0.567416311135301 | 0.567416311135301 |
| ok | Summary!P30 | — | — |
| ok | Summary!L30 | 0.6425414312961244 | 0.6425414312961244 |
| ok | Summary!M30 | — | — |
| ok | Summary!Q31 | 2.235784126979763 | 2.235784126979763 |
| ok | Summary!R31 | — | — |
| ok | Summary!O31 | 2.337632791842765 | 2.337632791842765 |
| ok | Summary!P31 | — | — |
| ok | Summary!L31 | 1.0669203134927314 | 1.066920313492731 |
| ok | Summary!M31 | — | — |
| ok | Summary!Q32 | 1.2643517756318523 | 1.264351775631852 |
| ok | Summary!R32 | — | — |
| ok | Summary!O32 | 1.335191354225073 | 1.335191354225073 |
| ok | Summary!P32 | — | — |
| ok | Summary!L32 | 0.806316079340961 | 0.806316079340961 |
| ok | Summary!M32 | — | — |
| ok | Summary!Q34 | 3.4607863533841217 | 3.460786353384122 |
| ok | Summary!R34 | — | — |
| ok | Summary!O34 | 3.6246728510966824 | 3.6246728510966824 |
| ok | Summary!P34 | — | — |
| ok | Summary!L34 | 1.5044521270246505 | 1.50445212702465 |
| ok | Summary!M34 | — | — |
| ok | Summary!Q35 | 4.471042669628076 | 4.471042669628076 |
| ok | Summary!R35 | — | — |
| ok | Summary!O35 | 4.704928599551942 | 4.704928599551942 |
| ok | Summary!P35 | — | — |
| ok | Summary!L35 | 1.8181981397616722 | 1.818198139761672 |
| ok | Summary!M35 | — | — |
| ok | Summary!Q36 | 1.2743910279761643 | 1.274391027976164 |
| ok | Summary!R36 | — | — |
| ok | Summary!O36 | 1.2817532720019105 | 1.2817532720019105 |
| ok | Summary!P36 | — | — |
| ok | Summary!L36 | 0.6718595186986783 | 0.6718595186986783 |
| ok | Summary!M36 | — | — |
| ok | Summary!Q37 | 1.090469782017345 | 1.090469782017345 |
| ok | Summary!R37 | — | — |
| ok | Summary!O37 | 1.2064995586031646 | 1.2064995586031646 |
| ok | Summary!P37 | — | — |
| ok | Summary!L37 | 0.5625486737210279 | 0.5625486737210279 |
| ok | Summary!M37 | — | — |
| ok | Summary!Q38 | 0.11564561938673575 | 0.1156456193867357 |
| ok | Summary!R38 | — | — |
| ok | Summary!O38 | 0.04226356389117069 | 0.04226356389117069 |
| ok | Summary!P38 | — | — |
| ok | Summary!L38 | 0.20537020569639608 | 0.2053702056963961 |
| ok | Summary!M38 | — | — |
| ok | Summary!Q39 | 2.4805064293802452 | 2.480506429380245 |
| ok | Summary!R39 | — | — |
| ok | Summary!O39 | 2.530516394496246 | 2.530516394496246 |
| ok | Summary!P39 | — | — |
| ok | Summary!L39 | 1.4397783981161023 | 1.439778398116102 |
| ok | Summary!M39 | — | — |
| ok | Summary!Q40 | 1.206115401404081 | 1.206115401404081 |
| ok | Summary!R40 | — | — |
| ok | Summary!O40 | 1.2487631224943354 | 1.2487631224943354 |
| ok | Summary!P40 | — | — |
| ok | Summary!L40 | 0.767918879417424 | 0.767918879417424 |
| ok | Summary!M40 | — | — |
| ok | Summary!H14 | 86.75395050652514 | 86.75395050652514 |
| ok | Summary!I14 | — | — |
| ok | Summary!F14 | 87.93662718269165 | 87.93662718269165 |
| ok | Summary!G14 | — | — |
| ok | Summary!C14 | 80.46011871917379 | 80.46011871917379 |
| ok | Summary!D14 | — | — |
| ok | Summary!C15 | -7.47650846351786 | -7.47650846351786 |
| ok | Summary!D15 | — | — |
| ok | Summary!C16 | -6.293831787351351 | -6.293831787351351 |
| ok | Summary!D16 | — | — |
| ok | Summary!Q14 | 75.39444814591982 | 75.39444814591982 |
| ok | Summary!R14 | — | — |
| ok | Summary!O14 | 78.30700461494897 | 78.30700461494897 |
| ok | Summary!P14 | — | — |
| ok | Summary!L14 | 60.69541942774161 | 60.69541942774161 |
| ok | Summary!M14 | — | — |
| ok | Summary!L15 | -17.611585187207353 | -17.61158518720735 |
| ok | Summary!M15 | — | — |
| ok | Summary!L16 | -14.699028718178212 | -14.69902871817821 |
| ok | Summary!M16 | — | — |
| ok | Lines by source!E5 | 3.7767880822325957 | 3.776788082232596 |
| ok | Lines by source!F5 | 0.7956862425886584 | 0.7956862425886584 |
| ok | Lines by source!G5 | 10.327957313003356 | 10.32795731300336 |
| ok | Lines by source!L5 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M5 | 4.009514461690263 | 4.009514461690263 |
| ok | Lines by source!H5 | 2.9811018396439373 | 2.9811018396439377 |
| ok | Lines by source!I5 | 3.3789449609382665 | 3.378944960938267 |
| ok | Lines by source!J5 | 4.174631203526925 | 4.174631203526925 |
| ok | Lines by source!K5 | 6.100245336897119 | 6.100245336897121 |
| ok | Lines by source!Q5 | 3 | 3 |
| ok | Lines by source!R5 | Moderate | Moderate |
| ok | Lines by source!S5 |  |  |
| ok | Lines by source!E6 | 3.6309091634405473 | 3.6309091634405473 |
| ok | Lines by source!F6 | 1.0331756339975655 | 1.0331756339975655 |
| ok | Lines by source!G6 | 10.346442383612649 | 10.346442383612649 |
| ok | Lines by source!L6 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M6 | 3.9545852353018254 | 3.9545852353018254 |
| ok | Lines by source!H6 | 2.5977335294429817 | 2.5977335294429817 |
| ok | Lines by source!I6 | 3.1143213464417645 | 3.1143213464417645 |
| ok | Lines by source!J6 | 4.14749698043933 | 4.14749698043933 |
| ok | Lines by source!K6 | 6.033257977157906 | 6.033257977157906 |
| ok | Lines by source!Q6 | 3 | 3 |
| ok | Lines by source!R6 | Moderate | Moderate |
| ok | Lines by source!S6 |  |  |
| ok | Lines by source!E7 | 3.4107661467352233 | 3.410766146735223 |
| ok | Lines by source!F7 | 0.5615126969292105 | 0.5615126969292091 |
| ok | Lines by source!G7 | 4.486652330490333 | 4.486652330490333 |
| ok | Lines by source!L7 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M7 | 3.7557700716206863 | 3.755770071620686 |
| ok | Lines by source!Q7 |  |  |
| ok | Lines by source!S7 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E8 | 4.593159067379571 | 4.593159067379571 |
| ok | Lines by source!F8 | 0.8750888292064387 | 0.8750888292064387 |
| ok | Lines by source!G8 | 11.261249252680265 | 11.26124925268027 |
| ok | Lines by source!L8 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M8 | 5.194125778490533 | 5.194125778490533 |
| ok | Lines by source!H8 | 3.7180702381731328 | 3.7180702381731328 |
| ok | Lines by source!I8 | 4.155614652776352 | 4.155614652776352 |
| ok | Lines by source!J8 | 5.0307034819827905 | 5.0307034819827905 |
| ok | Lines by source!K8 | 7.266197756583032 | 7.266197756583034 |
| ok | Lines by source!Q8 | 4 | 4 |
| ok | Lines by source!R8 | Moderate-High | Moderate-High |
| ok | Lines by source!S8 |  |  |
| ok | Lines by source!E9 | 4.41930755656581 | 4.41930755656581 |
| ok | Lines by source!F9 | 1.0050934045734172 | 1.0050934045734172 |
| ok | Lines by source!G9 | 11.08204255884491 | 11.08204255884491 |
| ok | Lines by source!L9 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M9 | 5.1312227443145 | 5.1312227443145 |
| ok | Lines by source!H9 | 3.414214151992393 | 3.414214151992393 |
| ok | Lines by source!I9 | 3.9167608542791017 | 3.9167608542791017 |
| ok | Lines by source!J9 | 4.921854258852519 | 4.921854258852519 |
| ok | Lines by source!K9 | 7.161789747985985 | 7.161789747985985 |
| ok | Lines by source!Q9 | 4 | 4 |
| ok | Lines by source!R9 | Moderate-High | Moderate-High |
| ok | Lines by source!S9 |  |  |
| ok | Lines by source!E10 | 4.008313217289569 | 4.008313217289569 |
| ok | Lines by source!F10 | 0.44751121698069046 | 0.4475112169806898 |
| ok | Lines by source!G10 | 5.143682200037591 | 5.143682200037591 |
| ok | Lines by source!L10 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M10 | 4.5892741608892 | 4.5892741608892 |
| ok | Lines by source!H10 | 3.5608020003088785 | 3.560802000308879 |
| ok | Lines by source!I10 | 3.7845576087992234 | 3.784557608799224 |
| ok | Lines by source!J10 | 4.232068825779914 | 4.232068825779914 |
| ok | Lines by source!K10 | 4.897131237906283 | 4.897131237906283 |
| ok | Lines by source!Q10 | 4 | 4 |
| ok | Lines by source!R10 | Moderate-High | Moderate-High |
| ok | Lines by source!S10 |  |  |
| ok | Lines by source!E11 | 1.385284901363474 | 1.3852849013634736 |
| ok | Lines by source!F11 | 0.22291392479165073 | 0.2229139247916504 |
| ok | Lines by source!G11 | 3.0814595865124894 | 3.081459586512489 |
| ok | Lines by source!L11 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M11 | 1.369877603605913 | 1.369877603605913 |
| ok | Lines by source!H11 | 1.1623709765718233 | 1.162370976571823 |
| ok | Lines by source!I11 | 1.2738279389676488 | 1.2738279389676483 |
| ok | Lines by source!J11 | 1.4967418637592993 | 1.4967418637592989 |
| ok | Lines by source!K11 | 2.2440524152342256 | 2.2440524152342225 |
| ok | Lines by source!Q11 | 3 | 3 |
| ok | Lines by source!R11 | Moderate | Moderate |
| ok | Lines by source!S11 |  |  |
| ok | Lines by source!E12 | 1.361585946989873 | 1.361585946989873 |
| ok | Lines by source!F12 | 0.2480271403972293 | 0.2480271403972293 |
| ok | Lines by source!G12 | 3.2686089856800993 | 3.2686089856800993 |
| ok | Lines by source!L12 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M12 | 1.3341908238105804 | 1.3341908238105804 |
| ok | Lines by source!H12 | 1.1135588065926436 | 1.1135588065926436 |
| ok | Lines by source!I12 | 1.2375723767912583 | 1.2375723767912583 |
| ok | Lines by source!J12 | 1.4855995171884877 | 1.4855995171884877 |
| ok | Lines by source!K12 | 2.4716156860351397 | 2.4716156860351397 |
| ok | Lines by source!Q12 | 3 | 3 |
| ok | Lines by source!R12 | Moderate | Moderate |
| ok | Lines by source!S12 |  |  |
| ok | Lines by source!E13 | 1.0469513315336536 | 1.0469513315336536 |
| ok | Lines by source!F13 | 0.18828267725868064 | 0.18828267725867998 |
| ok | Lines by source!G13 | 2.264562901677295 | 2.264562901677295 |
| ok | Lines by source!L13 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M13 | 0.9203649082818812 | 0.9203649082818812 |
| ok | Lines by source!H13 | 0.858668654274973 | 0.8586686542749736 |
| ok | Lines by source!I13 | 0.9528099929043132 | 0.9528099929043137 |
| ok | Lines by source!J13 | 1.141092670162994 | 1.1410926701629935 |
| ok | Lines by source!K13 | 1.511710475952499 | 1.511710475952499 |
| ok | Lines by source!Q13 | 2 | 2 |
| ok | Lines by source!R13 | Moderate-Low | Moderate-Low |
| ok | Lines by source!S13 |  |  |
| ok | Lines by source!E14 | 1.2826137486632863 | 1.2826137486632865 |
| ok | Lines by source!F14 | 0.21062611857384203 | 0.2106261185738425 |
| ok | Lines by source!G14 | 2.9460450659113744 | 2.946045065911374 |
| ok | Lines by source!L14 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M14 | 1.3597572332361343 | 1.359757233236134 |
| ok | Lines by source!H14 | 1.0719876300894442 | 1.071987630089444 |
| ok | Lines by source!I14 | 1.1773006893763653 | 1.1773006893763651 |
| ok | Lines by source!J14 | 1.3879268079502072 | 1.3879268079502078 |
| ok | Lines by source!K14 | 2.3260492961418144 | 2.326049296141816 |
| ok | Lines by source!Q14 | 3 | 3 |
| ok | Lines by source!R14 | Moderate | Moderate |
| ok | Lines by source!S14 |  |  |
| ok | Lines by source!E15 | 1.2643618319521448 | 1.2643618319521448 |
| ok | Lines by source!F15 | 0.19524869873385414 | 0.19524869873385414 |
| ok | Lines by source!G15 | 2.9200379551697373 | 2.9200379551697373 |
| ok | Lines by source!L15 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M15 | 1.3752942515968747 | 1.3752942515968747 |
| ok | Lines by source!H15 | 1.0691131332182906 | 1.0691131332182906 |
| ok | Lines by source!I15 | 1.1667374825852177 | 1.1667374825852177 |
| ok | Lines by source!J15 | 1.361986181319072 | 1.361986181319072 |
| ok | Lines by source!K15 | 2.206324717929771 | 2.206324717929771 |
| ok | Lines by source!Q15 | 4 | 4 |
| ok | Lines by source!R15 | Moderate-High | Moderate-High |
| ok | Lines by source!S15 |  |  |
| ok | Lines by source!E16 | 0.9886897630256543 | 0.9886897630256543 |
| ok | Lines by source!F16 | 0.19448805945055525 | 0.19448805945055525 |
| ok | Lines by source!G16 | 2.08371240069629 | 2.08371240069629 |
| ok | Lines by source!L16 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M16 | 1.0086456886494444 | 1.008645688649444 |
| ok | Lines by source!H16 | 0.794201703575099 | 0.794201703575099 |
| ok | Lines by source!I16 | 0.8914457333003767 | 0.8914457333003767 |
| ok | Lines by source!J16 | 1.0859337927509318 | 1.0859337927509318 |
| ok | Lines by source!K16 | 1.476852232230776 | 1.4768522322307756 |
| ok | Lines by source!Q16 | 3 | 3 |
| ok | Lines by source!R16 | Moderate | Moderate |
| ok | Lines by source!S16 |  |  |
| ok | Lines by source!E17 | 0.12675353873803286 | 0.12675353873803286 |
| ok | Lines by source!F17 | 0.030281139300914434 | 0.030281139300914372 |
| ok | Lines by source!G17 | 0.6498546849136658 | 0.6498546849136658 |
| ok | Lines by source!L17 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M17 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Lines by source!H17 | 0.09647239943711843 | 0.09647239943711848 |
| ok | Lines by source!I17 | 0.11161296908757563 | 0.11161296908757568 |
| ok | Lines by source!J17 | 0.14189410838849006 | 0.14189410838849004 |
| ok | Lines by source!K17 | 0.26956719550232344 | 0.26956719550232344 |
| ok | Lines by source!Q17 | 1 | 1 |
| ok | Lines by source!R17 | Low | Low |
| ok | Lines by source!S17 |  |  |
| ok | Lines by source!E18 | 0.03869371824098213 | 0.03869371824098213 |
| ok | Lines by source!F18 | 0.016309807391292293 | 0.016309807391292293 |
| ok | Lines by source!G18 | 1.1988194225041855 | 1.1988194225041855 |
| ok | Lines by source!L18 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M18 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Lines by source!H18 | 0.02238391084968984 | 0.02238391084968984 |
| ok | Lines by source!I18 | 0.030538814545335986 | 0.030538814545335986 |
| ok | Lines by source!J18 | 0.04684862193662828 | 0.04684862193662828 |
| ok | Lines by source!K18 | 0.14753123968182763 | 0.14753123968182763 |
| ok | Lines by source!Q18 | 1 | 1 |
| ok | Lines by source!R18 | Low | Low |
| ok | Lines by source!S18 |  |  |
| ok | Lines by source!E19 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Lines by source!F19 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Lines by source!G19 | 1.8086714674791118 | 1.808671467479112 |
| ok | Lines by source!L19 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!H19 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Lines by source!I19 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Lines by source!J19 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Lines by source!K19 | 0.6295871211811148 | 0.629587121181115 |
| ok | Lines by source!Q19 | 5 | 5 |
| ok | Lines by source!R19 | High | High |
| ok | Lines by source!S19 |  |  |
| ok | Lines by source!E20 | 2.8083865946403943 | 2.8083865946403943 |
| ok | Lines by source!F20 | 0.4583327051330208 | 0.45833270513302055 |
| ok | Lines by source!G20 | 6.474157942218599 | 6.474157942218599 |
| ok | Lines by source!L20 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M20 | 2.810916225966142 | 2.810916225966142 |
| ok | Lines by source!H20 | 2.3500538895073735 | 2.350053889507374 |
| ok | Lines by source!I20 | 2.579220242073884 | 2.579220242073884 |
| ok | Lines by source!J20 | 3.0375529472069047 | 3.0375529472069047 |
| ok | Lines by source!K20 | 4.768327261863595 | 4.768327261863595 |
| ok | Lines by source!Q20 | 3 | 3 |
| ok | Lines by source!R20 | Moderate | Moderate |
| ok | Lines by source!S20 |  |  |
| ok | Lines by source!E21 | 2.6882025856762084 | 2.6882025856762084 |
| ok | Lines by source!F21 | 0.48981283003768394 | 0.48981283003768394 |
| ok | Lines by source!G21 | 7.215140763440455 | 7.215140763440455 |
| ok | Lines by source!L21 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M21 | 2.7167019777414856 | 2.7167019777414856 |
| ok | Lines by source!H21 | 2.1983897556385243 | 2.1983897556385243 |
| ok | Lines by source!I21 | 2.4432961706573666 | 2.4432961706573666 |
| ok | Lines by source!J21 | 2.93310900069505 | 2.93310900069505 |
| ok | Lines by source!K21 | 4.790886629332917 | 4.790886629332917 |
| ok | Lines by source!Q21 | 3 | 3 |
| ok | Lines by source!R21 | Moderate | Moderate |
| ok | Lines by source!S21 |  |  |
| ok | Lines by source!E22 | 2.400766265498698 | 2.400766265498698 |
| ok | Lines by source!F22 | 0.3677237461945026 | 0.3677237461945031 |
| ok | Lines by source!G22 | 3.796929733446994 | 3.796929733446994 |
| ok | Lines by source!L22 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M22 | 2.6198238917146655 | 2.619823891714665 |
| ok | Lines by source!H22 | 2.0330425193041957 | 2.033042519304195 |
| ok | Lines by source!I22 | 2.216904392401447 | 2.2169043924014464 |
| ok | Lines by source!J22 | 2.5846281385959493 | 2.5846281385959498 |
| ok | Lines by source!K22 | 3.75435702562653 | 3.75435702562653 |
| ok | Lines by source!Q22 | 4 | 4 |
| ok | Lines by source!R22 | Moderate-High | Moderate-High |
| ok | Lines by source!S22 |  |  |
| ok | Lines by source!E23 | 1.4241101454772385 | 1.4241101454772385 |
| ok | Lines by source!F23 | 0.30863110581891345 | 0.3086311058189138 |
| ok | Lines by source!G23 | 3.5579503382053876 | 3.557950338205388 |
| ok | Lines by source!L23 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M23 | 1.441038622360229 | 1.441038622360229 |
| ok | Lines by source!H23 | 1.115479039658325 | 1.1154790396583247 |
| ok | Lines by source!I23 | 1.2697945925677818 | 1.2697945925677816 |
| ok | Lines by source!J23 | 1.578425698386695 | 1.5784256983866953 |
| ok | Lines by source!K23 | 2.461666717375178 | 2.461666717375178 |
| ok | Lines by source!Q23 | 3 | 3 |
| ok | Lines by source!R23 | Moderate | Moderate |
| ok | Lines by source!S23 |  |  |
| ok | Lines by source!E24 | 1.3422365424202862 | 1.3422365424202862 |
| ok | Lines by source!F24 | 0.2621007314463733 | 0.2621007314463733 |
| ok | Lines by source!G24 | 4.117719220352539 | 4.117719220352539 |
| ok | Lines by source!L24 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M24 | 1.3825111539309054 | 1.3825111539309054 |
| ok | Lines by source!H24 | 1.080135810973913 | 1.080135810973913 |
| ok | Lines by source!I24 | 1.2111861766970995 | 1.2111861766970995 |
| ok | Lines by source!J24 | 1.473286908143473 | 1.473286908143473 |
| ok | Lines by source!K24 | 2.4430957218082887 | 2.4430957218082887 |
| ok | Lines by source!Q24 | 3 | 3 |
| ok | Lines by source!R24 | Moderate | Moderate |
| ok | Lines by source!S24 |  |  |
| ok | Lines by source!E25 | 1.2641764984401482 | 1.2641764984401487 |
| ok | Lines by source!F25 | 0.22485002443556373 | 0.22485002443556357 |
| ok | Lines by source!G25 | 2.214374234403318 | 2.214374234403318 |
| ok | Lines by source!L25 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M25 | 1.699458983432784 | 1.699458983432784 |
| ok | Lines by source!H25 | 1.0393264740045844 | 1.039326474004585 |
| ok | Lines by source!I25 | 1.1517514862223663 | 1.1517514862223668 |
| ok | Lines by source!J25 | 1.3766015106579301 | 1.3766015106579306 |
| ok | Lines by source!K25 | 1.9984688427507002 | 1.9984688427507031 |
| ok | Lines by source!Q25 | 4 | 4 |
| ok | Lines by source!R25 | Moderate-High | Moderate-High |
| ok | Lines by source!S25 |  |  |
| ok | Lines by source!E26 | 0.05926778269446801 | 0.05926778269446801 |
| ok | Lines by source!F26 | 0.05937714243884957 | 0.05937714243884953 |
| ok | Lines by source!G26 | 1.5285126504018145 | 1.528512650401814 |
| ok | Lines by source!L26 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M26 | 0.0034023275592908768 | 0.003402327559290877 |
| ok | Lines by source!Q26 |  |  |
| ok | Lines by source!S26 | Refused: Moderate-Low would begin at or below zero | Refused: Moderate-Low would begin at or below zero |
| ok | Lines by source!E27 | 0.05769147832318315 | 0.05769147832318315 |
| ok | Lines by source!F27 | 0.05080303494815244 | 0.05080303494815244 |
| ok | Lines by source!G27 | 1.8226688527762305 | 1.8226688527762305 |
| ok | Lines by source!L27 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M27 | -0.0024265883136588345 | -0.0024265883136588345 |
| ok | Lines by source!H27 | 0.006888443375030709 | 0.006888443375030709 |
| ok | Lines by source!I27 | 0.03228996084910693 | 0.03228996084910693 |
| ok | Lines by source!J27 | 0.08309299579725937 | 0.08309299579725937 |
| ok | Lines by source!K27 | 0.31440084395176326 | 0.31440084395176326 |
| ok | Lines by source!Q27 | 1 | 1 |
| ok | Lines by source!R27 | Low | Low |
| ok | Lines by source!S27 |  |  |
| ok | Lines by source!E28 | 0.053909503953416066 | 0.053909503953416066 |
| ok | Lines by source!F28 | 0.05177328770531841 | 0.05177328770531837 |
| ok | Lines by source!G28 | 0.6450995313468453 | 0.6450995313468453 |
| ok | Lines by source!L28 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M28 | -0.014683811346124514 | -0.01468381134612451 |
| ok | Lines by source!H28 | 0.002136216248097657 | 0.0021362162480976984 |
| ok | Lines by source!I28 | 0.02802286010075686 | 0.028022860100756882 |
| ok | Lines by source!J28 | 0.07979614780607527 | 0.07979614780607525 |
| ok | Lines by source!K28 | 0.3032492413573249 | 0.3032492413573249 |
| ok | Lines by source!Q28 | 1 | 1 |
| ok | Lines by source!R28 | Low | Low |
| ok | Lines by source!S28 |  |  |
| ok | Lines by source!E29 | 0.09898171119771204 | 0.09898171119771204 |
| ok | Lines by source!F29 | 0.057635144014341555 | 0.05763514401434156 |
| ok | Lines by source!G29 | 1.5729880669306757 | 1.572988066930676 |
| ok | Lines by source!L29 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M29 | 0.01680541154576976 | 0.01680541154576976 |
| ok | Lines by source!H29 | 0.041346567183370486 | 0.04134656718337048 |
| ok | Lines by source!I29 | 0.07016413919054126 | 0.07016413919054126 |
| ok | Lines by source!J29 | 0.12779928320488282 | 0.12779928320488282 |
| ok | Lines by source!K29 | 0.3961235931966425 | 0.3961235931966425 |
| ok | Lines by source!Q29 | 1 | 1 |
| ok | Lines by source!R29 | Low | Low |
| ok | Lines by source!S29 |  |  |
| ok | Lines by source!E30 | 0.10067437602246657 | 0.10067437602246657 |
| ok | Lines by source!F30 | 0.07408555923561358 | 0.07408555923561358 |
| ok | Lines by source!G30 | 1.8627989100886482 | 1.8627989100886482 |
| ok | Lines by source!L30 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M30 | 0.014506762667246017 | 0.014506762667246017 |
| ok | Lines by source!H30 | 0.026588816786852987 | 0.026588816786852987 |
| ok | Lines by source!I30 | 0.06363159640465978 | 0.06363159640465978 |
| ok | Lines by source!J30 | 0.13771715564027337 | 0.13771715564027337 |
| ok | Lines by source!K30 | 0.401637147442684 | 0.401637147442684 |
| ok | Lines by source!Q30 | 1 | 1 |
| ok | Lines by source!R30 | Low | Low |
| ok | Lines by source!S30 |  |  |
| ok | Lines by source!E31 | 0.10718270085000456 | 0.10718270085000456 |
| ok | Lines by source!F31 | 0.0538142876148655 | 0.05381428761486552 |
| ok | Lines by source!G31 | 0.6902077466281831 | 0.6902077466281831 |
| ok | Lines by source!L31 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M31 | 0.00901829163851567 | 0.00901829163851567 |
| ok | Lines by source!H31 | 0.05336841323513906 | 0.05336841323513904 |
| ok | Lines by source!I31 | 0.0802755570425718 | 0.0802755570425718 |
| ok | Lines by source!J31 | 0.1340898446574373 | 0.1340898446574373 |
| ok | Lines by source!K31 | 0.4629278199955724 | 0.4629278199955724 |
| ok | Lines by source!Q31 | 1 | 1 |
| ok | Lines by source!R31 | Low | Low |
| ok | Lines by source!S31 |  |  |
| ok | Lines by source!E32 | 1.2260333535309855 | 1.226033353530985 |
| ok | Lines by source!F32 | 0.19976502137545216 | 0.1997650213754525 |
| ok | Lines by source!G32 | 3.431030532462312 | 3.431030532462312 |
| ok | Lines by source!L32 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M32 | 0.6021167144740369 | 0.6021167144740369 |
| ok | Lines by source!H32 | 1.0262683321555333 | 1.0262683321555326 |
| ok | Lines by source!I32 | 1.1261508428432594 | 1.1261508428432587 |
| ok | Lines by source!J32 | 1.3259158642187117 | 1.3259158642187114 |
| ok | Lines by source!K32 | 3.348808602450412 | 3.3488086024504113 |
| ok | Lines by source!Q32 | 1 | 1 |
| ok | Lines by source!R32 | Low | Low |
| ok | Lines by source!S32 |  |  |
| ok | Lines by source!E33 | 1.586167224183462 | 1.586167224183462 |
| ok | Lines by source!F33 | 0.2693480146722256 | 0.2693480146722256 |
| ok | Lines by source!G33 | 4.650784621533351 | 4.650784621533351 |
| ok | Lines by source!L33 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M33 | 0.5950344128542266 | 0.5950344128542266 |
| ok | Lines by source!Q33 |  |  |
| ok | Lines by source!S33 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E34 | 0.502268447713562 | 0.502268447713562 |
| ok | Lines by source!F34 | 0.13959801136509545 | 0.1395980113650954 |
| ok | Lines by source!G34 | 2.6280645190272605 | 2.62806451902726 |
| ok | Lines by source!L34 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M34 | 0.11323781597973155 | 0.1132378159797316 |
| ok | Lines by source!H34 | 0.36267043634846663 | 0.36267043634846663 |
| ok | Lines by source!I34 | 0.43246944203101434 | 0.43246944203101434 |
| ok | Lines by source!J34 | 0.5720674533961098 | 0.5720674533961098 |
| ok | Lines by source!K34 | 1.9985482704548616 | 1.9985482704548616 |
| ok | Lines by source!Q34 | 1 | 1 |
| ok | Lines by source!R34 | Low | Low |
| ok | Lines by source!S34 |  |  |
| ok | Lines by source!E35 | 1.334971867039263 | 1.334971867039263 |
| ok | Lines by source!F35 | 0.47340590019800594 | 0.47340590019800527 |
| ok | Lines by source!G35 | 5.7696939909873475 | 5.769693990987347 |
| ok | Lines by source!L35 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M35 | 0.7090160674676405 | 0.7090160674676405 |
| ok | Lines by source!H35 | 0.861565966841257 | 0.8615659668412576 |
| ok | Lines by source!I35 | 1.09826891694026 | 1.0982689169402604 |
| ok | Lines by source!J35 | 1.571674817138266 | 1.5716748171382655 |
| ok | Lines by source!K35 | 4.330290154596956 | 4.330290154596956 |
| ok | Lines by source!Q35 | 1 | 1 |
| ok | Lines by source!R35 | Low | Low |
| ok | Lines by source!S35 |  |  |
| ok | Lines by source!E36 | 1.7634852859560215 | 1.7634852859560215 |
| ok | Lines by source!F36 | 0.7394856489633126 | 0.7394856489633126 |
| ok | Lines by source!G36 | 10.851519932921951 | 10.851519932921951 |
| ok | Lines by source!L36 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M36 | 0.701161908282818 | 0.701161908282818 |
| ok | Lines by source!H36 | 1.023999636992709 | 1.023999636992709 |
| ok | Lines by source!I36 | 1.3937424614743652 | 1.3937424614743652 |
| ok | Lines by source!J36 | 2.1332281104376776 | 2.1332281104376776 |
| ok | Lines by source!K36 | 6.076269650678316 | 6.076269650678316 |
| ok | Lines by source!Q36 | 1 | 1 |
| ok | Lines by source!R36 | Low | Low |
| ok | Lines by source!S36 |  |  |
| ok | Lines by source!E37 | 0.08473707828833965 | 0.08473707828833965 |
| ok | Lines by source!F37 | 0.056281512834607646 | 0.05628151283460766 |
| ok | Lines by source!G37 | 0.8401436722022826 | 0.8401436722022826 |
| ok | Lines by source!L37 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M37 | 0.07287173365206458 | 0.07287173365206458 |
| ok | Lines by source!H37 | 0.028455565453732005 | 0.02845556545373199 |
| ok | Lines by source!I37 | 0.05659632187103583 | 0.05659632187103582 |
| ok | Lines by source!J37 | 0.11287783470564347 | 0.11287783470564348 |
| ok | Lines by source!K37 | 0.34380420427431163 | 0.34380420427431163 |
| ok | Lines by source!Q37 | 3 | 3 |
| ok | Lines by source!R37 | Moderate | Moderate |
| ok | Lines by source!S37 |  |  |
| ok | Lines by source!E38 | 1.116520389118704 | 1.1165203891187039 |
| ok | Lines by source!F38 | 0.42405206440845394 | 0.42405206440845344 |
| ok | Lines by source!G38 | 5.314995089339884 | 5.314995089339884 |
| ok | Lines by source!L38 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M38 | 0.6896266904344225 | 0.6896266904344225 |
| ok | Lines by source!H38 | 0.6924683247102501 | 0.6924683247102504 |
| ok | Lines by source!I38 | 0.9044943569144771 | 0.9044943569144772 |
| ok | Lines by source!J38 | 1.328546421322931 | 1.3285464213229305 |
| ok | Lines by source!K38 | 2.8595944212736892 | 2.8595944212736883 |
| ok | Lines by source!Q38 | 1 | 1 |
| ok | Lines by source!R38 | Low | Low |
| ok | Lines by source!S38 |  |  |
| ok | Lines by source!E39 | 1.2615157982740963 | 1.2615157982740963 |
| ok | Lines by source!F39 | 0.505980360917241 | 0.505980360917241 |
| ok | Lines by source!G39 | 6.601784134356333 | 6.601784134356333 |
| ok | Lines by source!L39 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M39 | 0.799356429758733 | 0.799356429758733 |
| ok | Lines by source!H39 | 0.7555354373568554 | 0.7555354373568554 |
| ok | Lines by source!I39 | 1.0085256178154758 | 1.0085256178154758 |
| ok | Lines by source!J39 | 1.5145059787327169 | 1.5145059787327169 |
| ok | Lines by source!K39 | 3.2059297379301746 | 3.2059297379301746 |
| ok | Lines by source!Q39 | 2 | 2 |
| ok | Lines by source!R39 | Moderate-Low | Moderate-Low |
| ok | Lines by source!S39 |  |  |
| ok | Lines by source!E40 | 1.5007440239185126 | 1.5007440239185126 |
| ok | Lines by source!F40 | 0.38520698436210393 | 0.38520698436210427 |
| ok | Lines by source!G40 | 3.740519476933407 | 3.740519476933407 |
| ok | Lines by source!L40 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M40 | 0.5848928248693543 | 0.5848928248693543 |
| ok | Lines by source!Q40 |  |  |
| ok | Lines by source!S40 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E41 | 3.7222033146233753 | 3.7222033146233757 |
| ok | Lines by source!F41 | 0.8867555641585243 | 0.8867555641585235 |
| ok | Lines by source!G41 | 13.966274659818525 | 13.96627465981853 |
| ok | Lines by source!L41 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M41 | 2.0007594723761 | 2.0007594723761 |
| ok | Lines by source!H41 | 2.835447750464851 | 2.8354477504648523 |
| ok | Lines by source!I41 | 3.278825532544113 | 3.278825532544114 |
| ok | Lines by source!J41 | 4.165581096702637 | 4.165581096702637 |
| ok | Lines by source!K41 | 10.52987658918464 | 10.529876589184642 |
| ok | Lines by source!Q41 | 1 | 1 |
| ok | Lines by source!R41 | Low | Low |
| ok | Lines by source!S41 |  |  |
| ok | Lines by source!E42 | 4.900570186933169 | 4.900570186933169 |
| ok | Lines by source!F42 | 1.3359968247987575 | 1.3359968247987575 |
| ok | Lines by source!G42 | 21.76565414731995 | 21.76565414731995 |
| ok | Lines by source!L42 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M42 | 2.0955527508957776 | 2.0955527508957776 |
| ok | Lines by source!H42 | 3.564573362134411 | 3.564573362134411 |
| ok | Lines by source!I42 | 4.23257177453379 | 4.23257177453379 |
| ok | Lines by source!J42 | 5.568568599332547 | 5.568568599332547 |
| ok | Lines by source!K42 | 15.288124017780383 | 15.288124017780383 |
| ok | Lines by source!Q42 | 1 | 1 |
| ok | Lines by source!R42 | Low | Low |
| ok | Lines by source!S42 |  |  |
| ok | Lines by source!E43 | 2.3881581999518646 | 2.3881581999518646 |
| ok | Lines by source!F43 | 0.5373878876463191 | 0.5373878876463187 |
| ok | Lines by source!G43 | 6.206914476479203 | 6.206914476479203 |
| ok | Lines by source!L43 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M43 | 0.7710023745011505 | 0.7710023745011505 |
| ok | Lines by source!Q43 |  |  |
| ok | Lines by source!S43 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E44 | 2.5701014344541004 | 2.5701014344541004 |
| ok | Lines by source!F44 | 0.6668479018678135 | 0.6668479018678138 |
| ok | Lines by source!G44 | 10.80911542699601 | 10.80911542699601 |
| ok | Lines by source!L44 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M44 | 1.398642757902063 | 1.398642757902063 |
| ok | Lines by source!H44 | 1.903253532586287 | 1.9032535325862865 |
| ok | Lines by source!I44 | 2.236677483520194 | 2.2366774835201935 |
| ok | Lines by source!J44 | 2.903525385388007 | 2.9035253853880074 |
| ok | Lines by source!K44 | 7.579848393688387 | 7.579848393688387 |
| ok | Lines by source!Q44 | 1 | 1 |
| ok | Lines by source!R44 | Low | Low |
| ok | Lines by source!S44 |  |  |
| ok | Lines by source!E45 | 3.150917070645634 | 3.150917070645634 |
| ok | Lines by source!F45 | 1.3163337498095506 | 1.3163337498095506 |
| ok | Lines by source!G45 | 17.45330406727828 | 17.45330406727828 |
| ok | Lines by source!L45 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M45 | 1.500518338041551 | 1.500518338041551 |
| ok | Lines by source!H45 | 1.8345833208360833 | 1.8345833208360833 |
| ok | Lines by source!I45 | 2.4927501957408587 | 2.4927501957408587 |
| ok | Lines by source!J45 | 3.8090839455504093 | 3.8090839455504093 |
| ok | Lines by source!K45 | 9.63401439041635 | 9.63401439041635 |
| ok | Lines by source!Q45 | 1 | 1 |
| ok | Lines by source!R45 | Low | Low |
| ok | Lines by source!S45 |  |  |
| ok | Lines by source!E46 | 1.7639060110456959 | 1.7639060110456959 |
| ok | Lines by source!F46 | 0.3901239421440688 | 0.39012394214406915 |
| ok | Lines by source!G46 | 4.230713409465992 | 4.230713409465992 |
| ok | Lines by source!L46 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M46 | 0.6577645585214189 | 0.6577645585214189 |
| ok | Lines by source!Q46 |  |  |
| ok | Lines by source!S46 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E47 | 0.21824609110223614 | 0.2182460911022361 |
| ok | Lines by source!F47 | 0.1488386967682739 | 0.1488386967682739 |
| ok | Lines by source!G47 | 3.0906468540423884 | 3.090646854042388 |
| ok | Lines by source!L47 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M47 | -0.019378006304722882 | -0.01937800630472288 |
| ok | Lines by source!H47 | 0.06940739433396223 | 0.0694073943339622 |
| ok | Lines by source!I47 | 0.1438267427180992 | 0.14382674271809914 |
| ok | Lines by source!J47 | 0.2926654394863731 | 0.2926654394863731 |
| ok | Lines by source!K47 | 1.3252576286017723 | 1.3252576286017723 |
| ok | Lines by source!Q47 | 1 | 1 |
| ok | Lines by source!R47 | Low | Low |
| ok | Lines by source!S47 |  |  |
| ok | Lines by source!E48 | 0.2745045861276751 | 0.2745045861276751 |
| ok | Lines by source!F48 | 0.1866739163257934 | 0.1866739163257934 |
| ok | Lines by source!G48 | 3.4581925317375726 | 3.4581925317375726 |
| ok | Lines by source!L48 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M48 | -0.06631193529668558 | -0.06631193529668558 |
| ok | Lines by source!H48 | 0.0878306698018817 | 0.0878306698018817 |
| ok | Lines by source!I48 | 0.1811676279647784 | 0.1811676279647784 |
| ok | Lines by source!J48 | 0.3678415442905718 | 0.3678415442905718 |
| ok | Lines by source!K48 | 1.7227177132768419 | 1.7227177132768419 |
| ok | Lines by source!Q48 | 1 | 1 |
| ok | Lines by source!R48 | Low | Low |
| ok | Lines by source!S48 |  |  |
| ok | Lines by source!E49 | 0.17517119680748014 | 0.17517119680748014 |
| ok | Lines by source!F49 | 0.0999264932895555 | 0.0999264932895555 |
| ok | Lines by source!G49 | 0.9557110525379066 | 0.9557110525379066 |
| ok | Lines by source!L49 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M49 | 0.03257808684852553 | 0.03257808684852553 |
| ok | Lines by source!H49 | 0.07524470351792464 | 0.07524470351792464 |
| ok | Lines by source!I49 | 0.1252079501627024 | 0.1252079501627024 |
| ok | Lines by source!J49 | 0.2251344434522579 | 0.2251344434522579 |
| ok | Lines by source!K49 | 0.7442323116588719 | 0.7442323116588722 |
| ok | Lines by source!Q49 | 1 | 1 |
| ok | Lines by source!R49 | Low | Low |
| ok | Lines by source!S49 |  |  |
| ok | Lines by source!E50 | 0.4481932269247423 | 0.4481932269247423 |
| ok | Lines by source!F50 | 0.08759941431270868 | 0.08759941431270855 |
| ok | Lines by source!G50 | 3.192798104447804 | 3.192798104447804 |
| ok | Lines by source!L50 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M50 | 0.08750898529165822 | 0.08750898529165822 |
| ok | Lines by source!H50 | 0.3605938126120336 | 0.3605938126120337 |
| ok | Lines by source!I50 | 0.40439351976838794 | 0.404393519768388 |
| ok | Lines by source!J50 | 0.4919929340810966 | 0.49199293408109657 |
| ok | Lines by source!K50 | 1.7311086948134276 | 1.731108694813428 |
| ok | Lines by source!Q50 | 1 | 1 |
| ok | Lines by source!R50 | Low | Low |
| ok | Lines by source!S50 |  |  |
| ok | Lines by source!E51 | 0.541311420007059 | 0.541311420007059 |
| ok | Lines by source!F51 | 0.11057098555547462 | 0.11057098555547462 |
| ok | Lines by source!G51 | 3.5621147284413457 | 3.5621147284413457 |
| ok | Lines by source!L51 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M51 | 0.10262904527785062 | 0.10262904527785062 |
| ok | Lines by source!H51 | 0.4307404344515844 | 0.4307404344515844 |
| ok | Lines by source!I51 | 0.4860259272293217 | 0.4860259272293217 |
| ok | Lines by source!J51 | 0.5965969127847963 | 0.5965969127847963 |
| ok | Lines by source!K51 | 2.0261761062212233 | 2.0261761062212233 |
| ok | Lines by source!Q51 | 1 | 1 |
| ok | Lines by source!R51 | Low | Low |
| ok | Lines by source!S51 |  |  |
| ok | Lines by source!E52 | 0.2574813358086204 | 0.2574813358086204 |
| ok | Lines by source!F52 | 0.11199358754628705 | 0.11199358754628708 |
| ok | Lines by source!G52 | 1.0082309589244485 | 1.008230958924448 |
| ok | Lines by source!L52 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M52 | 0.07719012006354721 | 0.07719012006354721 |
| ok | Lines by source!H52 | 0.14548774826233338 | 0.14548774826233335 |
| ok | Lines by source!I52 | 0.2014845420354769 | 0.2014845420354769 |
| ok | Lines by source!J52 | 0.31347812958176396 | 0.31347812958176396 |
| ok | Lines by source!K52 | 0.8699582080262569 | 0.8699582080262569 |
| ok | Lines by source!Q52 | 1 | 1 |
| ok | Lines by source!R52 | Low | Low |
| ok | Lines by source!S52 |  |  |
| ok | Lines by source!E53 | 0.6533034615691918 | 0.6533034615691918 |
| ok | Lines by source!F53 | 0.11824676645243191 | 0.11824676645243191 |
| ok | Lines by source!G53 | 1.7921749189351388 | 1.792174918935139 |
| ok | Lines by source!L53 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M53 | 0.5204319093538794 | 0.5204319093538794 |
| ok | Lines by source!H53 | 0.5350566951167599 | 0.5350566951167599 |
| ok | Lines by source!I53 | 0.5941800783429759 | 0.5941800783429759 |
| ok | Lines by source!J53 | 0.7124268447954077 | 0.7124268447954077 |
| ok | Lines by source!K53 | 1.0849804271312955 | 1.0849804271312955 |
| ok | Lines by source!Q53 | 1 | 1 |
| ok | Lines by source!R53 | Low | Low |
| ok | Lines by source!S53 |  |  |
| ok | Lines by source!E54 | 0.7581386743467546 | 0.7581386743467546 |
| ok | Lines by source!F54 | 0.12768589719572593 | 0.12768589719572593 |
| ok | Lines by source!G54 | 1.8539966336909295 | 1.8539966336909295 |
| ok | Lines by source!L54 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M54 | 0.5326480276667482 | 0.5326480276667482 |
| ok | Lines by source!H54 | 0.6304527771510287 | 0.6304527771510287 |
| ok | Lines by source!I54 | 0.6942957257488916 | 0.6942957257488916 |
| ok | Lines by source!J54 | 0.8219816229446176 | 0.8219816229446176 |
| ok | Lines by source!K54 | 1.4187917944512147 | 1.4187917944512147 |
| ok | Lines by source!Q54 | 1 | 1 |
| ok | Lines by source!R54 | Low | Low |
| ok | Lines by source!S54 |  |  |
| ok | Lines by source!E55 | 0.7403071089005516 | 0.7403071089005516 |
| ok | Lines by source!F55 | 0.12392506084713549 | 0.12392506084713549 |
| ok | Lines by source!G55 | 0.994745057009896 | 0.994745057009896 |
| ok | Lines by source!L55 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M55 | 0.5338326102465549 | 0.5338326102465549 |
| ok | Lines by source!Q55 |  |  |
| ok | Lines by source!S55 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E56 | 0.16176830070839332 | 0.16176830070839338 |
| ok | Lines by source!F56 | 0.030225853583847436 | 0.0302258535838475 |
| ok | Lines by source!G56 | 0.5126928626742963 | 0.5126928626742963 |
| ok | Lines by source!L56 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M56 | 0.05413210722089782 | 0.05413210722089782 |
| ok | Lines by source!Q56 |  |  |
| ok | Lines by source!S56 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E57 | 0.2496168290498928 | 0.2496168290498928 |
| ok | Lines by source!F57 | 0.03939189363278762 | 0.03939189363278762 |
| ok | Lines by source!G57 | 0.7134754600637128 | 0.7134754600637128 |
| ok | Lines by source!L57 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M57 | 0.04595209206224703 | 0.04595209206224703 |
| ok | Lines by source!Q57 |  |  |
| ok | Lines by source!S57 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E58 | 0.12631866741620734 | 0.1263186674162073 |
| ok | Lines by source!F58 | 0.038151889314316026 | 0.038151889314316005 |
| ok | Lines by source!G58 | 0.23293578284301256 | 0.2329357828430126 |
| ok | Lines by source!L58 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M58 | 0.07072710329502283 | 0.07072710329502283 |
| ok | Lines by source!Q58 |  |  |
| ok | Lines by source!S58 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E59 | 1.6711553713948304 | 1.6711553713948306 |
| ok | Lines by source!F59 | 0.1801031764023845 | 0.18010317640238283 |
| ok | Lines by source!G59 | 2.532642513684638 | 2.532642513684638 |
| ok | Lines by source!L59 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M59 | 1.451503633202392 | 1.451503633202392 |
| ok | Lines by source!Q59 |  |  |
| ok | Lines by source!S59 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E60 | 2.5448967792923494 | 2.5448967792923494 |
| ok | Lines by source!F60 | 0.25863156807742665 | 0.25863156807742665 |
| ok | Lines by source!G60 | 3.1676116100567104 | 3.1676116100567104 |
| ok | Lines by source!L60 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M60 | 2.2209814576008475 | 2.2209814576008475 |
| ok | Lines by source!Q60 |  |  |
| ok | Lines by source!S60 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E61 | 1.7411276888155705 | 1.7411276888155705 |
| ok | Lines by source!F61 | 0.20086138838000855 | 0.2008613883800089 |
| ok | Lines by source!G61 | 2.347574113033627 | 2.347574113033627 |
| ok | Lines by source!L61 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M61 | 1.8537532811982647 | 1.853753281198265 |
| ok | Lines by source!Q61 |  |  |
| ok | Lines by source!S61 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E62 | 2.8169977527340375 | 2.8169977527340375 |
| ok | Lines by source!F62 | 0.20692027541165528 | 0.20692027541165528 |
| ok | Lines by source!G62 | 3.8538312589584676 | 3.853831258958468 |
| ok | Lines by source!L62 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M62 | 2.0260676497771692 | 2.026067649777169 |
| ok | Lines by source!Q62 |  |  |
| ok | Lines by source!S62 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E63 | 3.40426809133817 | 3.40426809133817 |
| ok | Lines by source!F63 | 0.3354352756256615 | 0.3354352756256615 |
| ok | Lines by source!G63 | 4.6688415940912 | 4.6688415940912 |
| ok | Lines by source!L63 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M63 | 2.799581577329843 | 2.799581577329843 |
| ok | Lines by source!Q63 |  |  |
| ok | Lines by source!S63 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E64 | 2.5066461833672604 | 2.506646183367261 |
| ok | Lines by source!F64 | 0.24012393344654226 | 0.24012393344654193 |
| ok | Lines by source!G64 | 3.0328596973774875 | 3.032859697377488 |
| ok | Lines by source!L64 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M64 | 2.4583129947398423 | 2.458312994739842 |
| ok | Lines by source!Q64 |  |  |
| ok | Lines by source!S64 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E65 | 1.849638183004821 | 1.8496381830048212 |
| ok | Lines by source!F65 | 0.2069225565270242 | 0.20692255652702438 |
| ok | Lines by source!G65 | 2.883560925894692 | 2.883560925894692 |
| ok | Lines by source!L65 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M65 | 1.5056357404232898 | 1.50563574042329 |
| ok | Lines by source!Q65 |  |  |
| ok | Lines by source!S65 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E66 | 2.629462610956206 | 2.629462610956206 |
| ok | Lines by source!F66 | 0.2941146451256141 | 0.2941146451256141 |
| ok | Lines by source!G66 | 3.580637882435159 | 3.580637882435159 |
| ok | Lines by source!L66 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M66 | 2.2669335496630945 | 2.2669335496630945 |
| ok | Lines by source!Q66 |  |  |
| ok | Lines by source!S66 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E67 | 1.8568061014226394 | 1.856806101422639 |
| ok | Lines by source!F67 | 0.21182642872378069 | 0.21182642872378069 |
| ok | Lines by source!G67 | 2.5203446988300735 | 2.520344698830074 |
| ok | Lines by source!L67 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M67 | 1.9244803844932874 | 1.924480384493287 |
| ok | Lines by source!Q67 |  |  |
| ok | Lines by source!S67 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E68 | 1.1566286559810266 | 1.156628655981027 |
| ok | Lines by source!F68 | 0.37195537534552364 | 0.37195537534552425 |
| ok | Lines by source!G68 | 2.9986928936336716 | 2.998692893633672 |
| ok | Lines by source!L68 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M68 | 1.6138446897622272 | 1.613844689762227 |
| ok | Lines by source!H68 | 0.784673280635503 | 0.7846732806355028 |
| ok | Lines by source!I68 | 0.9706509683082648 | 0.9706509683082649 |
| ok | Lines by source!J68 | 1.3426063436537885 | 1.3426063436537892 |
| ok | Lines by source!K68 | 2.3448839057708497 | 2.3448839057708524 |
| ok | Lines by source!Q68 | 4 | 4 |
| ok | Lines by source!R68 | Moderate-High | Moderate-High |
| ok | Lines by source!S68 |  |  |
| ok | Lines by source!E69 | 1.0903375330450853 | 1.0903375330450853 |
| ok | Lines by source!F69 | 0.26535646656268286 | 0.26535646656268286 |
| ok | Lines by source!G69 | 2.1096039782489724 | 2.1096039782489724 |
| ok | Lines by source!L69 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M69 | 1.550392085338516 | 1.550392085338516 |
| ok | Lines by source!H69 | 0.8249810664824024 | 0.8249810664824024 |
| ok | Lines by source!I69 | 0.9576592997637439 | 0.9576592997637439 |
| ok | Lines by source!J69 | 1.2230157663264267 | 1.2230157663264267 |
| ok | Lines by source!K69 | 1.829281853856854 | 1.829281853856854 |
| ok | Lines by source!Q69 | 4 | 4 |
| ok | Lines by source!R69 | Moderate-High | Moderate-High |
| ok | Lines by source!S69 |  |  |
| ok | Lines by source!E70 | 1.0190485551954143 | 1.019048555195414 |
| ok | Lines by source!F70 | 0.24368906679390187 | 0.24368906679390087 |
| ok | Lines by source!G70 | 1.5504635338255814 | 1.550463533825581 |
| ok | Lines by source!L70 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M70 | 1.05873659463189 | 1.05873659463189 |
| ok | Lines by source!Q70 |  |  |
| ok | Lines by source!S70 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E71 | 1.4631547774584708 | 1.463154777458471 |
| ok | Lines by source!F71 | 0.4401960951581682 | 0.4401960951581679 |
| ok | Lines by source!G71 | 3.570809928981094 | 3.570809928981094 |
| ok | Lines by source!L71 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M71 | 2.0372465877364028 | 2.037246587736403 |
| ok | Lines by source!H71 | 1.0229586823003025 | 1.0229586823003032 |
| ok | Lines by source!I71 | 1.2430567298793866 | 1.243056729879387 |
| ok | Lines by source!J71 | 1.683252825037555 | 1.683252825037555 |
| ok | Lines by source!K71 | 2.805930750348988 | 2.8059307503489856 |
| ok | Lines by source!Q71 | 4 | 4 |
| ok | Lines by source!R71 | Moderate-High | Moderate-High |
| ok | Lines by source!S71 |  |  |
| ok | Lines by source!E72 | 1.408595073366724 | 1.408595073366724 |
| ok | Lines by source!F72 | 0.38283663497286924 | 0.38283663497286924 |
| ok | Lines by source!G72 | 2.729182420135111 | 2.729182420135111 |
| ok | Lines by source!L72 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M72 | 2.0194451522005985 | 2.0194451522005985 |
| ok | Lines by source!H72 | 1.0257584383938547 | 1.0257584383938547 |
| ok | Lines by source!I72 | 1.2171767558802895 | 1.2171767558802895 |
| ok | Lines by source!J72 | 1.6000133908531586 | 1.6000133908531586 |
| ok | Lines by source!K72 | 2.4232587134610246 | 2.4232587134610246 |
| ok | Lines by source!Q72 | 4 | 4 |
| ok | Lines by source!R72 | Moderate-High | Moderate-High |
| ok | Lines by source!S72 |  |  |
| ok | Lines by source!E73 | 1.181272946395066 | 1.181272946395066 |
| ok | Lines by source!F73 | 0.1974776968264934 | 0.1974776968264934 |
| ok | Lines by source!G73 | 2.0617647069338627 | 2.061764706933863 |
| ok | Lines by source!L73 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M73 | 1.269580994403605 | 1.269580994403605 |
| ok | Lines by source!Q73 |  |  |
| ok | Lines by source!S73 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E74 | 1.002682892017849 | 1.002682892017849 |
| ok | Lines by source!F74 | 0.14056930761486228 | 0.14056930761486194 |
| ok | Lines by source!G74 | 2.47598290931125 | 2.47598290931125 |
| ok | Lines by source!L74 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M74 | 0.9530633219641633 | 0.9530633219641633 |
| ok | Lines by source!H74 | 0.8621135844029867 | 0.862113584402987 |
| ok | Lines by source!I74 | 0.9323982382104179 | 0.932398238210418 |
| ok | Lines by source!J74 | 1.07296754582528 | 1.0729675458252799 |
| ok | Lines by source!K74 | 2.2610608219546595 | 2.2610608219546604 |
| ok | Lines by source!Q74 | 3 | 3 |
| ok | Lines by source!R74 | Moderate | Moderate |
| ok | Lines by source!S74 |  |  |
| ok | Lines by source!E75 | 1.0831133244591462 | 1.0831133244591462 |
| ok | Lines by source!F75 | 0.2007984015323891 | 0.2007984015323891 |
| ok | Lines by source!G75 | 2.4228391210042792 | 2.4228391210042792 |
| ok | Lines by source!L75 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M75 | 0.951295071676428 | 0.951295071676428 |
| ok | Lines by source!Q75 |  |  |
| ok | Lines by source!S75 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E76 | 1.3498209481310717 | 1.3498209481310717 |
| ok | Lines by source!F76 | 0.26771379985763033 | 0.2677137998576302 |
| ok | Lines by source!G76 | 2.8084901945741167 | 2.808490194574117 |
| ok | Lines by source!L76 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M76 | 0.6203355401492896 | 0.6203355401492896 |
| ok | Lines by source!Q76 |  |  |
| ok | Lines by source!S76 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E77 | 0.5524102578287597 | 0.5524102578287597 |
| ok | Lines by source!F77 | 0.12259240645979824 | 0.1225924064597982 |
| ok | Lines by source!G77 | 1.6689289347502616 | 1.668928934750262 |
| ok | Lines by source!L77 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M77 | 0.18427413737016327 | 0.1842741373701633 |
| ok | Lines by source!H77 | 0.4298178513689615 | 0.42981785136896156 |
| ok | Lines by source!I77 | 0.4911140545988606 | 0.49111405459886065 |
| ok | Lines by source!J77 | 0.6137064610586589 | 0.6137064610586589 |
| ok | Lines by source!K77 | 1.5515134982241898 | 1.5515134982241903 |
| ok | Lines by source!Q77 | 1 | 1 |
| ok | Lines by source!R77 | Low | Low |
| ok | Lines by source!S77 |  |  |
| ok | Lines by source!E78 | 0.5403526578880691 | 0.5403526578880691 |
| ok | Lines by source!F78 | 0.21185782762414027 | 0.21185782762414027 |
| ok | Lines by source!G78 | 1.5706376982148618 | 1.5706376982148618 |
| ok | Lines by source!L78 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M78 | 0.14276586877115047 | 0.14276586877115047 |
| ok | Lines by source!H78 | 0.3284948302639288 | 0.3284948302639288 |
| ok | Lines by source!I78 | 0.43442374407599893 | 0.43442374407599893 |
| ok | Lines by source!J78 | 0.6462815717001392 | 0.6462815717001392 |
| ok | Lines by source!K78 | 1.4223154868117307 | 1.4223154868117307 |
| ok | Lines by source!Q78 | 1 | 1 |
| ok | Lines by source!R78 | Low | Low |
| ok | Lines by source!S78 |  |  |
| ok | Lines by source!E79 | 0.534883128684778 | 0.534883128684778 |
| ok | Lines by source!F79 | 0.1366172041130495 | 0.1366172041130495 |
| ok | Lines by source!G79 | 1.317066342919824 | 1.317066342919824 |
| ok | Lines by source!L79 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M79 | 0.47005694520492464 | 0.4700569452049246 |
| ok | Lines by source!Q79 |  |  |
| ok | Lines by source!S79 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E80 | 0.23989452448745785 | 0.23989452448745785 |
| ok | Lines by source!F80 | 0.046617808605711145 | 0.0466178086057111 |
| ok | Lines by source!G80 | 0.47625984480906836 | 0.4762598448090684 |
| ok | Lines by source!L80 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M80 | 0.23128678890546345 | 0.2312867889054634 |
| ok | Lines by source!Q80 |  |  |
| ok | Lines by source!S80 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E81 | 0.2990239457002397 | 0.2990239457002397 |
| ok | Lines by source!F81 | 0.07032597997382009 | 0.07032597997382009 |
| ok | Lines by source!G81 | 0.613695884534981 | 0.613695884534981 |
| ok | Lines by source!L81 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M81 | 0.2631254521014802 | 0.2631254521014802 |
| ok | Lines by source!Q81 |  |  |
| ok | Lines by source!S81 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E82 | 0.3021955989027553 | 0.30219559890275527 |
| ok | Lines by source!F82 | 0.12019476977642986 | 0.12019476977642987 |
| ok | Lines by source!G82 | 0.8386609772930828 | 0.8386609772930828 |
| ok | Lines by source!L82 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M82 | 0.10472064090822332 | 0.1047206409082233 |
| ok | Lines by source!H82 | 0.18200082912632548 | 0.1820008291263254 |
| ok | Lines by source!I82 | 0.2420982140145404 | 0.24209821401454035 |
| ok | Lines by source!J82 | 0.36229298379097025 | 0.3622929837909702 |
| ok | Lines by source!K82 | 0.7855560017193836 | 0.7855560017193837 |
| ok | Lines by source!Q82 | 1 | 1 |
| ok | Lines by source!R82 | Low | Low |
| ok | Lines by source!S82 |  |  |
| ok | Lines by source!E83 | 1.8300926507311464 | 1.830092650731146 |
| ok | Lines by source!F83 | 0.25714523115713367 | 0.257145231157134 |
| ok | Lines by source!G83 | 4.214368284710485 | 4.214368284710485 |
| ok | Lines by source!L83 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M83 | 1.3686242482397901 | 1.36862424823979 |
| ok | Lines by source!Q83 |  |  |
| ok | Lines by source!S83 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E84 | 1.969600888238622 | 1.969600888238622 |
| ok | Lines by source!F84 | 0.41598014311214526 | 0.41598014311214526 |
| ok | Lines by source!G84 | 4.04789574586689 | 4.04789574586689 |
| ok | Lines by source!L84 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M84 | 1.3571863925490586 | 1.3571863925490586 |
| ok | Lines by source!Q84 |  |  |
| ok | Lines by source!S84 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E85 | 2.363365832333134 | 2.363365832333134 |
| ok | Lines by source!F85 | 0.32389918371069265 | 0.32389918371069265 |
| ok | Lines by source!G85 | 4.681942738741334 | 4.681942738741334 |
| ok | Lines by source!L85 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M85 | 1.1951131262624375 | 1.195113126262437 |
| ok | Lines by source!Q85 |  |  |
| ok | Lines by source!S85 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E86 | 0.7452479449485396 | 0.7452479449485396 |
| ok | Lines by source!F86 | 0.1267334989787225 | 0.12673349897872246 |
| ok | Lines by source!G86 | 2.0505198130364435 | 2.050519813036443 |
| ok | Lines by source!L86 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M86 | 0.41556092627562674 | 0.4155609262756267 |
| ok | Lines by source!H86 | 0.6185144459698171 | 0.6185144459698172 |
| ok | Lines by source!I86 | 0.6818811954591784 | 0.6818811954591784 |
| ok | Lines by source!J86 | 0.8086146944379009 | 0.8086146944379009 |
| ok | Lines by source!K86 | 1.9145450914838191 | 1.9145450914838191 |
| ok | Lines by source!Q86 | 1 | 1 |
| ok | Lines by source!R86 | Low | Low |
| ok | Lines by source!S86 |  |  |
| ok | Lines by source!E87 | 0.8432414625650378 | 0.8432414625650378 |
| ok | Lines by source!F87 | 0.24041097733051625 | 0.24041097733051625 |
| ok | Lines by source!G87 | 1.9539669108763122 | 1.9539669108763122 |
| ok | Lines by source!L87 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M87 | 0.4058913208726307 | 0.4058913208726307 |
| ok | Lines by source!Q87 |  |  |
| ok | Lines by source!S87 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E88 | 0.9168211953619952 | 0.9168211953619952 |
| ok | Lines by source!F88 | 0.21096363362678894 | 0.21096363362678877 |
| ok | Lines by source!G88 | 1.9441219292817395 | 1.94412192928174 |
| ok | Lines by source!L88 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M88 | 0.574777586113148 | 0.574777586113148 |
| ok | Lines by source!Q88 |  |  |
| ok | Lines by source!S88 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E89 | 0.6548820936069344 | 0.6548820936069344 |
| ok | Lines by source!F89 | 0.1479304022170215 | 0.1479304022170215 |
| ok | Lines by source!G89 | 1.1581294738640815 | 1.158129473864081 |
| ok | Lines by source!L89 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M89 | 0.9878539701554716 | 0.9878539701554716 |
| ok | Lines by source!Q89 |  |  |
| ok | Lines by source!S89 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E90 | 0.707080533527564 | 0.707080533527564 |
| ok | Lines by source!F90 | 0.1930127531951151 | 0.1930127531951151 |
| ok | Lines by source!G90 | 1.0470816731822656 | 1.0470816731822656 |
| ok | Lines by source!L90 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M90 | 0.8774784779654787 | 0.8774784779654787 |
| ok | Lines by source!Q90 |  |  |
| ok | Lines by source!S90 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E91 | 0.01034527350316824 | 0.01034527350316824 |
| ok | Lines by source!F91 | 0.048110295921705216 | 0.048110295921705175 |
| ok | Lines by source!G91 | 0.3152509896784223 | 0.3152509896784223 |
| ok | Lines by source!L91 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M91 | 0.09593421653723161 | 0.09593421653723161 |
| ok | Lines by source!Q91 |  |  |
| ok | Lines by source!S91 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E92 | 1.1101132486767291 | 1.1101132486767291 |
| ok | Lines by source!F92 | 0.19329298715357815 | 0.19329298715357815 |
| ok | Lines by source!G92 | 1.860696748575378 | 1.860696748575378 |
| ok | Lines by source!L92 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M92 | 1.7254849919194866 | 1.725484991919487 |
| ok | Lines by source!Q92 |  |  |
| ok | Lines by source!S92 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E93 | 1.211344101661908 | 1.211344101661908 |
| ok | Lines by source!F93 | 0.1623845657969841 | 0.1623845657969841 |
| ok | Lines by source!G93 | 1.7582619631903902 | 1.7582619631903902 |
| ok | Lines by source!L93 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M93 | 1.5906160217009966 | 1.5906160217009966 |
| ok | Lines by source!Q93 |  |  |
| ok | Lines by source!S93 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E94 | 0.5815013952222147 | 0.5815013952222147 |
| ok | Lines by source!F94 | 0.08264522189422571 | 0.08264522189422546 |
| ok | Lines by source!G94 | 0.9312919144628622 | 0.9312919144628622 |
| ok | Lines by source!L94 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M94 | 0.7781330896908787 | 0.7781330896908787 |
| ok | Lines by source!Q94 |  |  |
| ok | Lines by source!S94 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E95 | 1.7178397326619268 | 1.717839732661927 |
| ok | Lines by source!F95 | 0.1758795435447144 | 0.17587954354471458 |
| ok | Lines by source!G95 | 2.661596789704642 | 2.661596789704642 |
| ok | Lines by source!L95 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M95 | 2.1170273837661813 | 2.117027383766181 |
| ok | Lines by source!Q95 |  |  |
| ok | Lines by source!S95 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E96 | 1.905985475946889 | 1.905985475946889 |
| ok | Lines by source!F96 | 0.21784465951368195 | 0.21784465951368195 |
| ok | Lines by source!G96 | 2.6859186092098177 | 2.6859186092098177 |
| ok | Lines by source!L96 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M96 | 1.9632802207272166 | 1.9632802207272166 |
| ok | Lines by source!Q96 |  |  |
| ok | Lines by source!S96 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E97 | 0.4785223101474425 | 0.4785223101474425 |
| ok | Lines by source!F97 | 0.2535216666140795 | 0.25352166661407965 |
| ok | Lines by source!G97 | 1.6386063737187528 | 1.638606373718753 |
| ok | Lines by source!L97 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M97 | 0.4854368932038835 | 0.4854368932038835 |
| ok | Lines by source!H97 | 0.22500064353336302 | 0.22500064353336285 |
| ok | Lines by source!I97 | 0.35176147684040276 | 0.3517614768404027 |
| ok | Lines by source!J97 | 0.6052831434544823 | 0.6052831434544823 |
| ok | Lines by source!K97 | 1.064016718750587 | 1.064016718750587 |
| ok | Lines by source!Q97 | 3 | 3 |
| ok | Lines by source!R97 | Moderate | Moderate |
| ok | Lines by source!S97 |  |  |
| ok | Lines by source!E98 | 0.03885377388017677 | 0.03885377388017677 |
| ok | Lines by source!F98 | 0.008967751802618988 | 0.008967751802618983 |
| ok | Lines by source!G98 | 0.09381636319257845 | 0.09381636319257845 |
| ok | Lines by source!L98 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M98 | 0.017704651456628466 | 0.01770465145662847 |
| ok | Lines by source!H98 | 0.029886022077557785 | 0.02988602207755779 |
| ok | Lines by source!I98 | 0.034369897978867275 | 0.03436989797886728 |
| ok | Lines by source!J98 | 0.04333764978148627 | 0.043337649781486264 |
| ok | Lines by source!K98 | 0.07751594993896989 | 0.0775159499389699 |
| ok | Lines by source!Q98 | 1 | 1 |
| ok | Lines by source!R98 | Low | Low |
| ok | Lines by source!S98 |  |  |
| ok | Lines by source!E99 | 0.04312774790944599 | 0.04312774790944599 |
| ok | Lines by source!F99 | 0.012642907463903948 | 0.012642907463903948 |
| ok | Lines by source!G99 | 0.11604645717639248 | 0.11604645717639248 |
| ok | Lines by source!L99 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M99 | 0.022395815868242422 | 0.022395815868242422 |
| ok | Lines by source!H99 | 0.030484840445542043 | 0.030484840445542043 |
| ok | Lines by source!I99 | 0.036806294177494016 | 0.036806294177494016 |
| ok | Lines by source!J99 | 0.04944920164139797 | 0.04944920164139797 |
| ok | Lines by source!K99 | 0.0863493973653762 | 0.0863493973653762 |
| ok | Lines by source!Q99 | 1 | 1 |
| ok | Lines by source!R99 | Low | Low |
| ok | Lines by source!S99 |  |  |
| ok | Lines by source!E100 | 0.047109947113673833 | 0.047109947113673833 |
| ok | Lines by source!F100 | 0.02219199265457818 | 0.02219199265457818 |
| ok | Lines by source!G100 | 0.15246441853358353 | 0.1524644185335835 |
| ok | Lines by source!L100 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M100 | 0.0369703594161898 | 0.0369703594161898 |
| ok | Lines by source!H100 | 0.024917954459095653 | 0.024917954459095653 |
| ok | Lines by source!I100 | 0.036013950786384745 | 0.036013950786384745 |
| ok | Lines by source!J100 | 0.05820594344096292 | 0.05820594344096292 |
| ok | Lines by source!K100 | 0.10862588748262028 | 0.10862588748262028 |
| ok | Lines by source!Q100 | 3 | 3 |
| ok | Lines by source!R100 | Moderate | Moderate |
| ok | Lines by source!S100 |  |  |
| ok | Lines by source!E101 | 0.37735962868064343 | 0.37735962868064343 |
| ok | Lines by source!F101 | 0.059482446648641205 | 0.05948244664864127 |
| ok | Lines by source!G101 | 0.6791558894150471 | 0.6791558894150471 |
| ok | Lines by source!L101 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M101 | 0.6418505967481973 | 0.6418505967481973 |
| ok | Lines by source!Q101 |  |  |
| ok | Lines by source!S101 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E102 | 0.31236778312257785 | 0.31236778312257785 |
| ok | Lines by source!F102 | 0.061305931312655375 | 0.061305931312655375 |
| ok | Lines by source!G102 | 0.5370617740541132 | 0.5370617740541132 |
| ok | Lines by source!L102 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M102 | 0.5060268781190284 | 0.5060268781190284 |
| ok | Lines by source!Q102 |  |  |
| ok | Lines by source!S102 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E103 | 0.2566804637882613 | 0.25668046378826126 |
| ok | Lines by source!F103 | 0.13109322370459264 | 0.13109322370459262 |
| ok | Lines by source!G103 | 0.7985604896436687 | 0.7985604896436687 |
| ok | Lines by source!L103 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M103 | 0.5963479714524529 | 0.5963479714524529 |
| ok | Lines by source!Q103 |  |  |
| ok | Lines by source!S103 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E104 | 2.090284663933655 | 2.090284663933655 |
| ok | Lines by source!F104 | 0.25368518927484035 | 0.25368518927484 |
| ok | Lines by source!G104 | 3.3251014445355755 | 3.325101444535576 |
| ok | Lines by source!L104 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M104 | 2.776582631971007 | 2.776582631971007 |
| ok | Lines by source!Q104 |  |  |
| ok | Lines by source!S104 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E105 | 2.285682077388838 | 2.285682077388838 |
| ok | Lines by source!F105 | 0.285879492444018 | 0.285879492444018 |
| ok | Lines by source!G105 | 3.2306919898445274 | 3.2306919898445274 |
| ok | Lines by source!L105 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M105 | 2.4917029147144873 | 2.4917029147144873 |
| ok | Lines by source!Q105 |  |  |
| ok | Lines by source!S105 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E106 | 0.7716850728955458 | 0.7716850728955458 |
| ok | Lines by source!F106 | 0.3069437562611119 | 0.3069437562611119 |
| ok | Lines by source!G106 | 1.9333856257605293 | 1.933385625760529 |
| ok | Lines by source!L106 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M106 | 1.1187552240725263 | 1.118755224072526 |
| ok | Lines by source!H106 | 0.46474131663443385 | 0.46474131663443385 |
| ok | Lines by source!I106 | 0.6182131947649898 | 0.6182131947649898 |
| ok | Lines by source!J106 | 0.9251569510261017 | 0.9251569510261017 |
| ok | Lines by source!K106 | 1.8083151131649546 | 1.8083151131649546 |
| ok | Lines by source!Q106 | 4 | 4 |
| ok | Lines by source!R106 | Moderate-High | Moderate-High |
| ok | Lines by source!S106 |  |  |
| ok | Lines by source!E107 | 0.42455117735752945 | 0.42455117735752945 |
| ok | Lines by source!F107 | 0.05745515104976774 | 0.05745515104976768 |
| ok | Lines by source!G107 | 0.7086709776212976 | 0.7086709776212976 |
| ok | Lines by source!L107 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M107 | 0.6595552482048258 | 0.6595552482048258 |
| ok | Lines by source!Q107 |  |  |
| ok | Lines by source!S107 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E108 | 0.35963015461079606 | 0.35963015461079606 |
| ok | Lines by source!F108 | 0.06009246575154623 | 0.06009246575154623 |
| ok | Lines by source!G108 | 0.5695080383696894 | 0.5695080383696894 |
| ok | Lines by source!L108 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M108 | 0.5284226939872708 | 0.5284226939872708 |
| ok | Lines by source!Q108 |  |  |
| ok | Lines by source!S108 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E109 | 0.3072459076115344 | 0.3072459076115345 |
| ok | Lines by source!F109 | 0.14278106945546248 | 0.14278106945546234 |
| ok | Lines by source!G109 | 0.8484705202463979 | 0.8484705202463979 |
| ok | Lines by source!L109 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M109 | 0.6333183308686428 | 0.6333183308686428 |
| ok | Lines by source!Q109 |  |  |
| ok | Lines by source!S109 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E110 | 0.9810915500533465 | 0.9810915500533465 |
| ok | Lines by source!F110 | 0.40312835107517353 | 0.4031283510751732 |
| ok | Lines by source!G110 | 3.351084179033857 | 3.351084179033857 |
| ok | Lines by source!L110 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M110 | 1.174029706845404 | 1.174029706845404 |
| ok | Lines by source!H110 | 0.5779631989781729 | 0.5779631989781733 |
| ok | Lines by source!I110 | 0.7795273745157597 | 0.7795273745157598 |
| ok | Lines by source!J110 | 1.1826557255909331 | 1.1826557255909331 |
| ok | Lines by source!K110 | 1.8424761012893216 | 1.8424761012893216 |
| ok | Lines by source!Q110 | 3 | 3 |
| ok | Lines by source!R110 | Moderate | Moderate |
| ok | Lines by source!S110 |  |  |
| ok | Lines by source!E111 | 1.0812253429931626 | 1.0812253429931626 |
| ok | Lines by source!F111 | 0.45921038875816417 | 0.45921038875816417 |
| ok | Lines by source!G111 | 3.5457483437077104 | 3.5457483437077104 |
| ok | Lines by source!L111 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M111 | 1.4008357178877437 | 1.4008357178877437 |
| ok | Lines by source!H111 | 0.6220149542349984 | 0.6220149542349984 |
| ok | Lines by source!I111 | 0.8516201486140805 | 0.8516201486140805 |
| ok | Lines by source!J111 | 1.3108305373722446 | 1.3108305373722446 |
| ok | Lines by source!K111 | 2.1628463259785757 | 2.1628463259785757 |
| ok | Lines by source!Q111 | 4 | 4 |
| ok | Lines by source!R111 | Moderate-High | Moderate-High |
| ok | Lines by source!S111 |  |  |
| ok | Lines by source!E112 | 0.4569573586399822 | 0.4569573586399822 |
| ok | Lines by source!F112 | 0.14927505900858298 | 0.14927505900858296 |
| ok | Lines by source!G112 | 1.767870628743823 | 1.767870628743823 |
| ok | Lines by source!L112 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M112 | 0.27753507018220386 | 0.2775350701822039 |
| ok | Lines by source!H112 | 0.30768229963139926 | 0.30768229963139926 |
| ok | Lines by source!I112 | 0.38231982913569074 | 0.38231982913569074 |
| ok | Lines by source!J112 | 0.5315948881442737 | 0.5315948881442737 |
| ok | Lines by source!K112 | 1.1577113368432355 | 1.1577113368432355 |
| ok | Lines by source!Q112 | 1 | 1 |
| ok | Lines by source!R112 | Low | Low |
| ok | Lines by source!S112 |  |  |
| ok | Lines by source!E113 | 1.2762345378034017 | 1.276234537803402 |
| ok | Lines by source!F113 | 0.39977215268118377 | 0.3997721526811854 |
| ok | Lines by source!G113 | 3.6417066708924026 | 3.641706670892403 |
| ok | Lines by source!L113 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M113 | 1.5790107692017183 | 1.579010769201718 |
| ok | Lines by source!H113 | 0.876462385122218 | 0.8764623851222165 |
| ok | Lines by source!I113 | 1.0763484614628098 | 1.0763484614628092 |
| ok | Lines by source!J113 | 1.4761206141439935 | 1.4761206141439946 |
| ok | Lines by source!K113 | 2.3064349951851297 | 2.30643499518513 |
| ok | Lines by source!Q113 | 4 | 4 |
| ok | Lines by source!R113 | Moderate-High | Moderate-High |
| ok | Lines by source!S113 |  |  |
| ok | Lines by source!E114 | 1.4349502445758309 | 1.4349502445758309 |
| ok | Lines by source!F114 | 0.41984056041353823 | 0.41984056041353823 |
| ok | Lines by source!G114 | 3.807369836141289 | 3.807369836141289 |
| ok | Lines by source!L114 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M114 | 1.8900182585795187 | 1.8900182585795187 |
| ok | Lines by source!H114 | 1.0151096841622926 | 1.0151096841622926 |
| ok | Lines by source!I114 | 1.2250299643690616 | 1.2250299643690616 |
| ok | Lines by source!J114 | 1.6448705247826 | 1.6448705247826 |
| ok | Lines by source!K114 | 2.6458301600601573 | 2.6458301600601573 |
| ok | Lines by source!Q114 | 4 | 4 |
| ok | Lines by source!R114 | Moderate-High | Moderate-High |
| ok | Lines by source!S114 |  |  |
| ok | Lines by source!E115 | 0.6333902167028547 | 0.6333902167028547 |
| ok | Lines by source!F115 | 0.15266247818366824 | 0.15266247818366824 |
| ok | Lines by source!G115 | 2.001969412280337 | 2.001969412280337 |
| ok | Lines by source!L115 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M115 | 0.3596378648739932 | 0.3596378648739932 |
| ok | Lines by source!H115 | 0.48072773851918643 | 0.48072773851918643 |
| ok | Lines by source!I115 | 0.5570589776110205 | 0.5570589776110205 |
| ok | Lines by source!J115 | 0.7097214557946888 | 0.7097214557946888 |
| ok | Lines by source!K115 | 1.6486433884901102 | 1.6486433884901102 |
| ok | Lines by source!Q115 | 1 | 1 |
| ok | Lines by source!R115 | Low | Low |
| ok | Lines by source!S115 |  |  |
| ok | Lines by source!E116 | 1.125794311388629 | 1.125794311388629 |
| ok | Lines by source!F116 | 0.1332994052538935 | 0.13329940525389267 |
| ok | Lines by source!G116 | 2.120668429929012 | 2.120668429929012 |
| ok | Lines by source!L116 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M116 | 0.9714323513479108 | 0.9714323513479108 |
| ok | Lines by source!H116 | 0.9924949061347356 | 0.9924949061347363 |
| ok | Lines by source!I116 | 1.0591446087616823 | 1.0591446087616827 |
| ok | Lines by source!J116 | 1.1924440140155759 | 1.1924440140155754 |
| ok | Lines by source!K116 | 1.7337978655594382 | 1.7337978655594386 |
| ok | Lines by source!Q116 | 1 | 1 |
| ok | Lines by source!R116 | Low | Low |
| ok | Lines by source!S116 |  |  |
| ok | Lines by source!E117 | 1.2858826692571532 | 1.2858826692571532 |
| ok | Lines by source!F117 | 0.13877395330335213 | 0.13877395330335213 |
| ok | Lines by source!G117 | 2.635728490160466 | 2.635728490160466 |
| ok | Lines by source!L117 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M117 | 1.0024414376176916 | 1.0024414376176916 |
| ok | Lines by source!H117 | 1.1471087159538012 | 1.1471087159538012 |
| ok | Lines by source!I117 | 1.216495692605477 | 1.216495692605477 |
| ok | Lines by source!J117 | 1.3552696459088294 | 1.3552696459088294 |
| ok | Lines by source!K117 | 2.3385224005873813 | 2.3385224005873813 |
| ok | Lines by source!Q117 | 1 | 1 |
| ok | Lines by source!R117 | Low | Low |
| ok | Lines by source!S117 |  |  |
| ok | Lines by source!E118 | 0.5909884234891694 | 0.5909884234891694 |
| ok | Lines by source!F118 | 0.12839575249504626 | 0.12839575249504626 |
| ok | Lines by source!G118 | 1.8986353826842914 | 1.898635382684291 |
| ok | Lines by source!L118 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M118 | 0.26060423415177053 | 0.2606042341517705 |
| ok | Lines by source!H118 | 0.4625926709941231 | 0.4625926709941231 |
| ok | Lines by source!I118 | 0.5267905472416462 | 0.5267905472416462 |
| ok | Lines by source!J118 | 0.6551862997366925 | 0.6551862997366925 |
| ok | Lines by source!K118 | 1.827727525576131 | 1.827727525576131 |
| ok | Lines by source!Q118 | 1 | 1 |
| ok | Lines by source!R118 | Low | Low |
| ok | Lines by source!S118 |  |  |
| ok | Lines by source!E119 | 0.9615459655237879 | 0.9615459655237879 |
| ok | Lines by source!F119 | 0.22577001126894305 | 0.22577001126894305 |
| ok | Lines by source!G119 | 3.465834236683818 | 3.465834236683818 |
| ok | Lines by source!L119 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M119 | 0.7101545779643433 | 0.7101545779643433 |
| ok | Lines by source!H119 | 0.7357759542548449 | 0.7357759542548449 |
| ok | Lines by source!I119 | 0.8486609598893163 | 0.8486609598893163 |
| ok | Lines by source!J119 | 1.0744309711582594 | 1.0744309711582594 |
| ok | Lines by source!K119 | 2.123690895752092 | 2.123690895752092 |
| ok | Lines by source!Q119 | 1 | 1 |
| ok | Lines by source!R119 | Low | Low |
| ok | Lines by source!S119 |  |  |
| ok | Lines by source!E120 | 1.1439063254324955 | 1.1439063254324955 |
| ok | Lines by source!F120 | 0.3903781211941581 | 0.3903781211941581 |
| ok | Lines by source!G120 | 5.4313595978454146 | 5.4313595978454146 |
| ok | Lines by source!L120 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M120 | 0.7677750430897722 | 0.7677750430897722 |
| ok | Lines by source!H120 | 0.7535282042383373 | 0.7535282042383373 |
| ok | Lines by source!I120 | 0.9487172648354164 | 0.9487172648354164 |
| ok | Lines by source!J120 | 1.3390953860295745 | 1.3390953860295745 |
| ok | Lines by source!K120 | 2.8634070539380536 | 2.8634070539380536 |
| ok | Lines by source!Q120 | 2 | 2 |
| ok | Lines by source!R120 | Moderate-Low | Moderate-Low |
| ok | Lines by source!S120 |  |  |
| ok | Lines by source!E121 | 0.1841900875201496 | 0.1841900875201496 |
| ok | Lines by source!F121 | 0.061392947945865514 | 0.06139294794586551 |
| ok | Lines by source!G121 | 0.678116843818578 | 0.678116843818578 |
| ok | Lines by source!L121 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M121 | 0.1637746480448366 | 0.1637746480448366 |
| ok | Lines by source!H121 | 0.12279713957428408 | 0.12279713957428409 |
| ok | Lines by source!I121 | 0.15349361354721683 | 0.15349361354721683 |
| ok | Lines by source!J121 | 0.21488656149308236 | 0.21488656149308236 |
| ok | Lines by source!K121 | 0.5261321443087157 | 0.5261321443087157 |
| ok | Lines by source!Q121 | 3 | 3 |
| ok | Lines by source!R121 | Moderate | Moderate |
| ok | Lines by source!S121 |  |  |
| ok | Lines by source!E122 | 0.8081655532966946 | 0.8081655532966946 |
| ok | Lines by source!F122 | 0.1791379745673684 | 0.1791379745673684 |
| ok | Lines by source!G122 | 2.527047941580512 | 2.527047941580512 |
| ok | Lines by source!L122 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M122 | 0.5541971976675089 | 0.5541971976675089 |
| ok | Lines by source!H122 | 0.6290275787293262 | 0.6290275787293262 |
| ok | Lines by source!I122 | 0.7185965660130104 | 0.7185965660130104 |
| ok | Lines by source!J122 | 0.8977345405803788 | 0.8977345405803788 |
| ok | Lines by source!K122 | 1.7530856872692944 | 1.7530856872692944 |
| ok | Lines by source!Q122 | 1 | 1 |
| ok | Lines by source!R122 | Low | Low |
| ok | Lines by source!S122 |  |  |
| ok | Lines by source!E123 | 0.9148809538931477 | 0.9148809538931477 |
| ok | Lines by source!F123 | 0.20453262064133906 | 0.20453262064133906 |
| ok | Lines by source!G123 | 3.4270938287792108 | 3.4270938287792108 |
| ok | Lines by source!L123 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M123 | 0.567416311135301 | 0.567416311135301 |
| ok | Lines by source!H123 | 0.7103483332518087 | 0.7103483332518087 |
| ok | Lines by source!I123 | 0.8126146435724781 | 0.8126146435724781 |
| ok | Lines by source!J123 | 1.0171472642138173 | 1.0171472642138173 |
| ok | Lines by source!K123 | 2.11106347847558 | 2.11106347847558 |
| ok | Lines by source!Q123 | 1 | 1 |
| ok | Lines by source!R123 | Low | Low |
| ok | Lines by source!S123 |  |  |
| ok | Lines by source!E124 | 1.0634344714680593 | 1.0634344714680595 |
| ok | Lines by source!F124 | 0.1481105477176801 | 0.1481105477176807 |
| ok | Lines by source!G124 | 1.6836324111452914 | 1.683632411145291 |
| ok | Lines by source!L124 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M124 | 0.6425414312961244 | 0.6425414312961244 |
| ok | Lines by source!Q124 |  |  |
| ok | Lines by source!S124 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E125 | 2.833277532047106 | 2.8332775320471066 |
| ok | Lines by source!F125 | 0.4346479448947911 | 0.4346479448947911 |
| ok | Lines by source!G125 | 7.9201244682733964 | 7.920124468273396 |
| ok | Lines by source!L125 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M125 | 2.235784126979763 | 2.235784126979763 |
| ok | Lines by source!H125 | 2.398629587152315 | 2.398629587152316 |
| ok | Lines by source!I125 | 2.6159535595997108 | 2.615953559599711 |
| ok | Lines by source!J125 | 3.0506015044945016 | 3.050601504494502 |
| ok | Lines by source!K125 | 5.266040553802107 | 5.2660405538021084 |
| ok | Lines by source!Q125 | 1 | 1 |
| ok | Lines by source!R125 | Low | Low |
| ok | Lines by source!S125 |  |  |
| ok | Lines by source!E126 | 3.315437146713472 | 3.315437146713472 |
| ok | Lines by source!F126 | 0.605328466112788 | 0.605328466112788 |
| ok | Lines by source!G126 | 11.0831079173472 | 11.0831079173472 |
| ok | Lines by source!L126 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M126 | 2.337632791842765 | 2.337632791842765 |
| ok | Lines by source!H126 | 2.7101086806006838 | 2.7101086806006838 |
| ok | Lines by source!I126 | 3.012772913657078 | 3.012772913657078 |
| ok | Lines by source!J126 | 3.6181013797698656 | 3.6181013797698656 |
| ok | Lines by source!K126 | 6.982151717746485 | 6.982151717746485 |
| ok | Lines by source!Q126 | 1 | 1 |
| ok | Lines by source!R126 | Low | Low |
| ok | Lines by source!S126 |  |  |
| ok | Lines by source!E127 | 2.190511304669516 | 2.190511304669516 |
| ok | Lines by source!F127 | 0.29189526312122016 | 0.2918952631212205 |
| ok | Lines by source!G127 | 3.6674243491266427 | 3.667424349126643 |
| ok | Lines by source!L127 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M127 | 1.0669203134927314 | 1.066920313492731 |
| ok | Lines by source!Q127 |  |  |
| ok | Lines by source!S127 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E128 | 1.7675937504773587 | 1.7675937504773587 |
| ok | Lines by source!F128 | 0.41162582147613286 | 0.41162582147613286 |
| ok | Lines by source!G128 | 5.799456038344384 | 5.799456038344384 |
| ok | Lines by source!L128 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M128 | 1.2643517756318523 | 1.264351775631852 |
| ok | Lines by source!H128 | 1.3559679290012259 | 1.3559679290012259 |
| ok | Lines by source!I128 | 1.5617808397392923 | 1.5617808397392923 |
| ok | Lines by source!J128 | 1.973406661215425 | 1.973406661215425 |
| ok | Lines by source!K128 | 3.8898580694046307 | 3.8898580694046307 |
| ok | Lines by source!Q128 | 1 | 1 |
| ok | Lines by source!R128 | Low | Low |
| ok | Lines by source!S128 |  |  |
| ok | Lines by source!E129 | 1.989840793059677 | 1.989840793059677 |
| ok | Lines by source!F129 | 0.4867969701798481 | 0.4867969701798481 |
| ok | Lines by source!G129 | 8.731675106211403 | 8.731675106211403 |
| ok | Lines by source!L129 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M129 | 1.335191354225073 | 1.335191354225073 |
| ok | Lines by source!H129 | 1.503043822879829 | 1.503043822879829 |
| ok | Lines by source!I129 | 1.746442307969753 | 1.746442307969753 |
| ok | Lines by source!J129 | 2.2332392781496013 | 2.2332392781496013 |
| ok | Lines by source!K129 | 4.478074859208158 | 4.478074859208158 |
| ok | Lines by source!Q129 | 1 | 1 |
| ok | Lines by source!R129 | Low | Low |
| ok | Lines by source!S129 |  |  |
| ok | Lines by source!E130 | 1.49380419636298 | 1.49380419636298 |
| ok | Lines by source!F130 | 0.20562737624275068 | 0.20562737624275118 |
| ok | Lines by source!G130 | 2.197657917825771 | 2.197657917825771 |
| ok | Lines by source!L130 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M130 | 0.806316079340961 | 0.806316079340961 |
| ok | Lines by source!Q130 |  |  |
| ok | Lines by source!S130 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E131 | 2.8884616834965913 | 2.888461683496591 |
| ok | Lines by source!F131 | 0.6858834011900213 | 0.6858834011900219 |
| ok | Lines by source!G131 | 6.163014771514658 | 6.163014771514658 |
| ok | Lines by source!L131 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M131 | 3.4607863533841217 | 3.460786353384122 |
| ok | Lines by source!H131 | 2.20257828230657 | 2.202578282306569 |
| ok | Lines by source!I131 | 2.5455199829015807 | 2.5455199829015798 |
| ok | Lines by source!J131 | 3.231403384091602 | 3.231403384091602 |
| ok | Lines by source!K131 | 5.009783072434723 | 5.009783072434725 |
| ok | Lines by source!Q131 | 4 | 4 |
| ok | Lines by source!R131 | Moderate-High | Moderate-High |
| ok | Lines by source!S131 |  |  |
| ok | Lines by source!E132 | 2.8856938364695646 | 2.8856938364695646 |
| ok | Lines by source!F132 | 0.5511223935109058 | 0.5511223935109058 |
| ok | Lines by source!G132 | 6.414718968466882 | 6.414718968466882 |
| ok | Lines by source!L132 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M132 | 3.6246728510966824 | 3.6246728510966824 |
| ok | Lines by source!H132 | 2.3345714429586586 | 2.3345714429586586 |
| ok | Lines by source!I132 | 2.6101326397141116 | 2.6101326397141116 |
| ok | Lines by source!J132 | 3.1612550332250176 | 3.1612550332250176 |
| ok | Lines by source!K132 | 4.574032277703024 | 4.574032277703024 |
| ok | Lines by source!Q132 | 4 | 4 |
| ok | Lines by source!R132 | Moderate-High | Moderate-High |
| ok | Lines by source!S132 |  |  |
| ok | Lines by source!E133 | 1.5967745046694737 | 1.596774504669474 |
| ok | Lines by source!F133 | 0.443014490398444 | 0.4430144903984443 |
| ok | Lines by source!G133 | 3.8971538921128452 | 3.897153892112845 |
| ok | Lines by source!L133 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M133 | 1.5044521270246505 | 1.50445212702465 |
| ok | Lines by source!H133 | 1.1537600142710298 | 1.1537600142710296 |
| ok | Lines by source!I133 | 1.3752672594702517 | 1.3752672594702517 |
| ok | Lines by source!J133 | 1.8182817498686956 | 1.818281749868696 |
| ok | Lines by source!K133 | 2.6991364986063426 | 2.699136498606343 |
| ok | Lines by source!Q133 | 3 | 3 |
| ok | Lines by source!R133 | Moderate | Moderate |
| ok | Lines by source!S133 |  |  |
| ok | Lines by source!E134 | 3.503945381984005 | 3.503945381984005 |
| ok | Lines by source!F134 | 0.7900412775280368 | 0.7900412775280354 |
| ok | Lines by source!G134 | 6.906511508778552 | 6.906511508778552 |
| ok | Lines by source!L134 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M134 | 4.471042669628076 | 4.471042669628076 |
| ok | Lines by source!H134 | 2.7139041044559686 | 2.7139041044559695 |
| ok | Lines by source!I134 | 3.108924743219987 | 3.1089247432199874 |
| ok | Lines by source!J134 | 3.8989660207480235 | 3.898966020748023 |
| ok | Lines by source!K134 | 5.720239392240383 | 5.720239392240383 |
| ok | Lines by source!Q134 | 4 | 4 |
| ok | Lines by source!R134 | Moderate-High | Moderate-High |
| ok | Lines by source!S134 |  |  |
| ok | Lines by source!E135 | 3.530152838231762 | 3.530152838231762 |
| ok | Lines by source!F135 | 0.599500452395496 | 0.599500452395496 |
| ok | Lines by source!G135 | 7.411377050165768 | 7.411377050165768 |
| ok | Lines by source!L135 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M135 | 4.704928599551942 | 4.704928599551942 |
| ok | Lines by source!H135 | 2.930652385836266 | 2.930652385836266 |
| ok | Lines by source!I135 | 3.230402612034014 | 3.230402612034014 |
| ok | Lines by source!J135 | 3.82990306442951 | 3.82990306442951 |
| ok | Lines by source!K135 | 5.453105303353815 | 5.453105303353815 |
| ok | Lines by source!Q135 | 4 | 4 |
| ok | Lines by source!R135 | Moderate-High | Moderate-High |
| ok | Lines by source!S135 |  |  |
| ok | Lines by source!E136 | 2.075521734757535 | 2.075521734757535 |
| ok | Lines by source!F136 | 0.46355367019826216 | 0.463553670198263 |
| ok | Lines by source!G136 | 4.527155320116291 | 4.527155320116291 |
| ok | Lines by source!L136 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M136 | 1.8181981397616722 | 1.818198139761672 |
| ok | Lines by source!H136 | 1.6119680645592729 | 1.611968064559272 |
| ok | Lines by source!I136 | 1.8437448996584038 | 1.8437448996584034 |
| ok | Lines by source!J136 | 2.307298569856666 | 2.3072985698566666 |
| ok | Lines by source!K136 | 3.4917895575898035 | 3.4917895575898026 |
| ok | Lines by source!Q136 | 2 | 2 |
| ok | Lines by source!R136 | Moderate-Low | Moderate-Low |
| ok | Lines by source!S136 |  |  |
| ok | Lines by source!E137 | 1.2878313046176861 | 1.2878313046176864 |
| ok | Lines by source!F137 | 0.23618090878450623 | 0.23618090878450543 |
| ok | Lines by source!G137 | 2.6535773354288854 | 2.653577335428885 |
| ok | Lines by source!L137 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M137 | 1.2743910279761643 | 1.274391027976164 |
| ok | Lines by source!H137 | 1.05165039583318 | 1.0516503958331809 |
| ok | Lines by source!I137 | 1.169740850225433 | 1.1697408502254336 |
| ok | Lines by source!J137 | 1.4059217590099393 | 1.405921759009939 |
| ok | Lines by source!K137 | 2.097981189920541 | 2.097981189920542 |
| ok | Lines by source!Q137 | 3 | 3 |
| ok | Lines by source!R137 | Moderate | Moderate |
| ok | Lines by source!S137 |  |  |
| ok | Lines by source!E138 | 1.3321382001444686 | 1.3321382001444686 |
| ok | Lines by source!F138 | 0.18740785001006177 | 0.18740785001006177 |
| ok | Lines by source!G138 | 2.4964632071865442 | 2.4964632071865442 |
| ok | Lines by source!L138 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M138 | 1.2817532720019105 | 1.2817532720019105 |
| ok | Lines by source!Q138 |  |  |
| ok | Lines by source!S138 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E139 | 1.3443443501775973 | 1.3443443501775976 |
| ok | Lines by source!F139 | 0.2618630148379247 | 0.261863014837925 |
| ok | Lines by source!G139 | 2.8084901945741167 | 2.808490194574117 |
| ok | Lines by source!L139 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M139 | 0.6718595186986783 | 0.6718595186986783 |
| ok | Lines by source!Q139 |  |  |
| ok | Lines by source!S139 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E140 | 1.03682587069295 | 1.03682587069295 |
| ok | Lines by source!F140 | 0.18329451527920002 | 0.18329451527920002 |
| ok | Lines by source!G140 | 2.0388662146704837 | 2.038866214670484 |
| ok | Lines by source!L140 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M140 | 1.090469782017345 | 1.090469782017345 |
| ok | Lines by source!H140 | 0.85353135541375 | 0.85353135541375 |
| ok | Lines by source!I140 | 0.94517861305335 | 0.94517861305335 |
| ok | Lines by source!J140 | 1.12847312833255 | 1.12847312833255 |
| ok | Lines by source!K140 | 1.5124377842607981 | 1.5124377842607983 |
| ok | Lines by source!Q140 | 3 | 3 |
| ok | Lines by source!R140 | Moderate | Moderate |
| ok | Lines by source!S140 |  |  |
| ok | Lines by source!E141 | 0.9464036705812997 | 0.9464036705812997 |
| ok | Lines by source!F141 | 0.17566059807415266 | 0.17566059807415266 |
| ok | Lines by source!G141 | 1.4570541868550897 | 1.4570541868550897 |
| ok | Lines by source!L141 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M141 | 1.2064995586031646 | 1.2064995586031646 |
| ok | Lines by source!Q141 |  |  |
| ok | Lines by source!S141 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E142 | 0.6264901049776348 | 0.6264901049776348 |
| ok | Lines by source!F142 | 0.1442227915124758 | 0.1442227915124758 |
| ok | Lines by source!G142 | 1.317066342919824 | 1.317066342919824 |
| ok | Lines by source!L142 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M142 | 0.5625486737210279 | 0.5625486737210279 |
| ok | Lines by source!Q142 |  |  |
| ok | Lines by source!S142 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E143 | 0.15336194090189578 | 0.1533619409018958 |
| ok | Lines by source!F143 | 0.02333604440914749 | 0.023336044409147595 |
| ok | Lines by source!G143 | 0.48215484939161274 | 0.4821548493916127 |
| ok | Lines by source!L143 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M143 | 0.11564561938673575 | 0.1156456193867357 |
| ok | Lines by source!H143 | 0.1300258964927483 | 0.1300258964927482 |
| ok | Lines by source!I143 | 0.14169391869732204 | 0.141693918697322 |
| ok | Lines by source!J143 | 0.16502996310646953 | 0.1650299631064696 |
| ok | Lines by source!K143 | 0.2801508873729789 | 0.28015088737297894 |
| ok | Lines by source!Q143 | 1 | 1 |
| ok | Lines by source!R143 | Low | Low |
| ok | Lines by source!S143 |  |  |
| ok | Lines by source!E144 | 0.12525515063716344 | 0.12525515063716344 |
| ok | Lines by source!F144 | 0.03523291031499291 | 0.03523291031499291 |
| ok | Lines by source!G144 | 0.7183764048739874 | 0.7183764048739874 |
| ok | Lines by source!L144 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M144 | 0.04226356389117069 | 0.04226356389117069 |
| ok | Lines by source!H144 | 0.09002224032217053 | 0.09002224032217053 |
| ok | Lines by source!I144 | 0.10763869547966698 | 0.10763869547966698 |
| ok | Lines by source!J144 | 0.1428716057946599 | 0.1428716057946599 |
| ok | Lines by source!K144 | 0.3985991434127468 | 0.3985991434127468 |
| ok | Lines by source!Q144 | 1 | 1 |
| ok | Lines by source!R144 | Low | Low |
| ok | Lines by source!S144 |  |  |
| ok | Lines by source!E145 | 0.2879071917007874 | 0.2879071917007874 |
| ok | Lines by source!F145 | 0.11485245683360562 | 0.11485245683360575 |
| ok | Lines by source!G145 | 0.8386609772930828 | 0.8386609772930828 |
| ok | Lines by source!L145 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M145 | 0.20537020569639608 | 0.2053702056963961 |
| ok | Lines by source!H145 | 0.17305473486718176 | 0.17305473486718165 |
| ok | Lines by source!I145 | 0.23048096328398457 | 0.2304809632839845 |
| ok | Lines by source!J145 | 0.34533342011759016 | 0.3453334201175903 |
| ok | Lines by source!K145 | 0.6075635575956757 | 0.6075635575956757 |
| ok | Lines by source!Q145 | 2 | 2 |
| ok | Lines by source!R145 | Moderate-Low | Moderate-Low |
| ok | Lines by source!S145 |  |  |
| ok | Lines by source!E146 | 2.5776648778148967 | 2.5776648778148967 |
| ok | Lines by source!F146 | 0.4747582359200862 | 0.47475823592008554 |
| ok | Lines by source!G146 | 4.792056353654756 | 4.792056353654756 |
| ok | Lines by source!L146 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M146 | 2.4805064293802452 | 2.480506429380245 |
| ok | Lines by source!H146 | 2.1029066418948106 | 2.102906641894811 |
| ok | Lines by source!I146 | 2.3402857598548534 | 2.340285759854854 |
| ok | Lines by source!J146 | 2.81504399577494 | 2.8150439957749396 |
| ok | Lines by source!K146 | 4.12181248425542 | 4.12181248425542 |
| ok | Lines by source!Q146 | 3 | 3 |
| ok | Lines by source!R146 | Moderate | Moderate |
| ok | Lines by source!S146 |  |  |
| ok | Lines by source!E147 | 2.6555412112520678 | 2.6555412112520678 |
| ok | Lines by source!F147 | 0.38379127163803517 | 0.38379127163803517 |
| ok | Lines by source!G147 | 4.248676340707577 | 4.248676340707577 |
| ok | Lines by source!L147 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M147 | 2.530516394496246 | 2.530516394496246 |
| ok | Lines by source!Q147 |  |  |
| ok | Lines by source!S147 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E148 | 2.368344093818239 | 2.368344093818239 |
| ok | Lines by source!F148 | 0.3656187980833281 | 0.36561879808332776 |
| ok | Lines by source!G148 | 4.681942738741334 | 4.681942738741334 |
| ok | Lines by source!L148 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M148 | 1.4397783981161023 | 1.439778398116102 |
| ok | Lines by source!Q148 |  |  |
| ok | Lines by source!S148 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E149 | 1.2087499488700577 | 1.208749948870058 |
| ok | Lines by source!F149 | 0.2621939125793908 | 0.2621939125793914 |
| ok | Lines by source!G149 | 2.3374018750054835 | 2.337401875005483 |
| ok | Lines by source!L149 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M149 | 1.206115401404081 | 1.206115401404081 |
| ok | Lines by source!H149 | 0.9465560362906669 | 0.9465560362906665 |
| ok | Lines by source!I149 | 1.0776529925803624 | 1.0776529925803622 |
| ok | Lines by source!J149 | 1.339846905159753 | 1.3398469051597537 |
| ok | Lines by source!K149 | 1.8015561757597054 | 1.8015561757597065 |
| ok | Lines by source!Q149 | 3 | 3 |
| ok | Lines by source!R149 | Moderate | Moderate |
| ok | Lines by source!S149 |  |  |
| ok | Lines by source!E150 | 1.1393678742078506 | 1.1393678742078506 |
| ok | Lines by source!F150 | 0.24379131698529033 | 0.24379131698529033 |
| ok | Lines by source!G150 | 2.038939246794036 | 2.038939246794036 |
| ok | Lines by source!L150 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M150 | 1.2487631224943354 | 1.2487631224943354 |
| ok | Lines by source!H150 | 0.8955765572225602 | 0.8955765572225602 |
| ok | Lines by source!I150 | 1.0174722157152054 | 1.0174722157152054 |
| ok | Lines by source!J150 | 1.2612635327004957 | 1.2612635327004957 |
| ok | Lines by source!K150 | 1.9950142598875207 | 1.9950142598875207 |
| ok | Lines by source!Q150 | 3 | 3 |
| ok | Lines by source!R150 | Moderate | Moderate |
| ok | Lines by source!S150 |  |  |
| ok | Lines by source!E151 | 0.9437910322530179 | 0.9437910322530179 |
| ok | Lines by source!F151 | 0.21076131827011996 | 0.21076131827011982 |
| ok | Lines by source!G151 | 1.9441219292817395 | 1.94412192928174 |
| ok | Lines by source!L151 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M151 | 0.767918879417424 | 0.767918879417424 |
| ok | Lines by source!Q151 |  |  |
| ok | Lines by source!S151 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E152 | 85.39569234987228 | 85.39569234987228 |
| ok | Lines by source!F152 | 1.8126088726501912 | 1.8126088726501912 |
| ok | Lines by source!G152 | 115.40725486972272 | 115.4072548697227 |
| ok | Lines by source!L152 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M152 | 86.75395050652514 | 86.75395050652514 |
| ok | Lines by source!H152 | 83.58308347722209 | 83.58308347722209 |
| ok | Lines by source!I152 | 84.48938791354718 | 84.48938791354718 |
| ok | Lines by source!J152 | 86.30199678619738 | 86.30199678619738 |
| ok | Lines by source!K152 | 94.68228339961314 | 94.68228339961314 |
| ok | Lines by source!Q152 | 4 | 4 |
| ok | Lines by source!R152 | Moderate-High | Moderate-High |
| ok | Lines by source!S152 |  |  |
| ok | Lines by source!E153 | 85.05323222695057 | 85.05323222695057 |
| ok | Lines by source!F153 | 3.2749995359819026 | 3.2749995359819026 |
| ok | Lines by source!G153 | 90.80456982660839 | 90.80456982660839 |
| ok | Lines by source!L153 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M153 | 87.93662718269165 | 87.93662718269165 |
| ok | Lines by source!Q153 |  |  |
| ok | Lines by source!S153 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E154 | 90.50312306604258 | 90.50312306604258 |
| ok | Lines by source!F154 | 4.929037784549017 | 4.929037784549017 |
| ok | Lines by source!G154 | 98.01402035920833 | 98.01402035920833 |
| ok | Lines by source!L154 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M154 | 80.46011871917379 | 80.46011871917379 |
| ok | Lines by source!Q154 |  |  |
| ok | Lines by source!S154 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E155 | 3.0953349624616706 | 3.095334962461671 |
| ok | Lines by source!F155 | 5.724253752014427 | 5.724253752014427 |
| ok | Lines by source!G155 | 8.997105092584604 | 8.997105092584604 |
| ok | Lines by source!L155 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M155 | -7.47650846351786 | -7.47650846351786 |
| ok | Lines by source!Q155 |  |  |
| ok | Lines by source!S155 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E156 | 4.747621781233882 | 4.747621781233882 |
| ok | Lines by source!F156 | 4.790736243869452 | 4.790736243869449 |
| ok | Lines by source!G156 | 11.582566207791047 | 11.58256620779105 |
| ok | Lines by source!L156 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M156 | -6.293831787351351 | -6.293831787351351 |
| ok | Lines by source!Q156 |  |  |
| ok | Lines by source!S156 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E157 | 39.043987447485875 | 39.04398744748588 |
| ok | Lines by source!F157 | 6.47567007945139 | 6.47567007945139 |
| ok | Lines by source!G157 | 75.39444814591982 | 75.39444814591982 |
| ok | Lines by source!L157 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M157 | 75.39444814591982 | 75.39444814591982 |
| ok | Lines by source!H157 | 32.568317368034485 | 32.56831736803449 |
| ok | Lines by source!I157 | 35.80615240776018 | 35.80615240776019 |
| ok | Lines by source!J157 | 42.28182248721157 | 42.28182248721158 |
| ok | Lines by source!K157 | 74.48343698436494 | 74.48343698436494 |
| ok | Lines by source!Q157 | 5 | 5 |
| ok | Lines by source!R157 | High | High |
| ok | Lines by source!S157 |  |  |
| ok | Lines by source!E158 | 38.27089723188468 | 38.27089723188468 |
| ok | Lines by source!F158 | 8.35026879541986 | 8.350268795419854 |
| ok | Lines by source!G158 | 80.99089140015627 | 80.99089140015627 |
| ok | Lines by source!L158 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M158 | 78.30700461494897 | 78.30700461494897 |
| ok | Lines by source!H158 | 29.920628436464824 | 29.920628436464828 |
| ok | Lines by source!I158 | 34.09576283417475 | 34.09576283417476 |
| ok | Lines by source!J158 | 42.446031629594614 | 42.44603162959461 |
| ok | Lines by source!K158 | 78.74063632759871 | 78.74063632759871 |
| ok | Lines by source!Q158 | 4 | 4 |
| ok | Lines by source!R158 | Moderate-High | Moderate-High |
| ok | Lines by source!S158 |  |  |
| ok | Lines by source!E159 | 41.38114166069304 | 41.38114166069303 |
| ok | Lines by source!F159 | 3.9891114096937077 | 3.9891114096937184 |
| ok | Lines by source!G159 | 61.27269242142023 | 61.27269242142023 |
| ok | Lines by source!L159 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M159 | 60.69541942774161 | 60.69541942774161 |
| ok | Lines by source!Q159 |  |  |
| ok | Lines by source!S159 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E160 | -11.959999248875647 | -11.959999248875645 |
| ok | Lines by source!F160 | 12.559877171012783 | 12.559877171012792 |
| ok | Lines by source!G160 | 19.45006895576618 | 19.45006895576618 |
| ok | Lines by source!L160 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M160 | -17.611585187207353 | -17.61158518720735 |
| ok | Lines by source!Q160 |  |  |
| ok | Lines by source!S160 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E161 | -5.048679499105322 | -5.048679499105322 |
| ok | Lines by source!F161 | 7.472375391453183 | 7.472375391453182 |
| ok | Lines by source!G161 | 7.86329008337524 | 7.86329008337524 |
| ok | Lines by source!L161 | 2025Q4 | 2025Q4 |
| ok | Lines by source!M161 | -14.699028718178212 | -14.69902871817821 |
| ok | Lines by source!Q161 |  |  |
| ok | Lines by source!S161 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E162 | 9.5 | 9.5 |
| ok | Lines by source!F162 | 0.45219299999999957 | 0.45219299999999957 |
| ok | Lines by source!G162 | 11.01 | 11.01 |
| ok | Lines by source!L162 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M162 | 10.15 | 10.15 |
| ok | Lines by source!Q162 |  |  |
| ok | Lines by source!S162 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Lines by source!E163 | 4.215576591869578 | 4.215576591869578 |
| ok | Lines by source!F163 | 0.8587105567365916 | 0.8587105567365929 |
| ok | Lines by source!G163 | 10.327957313003356 | 10.32795731300336 |
| ok | Lines by source!L163 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M163 | 4.009514461690263 | 4.009514461690263 |
| ok | Lines by source!H163 | 3.3568660351329864 | 3.3568660351329846 |
| ok | Lines by source!I163 | 3.786221313501282 | 3.786221313501281 |
| ok | Lines by source!J163 | 4.6449318702378735 | 4.644931870237874 |
| ok | Lines by source!K163 | 6.954778878346481 | 6.954778878346481 |
| ok | Lines by source!Q163 | 3 | 3 |
| ok | Lines by source!R163 | Moderate | Moderate |
| ok | Lines by source!S163 |  |  |
| ok | Lines by source!E164 | 5.040919240726448 | 5.040919240726448 |
| ok | Lines by source!F164 | 0.9112040405828625 | 0.9112040405828625 |
| ok | Lines by source!G164 | 11.261249252680265 | 11.26124925268027 |
| ok | Lines by source!L164 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M164 | 5.194125778490533 | 5.194125778490533 |
| ok | Lines by source!H164 | 4.129715200143586 | 4.129715200143586 |
| ok | Lines by source!I164 | 4.585317220435017 | 4.585317220435017 |
| ok | Lines by source!J164 | 5.49652126101788 | 5.49652126101788 |
| ok | Lines by source!K164 | 7.982491308540245 | 7.982491308540245 |
| ok | Lines by source!Q164 | 3 | 3 |
| ok | Lines by source!R164 | Moderate | Moderate |
| ok | Lines by source!S164 |  |  |
| ok | Lines by source!E165 | 0.17472161287886812 | 0.1747216128788681 |
| ok | Lines by source!F165 | 0.10849104164753649 | 0.10849104164753659 |
| ok | Lines by source!G165 | 3.0906468540423884 | 3.090646854042388 |
| ok | Lines by source!L165 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M165 | -0.019378006304722882 | -0.01937800630472288 |
| ok | Lines by source!H165 | 0.06623057123133162 | 0.0662305712313315 |
| ok | Lines by source!I165 | 0.12047609205509988 | 0.12047609205509979 |
| ok | Lines by source!J165 | 0.22896713370263636 | 0.22896713370263638 |
| ok | Lines by source!K165 | 0.6457844088927323 | 0.6457844088927325 |
| ok | Lines by source!Q165 | 1 | 1 |
| ok | Lines by source!R165 | Low | Low |
| ok | Lines by source!S165 |  |  |
| ok | Lines by source!E166 | 0.242904101257147 | 0.242904101257147 |
| ok | Lines by source!F166 | 0.0905451883389113 | 0.09054518833891122 |
| ok | Lines by source!G166 | 3.192798104447804 | 3.192798104447804 |
| ok | Lines by source!L166 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M166 | 0.08750898529165822 | 0.08750898529165822 |
| ok | Lines by source!H166 | 0.15235891291823572 | 0.15235891291823578 |
| ok | Lines by source!I166 | 0.19763150708769137 | 0.1976315070876914 |
| ok | Lines by source!J166 | 0.2881766954266027 | 0.2881766954266026 |
| ok | Lines by source!K166 | 0.6644465471181134 | 0.6644465471181135 |
| ok | Lines by source!Q166 | 1 | 1 |
| ok | Lines by source!R166 | Low | Low |
| ok | Lines by source!S166 |  |  |
| ok | Lines by source!E167 | 1.1141675219361389 | 1.114167521936139 |
| ok | Lines by source!F167 | 0.2788136824149038 | 0.27881368241490245 |
| ok | Lines by source!G167 | 2.9986928936336716 | 2.998692893633672 |
| ok | Lines by source!L167 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M167 | 1.6138446897622272 | 1.613844689762227 |
| ok | Lines by source!H167 | 0.8353538395212351 | 0.8353538395212367 |
| ok | Lines by source!I167 | 0.974760680728687 | 0.9747606807286879 |
| ok | Lines by source!J167 | 1.2535743631435907 | 1.2535743631435903 |
| ok | Lines by source!K167 | 1.9912746088176738 | 1.9912746088176747 |
| ok | Lines by source!Q167 | 4 | 4 |
| ok | Lines by source!R167 | Moderate-High | Moderate-High |
| ok | Lines by source!S167 |  |  |
| ok | Lines by source!E168 | 1.5385651932231141 | 1.538565193223114 |
| ok | Lines by source!F168 | 0.3000551669728642 | 0.3000551669728659 |
| ok | Lines by source!G168 | 3.570809928981094 | 3.570809928981094 |
| ok | Lines by source!L168 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M168 | 2.0372465877364028 | 2.037246587736403 |
| ok | Lines by source!H168 | 1.23851002625025 | 1.238510026250248 |
| ok | Lines by source!I168 | 1.388537609736682 | 1.388537609736681 |
| ok | Lines by source!J168 | 1.6885927767095463 | 1.6885927767095468 |
| ok | Lines by source!K168 | 2.6335033989487284 | 2.6335033989487275 |
| ok | Lines by source!Q168 | 4 | 4 |
| ok | Lines by source!R168 | Moderate-High | Moderate-High |
| ok | Lines by source!S168 |  |  |
| ok | Lines by source!AB4 | Spearman, value | Spearman, value |
| ok | Lines by source!AC4 | Spearman, change | Spearman, change |
| ok | Lines by source!AD4 | Quarters tested | Quarters tested |
| ok | Lines by source!AB5 | 0.4431250086600857 | 0.4431250086600857 |
| ok | Lines by source!AC5 | -0.41825170642210446 | -0.4182517064221045 |
| ok | Lines by source!AD5 | 35 | 35 |
| ok | Lines by source!AE5 | 0.3409102440362786 | 0.3409102440362786 |
| ok | Lines by source!AF5 | -0.24080903304395795 | -0.240809033043958 |
| ok | Lines by source!AG5 | -0.24224042575194749 | -0.2422404257519475 |
| ok | Lines by source!AH5 |  | None |
| ok | Lines by source!AI5 |  | None |
| ok | Lines by source!AB91 |  | None |
| ok | Lines by source!AC91 |  | None |
| ok | Lines by source!AD91 | 0 | 0 |
| ok | Lines by source!B174 | Auto - Net charge-offs - KeyBank: Not tested: 15 observations after smoothing; at least mi | Auto - Net charge-offs - KeyBank: Not tested: 15 observations after smoothing; at least mi |

## B3 · On Decide, click Credit card and Nonaccrual, and pick KeyBank under Lines set from: 59 of 59

One row shows; the lines are KeyBank's own; every source is rated on them, beside what its own history would give.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | visible_rows | [14] | [14] |
| ok | Decide!B67 | Credit card, nonaccrual: lines set from KeyBank | Credit card, nonaccrual: lines set from KeyBank |
| ok | Decide!I67 | KeyBank: 5 High | KeyBank: 5 High |
| ok | Decide!B68 | Check: OK, your settings fit the history the lines are set from. | Check: OK, your settings fit the history the lines are set from. |
| ok | Decide!M73 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Decide!M74 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Decide!M75 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Decide!M76 | 0.6295871211811148 | 0.629587121181115 |
| ok | Decide!M80 | 1 Low | 1 Low |
| ok | Decide!N80 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Decide!M94 | 0.09647239943711843 | 0.09647239943711848 |
| ok | Decide!N94 | 0.11161296908757563 | 0.11161296908757568 |
| ok | Decide!O94 | 0.14189410838849006 | 0.14189410838849004 |
| ok | Decide!P94 | 0.26956719550232344 | 0.26956719550232344 |
| ok | Decide!Q94 | 0.6498546849136658 | 0.6498546849136658 |
| ok | Decide!M81 | 1 Low | 1 Low |
| ok | Decide!N81 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Decide!M95 | 0.02238391084968984 | 0.02238391084968984 |
| ok | Decide!N95 | 0.030538814545335986 | 0.030538814545335986 |
| ok | Decide!O95 | 0.04684862193662828 | 0.04684862193662828 |
| ok | Decide!P95 | 0.14753123968182763 | 0.14753123968182763 |
| ok | Decide!Q95 | 1.1988194225041855 | 1.1988194225041855 |
| ok | Decide!M82 | 5 High | 5 High |
| ok | Decide!N82 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Decide!M96 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Decide!N96 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Decide!O96 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Decide!P96 | 0.6295871211811148 | 0.629587121181115 |
| ok | Decide!Q96 | 1.8086714674791118 | 1.808671467479112 |
| ok | Thresholds!D9 | KeyBank | KeyBank |
| ok | Thresholds!E9 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Thresholds!F9 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Thresholds!G9 | 1.8086714674791118 | 1.808671467479112 |
| ok | Thresholds!H9 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Thresholds!I9 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Thresholds!J9 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Thresholds!K9 | 0.6295871211811148 | 0.629587121181115 |
| ok | Thresholds!Q9 | 1 Low | 1 Low |
| ok | Thresholds!P9 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Thresholds!O9 | 1 Low | 1 Low |
| ok | Thresholds!N9 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Thresholds!M9 | 5 High | 5 High |
| ok | Thresholds!L9 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!E19 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Lines by source!F19 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Lines by source!G19 | 1.8086714674791118 | 1.808671467479112 |
| ok | Lines by source!L19 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!H19 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Lines by source!I19 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Lines by source!J19 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Lines by source!K19 | 0.6295871211811148 | 0.629587121181115 |
| ok | Lines by source!Q19 | 5 | 5 |
| ok | Lines by source!R19 | High | High |
| ok | Lines by source!S19 |  |  |
| ok | Decide!L107 | Fits below 1.00, where Moderate-Low begins. It fits. | Fits below 1.00, where Moderate-Low begins. It fits. |
| ok | Decide!L108 | Fits above 0.50, and below 2.98 so line 2 stays above zero. It fits. | Fits above 0.50, and below 2.98 so line 2 stays above zero. It fits. |
| ok | Decide!L109 | Fits above 0.34 (High beyond Moderate-High) and up to 10.98 (some quarter kept can rate Hi | Fits above 0.34 (High beyond Moderate-High) and up to 10.98 (some quarter kept can rate Hi |
| ok | Decide!L110 | Either fits. | Either fits. |

## B4 · Type 3.5 under How rare High is (z), in the yellow row: 55 of 55

High's line moves for every source of the row; Thresholds and Summary follow.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Thresholds!D9 | KeyBank | KeyBank |
| ok | Thresholds!E9 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Thresholds!F9 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Thresholds!G9 | 1.8086714674791118 | 1.808671467479112 |
| ok | Thresholds!H9 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Thresholds!I9 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Thresholds!J9 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Thresholds!K9 | 0.7685831667662775 | 0.7685831667662779 |
| ok | Thresholds!Q9 | 1 Low | 1 Low |
| ok | Thresholds!P9 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Thresholds!O9 | 1 Low | 1 Low |
| ok | Thresholds!N9 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Thresholds!M9 | 4 Moderate-High | 4 Moderate-High |
| ok | Thresholds!L9 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!E17 | 0.12675353873803286 | 0.12675353873803286 |
| ok | Lines by source!F17 | 0.030281139300914434 | 0.030281139300914372 |
| ok | Lines by source!G17 | 0.6498546849136658 | 0.6498546849136658 |
| ok | Lines by source!L17 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M17 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Lines by source!H17 | 0.09647239943711843 | 0.09647239943711848 |
| ok | Lines by source!I17 | 0.11161296908757563 | 0.11161296908757568 |
| ok | Lines by source!J17 | 0.14189410838849006 | 0.14189410838849004 |
| ok | Lines by source!K17 | 0.3266926582080397 | 0.3266926582080397 |
| ok | Lines by source!Q17 | 1 | 1 |
| ok | Lines by source!R17 | Low | Low |
| ok | Lines by source!S17 |  |  |
| ok | Lines by source!E18 | 0.03869371824098213 | 0.03869371824098213 |
| ok | Lines by source!F18 | 0.016309807391292293 | 0.016309807391292293 |
| ok | Lines by source!G18 | 1.1988194225041855 | 1.1988194225041855 |
| ok | Lines by source!L18 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M18 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Lines by source!H18 | 0.02238391084968984 | 0.02238391084968984 |
| ok | Lines by source!I18 | 0.030538814545335986 | 0.030538814545335986 |
| ok | Lines by source!J18 | 0.04684862193662828 | 0.04684862193662828 |
| ok | Lines by source!K18 | 0.19106624825816584 | 0.19106624825816584 |
| ok | Lines by source!Q18 | 1 | 1 |
| ok | Lines by source!R18 | Low | Low |
| ok | Lines by source!S18 |  |  |
| ok | Lines by source!E19 | 0.28209700721820813 | 0.2820970072182082 |
| ok | Lines by source!F19 | 0.09472939802198616 | 0.09472939802198616 |
| ok | Lines by source!G19 | 1.8086714674791118 | 1.808671467479112 |
| ok | Lines by source!L19 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!H19 | 0.18736760919622197 | 0.18736760919622203 |
| ok | Lines by source!I19 | 0.23473230820721505 | 0.2347323082072151 |
| ok | Lines by source!J19 | 0.32946170622920123 | 0.32946170622920123 |
| ok | Lines by source!K19 | 0.7685831667662775 | 0.7685831667662779 |
| ok | Lines by source!Q19 | 4 | 4 |
| ok | Lines by source!R19 | Moderate-High | Moderate-High |
| ok | Lines by source!S19 |  |  |
| ok | Summary!D11 | 4 Moderate-High | 4 Moderate-High |
| ok | Decide!L107 | Fits below 1.00, where Moderate-Low begins. It fits. | Fits below 1.00, where Moderate-Low begins. It fits. |
| ok | Decide!L108 | Fits above 0.50, and below 2.98 so line 2 stays above zero. It fits. | Fits above 0.50, and below 2.98 so line 2 stays above zero. It fits. |
| ok | Decide!L109 | Fits above 0.34 (High beyond Moderate-High) and up to 10.98 (some quarter kept can rate Hi | Fits above 0.34 (High beyond Moderate-High) and up to 10.98 (some quarter kept can rate Hi |
| ok | Decide!L110 | Either fits. | Either fits. |

## B5 · Leave out 2012Q3 to 2013Q4, the period Decide suggests, with a reason: 41 of 41

KeyBank's lines move as the reference says; the other sources' own lines do not; Assess lists the period under KeyBank's series, its Status whole.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!D101 | Leave out 2012Q3 to 2013Q4 | Leave out 2012Q3 to 2013Q4 |
| ok | Assess!N186 | Credit card - Nonaccrual - KeyBank | Credit card - Nonaccrual - KeyBank |
| ok | Assess!T186 | Left out: 6 quarters | Left out: 6 quarters |
| ok | Lines by source!E19 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Lines by source!F19 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Lines by source!G19 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Lines by source!L19 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!H19 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Lines by source!I19 | 0.235387727674618 | 0.235387727674618 |
| ok | Lines by source!J19 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Lines by source!K19 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Lines by source!Q19 | 5 | 5 |
| ok | Lines by source!R19 | High | High |
| ok | Lines by source!S19 |  |  |
| ok | Lines by source!E17 | 0.12675353873803286 | 0.12675353873803286 |
| ok | Lines by source!F17 | 0.030281139300914434 | 0.030281139300914372 |
| ok | Lines by source!G17 | 0.6498546849136658 | 0.6498546849136658 |
| ok | Lines by source!L17 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M17 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Lines by source!H17 | 0.09647239943711843 | 0.09647239943711848 |
| ok | Lines by source!I17 | 0.11161296908757563 | 0.11161296908757568 |
| ok | Lines by source!J17 | 0.14189410838849006 | 0.14189410838849004 |
| ok | Lines by source!K17 | 0.3266926582080397 | 0.3266926582080397 |
| ok | Lines by source!Q17 | 1 | 1 |
| ok | Lines by source!R17 | Low | Low |
| ok | Lines by source!S17 |  |  |
| ok | Thresholds!D9 | KeyBank | KeyBank |
| ok | Thresholds!E9 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Thresholds!F9 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Thresholds!G9 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Thresholds!H9 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Thresholds!I9 | 0.235387727674618 | 0.235387727674618 |
| ok | Thresholds!J9 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Thresholds!K9 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Thresholds!Q9 | 1 Low | 1 Low |
| ok | Thresholds!P9 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Thresholds!O9 | 1 Low | 1 Low |
| ok | Thresholds!N9 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Thresholds!M9 | 5 High | 5 High |
| ok | Thresholds!L9 | 0.6908132947833397 | 0.6908132947833397 |

## B6 · Clear the reason: 3 of 3

The lines are refused, saying why and what to do.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Lines by source!S19 | Refused: a period left out for this product is not whole; its Status on Assess says what i | Refused: a period left out for this product is not whole; its Status on Assess says what i |
| ok | Thresholds!S9 | To fix: Finish its row on Decide | To fix: Finish its row on Decide (product, From, To and a reason), or clear all four of it |
| ok | Decide!N14 | Refused: see the fix below | Refused: see the fix below |

## B6b · Type the reason back: 26 of 26

The lines are back as in B5.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Lines by source!E19 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Lines by source!F19 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Lines by source!G19 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Lines by source!L19 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!H19 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Lines by source!I19 | 0.235387727674618 | 0.235387727674618 |
| ok | Lines by source!J19 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Lines by source!K19 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Lines by source!Q19 | 5 | 5 |
| ok | Lines by source!R19 | High | High |
| ok | Lines by source!S19 |  |  |
| ok | Thresholds!D9 | KeyBank | KeyBank |
| ok | Thresholds!E9 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Thresholds!F9 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Thresholds!G9 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Thresholds!H9 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Thresholds!I9 | 0.235387727674618 | 0.235387727674618 |
| ok | Thresholds!J9 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Thresholds!K9 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Thresholds!Q9 | 1 Low | 1 Low |
| ok | Thresholds!P9 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Thresholds!O9 | 1 Low | 1 Low |
| ok | Thresholds!N9 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Thresholds!M9 | 5 High | 5 High |
| ok | Thresholds!L9 | 0.6908132947833397 | 0.6908132947833397 |

## B7 · Pick Accept these lines and write a note: 4 of 4

The count at the top; the decision on Thresholds, and on Lines by source beside the source the lines are set from.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!L1 | Decided: 1 of 56 · accepted 1 · rejected 0 | Decided: 1 of 56 · accepted 1 · rejected 0 |
| ok | Thresholds!R9 | Accept these lines | Accept these lines |
| ok | Lines by source!O19 | Accept these lines | Accept these lines |
| ok | Lines by source!O17 |  |  |

## B8 · Click Auto and Net charge-offs, and pick Industry (every bank) under Lines set from: 31 of 31

KeyBank's life-to-date history (15 quarters) rated on the lines the industry's longer history gives; Summary agrees.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | visible_rows | [38] | [38] |
| ok | Decide!B67 | Auto, net charge-offs: lines set from Industry (every bank) | Auto, net charge-offs: lines set from Industry (every bank) |
| ok | Decide!I67 | No rating: see the Check | No rating: see the Check |
| ok | Summary!M18 | Refused | Refused |
| ok | Decide!B68 | Refused: High would begin beyond the worst quarter kept | Refused: High would begin beyond the worst quarter kept |
| ok | Decide!M80 | No rating | No rating |
| ok | Decide!N80 | 0.9878539701554716 | 0.9878539701554716 |
| ok | Decide!M94 | Refused | Refused |
| ok | Decide!Q94 | 1.1581294738640815 | 1.158129473864081 |
| ok | Decide!M81 | No rating | No rating |
| ok | Decide!N81 | 0.8774784779654787 | 0.8774784779654787 |
| ok | Decide!M95 | Refused | Refused |
| ok | Decide!Q95 | 1.0470816731822656 | 1.0470816731822656 |
| ok | Decide!M82 | No rating | No rating |
| ok | Decide!N82 | 0.09593421653723161 | 0.09593421653723161 |
| ok | Decide!M96 | Refused | Refused |
| ok | Decide!Q96 | 0.3152509896784223 | 0.3152509896784223 |
| ok | Thresholds!D33 | Industry (every bank) | Industry (every bank) |
| ok | Thresholds!E33 | 0.6548820936069344 | 0.6548820936069344 |
| ok | Thresholds!F33 | 0.1479304022170215 | 0.1479304022170215 |
| ok | Thresholds!G33 | 1.1581294738640815 | 1.158129473864081 |
| ok | Thresholds!H33 |  |  |
| ok | Thresholds!I33 |  |  |
| ok | Thresholds!J33 |  |  |
| ok | Thresholds!K33 |  |  |
| ok | Thresholds!Q33 | Refused | Refused |
| ok | Thresholds!P33 | 0.9878539701554716 | 0.9878539701554716 |
| ok | Thresholds!O33 | Refused | Refused |
| ok | Thresholds!N33 | 0.8774784779654787 | 0.8774784779654787 |
| ok | Thresholds!M33 | Refused | Refused |
| ok | Thresholds!L33 | 0.09593421653723161 | 0.09593421653723161 |

## B9 · Click Mortgage and Net charge-offs, and pick Industry (every bank): 25 of 25

Refused, with what to type.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!B68 | Refused: Moderate-Low would begin at or below zero | Refused: Moderate-Low would begin at or below zero |
| ok | Decide!I68 | To fix:  | To fix: Lower Moderate-Low begins to 0.99 or less. |
| ok | Decide!I67 | No rating: see the Check | No rating: see the Check |
| ok | Thresholds!S12 | To fix:  | To fix: Lower Moderate-Low begins to 0.99 or less. |
| ok | Thresholds!D12 | Industry (every bank) | Industry (every bank) |
| ok | Thresholds!E12 | 0.05926778269446801 | 0.05926778269446801 |
| ok | Thresholds!F12 | 0.05937714243884957 | 0.05937714243884953 |
| ok | Thresholds!G12 | 1.5285126504018145 | 1.528512650401814 |
| ok | Thresholds!H12 |  |  |
| ok | Thresholds!I12 |  |  |
| ok | Thresholds!J12 |  |  |
| ok | Thresholds!K12 |  |  |
| ok | Thresholds!Q12 | Refused | Refused |
| ok | Thresholds!P12 | 0.0034023275592908768 | 0.003402327559290877 |
| ok | Thresholds!O12 | Refused | Refused |
| ok | Thresholds!N12 | -0.0024265883136588345 | -0.0024265883136588345 |
| ok | Thresholds!M12 | Refused | Refused |
| ok | Thresholds!L12 | -0.014683811346124514 | -0.01468381134612451 |
| ok | Lines by source!E26 | 0.05926778269446801 | 0.05926778269446801 |
| ok | Lines by source!F26 | 0.05937714243884957 | 0.05937714243884953 |
| ok | Lines by source!G26 | 1.5285126504018145 | 1.528512650401814 |
| ok | Lines by source!L26 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M26 | 0.0034023275592908768 | 0.003402327559290877 |
| ok | Lines by source!Q26 |  |  |
| ok | Lines by source!S26 | Refused: Moderate-Low would begin at or below zero | Refused: Moderate-Low would begin at or below zero |

## B10 · Save (Ctrl+S), close Excel, open the file again: 40 of 40

Every decision, pick and setting typed is still there, and the lines with them.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Decide!D14 | KeyBank | KeyBank |
| ok | Decide!H14 | 3.5 | 3.5 |
| ok | Decide!J14 | 2012Q3 | 2012Q3 |
| ok | Decide!E14 | Accept these lines | Accept these lines |
| ok | Decide!M14 | Walkthrough: accepted with z 3.5 | Walkthrough: accepted with z 3.5 |
| ok | Decide!L1 | Decided: 1 of 56 · accepted 1 · rejected 0 | Decided: 1 of 56 · accepted 1 · rejected 0 |
| ok | slicers | {'Product': 'Mortgage', 'Measure': 'Net charge-offs'} | {'Product': 'Mortgage', 'Measure': 'Net charge-offs'} |
| ok | Lines by source!E19 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Lines by source!F19 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Lines by source!G19 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Lines by source!L19 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M19 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Lines by source!H19 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Lines by source!I19 | 0.235387727674618 | 0.235387727674618 |
| ok | Lines by source!J19 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Lines by source!K19 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Lines by source!Q19 | 5 | 5 |
| ok | Lines by source!R19 | High | High |
| ok | Lines by source!S19 |  |  |
| ok | Thresholds!D9 | KeyBank | KeyBank |
| ok | Thresholds!E9 | 0.2721174589355553 | 0.2721174589355553 |
| ok | Thresholds!F9 | 0.07345946252187459 | 0.07345946252187457 |
| ok | Thresholds!G9 | 0.7981451323525353 | 0.7981451323525353 |
| ok | Thresholds!H9 | 0.1986579964136807 | 0.1986579964136807 |
| ok | Thresholds!I9 | 0.235387727674618 | 0.235387727674618 |
| ok | Thresholds!J9 | 0.3088471901964926 | 0.30884719019649254 |
| ok | Thresholds!K9 | 0.6397778646238813 | 0.6397778646238812 |
| ok | Thresholds!Q9 | 1 Low | 1 Low |
| ok | Thresholds!P9 | 0.08128138912409479 | 0.08128138912409479 |
| ok | Thresholds!O9 | 1 Low | 1 Low |
| ok | Thresholds!N9 | 0.007216902334030721 | 0.007216902334030721 |
| ok | Thresholds!M9 | 5 High | 5 High |
| ok | Thresholds!L9 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Summary!R1 | Lines picked: 3 of 56 · KeyBank rated 4 or 5: 1 · refused: 2 | Lines picked: 3 of 56 · KeyBank rated 4 or 5: 1 · refused: 2 |
| ok | Thresholds!S1 | Lines picked: 3 of 56 · KeyBank rated 4 or 5: 1 · refused: 2 | Lines picked: 3 of 56 · KeyBank rated 4 or 5: 1 · refused: 2 |
| ok | Summary!B36 | Credit card | Credit card |
| ok | Summary!C36 | Nonaccrual | Nonaccrual |
| ok | Summary!F36 | 0.6908132947833397 | 0.6908132947833397 |
| ok | Summary!G36 | 5 High | 5 High |
| ok | Summary!H36 | lines from KeyBank | lines from KeyBank |

## B11 · On Peers, set Banks in the pack to Regionals only: 11 of 11

Every peer group series on Decide, Lines by source, Thresholds and Summary is summed over the 10 regionals: the latest values below are their composite.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Lines by source!L6 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M6 | 3.787247638881625 | 3.787247638881625 |
| ok | Lines by source!L69 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M69 | 1.4198154778682879 | 1.4198154778682879 |
| ok | Lines by source!L24 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M24 | 1.143434987871377 | 1.143434987871377 |
| ok | Peers!B14 | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe |
| ok | Peers!B39 | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe |
| ok | Peers!J39 | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe |
| ok | Decide!B91 | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe |
| ok | Signals!B6 | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe | Peer group · 9 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on Pe |

## B12 · Set Banks in the pack back to Every peer, and JPMorgan's cell to No: 11 of 11

The peer group is every peer but JPMorgan.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Lines by source!L6 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M6 | 4.252592915239804 | 4.252592915239804 |
| ok | Lines by source!L69 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M69 | 1.7016297268673766 | 1.7016297268673766 |
| ok | Lines by source!L24 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M24 | 1.5238862704282101 | 1.5238862704282101 |
| ok | Peers!B14 | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P |
| ok | Peers!B39 | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P |
| ok | Peers!J39 | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P |
| ok | Decide!B91 | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P |
| ok | Signals!B6 | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P | Peer group · 13 of 15 in · out by the book's rules, 2026Q2: Huntington · switched off on P |

## B13 · Set JPMorgan's cell back to Pack: 14 of 14

The peer group is every peer again: each latest value is the series file's own.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Lines by source!L6 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M6 | 3.9545852353018254 | 3.9545852353018254 |
| ok | Lines by source!L69 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M69 | 1.550392085338516 | 1.550392085338516 |
| ok | Lines by source!L24 | 2026Q2 | 2026Q2 |
| ok | Lines by source!M24 | 1.3825111539309054 | 1.3825111539309054 |
| ok | Lines by source!M6 | 3.9545852353018254 | 3.9545852353018254 |
| ok | Lines by source!M69 | 1.550392085338516 | 1.550392085338516 |
| ok | Lines by source!M24 | 1.3825111539309054 | 1.3825111539309054 |
| ok | Peers!B14 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Peers!B39 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Peers!J39 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Decide!B91 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Signals!B6 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |

## B14 · Open Signals: 124 of 124

The pick as built (other consumer, 30+ incl. nonaccrual, KeyBank) is in the book; where the dollars are reads KeyBank's Call Report by product; the pack line names the peers in and out; two fit tables agree with the same correlations worked out from the series, lead by lead.

| | Cell | Expected | Excel |
|---|---|---|---|
| ok | Signals!B5 | Other consumer | Other consumer |
| ok | Signals!E5 | 30+ days past due incl. nonaccrual | 30+ days past due incl. nonaccrual |
| ok | Signals!I5 | KeyBank | KeyBank |
| ok | Signals!K5 | fits best | fits best |
| ok | Signals!M5 | All quarters | All quarters |
| ok | Signals!P5 | Other consumer · 30+ days past due incl. nonaccrual · KeyBank | Other consumer · 30+ days past due incl. nonaccrual · KeyBank |
| ok | Signals!B6 | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington | Peer group · 14 of 15 in · out by the book's rules, 2026Q2: Huntington |
| ok | Signals!B11 | Credit card | Credit card |
| ok | Signals!D11 | 926589 | 926589 |
| ok | Signals!E11 | 0.03198275740963098 | 0.03198275740963098 |
| ok | Signals!F11 | 42666 | 42666 |
| ok | Signals!G11 | 0.39868804664723034 | 0.39868804664723034 |
| ok | Signals!H11 | 24275 | 24275 |
| ok | Signals!I11 | 0.07853369265261094 | 0.07853369265261094 |
| ok | Signals!B12 | Other consumer | Other consumer |
| ok | Signals!D12 | 4469033 | 4469033 |
| ok | Signals!E12 | 0.1542560922853988 | 0.1542560922853988 |
| ok | Signals!F12 | 59618 | 59618 |
| ok | Signals!G12 | 0.5570942662779398 | 0.5570942662779398 |
| ok | Signals!H12 | 53410 | 53410 |
| ok | Signals!I12 | 0.1727902996735716 | 0.1727902996735716 |
| ok | Signals!B13 | Home equity | Home equity |
| ok | Signals!D13 | 2929570 | 2929570 |
| ok | Signals!E13 | 0.10111897143667002 | 0.10111897143667002 |
| ok | Signals!F13 | 2322 | 2322 |
| ok | Signals!G13 | 0.021697690065037002 | 0.021697690065037002 |
| ok | Signals!H13 | 72018 | 72018 |
| ok | Signals!I13 | 0.23299029773247104 | 0.23299029773247104 |
| ok | Signals!B14 | Mortgage | Mortgage |
| ok | Signals!D14 | 20584113 | 20584113 |
| ok | Signals!E14 | 0.7104948284206174 | 0.7104948284206174 |
| ok | Signals!F14 | 1899 | 1899 |
| ok | Signals!G14 | 0.017745010091948867 | 0.017745010091948867 |
| ok | Signals!H14 | 158704 | 158704 |
| ok | Signals!I14 | 0.5134340333157555 | 0.5134340333157555 |
| ok | Signals!B15 | Auto | Auto |
| ok | Signals!D15 | 62212 | 62212 |
| ok | Signals!E15 | 0.002147350447682805 | 0.002147350447682805 |
| ok | Signals!F15 | 511 | 511 |
| ok | Signals!G15 | 0.0047749869178440605 | 0.0047749869178440605 |
| ok | Signals!H15 | 696 | 696 |
| ok | Signals!I15 | 0.0022516766255908224 | 0.0022516766255908224 |
| ok | Signals!D16 | 28971517 | 28971517 |
| ok | Signals!F16 | 107016 | 107016 |
| ok | Signals!H16 | 309103 | 309103 |
| ok | Signals!B20 | Yes | Yes |
| ok | Signals!C20 | Yes | Yes |
| ok | Signals!D20 | Yes | Yes |
| ok | Signals!E20 | Yes | Yes |
| ok | Signals!F20 | Yes | Yes |
| ok | Signals!R74 | 2 | 2 |
| ok | Signals!S74 | 0.8923573311318846 | 0.8923573311318843 |
| ok | Signals!U74 | 29 | 29 |
| ok | Signals!T74 | 0.9666015097137213 | 0.9666015097137214 |
| ok | Signals!R75 | 2 | 2 |
| ok | Signals!S75 | 0.8604408488787167 | 0.8604408488787165 |
| ok | Signals!U75 | 29 | 29 |
| ok | Signals!T75 | 0.8307722344365586 | 0.8307722344365583 |
| ok | Signals!R76 | 2 | 2 |
| ok | Signals!S76 | 0.8339772638856662 | 0.8339772638856662 |
| ok | Signals!U76 | 29 | 29 |
| ok | Signals!T76 | 0.3080802393004971 | 0.3080802393004945 |
| ok | Signals!R77 | -1 | -1 |
| ok | Signals!S77 | 0.7569587749225609 | 0.7569587749225606 |
| ok | Signals!U77 | 29 | 29 |
| ok | Signals!T77 | 0.34410415755063956 | 0.3441041575506396 |
| ok | Signals!R78 | -1 | -1 |
| ok | Signals!S78 | 0.9129499906596658 | 0.9129499906596653 |
| ok | Signals!U78 | 29 | 29 |
| ok | Signals!T78 | 0.8579660011363002 | 0.8579660011363011 |
| ok | Signals!R79 | -4 | -4 |
| ok | Signals!S79 | 0.7817046927495512 | 0.7817046927495511 |
| ok | Signals!U79 | 29 | 29 |
| ok | Signals!T79 | 0.618676221626357 | 0.6186762216263574 |
| ok | Signals!R80 | 6 | 6 |
| ok | Signals!S80 | 0.6812375273649898 | 0.6812375273649897 |
| ok | Signals!U80 | 29 | 29 |
| ok | Signals!T80 | -0.7329267796471881 | -0.7329267796471896 |
| ok | Signals!R81 | 6 | 6 |
| ok | Signals!S81 | 0.5051634081457965 | 0.5051634081457965 |
| ok | Signals!U81 | 29 | 29 |
| ok | Signals!T81 | -0.8785693868848957 | -0.8785693868848993 |
| ok | Signals!O73 | Other consumer · 30+ incl. nonaccrual · KeyBank | Other consumer · 30+ incl. nonaccrual · KeyBank |
| ok | Signals!R73 | -4 | -4 |
| ok | Signals!S73 | 0.7817046927495512 | 0.7817046927495511 |
| ok | Signals!U73 | 29 | 29 |
| ok | Signals!T73 | 0.618676221626357 | 0.6186762216263574 |
| ok | Signals!R93 | 4 | 4 |
| ok | Signals!S93 | 0.8248286522101923 | 0.8248286522101921 |
| ok | Signals!U93 | 52 | 52 |
| ok | Signals!T93 | 0.3343361919039883 | 0.33433619190398817 |
| ok | Signals!R94 | 2 | 2 |
| ok | Signals!S94 | 0.6496075304096223 | 0.649607530409622 |
| ok | Signals!U94 | 47 | 47 |
| ok | Signals!T94 | 0.5483677972129555 | 0.5483677972129556 |
| ok | Signals!R95 | 4 | 4 |
| ok | Signals!S95 | 0.727205759606632 | 0.7272057596066318 |
| ok | Signals!U95 | 52 | 52 |
| ok | Signals!T95 | 0.42257694197164625 | 0.4225769419716454 |
| ok | Signals!R96 | 1 | 1 |
| ok | Signals!S96 | 0.7305729102024882 | 0.7305729102024879 |
| ok | Signals!U96 | 39 | 39 |
| ok | Signals!T96 | 0.6696662859769211 | 0.6696662859769216 |
| ok | Signals!R97 | 0 | 0 |
| ok | Signals!S97 | 0.8526871793915897 | 0.8526871793915897 |
| ok | Signals!U97 | 52 | 52 |
| ok | Signals!T97 | 0.5392094256518403 | 0.53920942565184 |
| ok | Signals!R98 | -3 | -3 |
| ok | Signals!S98 | 0.5082401370242108 | 0.508240137024211 |
| ok | Signals!U98 | 52 | 52 |
| ok | Signals!T98 | -0.39273193956532265 | -0.39273193956532243 |
| ok | Signals!R99 | 7 | 7 |
| ok | Signals!S99 | 0.31660819802914997 | 0.31660819802914997 |
| ok | Signals!U99 | 52 | 52 |
| ok | Signals!T99 | 0.7384681296983978 | 0.7384681296983978 |
| ok | Signals!R100 | 7 | 7 |
| ok | Signals!S100 | 0.22584854043033203 | 0.22584854043033187 |
| ok | Signals!U100 | 52 | 52 |
| ok | Signals!T100 | -0.06506447848812397 | -0.06506447848812379 |
| ok | Signals!O92 | Other consumer · 30+ incl. nonaccrual · KeyBank | Other consumer · 30+ incl. nonaccrual · KeyBank |
| ok | Signals!R92 | -3 | -3 |
| ok | Signals!S92 | 0.5082401370242108 | 0.508240137024211 |
| ok | Signals!U92 | 52 | 52 |
| ok | Signals!T92 | -0.39273193956532265 | -0.39273193956532243 |
