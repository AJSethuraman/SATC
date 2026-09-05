# Problems — the denominator

**The answers are not ours.** Every row's conclusion is read off the authority's
own worked example or the publication's own answer, and `Answer read from` names
where, quoting the sentence that decided it. A score against answers we wrote
would measure agreement, not correctness.

**The conclusion is withheld from the facts.** `Facts` is the regulation's
example verbatim, cut at the first sentence in which the regulation announces
its outcome — and the example's own HEADING is dropped, because "Unit of
property that costs $200 or less" is half the answer.

**Two rules, stated before the rows so they are not chosen row by row.**

1. On § 1.263(a)-1 the **citation** is the paragraph the regulation's withheld
   analysis names for the safe harbour result, and the **answer** is whether the
   safe harbour applies. Note that CD1 and CD2 share one citation with opposite
   answers, as do CD3/CD5/CD7 against CD4 — a desk cannot get these by mapping
   a citation to a conclusion.
2. On § 1.162-3 the **citation** is the definitional paragraph the analysis
   names as deciding whether the property is a material or supply, and the
   **answer** is the treatment the regulation states. MS1 and MS2 share
   (c)(1)(i) with opposite answers.

## What was left out, and why

| Example | Why it is not a problem |
|---|---|
| § 1.263(a)-1(f)(7) Example 6 | States two outcomes — the furniture qualifies AND the designer's fee need not be capitalised. Nothing reduces to one scorable conclusion. |
| § 1.263(a)-1(f)(7) Example 8 | Its facts are "Assume the facts as in Example 7", so they are not self-contained; and its analysis names two paragraphs, neither containing the other. |
| § 1.263(a)-1(f)(7) Example 10 | Concludes only that amounts "may be subject to capitalization under section 263A" — a conditional, not a conclusion. |
| § 1.162-3(h) Examples 2, 3 | Turn on the optional method for rotable parts, which this desk does not store. |
| § 1.162-3(h) Examples 7, 8 | Example 8's facts are "the same facts as in Example 7"; Example 7 alone repeats Example 6's conclusion on the same paragraph. |
| § 1.162-3(h) Examples 11, 12 | Both end in "may be subject to capitalization under section 263A" — conditional. |
| § 1.162-3(h) Example 13 | States two outcomes: deductible on disposal, or capitalised if the taxpayer elects. |
| § 1.162-3(h) Example 14 | Three outcomes across two classes of property, one of them conditional on an election. |

## The three rows that can only ever escalate

`TP1`, `TP2` and `TP3` rest on an IRS explanation, which is **secondary**.
`engine._check` refuses `authority_permits_choice` before any conclusion is
compared, so these rows grade `escalated` whatever is answered — they can never
grade `correct`. They are here because they are the only rows on this desk that
exercise the escalation half of the design at all. Read them as a test of the
tier gate, not as questions the desk answers. If the firm ratifies POS2, the
position outranks the passage and TP-row grading changes shape; that is the
mechanism working, and it is why the proposal exists.

---

## CD1 · Ten printers at $250, no financial statement

**Citation:** 26 CFR 1.263(a)-1(f)(1)(ii)

**Answer:** the de minimis safe harbor applies; the amount is not capitalized

**Facts:** In Year 1, A purchases 10 printers at $250 each for a total cost of $2,500 as indicated by the invoice. Assume that each printer is a unit of property under § 1.263(a)-3(e). A does not have an AFS. A has accounting procedures in place at the beginning of Year 1 to expense amounts paid for property costing less than $500, and A treats the amounts paid for the printers as an expense on its books and records.

**Answer read from:** § 1.263(a)-1(f)(7) Example 1 — the withheld sentences read: “The amounts paid for the printers meet the requirements for the de minimis safe harbor under paragraph (f)(1)(ii) of this section. … A may not capitalize the amounts paid for the 10 printers.”

---

## CD2 · Ten computers at $600, no financial statement

**Citation:** 26 CFR 1.263(a)-1(f)(1)(ii)

**Answer:** the de minimis safe harbor does not apply to the amount

**Facts:** In Year 1, B purchases 10 computers at $600 each for a total cost of $6,000 as indicated by the invoice. Assume that each computer is a unit of property under § 1.263(a)-3(e). B does not have an AFS. B has accounting procedures in place at the beginning of Year 1 to expense amounts paid for property costing less than $1,000 and B treats the amounts paid for the computers as an expense on its books and records.

**Answer read from:** § 1.263(a)-1(f)(7) Example 2 — “The amounts paid for the printers do not meet the requirements for the de minimis safe harbor under paragraph (f)(1)(ii) of this section because the amount paid for the property exceeds $500 per invoice … B may not apply the de minimis safe harbor election.” (The regulation says “printers” where its own facts say computers; quoted as written.)

