# Walkthrough result

Excel 16.0, workbook `rehearsal.xlsx`.

**407 of 407 cells as expected, in 30 of 30 steps.** Tabs in order: yes. Workbook back as built after every step: yes.

| Step | What | Cells | Result |
|---|---|---|---|
| W1 | Build the four-product workbook and open it | 9 | as expected |
| W2 | Thresholds as built: every product, nothing left out | 48 | as expected |
| W3.1 | Assess: pick Credit card | 17 | as expected |
| W3.2 | Assess: pick Mortgage | 17 | as expected |
| W3.3 | Assess: pick Home equity | 17 | as expected |
| W3.4 | Assess: pick Other consumer | 17 | as expected |
| W4 | Leave out the financial crisis on Credit card | 22 | as expected |
| W5 | Add the second leave-out: the pandemic (the rehearsal settings) | 26 | as expected |
| W6 | Moderate's half-width 0.5 to 0.75 (H6) | 31 | as expected |
| W7 | Moderate-Low step 1.0 to 1.5 (I6) | 31 | as expected |
| W8 | High's z 2.5 to 3.0 (J6) | 31 | as expected |
| W9a | On the line takes the worse score (half-width 0) | 22 | as expected |
| W9b | On the line takes the better score (half-width 0) | 22 | as expected |
| W10.1 | Refused: a leave-out with a start and nothing else | 3 | as expected |
| W10.2 | Refused: a second leave-out in reverse order | 3 | as expected |
| W10.3 | Refused: a leave-out with no reason | 3 | as expected |
| W10.4 | Refused: a half-width below 0 | 3 | as expected |
| W10.5 | Refused: a z of 0 | 3 | as expected |
| W10.6 | Refused: a step typed as text | 3 | as expected |
| W10.7 | Refused: too little history kept | 3 | as expected |
| W10.8 | Refused: the median at or below zero (Mortgage, keeping 2011Q4 to 2026Q2) | 3 | as expected |
| W10.9 | Refused: Moderate-Low inside Moderate | 3 | as expected |
| W10.10 | Refused: High inside Moderate-High (z 0.3) | 3 | as expected |
| W10.11 | Refused: High beyond the worst quarter kept (z 8) | 3 | as expected |
| W10.12 | Refused: Moderate-Low at or below zero (step 6) | 3 | as expected |
| W11 | Run tab: each file's fingerprint and the decisions as typed | 12 | as expected |
| W12 | Chart: switch Mortgage off | 2 | as expected |
| W13 | Evidence and Backtest for Credit card | 11 | as expected |
| W14a | A lower-is-worse score, on the line takes the worse score | 18 | as expected |
| W14b | A lower-is-worse score, on the line takes the better score | 18 | as expected |