---

## CD3 · 1,250 computers at $5,000 each, group financial statement

**Citation:** 26 CFR 1.263(a)-1(f)(1)(i)

**Answer:** the de minimis safe harbor applies; the amount is not capitalized

**Facts:** C is a member of a consolidated group for Federal income tax purposes. C's financial results are reported on the consolidated applicable financial statements for the affiliated group. C's affiliated group has a written accounting policy at the beginning of Year 1, which is followed by C, to expense amounts paid for property costing $5,000 or less. In Year 1, C pays $6,250,000 to purchase 1,250 computers at $5,000 each. C receives an invoice from its supplier indicating the total amount due ($6,250,000) and the price per item ($5,000). Assume that each computer is a unit of property under § 1.263(a)-3(e).

**Answer read from:** § 1.263(a)-1(f)(7) Example 3 — “The amounts paid for the computers meet the requirements for the de minimis safe harbor under paragraph (f)(1)(i) of this section. … C may not capitalize the amounts paid for the 1,250 computers.”

---

## CD4 · 800 machines at $6,000 each against a $15,000 book policy

**Citation:** 26 CFR 1.263(a)-1(f)(1)

**Answer:** the de minimis safe harbor does not apply to the amount

**Facts:** D is a member of a consolidated group for Federal income tax purposes. D's financial results are reported on the consolidated applicable financial statements for the affiliated group. D's affiliated group has a written accounting policy at the beginning of Year 1, which is followed by D, to expense amounts paid for property costing less than $15,000. In Year 1, D pays $4,800,000 to purchase 800 elliptical machines at $6,000 each. D receives an invoice from its supplier indicating the total amount due ($4,800,000) and the price per item ($6,000). Assume that each elliptical machine is a unit of property under § 1.263(a)-3(e).

**Answer read from:** § 1.263(a)-1(f)(7) Example 4 — “D may not apply the de minimis safe harbor election to the amounts paid for the 800 elliptical machines under paragraph (f)(1) of this section because the amount paid for the property exceeds $5,000 per invoice (or per item as substantiated by the invoice).”

---

## CD5 · Routers whose delivery and installation are on the same invoice

**Citation:** 26 CFR 1.263(a)-1(f)(1)(i)

**Answer:** the de minimis safe harbor applies; the amount is not capitalized

**Facts:** E is a member of a consolidated group for Federal income tax purposes. E's financial results are reported on the consolidated applicable financial statements for the affiliated group. E's affiliated group has a written accounting policy at the beginning of Year 1, which is followed by E, to expense amounts paid for property costing less than $5,000. In Year 1, E pays $45,000 for the purchase and installation of wireless routers in each of its 10 office locations. Assume that each wireless router is a unit of property under § 1.263(a)-3(e). E receives an invoice from its supplier indicating the total amount due ($45,000), including the material price per item ($2,500), and total delivery and installation ($20,000). E allocates the additional invoice costs to the materials on a pro rata basis, bringing the cost of each router to $4,500 ($2,500 materials + $2,000 labor and overhead).

**Answer read from:** § 1.263(a)-1(f)(7) Example 5 — “The amounts paid for each router, including the allocable additional invoice costs, meet the requirements for the de minimis safe harbor under paragraph (f)(1)(i) of this section.”

---

## CD6 · Devices and tablets with a useful life of twelve months or less

**Citation:** 26 CFR 1.263(a)-1(f)(1)(ii)

**Answer:** the de minimis safe harbor applies; the amount is not capitalized

**Facts:** G operates a restaurant. In Year 1, G purchases 10 hand-held point-of-service devices at $300 each for a total cost of $3,000 as indicated by invoice. G also purchases 3 tablet computers at $500 each for a total cost of $1,500 as indicated by invoice. Assume each point-of-service device and each tablet computer has an economic useful life of 12 months or less, beginning when they are used in G's business. Assume that each device and each tablet is a unit of property under § 1.263(a)-3(e). G does not have an AFS, but G has accounting procedures in place at the beginning of Year 1 to expense amounts paid for property costing $300 or less and to expense amounts paid for property with an economic useful life of 12 months or less. Thus, G expenses the amounts paid for the hand-held devices on its books and records because each device costs $300. G also expenses the amounts paid for the tablet computers on its books and records because the computers have an economic useful life of 12 months of less, beginning when they are used.

**Answer read from:** § 1.263(a)-1(f)(7) Example 7 — “The amounts paid for the hand-held devices and the tablet computers meet the requirements for the de minimis safe harbor under paragraph (f)(1)(ii) of this section.”

---

## CD7 · Computers, chairs and briefcases expensed on a $5,000 policy

**Citation:** 26 CFR 1.263(a)-1(f)(1)(i)

**Answer:** the de minimis safe harbor applies; the amount is not capitalized

**Facts:** H is a corporation that provides consulting services to its customers. H has an AFS and a written accounting policy at the beginning of the taxable year to expense amounts paid for property costing $5,000 or less. In Year 1, H purchases 1,000 computers at $500 each for a total cost of $500,000. Assume that each computer is a unit of property under § 1.263(a)-3(e) and is not a material or supply under § 1.162-3. In addition, H purchases 200 office chairs at $100 each for a total cost of $20,000 and 250 customized briefcases at $80 each for a total cost of $20,000. Assume that each office chair and each briefcase is a material or supply under § 1.162-3(c)(1). H treats the amounts paid for the computers, office chairs, and briefcases as expenses on its AFS.

**Answer read from:** § 1.263(a)-1(f)(7) Example 9 — “The amounts paid for computers, office chairs, and briefcases meet the requirements for the de minimis safe harbor under paragraph (f)(1)(i) of this section.”

---

## CD8 · A used truck invoiced in four parts

**Citation:** 26 CFR 1.263(a)-1(f)(6)

**Answer:** the de minimis safe harbor does not apply to the amount

**Facts:** K is a corporation that provides hauling services to its customers. In Year 1, K decides to purchase a truck to use in its business. K does not have an AFS. K has accounting procedures in place at the beginning of Year 1 to expense amounts paid for property costing less than $500. K arranges to purchase a used truck for a total of $1,500. Prior to the acquisition, K requests the seller to provide multiple invoices for different parts of the truck. Accordingly, the seller provides K with four invoices during Year 1—one invoice of $500 for the cab, one invoice of $500 for the engine, one invoice of $300 for the trailer, and a fourth invoice of $200 for the tires. K treats the amounts paid under each invoice as an expense on its books and records. K elects to apply the de minimis safe harbor under paragraph (f) of this section in Year 1 and does not capitalize the amounts paid for each invoice pursuant to the safe harbor.

**Answer read from:** § 1.263(a)-1(f)(7) Example 11 — “Under paragraph (f)(6) of this section, K has applied the de minimis rule to amounts substantiated with invoices created to componentize property … As a result, K may not apply the de minimis rule to these amounts and is subject to appropriate adjustments.”

---

## MS1 · Spare parts bought in one year and used to repair in the next

**Citation:** 26 CFR 1.162-3(c)(1)(i)

**Answer:** a material or supply, deductible in the taxable year first used or consumed

**Facts:** A owns a fleet of aircraft that it operates in its business. In Year 1, A purchases a stock of spare parts, which it uses to maintain and repair its aircraft. A keeps a record of consumption of these spare parts. In Year 2, A uses the spare parts for the repair and maintenance of one of its aircraft. Assume each aircraft is a unit of property under § 1.263(a)-3(e) and that spare parts are not rotable or temporary spare parts under paragraph (c)(2) of this section. Assume these repair and maintenance activities do not improve the aircraft under § 1.263(a)-3.

**Answer read from:** § 1.162-3(h) Example 1 — “These parts are materials and supplies under paragraph (c)(1)(i) of this section … the amounts that A paid for the spare parts in Year 1 are deductible in Year 2, the taxable year in which the spare parts are first used to repair and maintain the aircraft.”

---

## MS2 · Engines bought as part of the aircraft and later removed

**Citation:** 26 CFR 1.162-3(c)(1)(i)

**Answer:** not a material or supply; treated under §§ 1.263(a)-2 and 1.263(a)-3

**Facts:** D operates a fleet of aircraft. In Year 1, D acquires a new aircraft, which includes two new aircraft engines. The aircraft costs $500,000 and has an economic useful life of more than 12 months, beginning when it is placed in service. In Year 5, after the aircraft is operated for several years in D's business, D removes the engines from the aircraft, repairs or improves the engines, and either reinstalls the engines on a similar aircraft or stores the engines for later reinstallation. Assume the aircraft purchased in Year 1, including its two engines, is a unit of property under § 1.263(a)-3(e).

**Answer read from:** § 1.162-3(h) Example 4 — “Because the engines were acquired as part of the aircraft, a single unit of property, the engines are not materials or supplies under paragraph (c)(1)(i) of this section … Rather, D must apply the rules under §§ 1.263(a)-2 and 1.263(a)-3.”

---

## MS3 · A two-year supply of fuel bought on the last day of the year

**Citation:** 26 CFR 1.162-3(c)(1)(ii)

**Answer:** a material or supply, deductible in the taxable year first used or consumed

**Facts:** E operates a fleet of aircraft that carries freight for its customers. E has several storage tanks on its premises, which hold jet fuel for its aircraft. Assume that once the jet fuel is placed in E's aircraft, the jet fuel is reasonably expected to be consumed within 12 months or less. On December 31, Year 1, E purchases a two-year supply of jet fuel. In Year 2, E uses a portion of the jet fuel purchased on December 31, Year 1, to fuel the aircraft used in its business.

**Answer read from:** § 1.162-3(h) Example 5 — “The jet fuel that E purchased in Year 1 is a material or supply under paragraph (c)(1)(ii) of this section … E may deduct in Year 2 the amounts paid for the portion of jet fuel used.”

---

## MS4 · Small rental items bought in one year and put into service the next

**Citation:** 26 CFR 1.162-3(c)(1)(iv)

**Answer:** a material or supply, deductible in the taxable year first used or consumed

**Facts:** F operates a business that rents out a variety of small individual items to customers (rental items). F maintains a supply of rental items on hand. In Year 1, F purchases a large quantity of rental items to use in its rental business. Assume that each rental item is a unit of property under § 1.263(a)-3(e) and costs $200 or less. In Year 2, F begins using all the rental items purchased in Year 1 by providing them to customers of its rental business. F does not sell or exchange these items on established retail markets at any time after the items are used in the rental business.

**Answer read from:** § 1.162-3(h) Example 6 — “The rental items are materials and supplies under paragraph (c)(1)(iv) of this section … the amounts that F paid for the rental items in Year 1 are deductible in Year 2, the taxable year in which the rental items are first used in F's business.”

---

## MS5 · One box costing more than $200 holding ten items that do not

**Citation:** 26 CFR 1.162-3(c)(1)(iv)

**Answer:** a material or supply, deductible in the taxable year first used or consumed

**Facts:** H provides consulting services to its customers. In Year 1, H pays $500 to purchase one box of 10 toner cartridges to use as needed for H's printers. Assume each toner cartridge is a unit of property under § 1.263(a)-3(e). In Year 1, H's employees place 8 of the toner cartridges in printers in H's office, and store the remaining 2 cartridges for use in a later taxable year.

**Answer read from:** § 1.162-3(h) Example 9 — “The toner cartridges are materials and supplies under paragraph (c)(1)(iv) of this section because even though purchased in one box costing more than $200, the allocable cost of each unit of property equals $50. Therefore … deductible in Year 1, the taxable year in which H first uses each of those cartridges.”

---

## TP1 · A purchase over the ceiling, by a taxpayer who elected the harbor

**Citation:** IRS Tangible Property Final Regulations, "If you use the de minimis safe harbor, do you have to capitalize all expenses that exceed the limitations?"

**Answer:** no; an amount over the threshold is treated under the normal rules and may still be currently deductible

**Facts:** A taxpayer without an applicable financial statement elected the de minimis safe harbor for the year. One amount paid to acquire tangible property is above the $2,500 threshold. Everything else about the purchase is ordinary. Must that amount be capitalized because it is over the threshold?

**Answer read from:** Read off the answer the IRS gives under that heading: “No. Amounts paid for the acquisition or production of tangible property that exceed the safe harbor limitations aren't subject to the de minimis safe harbor election. … If an amount doesn't qualify under the de minimis safe harbor, you should treat the amount under the normal rules that apply, i.e., currently deductible if paid for incidental materials and supplies or for repair and maintenance.”

---

## TP2 · Whether the book policy has to be in writing without a financial statement

**Citation:** IRS Tangible Property Final Regulations, "If you don't have an AFS, are you required to have a written accounting procedure at the beginning of your taxable year?"

**Answer:** no written procedure is required without an AFS, but a consistent policy must exist at the beginning of the taxable year

**Facts:** A business with no applicable financial statement wants to use the $2,500 de minimis threshold for the coming year. It has never written its expensing policy down. Does the threshold require a written accounting procedure?

**Answer read from:** Read off the answer the IRS gives under that heading: “If you don't have an AFS, you are not required to have written accounting procedures; however, you must expense amounts on your books and records for the taxable year in accordance with a consistent accounting procedure or policy existing at the beginning of the taxable year. If you have AFS, you must have the accounting procedures in writing.”

---

## TP3 · A book policy set above the ceiling

**Citation:** IRS Tangible Property Final Regulations, "What if your book policy exceeds the de minimis safe harbor ceiling?"

**Answer:** the amounts may still be deducted for federal tax purposes if the reporting policy clearly reflects income

**Facts:** A business with no applicable financial statement has a book policy of expensing anything under $4,000 — above the $2,500 threshold. It wants to know what happens to the amounts between the two figures.

**Answer read from:** Read off the answer the IRS gives under that heading: “If you don't have an AFS and have a policy for your books and records of deducting amounts more than $2,500 ($500 prior to Jan. 1, 2016), you may properly deduct these amounts for federal tax purposes, as long as you can show that your reporting policy clearly reflects your income.”

---

