# Problems — fact patterns whose answer is already known

Concatenated from the seven records unchanged. Ids were already unique across
them (CB1, VE9, ...) because each was prefixed by hand.

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
tier gate, not as questions the desk answers. **Their FACTS are this session's,
not the IRS's** — the page poses each as a question rather than as a worked
example, so the fact pattern is a restatement of the IRS's own question and only
the CONCLUSION is read off the page. That is exactly the shape the other thirteen
rows avoid, and it is survivable only because the tier gate stops these rows
before any conclusion is compared. If the firm ratifies POS2 and these rows begin
to grade against a position, they need real fact patterns first or they must
go. If the firm ratifies POS2, the
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

## CB1 · A deposit made on the last day of the month

**Citation:** IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the statement did not yet include

**Answer:** a reconciling item, no entry in the books

**Facts:** A deposit of $516.08 was made on 31 January and recorded in the books that day. It does not appear on the bank statement for the month ended 31 January.

---

## CB2 · A check that has not cleared

**Citation:** IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the statement did not yet include

**Answer:** a reconciling item, no entry in the books

**Facts:** Check number 94 for $150.00 was written on 20 January, sent to the payee, and recorded in the books. The bank statement for the month ended 31 January does not show it among the checks paid.

---

## CB3 · A deposit recorded for the wrong amount

**Citation:** IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the books are updated for

**Answer:** an entry in the books

**Facts:** A deposit of $600.40 made on 8 January was entered in the checkbook and the books as $594.40. The bank statement shows the deposit at $600.40.

---

## CB4 · A charge the bank made and nobody entered

**Citation:** IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the books are updated for

**Answer:** an entry in the books

**Facts:** The bank statement for the month ended 31 January shows a service charge of $10.00. Nothing for it appears in the checkbook or the books.

## The count, and every exclusion

| | |
|---|---|
| Examples in the section | **117** |
| Usable as problems | **16** |
| Left out | **101** |

| Left out | Because |
|---|---|
| 6 | analysis names more than one paragraph and none contains the rest |
| 6 | conclusion cannot be separated from the facts |
| 27 | depends on an example not shown |
| 1 | facts name the governing paragraph |
| 3 | states its conclusion conditionally |
| 1 | states more than one conclusion |
| 57 | states no conclusion this desk can score |

### Left out at the citation step, by name

These examples state a scorable conclusion and would have been problems under
the first record. They are not problems now, because the rule they rest on
cannot be read from their analysis without judgement.

| Example | Because | Its analysis names |
|---|---|---|
| (f)(4) Example 1 · Lessee improvements; additions to building | analysis names more than one paragraph and none contains the rest | (d), (e)(2)(ii), (e)(2)(ii)(A), (e)(2)(ii)(B), (e)(2)(v), (e)(2)(v)(A), (e)(2)(v)(B), (e)(2)(v)(B)(1), (f)(2)(i), (f)(2)(ii) |
| (j)(3) Example 10 · Betterment; relocation and reinstallation of equipment | facts name the governing paragraph | (j) |
| (k)(7) Example 6 · Restoration of property in a state of disrepair | analysis names more than one paragraph and none contains the rest | (d)(2), (e)(2)(ii), (e)(2)(ii)(A), (k)(1)(iv), (k)(2) |
| (k)(7) Example 13 · Not replacement of major component; incidental | analysis names more than one paragraph and none contains the rest | (k)(1)(vi), (k)(6)(i)(A), (k)(6)(i)(B) |
| (k)(7) Example 14 · Replacement of major component or substantial structural part; roof | analysis names more than one paragraph and none contains the rest | (d)(2), (e)(2)(ii), (e)(2)(ii)(A), (k)(1)(vi), (k)(2), (k)(6)(ii)(A), (k)(6)(ii)(B) |
| (k)(7) Example 15 · Not replacement of major component or substantial structural part; roof membrane | analysis names more than one paragraph and none contains the rest | (e)(2)(ii), (e)(2)(ii)(A), (k)(1)(vi), (k)(2), (k)(6)(ii)(A), (k)(6)(ii)(B) |
| (k)(7) Example 22 · Replacement of major component or substantial structural part; plumbing system | analysis names more than one paragraph and none contains the rest | (d)(2), (e)(2)(ii), (e)(2)(ii)(B)(2), (k)(1)(vi), (k)(2), (k)(6)(ii)(A) |

## What a model gets for free

| Answer | Problems |
|---|---|
| must capitalize | 6 |
| not required to capitalize | 10 |

**Always answering the most common one scores 10 of 16 (62%).** That is the number any
run has to beat before it has shown anything, and it is printed here because a
scoreboard whose baseline is unstated reads as skill when it may be arithmetic.

| Citation | Problems |
|---|---|
| 26 CFR 1.263(a)-3(i)(1)(i) | 1 |
| 26 CFR 1.263(a)-3(i)(1)(ii) | 2 |
| 26 CFR 1.263(a)-3(j) | 7 |
| 26 CFR 1.263(a)-3(k)(1)(vi) | 1 |
| 26 CFR 1.263(a)-3(l) | 5 |

**Always citing the most common one matches 7 of 16 (43%).** The index a
model cites from holds **172** paragraphs for **16** problems, so the
citation cannot be solved as an assignment puzzle -- the first record's 21-for-21
could, and was. Of the 16 problems, **3** have facts that name
some paragraph of this section in a stipulation; none names its own citation.

**Nothing is dropped silently.** An example that leans on one not shown cannot be
answered from what the desk is given, one whose outcome is not stated in
capitalisation terms cannot be scored without inventing a conclusion, and one
whose analysis does not name the rule it rests on cannot be cited without
inventing a citation — which is the single thing this whole plugin exists to
prevent.

---

## P1 · Routine maintenance on component

**Citation:** 26 CFR 1.263(a)-3(i)(1)(ii)

**Example:** 26 CFR 1.263(a)-3(i)(6) Example 1

**Answer:** not required to capitalize

**Facts:** (i) A is a commercial airline engaged in the business of transporting passengers and freight throughout the United States and abroad. To conduct its business, A owns or leases various types of aircraft. As a condition of maintaining its airworthiness certification for these aircraft, A is required by the Federal Aviation Administration (FAA) to establish and adhere to a continuous maintenance program for each aircraft within its fleet. These programs, which are designed by A and the aircraft's manufacturer and approved by the FAA, are incorporated into each aircraft's maintenance manual. The maintenance manuals require a variety of periodic maintenance visits at various intervals. One type of maintenance visit is an engine shop visit (ESV), which A expects to perform on its aircraft engines approximately every 4 years to keep its aircraft in its ordinarily efficient operating condition. In Year 1, A purchased a new aircraft, which included four new engines attached to the airframe. The four aircraft engines acquired with the aircraft are not materials or supplies under § 1.162-3(c)(1)(i) because they are acquired as part of a single unit of property, the aircraft. In Year 5, A performs its first ESV on the aircraft engines. The ESV includes disassembly, cleaning, inspection, repair, replacement, reassembly, and testing of the engine and its component parts. During the ESV, the engine is removed from the aircraft and shipped to an outside vendor who performs the ESV. If inspection or testing discloses a discrepancy in a part's conformity to the specifications in A's maintenance program, the part is repaired, or if necessary, replaced with a comparable and commercially available replacement part. After the ESVs, the engines are returned to A to be reinstalled on another aircraft or stored for later installation. Assume that the class life for A's aircraft, including the engines, is 12 years. Assume that none of the exceptions set out in paragraph (i)(3) of this section apply to the costs of performing the ESVs.

---

## P2 · Routine maintenance on non-rotable part

**Citation:** 26 CFR 1.263(a)-3(i)(1)(ii)

**Example:** 26 CFR 1.263(a)-3(i)(6) Example 9

**Answer:** not required to capitalize

**Facts:** E is a towboat operator that owns and leases a fleet of towboats. Each towboat is equipped with two diesel-powered engines. Assume that each towboat, including its engines, is the unit of property and that a towboat has a class life of 18 years. At the time that E places its towboats into service, E is aware that approximately every three to four years E will need to perform scheduled maintenance on the two towboat engines to keep the engines in their ordinarily efficient operating condition. This maintenance is completed while the engines are attached to the towboat and involves the cleaning and inspecting of the engines to determine which parts are within acceptable operating tolerances and can continue to be used, which parts must be reconditioned to be brought back to acceptable tolerances, and which parts must be replaced. Engine parts replaced during these procedures are replaced with comparable and commercially available replacement parts. Assume the towboat engines are not rotable spare parts under § 1.162-3(c)(2). In Year 1, E acquired a new towboat, including its two engines, and placed the towboat into service. In Year 5, E pays amounts to perform scheduled maintenance on both engines in the towboat. Assume that none of the exceptions set out in paragraph (i)(3) of this section apply to the scheduled maintenance costs.

---

## P3 · Routine maintenance on a building; escalator system

**Citation:** 26 CFR 1.263(a)-3(i)(1)(i)

**Example:** 26 CFR 1.263(a)-3(i)(6) Example 13

**Answer:** not required to capitalize

**Facts:** In Year 1, G acquires a large retail mall in which it leases space to retailers. The mall contains an escalator system with 40 escalators, which includes landing platforms, trusses, tracks, steps, handrails, and safety brushes. In Year 1, when G placed its building into service, G reasonably expected that it would need to replace the handrails on the escalators approximately every four years to keep the escalator system in its ordinarily efficient operating condition. After a routine inspection and test of the escalator system in Year 4, G determines that the handrails need to be replaced and pays an amount to replace the handrails with comparable and commercially available handrails. Assume that none of the exceptions in paragraph (i)(3) of this section apply to the scheduled maintenance costs.

---

## P4 · Not amelioration of pre-existing material condition or defect

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 3

**Answer:** not required to capitalize

**Facts:** (i) In January, Year 1, C purchased a used machine for use in its manufacturing operations. Assume that the machine is a unit of property and has a class life of 10 years. C placed the machine in service in January, Year 1 and at that time expected to perform manufacturer recommended scheduled maintenance on the machine every three years. The scheduled maintenance includes cleaning and oiling the machine, inspecting parts for defects, and replacing minor items, such as springs, bearings, and seals, with comparable and commercially available replacement parts. The scheduled maintenance does not include any material additions or materially increase the capacity, productivity, efficiency, strength, quality, or output of the machine. At the time C purchased the machine, it was approaching the end of a three-year scheduled maintenance period. As a result, in February, Year 1, C pays an amount to perform the manufacturer recommended scheduled maintenance to keep the machine in its ordinarily efficient operating condition. C acquired the machine just before it had received its three-year scheduled maintenance. Accordingly, the amount that C pays for the scheduled maintenance results from the prior owner's use of the property and ameliorates conditions or defects that existed prior to C's ownership of the machine.

---

## P5 · Not amelioration of pre-existing material condition or defect

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 4

**Answer:** not required to capitalize

**Facts:** D purchases a used ice resurfacing machine for use in the operation of its ice skating rink. To comply with local regulations, D is required to routinely monitor the air quality in the ice skating rink. One week after D places the machine into service, during a routine air quality check, D discovers that the operation of the machine is adversely affecting the air quality in the skating rink. As a result, D pays an amount to inspect and retune the machine, which includes replacing minor components of the engine that had worn out prior to D's acquisition of the machine. Assume the resurfacing machine, including the engine, is the unit of property. The amount that D pays to inspect, retune, and replace minor components of the ice resurfacing machine ameliorates a condition or defect that existed prior to D's acquisition of the equipment.

---

## P6 · Betterment; regulatory requirement

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 11

**Answer:** must capitalize

**Facts:** K owns a building that it uses in its business. In Year 1, City C passes an ordinance setting higher safety standards for buildings because of the hazardous conditions caused by earthquakes. To comply with the ordinance, K pays an amount to add expansion bolts to its building structure. These bolts anchor the wooden framing of K's building to its cement foundation, providing additional structural support and resistance to seismic forces, making the building more resistant to damage from lateral movement. Prior to the ordinance, the old building was in good condition but did not meet City C's new requirements for earthquake resistance.

---

## P7 · Material increase in capacity; building

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 14

**Answer:** must capitalize

**Facts:** N owns a factory building with a storage area on the second floor. N pays an amount to reinforce the columns and girders supporting the second floor to permit storage of supplies with a gross weight 50 percent greater than the previous load-carrying capacity of the storage area.

---

## P8 · Material increase in capacity; building

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 19

**Answer:** must capitalize

**Facts:** Q owns a building that it uses in its retail business. The building contains one floor of retail space with very high ceilings. Q pays an amount to add a stairway and a mezzanine for the purposes of adding additional selling space within its building.

---

## P9 · Not material increase in efficiency; HVAC system

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 20

**Answer:** not required to capitalize

**Facts:** R owns an office building that it uses to provide services to customers. The building contains an HVAC system that incorporates 10 roof-mounted units that provide heating and air conditioning for different parts of the building. The HVAC system also consists of controls for the entire system and duct work that distributes the heated or cooled air to the various spaces in the building's interior. After many years of use of the HVAC system, R begins to experience climate control problems in various offices throughout the office building and consults with a contractor to determine the cause. The contractor recommends that R replace two of the roof-mounted units. R pays an amount to replace the two specified units. The two new units are expected to eliminate the climate control problems and to be 10 percent more energy efficient than the replaced units in their original condition. No work is performed on the other roof-mounted heating/cooling units, the duct work, or the controls.

---

## P10 · Material increase in efficiency; building

**Citation:** 26 CFR 1.263(a)-3(j)

**Example:** 26 CFR 1.263(a)-3(j)(3) Example 21

**Answer:** must capitalize

**Facts:** S owns a building that it uses in its service business. S conducts an energy assessment and determines that it could significantly reduce its energy costs by adding insulation to its building. S pays an insulation contractor to apply a combination of loose-fill, spray foam, and blanket insulation throughout S's building structure, including within the attic, walls, and crawl spaces. S reasonably expects the new insulation to make the building more energy efficient because the contractor indicated that the new insulation would reduce its annual energy and power costs by approximately 50 percent of its annual costs during the last five years.

---

## P11 · Replacement of major component or substantial structural part; personal property

**Citation:** 26 CFR 1.263(a)-3(k)(1)(vi)

**Example:** 26 CFR 1.263(a)-3(k)(7) Example 10

**Answer:** must capitalize

**Facts:** G is a common carrier that owns a fleet of petroleum hauling trucks. G pays amounts to replace the existing engine, cab, and petroleum tank with a new engine, cab, and tank. Assume the tractor of the truck (which includes the cab and the engine) is a single unit of property and that the trailer (which contains the petroleum tank) is a separate unit of property. The new engine and the cab each constitute a part or combination of parts that comprise a major component of G's tractor, because they perform a discrete and critical function in the operation of the tractor. In addition, the cab constitutes a part or combination of parts that comprise a substantial structural part of G's tractor. Moreover, the new petroleum tank constitutes a part or combination of parts that comprise a major component and a substantial structural part of the trailer.

---

## P12 · New or different use; change in building use

**Citation:** 26 CFR 1.263(a)-3(l)

**Example:** 26 CFR 1.263(a)-3(l)(3) Example 1

**Answer:** must capitalize

**Facts:** A is a manufacturer and owns a manufacturing building that it has used for manufacturing since Year 1, when A placed it in service. In Year 30, A pays an amount to convert its manufacturing building into a showroom for its business. To convert the facility, A removes and replaces various structural components to provide a better layout for the showroom and its offices. A also repaints the building interiors as part of the conversion. When building materials are removed and replaced, A uses comparable and commercially available replacement materials.

---

## P13 · Not a new or different use; leased building

**Citation:** 26 CFR 1.263(a)-3(l)

**Example:** 26 CFR 1.263(a)-3(l)(3) Example 2

**Answer:** not required to capitalize

**Facts:** B owns and leases out space in a building consisting of twenty retail spaces. The space was designed to be reconfigured; that is, adjoining spaces could be combined into one space. One of the tenants expands its occupancy by leasing two adjoining retail spaces. To facilitate the new lease, B pays an amount to remove the walls between the three retail spaces. Assume that the walls between spaces are part of the building and its structural components.

---

## P14 · Not a new or different use; preparing building for sale

**Citation:** 26 CFR 1.263(a)-3(l)

**Example:** 26 CFR 1.263(a)-3(l)(3) Example 3

**Answer:** not required to capitalize

**Facts:** C owns a building consisting of twenty retail spaces. C decides to sell the building. In anticipation of selling the building, C pays an amount to repaint the interior walls and to refinish the hardwood floors.

---

## P15 · Not a new or different use; part of building

**Citation:** 26 CFR 1.263(a)-3(l)

**Example:** 26 CFR 1.263(a)-3(l)(3) Example 6

**Answer:** not required to capitalize

**Facts:** (i) F owns a building in which it operates a grocery store. The grocery store includes various departments for fresh produce, frozen foods, fresh meats, dairy products, toiletries, and over-the-counter medicines. The grocery store also includes separate counters for deli meats, prepared foods, and baked goods, often made to order. To better accommodate its customers' shopping needs, F decides to add a sushi bar where customers can order freshly prepared sushi from the counter for take-home or to eat at the counter. To create the sushi bar, F pays amounts to add a sushi counter and chairs, add additional wiring and outlets to support the counter, and install additional pipes and a sink, to provide for the safe handling of the food. F also pays amounts to replace flooring and wall coverings in the sushi bar area with decorative coverings to reflect more appropriate décor. Assume the sushi counter and chairs are section 1245 property, and F treats the amounts paid for those units of property as costs of acquiring new units of property under § 1.263(a)-2.

---

## P16 · Not a new or different use; part of building

**Citation:** 26 CFR 1.263(a)-3(l)

**Example:** 26 CFR 1.263(a)-3(l)(3) Example 7

**Answer:** not required to capitalize

**Facts:** (i) G owns a hospital with various departments dedicated to the provision of clinical medical care. To better accommodate its patients' needs, G decides to modify the emergency room space to provide both emergency care and outpatient surgery. To modify the space, G pays amounts to move interior walls, add additional wiring and outlets, replace floor tiles and doors, and repaint the walls. To complete the outpatient surgery center, G also pays amounts to install miscellaneous medical equipment necessary for the provision of surgical services. Assume the medical equipment is section 1245 property, and G treats the amounts paid for those units of property as costs of acquiring new units of property under § 1.263(a)-2.

## M1 · A meal with a customer

**Citation:** 26 CFR 1.274-12(a)(2)

**Answer:** 50 percent deductible

**Facts:** A sole proprietor takes a customer out to lunch to talk over the customer's account. The proprietor is present when the food is served, the amount is not out of line for the circumstances, and it is an ordinary and necessary expense of the business.

**Read from:** the regulation's own worked example at § 1.274-12(a)(3)(i), Example 1 — "Taxpayer A takes client B out to lunch. Under section 274(k) and (n) and paragraph (a) of this section, A may deduct 50 percent of the food or beverage expenses."

---

## M2 · Seats at a ball game with a supplier

**Citation:** 26 CFR 1.274-11(a)

**Answer:** not deductible

**Facts:** A contractor buys two tickets to a professional baseball game and takes a supplier along to talk over a proposed job. Neither business has anything to do with baseball.

**Read from:** the regulation's own worked example at § 1.274-11(d)(1), Example 1 — "the cost of the game tickets is an entertainment expenditure and is not deductible by A."

---

## M3 · Food bought at the concession stand

**Citation:** 26 CFR 1.274-11(b)(1)(ii)

**Answer:** 50 percent deductible

**Facts:** At that same baseball game the contractor buys hot dogs and drinks for the two of them at a concession stand and pays the stand for them there. Nothing was paid for anything to eat or drink when the seats were bought.

**Read from:** the regulation's own worked example at § 1.274-11(d)(2), Example 2 — "The cost of the hot dogs and drinks, which are purchased separately from the game tickets, is not an entertainment expenditure ... Therefore, A may deduct 50 percent of the expenses associated with the hot dogs and drinks purchased at the game if the expenses meet the requirements of section 162 and § 1.274-12."

---

## M4 · A suite where the bill shows one number

**Citation:** 26 CFR 1.274-11(b)(1)(ii)

**Answer:** not deductible

**Facts:** A firm buys seats for two people at a basketball game in a suite where food and drinks are available throughout. The invoice shows a single price for the suite and breaks out no amount for anything eaten or drunk there.

**Read from:** the regulation's own worked example at § 1.274-11(d)(3), Example 3 — "The cost of the food and beverages, which are not purchased separately from the game tickets, is not stated separately on the invoice ... C may not deduct the cost of the tickets or the food and beverages associated with the basketball game."

---

## M5 · A spouse at dinner on a business trip

**Citation:** 26 CFR 1.274-12(a)(4)(iii)

**Answer:** not deductible

**Facts:** A sole proprietor goes on business travel to another city for a series of meetings, and the proprietor's spouse comes along. The spouse is not an employee of the proprietor, has no business reason of the proprietor's for going, and could not deduct the cost independently. While away the two go out to dinner. The amount at issue is the spouse's dinner.

**Read from:** the regulation's own worked example at § 1.274-12(a)(4)(iii)(D) — "Therefore, the cost of F's spouse's dinner is not deductible."

---

## M6 · The staff holiday party

**Citation:** 26 CFR 1.274-12(c)(2)(iii)(A)

**Answer:** 100 percent deductible

**Facts:** An employer holds a holiday party in a hotel ballroom with a buffet dinner and an open bar, and invites every employee. Nothing about how it is run favours the employees who are highly compensated.

**Read from:** the regulation's own worked example at § 1.274-12(c)(2)(iii)(B)(1), Example 1 — "Thus, L may deduct 100 percent of the cost of the party."

---

## M7 · What is kept in the break room

**Citation:** 26 CFR 1.274-12(a)(2)

**Answer:** 50 percent deductible

**Facts:** An employer keeps free coffee, bottled water, chips and other snacks in a break room that any employee may use. Some employees chat to each other while they are in there.

**Read from:** the regulation's own worked example at § 1.274-12(c)(2)(iii)(B)(3), Example 3 — "A break room is not a recreational, social, or similar activity primarily for the benefit of the employees, even if some socializing related to the food and beverages provided occurs ... M may deduct only 50 percent of the expenses for food and beverages provided in the break room."

---

## M8 · Coffee in a customer waiting area

**Citation:** 26 CFR 1.274-12(c)(2)(iv)(A)

**Answer:** 100 percent deductible

**Facts:** An automobile service centre keeps coffee and snacks in its customer waiting area. Employees and customers both help themselves, and the owner reasonably estimates that customers take more than half of what is put out.

**Read from:** the regulation's own worked example at § 1.274-12(c)(2)(iv)(B)(2), Example 2 — "Thus, Q may deduct 100 percent of the food and beverage expenses."

---

## M9 · Staff meals where the business is the kitchen

**Citation:** 26 CFR 1.274-12(c)(2)(v)(A)

**Answer:** 100 percent deductible

**Facts:** A restaurant gives its kitchen and serving staff food and drinks at no charge before, during and after their shifts. The same items are sold across the counter to paying customers.

**Read from:** the regulation's own worked example at § 1.274-12(c)(2)(v)(B) — "Thus, T may deduct 100 percent of the food and beverage expenses."

---

## M10 · A company cafeteria, with the value put into wages

**Citation:** 26 CFR 1.274-12(c)(2)(i)(A)

**Answer:** 100 percent deductible

**Facts:** An employer serves food and drinks free of charge to employees at a company cafeteria on its own premises. None of those employees is a specified individual, and what is served does not qualify as a de minimis fringe. The employer puts the full fair market value of it into each employee's wages, works the amount out correctly, and reports it that way.

**Read from:** the regulation's own worked example at § 1.274-12(c)(2)(i)(E)(1), Example 1 — "Thus, G may deduct 100 percent of the food and beverage expenses."

---

## M11 · A company cafeteria, with the value left out of income

**Citation:** 26 CFR 1.274-12(c)(2)(i)(D)

**Answer:** 50 percent deductible

**Facts:** An employer serves meals free of charge to employees, and the whole value of them is left out of the employees' income because they are furnished for the employer's convenience. Nothing for them appears in the employees' wages.

**Read from:** the regulation's own worked example at § 1.274-12(c)(2)(i)(E)(3), Example 3 — "Thus, the exception in section 274(e)(2) and paragraph (c)(2)(i) of this section does not apply and, assuming no other exceptions ... apply, H may deduct only 50 percent of the expenses for the food and beverages provided to employees."

---

## M12 · One week of work and five weeks of holiday

**Citation:** 26 CFR 1.162-2(b)(1)

**Answer:** not deductible

**Facts:** A taxpayer flies to a distant city, spends one week there on work directly related to the business, and then stays a further five weeks doing nothing but personal things. There is no other showing about why the trip was made. The amount at issue is the air fare there and back.

**Read from:** two paragraphs, because it takes two. The regulation's own worked example at § 1.162-2(b)(2) — "the trip will be considered primarily personal in nature in the absence of a clear showing to the contrary" — and then the rule at the citation above, which is stored: "If the trip is primarily personal in nature, the traveling expenses to and from the destination are not deductible."

---

## M13 · Getting to work and back

**Citation:** 26 CFR 1.162-2(e)

**Answer:** not deductible

**Facts:** A sole proprietor buys a monthly rail pass — the fare from home to the business premises in the morning and back at night. It is used for nothing else.

**Read from:** not an example. The rule at the citation states its own conclusion in one sentence: "Commuters' fares are not considered as business expenses and are not deductible."

---

## M14 · A restaurant charge with nothing kept for it

**Citation:** 26 CFR 1.274-5(c)(2)(iii)(A)

**Answer:** documentary evidence is required

**Facts:** A card feed shows a $92 charge at a restaurant during a business trip. Nothing at all was kept for it: no receipt, no paid bill, no other document. It was not for lodging.

**Read from:** not an example. The rule at the citation states the requirement and the floor it starts at: documentary evidence "is required for ... Any other expenditure of $75 or more except, for transportation charges, documentary evidence will not be required if not readily available."

---

## M15 · A group that takes turns paying

**Citation:** IRS Pub. 463 (2025), "50% Limit" — taking turns paying for meals

**Answer:** not deductible

**Facts:** Several business acquaintances take turns picking up each other's meal checks. They do it because that is how the group has always done it, and without regard to whether any business is served by any particular meal.

**Read from:** not an example, and not a regulation. The publication states its own conclusion: "If a group of business acquaintances takes turns picking up each others' meal checks primarily for personal reasons, without regard to whether any business purposes are served, no member of the group can deduct any part of the expense." Publication 463 is secondary, so this row grades `escalated` rather than `correct` no matter who answers it — the recorded answer is what the source says, not what the desk may serve.

---

## M16 · What a feed does not carry

**Citation:** 26 CFR 1.274-5T(b)(2)

**Answer:** amount, time, place, and business purpose

**Facts:** A card feed shows an airline charge and a hotel charge for a trip out of state. Nothing else about the trip has been written down anywhere. The amount at issue is what the record has to establish before either charge can be substantiated.

**Read from:** not an example. The rule at the citation lists the elements by name and heads each with the word itself — "Amount", "Time", "Place", "Business purpose".

## PB1 · A housekeeping service for the house the owner lives in

**Citation:** 26 CFR 1.262-1(b)(3) — maintaining a household

**Answer:** not deductible

**Facts:** A sole proprietor pays a housekeeping service every fortnight to clean the house he and his family live in, and the charges run through the business account. The business leases a yard several miles away and works out of it. No part of the house is used to carry on the trade.

**Answer read from:** "Expenses of maintaining a household, including amounts paid for rent, water, utilities, domestic service, and the like, are not deductible."

---

## PB2 · An apartment where the owner sometimes works in the evening

**Citation:** 26 CFR 1.262-1(b)(3) — business conducted incidentally at a residence

**Answer:** no part of the rent is deductible

**Facts:** A taxpayer rents an apartment for residential purposes. His place of business is a rented shop on the other side of town. Two or three evenings a week he answers customer calls and writes up estimates at his kitchen table there. He asks what share of the apartment rent the business may take.

**Answer read from:** "A taxpayer who rents a property for residential purposes, but incidentally conducts business there (his place of business being elsewhere) shall not deduct any part of the rent."

---

## PB3 · One room of a rented house, and no other place of business

**Citation:** 26 CFR 1.262-1(b)(3) — part of the house used as the place of business

**Answer:** the portion properly attributable to the place of business is deductible as a business expense

**Facts:** A taxpayer rents a house. He carries on his trade from one room of it and has no other premises anywhere. He asks how the rent and similar outgoings on the house are treated.

**Answer read from:** "If, however, he uses part of the house as his place of business, such portion of the rent and other similar expenses as is properly attributable to such place of business is deductible as a business expense."

---

## PB4 · A sword, bought at a shop that sells clothing

**Citation:** 26 CFR 1.262-1(b)(8) — the sword and the uniform

**Answer:** an allowable deduction

**Facts:** A member of the armed services on continuous active duty buys a sword. It went on a card, and the feed carries the vendor's name and the amount and nothing else. The vendor is a retail outfitter whose catalogue is mostly civilian clothing. Asked what the purchase was, the client says it was the sword. No nontaxable allowance was received for it.

**Answer read from:** "For example, the cost of a sword is an allowable deduction in computing taxable income, but the cost of a uniform is not." — the first half of that sentence. The vendor is in the facts and in no part of the regulation.

---

## PB5 · A uniform, bought at the same shop, on the same card

**Citation:** 26 CFR 1.262-1(b)(8) — the sword and the uniform

**Answer:** not an allowable deduction

**Facts:** The same member of the armed services, on continuous active duty and not a reservist, buys a uniform from the same retail outfitter on the same card two weeks later. The feed again carries the vendor's name and the amount and nothing else. Asked what the purchase was, the client says it was the uniform.

**Answer read from:** "For example, the cost of a sword is an allowable deduction in computing taxable income, but the cost of a uniform is not." — the second half of the same sentence. Same seller as PB4, opposite answer.

---

## PB6 · Fuel for the drive to the yard and back

**Citation:** 26 CFR 1.262-1(b)(5) — commuting

**Answer:** personal expenses that do not qualify as deductible expenses

**Facts:** A sole proprietor drives each morning from the house where he and his family live to the yard his business rents, and drives home again each evening. Fuel for those trips is charged to the business card.

**Answer read from:** "The taxpayer's costs of commuting to his place of business or employment are personal expenses and do not qualify as deductible expenses."

---

## PB7 · The policy on the house the owner lives in

**Citation:** 26 CFR 1.262-1(b)(2) — insuring a personal residence

**Answer:** not deductible

**Facts:** The annual homeowner's policy on the dwelling the owner and his family own and occupy is paid from the business account. The business rents its premises elsewhere and insures them separately.

**Answer read from:** "The cost of insuring a dwelling owned and occupied by the taxpayer as a personal residence is not deductible."

---

## PB8 · A life policy on the owner's own life

**Citation:** 26 CFR 1.262-1(b)(1) — life insurance premiums

**Answer:** not deductible

**Facts:** A monthly premium on a life insurance policy is paid from the business account. The owner is the insured and pays it himself through the business.

**Answer read from:** "Premiums paid for life insurance by the insured are not deductible."

---

## PH1 · A den the family also uses

**Citation:** IRS Pub. 587 (2025), "Exclusive Use" — the den the family also uses

**Answer:** no deduction for the business use of the den

**Facts:** A self-employed attorney writes legal briefs and prepares clients' tax returns in a den at home. The attorney's family also uses the den for recreation.

**Answer read from:** "The den is not used exclusively in your trade or business, so you cannot claim a deduction for the business use of the den."

---

## PH2 · Half a basement, used for stock and sometimes for other things

**Citation:** IRS Pub. 587 (2025), "Exceptions to Exclusive Use" — the basement

**Answer:** the expenses for the storage space are deductible

**Facts:** A taxpayer's home is the only fixed location of a business selling mechanics' tools at retail. Half the basement is used regularly to keep inventory and product samples. The area is sometimes used for other things as well.

**Answer read from:** "The expenses for the storage space are deductible even though you do not use this part of your basement exclusively for business."

---

## PH3 · A greenhouse at home, feeding a shop in town

**Citation:** IRS Pub. 587 (2025), "Separate Structure" — the greenhouse

**Answer:** the expenses for its use are deductible

**Facts:** A florist operates a shop in town and grows the plants for the shop in a greenhouse at home. The greenhouse is used exclusively and regularly for the floral shop business.

**Answer read from:** "Bobbie uses the greenhouse exclusively and regularly for the floral shop business, so Bobbie can deduct the expenses for its use (subject to certain limitations, described later)."

---

## PH4 · A room used to run the taxpayer's own money

**Citation:** IRS Pub. 587 (2025), "Trade or Business Use" — the taxpayer's own investments

**Answer:** no deduction for the business use of the home

**Facts:** A taxpayer uses part of the home exclusively and regularly to read financial periodicals and reports, clip bond coupons and carry out similar activities relating to money the taxpayer has invested. The taxpayer is neither a broker nor a dealer.

**Answer read from:** "So, your activities are not part of a trade or business and you cannot take a deduction for the business use of your home."

## RW1 · A manufacturer's rebate to a retail car buyer

**Citation:** Rev. Rul. 2005-28, Rev. Rul. 76-96

**Answer:** the rebates reduce the purchase price of the cars and are not includible in the retail customer's gross income

**Facts:** An automobile manufacturer offers rebates of a set amount to retail customers who independently negotiate at arm's length with one of the manufacturer's dealers to arrive at a price for a new car. A customer negotiates such a price, buys the car, and is paid the rebate by the manufacturer.

---

## RW2 · A rebate cheque on a car bought for cash

**Citation:** IRS Pub. 525 (2025), "Cash rebates"

**Answer:** not income; the basis in the car is reduced by the amount of the rebate

**Facts:** You buy a new car for $24,000 cash and receive a $2,000 rebate check from the manufacturer.

---

## RW3 · Payments to the buyers' own employees

**Citation:** Rev. Rul. 2005-28, United Draperies

**Answer:** could not be excluded from income

**Facts:** A drapery manufacturer pays kickbacks to employees of the companies that buy its draperies, so that those employees send their employers' business to the manufacturer. The amounts are independent of the manufacturer's agreement with its purchasers fixing the selling price of the products sold, and are paid for a consideration separate from that selling price.

---

## RW4 · Medicaid rebates paid by a drug manufacturer

**Citation:** Rev. Rul. 2005-28, HOLDING

**Answer:** purchase price adjustments that are subtracted from gross receipts in determining gross income

**Facts:** A pharmaceutical manufacturer using an accrual method manufactures and sells prescription drugs. Under a Rebate Agreement signed with the Department of Health and Human Services it pays Medicaid Rebates directly to each State Medicaid Agency. A Medicaid Rebate is a portion of the price paid by State Medicaid Agencies to retailers for covered outpatient drugs dispensed to Medicaid beneficiaries, and the amount is negotiated and agreed before the manufacturer sells to its wholesaler.

---

## RW5 · Frequent flyer miles earned on business travel and used personally

**Citation:** Announcement 2002-18, the relief

**Answer:** the IRS will not assert that the taxpayer has understated his federal tax liability

**Facts:** An individual accumulates frequent flyer miles as the result of business travel paid for by the employer, and later exchanges those miles for free personal travel.

---

## RW6 · The same benefits, turned into money

**Citation:** Announcement 2002-18, what the relief does not cover

**Answer:** the relief does not apply

**Facts:** Promotional benefits attributable to a taxpayer's business travel are converted to cash.

---

## RW7 · Rebates earned on credit card purchases

**Citation:** PLR 201027015, Ruling request (1)

**Answer:** an adjustment to the purchase price of the items purchased, and not includible in gross income

**Facts:** Individuals hold credit cards issued under an arrangement promoted by a company. They make purchases with the cards and, as a result of those purchases, become entitled to an amount equal to a percentage of their credit card purchases less the company's fees. They may take that amount in cash, or instead direct the company to pay it to a charity they choose from a list.

---

## RW8 · A dealer's cars and the maker's price reduction

**Citation:** IRS Pub. 334 (2025), "Trade discounts"

**Answer:** the cost of the car in inventory is reduced by the amount allowed, and the amount is not shown separately as an item in gross income

**Facts:** An automobile dealer holds cars in inventory for sale. The manufacturer allows the dealer a reduction from the list price of each car. The reduction is not written into the invoice and is not charged to the customer.

---

## RW9 · A prompt-payment allowance credited to its own account

**Citation:** IRS Pub. 334 (2025), "Cash discounts"

**Answer:** the credit balance in that account is included in business income at the end of the tax year

**Facts:** A business's suppliers let it deduct an amount from its purchase invoices for paying promptly. The business credits those amounts to a separate discount account rather than deducting them from total purchases for the year.

---

## IR1 · A contractor paid by cheque

**Citation:** 26 USC 6041(a)

**Answer:** a return to the Secretary is required

**Facts:** A sole proprietor pays an individual who is not an employee $2,400 during calendar year 2026 for services performed in the course of the proprietor's business. Every payment was made by cheque drawn on the business account.

---

## IR2 · Telling the payee what was reported

**Citation:** 26 USC 6041(d)

**Answer:** on or before January 31 of the year following the calendar year

**Facts:** A business is required to make a return under section 6041 for calendar year 2026 covering payments to a person who is not an employee. It must also furnish that person a written statement of the amount shown on the return. By when?

---

## IR3 · Filing the nonemployee compensation return

**Citation:** 26 USC 6071(c)

**Answer:** on or before January 31 of the year following the calendar year

**Facts:** A payer has to file with the Service the return that reports nonemployee compensation for calendar year 2026. By when?

---

## IR4 · Paid by credit card

**Citation:** 26 CFR 1.6041-1(a)(1)(iv)

**Answer:** the payor is not required to file an information return under section 6041

**Facts:** Restaurant owner A, in the course of business, pays $600 of fixed or determinable income to B, a repairman, by credit card. B is one of a network of unrelated persons that has agreed to accept A's credit card as payment under an agreement that provides standards and mechanisms for settling the transactions between a merchant acquiring bank and the persons who accept the cards. Merchant acquiring bank Y is responsible for making the payment to B.

---

## IR5 · Paid through a third party payment network

**Citation:** 26 CFR 1.6041-1(a)(1)(iv)

**Answer:** the payor is not required to file an information return under section 6041

**Facts:** Restaurant owner A, in the course of business, pays $600 of fixed or determinable income to B, a repairman, through a third party payment network. B is one of a substantial number of persons who have established accounts with Y, a third party settlement organization that provides standards and mechanisms for settling the transactions and guarantees payments to those persons for goods or services purchased through the network. Y is responsible for making the payment to B.

---

## IR6 · A repair company that is a corporation

**Citation:** 26 CFR 1.6041-3(p)

**Answer:** returns of information are not required under section 6041

**Facts:** A business pays a plumbing company $9,000 during the calendar year for repair work at its premises. The plumbing company is a corporation. It provides no legal services and no medical and health care services.

---

## IR7 · A law firm that is a corporation

**Citation:** 26 CFR 1.6041-3(p)

**Answer:** a return of information is required

**Facts:** A business pays a law firm $12,000 during the calendar year in fees for legal work done in the course of the business. The law firm is a corporation. The payments were made in 2026.

---

## IR8 · A medical practice that is a corporation

**Citation:** 26 CFR 1.6041-3(p)

**Answer:** a return of information is required

**Facts:** A business pays $4,000 during the calendar year to a corporation engaged in providing medical and health care services. The corporation is not a hospital or extended care facility described in section 501(c)(3), and is not owned or operated by the United States, a State or any political subdivision.

---

## IR9 · A supplier's bills for goods

**Citation:** 26 CFR 1.6041-3(c)

**Answer:** returns of information are not required under section 6041

**Facts:** A business pays a supplier $30,000 during the calendar year on bills for merchandise bought for the business.

---

## IR10 · What the payment app itself has to report

**Citation:** 26 USC 6050W(e)

**Answer:** the third party settlement organization is not required to report

**Facts:** During the calendar year a third party settlement organization settles third party network transactions for one participating payee: 150 transactions totalling $30,000.

## VE1 · An inspector who uses her own car for a construction company

**Citation:** 26 CFR 1.280F-6(a)(2)(ii)

**Answer:** for the convenience of the employer and required as a condition of employment

**Facts:** An inspector works for a construction company with many construction sites in the local area. She is required to travel to the various construction sites on a regular basis, and she uses her own automobile to make these trips. The company does not furnish her an automobile, and it does not explicitly require her to use her own. The company reimburses her for any costs she incurs in traveling to the various job sites.

**Read from:** 26 CFR 1.280F-6(a)(4), Example 2 — "B's use of here automobile in here employment is for the convenience of X and is required as a condition of employment." (The two "here" are the eCFR's own typography.) The example names no paragraph; the rule its conclusion tracks is (a)(2)(ii), which states that "the employer need not explicitly require the employee to use the property" and that whether the use is required "depends on all the facts and circumstances" — the only fact the example varies.

---

## VE2 · The same inspector, when the company has a car she could have used

**Citation:** 26 CFR 1.280F-6(a)(2)(ii)

**Answer:** not for the convenience of the employer and not required as a condition of employment

**Facts:** An inspector works for a construction company with many construction sites in the local area. She is required to travel to the various construction sites on a regular basis. The company makes an automobile available to her; she chooses to use her own automobile instead and to receive reimbursement for the cost.

**Read from:** 26 CFR 1.280F-6(a)(4), Example 3 — "B's use of her own automobile is not for the convenience of X and is not required as a condition of employment." Example 3 is written as a variation on Example 2 ("Assume the same facts as in Example 2, except that…"); it is restated whole here so the problem stands alone.

---

## VE3 · A courier whose employer requires him to own a vehicle

**Citation:** 26 CFR 1.280F-6(a)(2)(ii)

**Answer:** for the convenience of the employer and required as a condition of employment

**Facts:** A courier is employed by a company providing local courier services. He owns a motorcycle and uses it to deliver packages to downtown offices for the company. The company does not provide delivery vehicles and explicitly requires all of its couriers to own a car or motorcycle for use in their employment with it.

**Read from:** 26 CFR 1.280F-6(a)(4), Example 1 — "A's use of the motorcycle for delivery purposes is for the convenience of W and is required as a condition of employment."

---

## VE4 · A proprietor's brother driving the company truck

**Citation:** 26 CFR 1.280F-6(d)(2)(ii)(A)(2)

**Answer:** not a qualified business use

**Facts:** The proprietor of a plumbing contracting business employs his brother in the company. As part of his compensation, the brother is allowed to use one of the company automobiles for personal use.

**Read from:** 26 CFR 1.280F-6(d)(5), Example 3 — "The use of the company automobiles by F's brother is not a qualified business use because F and F's brother are related parties within the meaning of section 267(b)." The rule the conclusion tracks is (d)(2)(ii)(A)(2), "Use of property provided as compensation for the performance of services by a 5-percent owner or related person"; (d)(2)(ii)(C)(2) is the definition that makes section 267(b) the test.

---

## VE5 · A company car taken home at night, with the value on the W-2

**Citation:** 26 CFR 1.280F-6(d)(2)(ii)(A)(3)

**Answer:** a qualified business use

**Facts:** A corporation owns several automobiles which its employees use for business purposes. The employees are also allowed to take the automobiles home at night. The fair market value of the use of an automobile for any personal purpose, such as commuting to work, is reported by the corporation as income to the employee and is withheld upon by the corporation.

**Read from:** 26 CFR 1.280F-6(d)(5), Example 5 — "The use of the automobile by the employee, even for personal purposes, is a qualified business use the respect to X." ("the respect to X" is the eCFR's own text.) The rule the conclusion tracks is (d)(2)(ii)(A)(3), which excludes such use from qualified business use "unless an amount is properly reported by the taxpayer as income to such person and, where required, there was withholding under chapter 24".

---

## VE6 · The same company cars, with nothing on anybody's W-2

**Citation:** 26 CFR 1.280F-6(d)(3)(iv)

**Answer:** not business/investment use

**Facts:** The proprietor of a plumbing contracting business allows employees unrelated to him to use company automobiles as part of their compensation. He does not include the value of these automobiles in the employees' gross income, and he does not withhold with respect to the use of these automobiles.

**Read from:** 26 CFR 1.280F-6(d)(5), Example 4 — "The use of the company automobiles by the employees in this case is not business/investment use." The rule the conclusion tracks is (d)(3)(iv), under which use of the taxpayer's automobile by another person is not use in a trade or business unless it is directly connected with the taxpayer's business, is reported as income with withholding, or produces fair market rent.

---

## VE7 · A daily rate with part of it labelled travel

**Citation:** 26 CFR 1.62-2(d)(3)(i)

**Answer:** does not satisfy the reimbursement requirement

**Facts:** An employer pays its engineers $200 a day. On those days that an engineer travels away from home on the employer's business, the employer designates $50 of the $200 as paid to reimburse the engineer's travel expenses. The employer would pay an engineer $200 a day regardless of whether the engineer was traveling away from home.

**Read from:** 26 CFR 1.62-2(j), Example 1 — "the arrangement does not satisfy the reimbursement requirement of paragraph (d)(3)(i) of this section."

---

## VE8 · An allowance paid only to the crews who actually travel

**Citation:** 26 CFR 1.62-2(d)(3)(i)

**Answer:** satisfies the reimbursement requirement

**Facts:** An airline pays all its employees a salary. It also pays an allowance, under an arrangement that meets every other condition for an accountable plan, to its pilots and flight attendants who travel away from their home base airports — whether or not they are away from home.

**Read from:** 26 CFR 1.62-2(j), Example 2 — "the arrangement satisfies the reimbursement requirement of paragraph (d)(3)(i) of this section." The example's own phrase "an arrangement that otherwise meets the requirements of paragraphs (d), (e), and (f) of this section" is replaced above, because it names the family the answer's citation comes from.

---

## VE9 · An allowance paid to salespeople who never leave the office

**Citation:** 26 CFR 1.62-2(d)(3)(i)

**Answer:** does not satisfy the reimbursement requirement

**Facts:** A corporation pays all its salespersons a salary. It also pays a travel allowance under an arrangement that meets every other condition for an accountable plan. That allowance is paid to all salespersons, including salespersons the corporation knows, or has reason to know, do not travel away from their offices on the corporation's business and would not be reasonably expected to incur travel expenses.

**Read from:** 26 CFR 1.62-2(j), Example 3 — "the arrangement does not satisfy the reimbursement requirement of paragraph (d)(3)(i) of this section."

---

## VE10 · Three months of records standing for the year

**Citation:** 26 CFR 1.274-5T(c)(3)(ii)(A)

**Answer:** based on sufficient corroborative evidence

**Facts:** A sole proprietor and calendar year taxpayer operates an interior decorating business out of her home. She uses an automobile for local business travel to visit the homes or offices of clients, to meet with suppliers and other subcontractors, and to pick up and deliver certain items to clients when feasible. There is no other business use of the automobile, but she and other members of her family also use it for personal purposes. She maintains adequate records for the first three months of the year that indicate 75 percent of the use of the automobile was in her business. Invoices from subcontractors and paid bills indicate that her business continued at approximately the same rate for the remainder of the year. No other circumstances change; she does not obtain a second car for exclusive use in her business.

**Read from:** 26 CFR 1.274-5T(c)(3)(ii)(C), Example 1 — "the determination that the business/investment use of the automobile for the taxable year is 75 percent is based on sufficient corroborative evidence." The lead-in at (c)(3)(ii)(C) states that its examples "illustrate this paragraph (c)(3)(ii)", and the sampling rule inside it is (c)(3)(ii)(A).

---

## VE11 · One week a month, standing for the month

**Citation:** 26 CFR 1.274-5T(c)(3)(ii)(A)

**Answer:** based on sufficient corroborative evidence

**Facts:** A sole proprietor and calendar year taxpayer operates an interior decorating business out of her home, and uses an automobile for local business travel to clients and suppliers. She and her family also use the automobile for personal purposes. She maintains adequate records during the first week of every month, which indicate that 75 percent of the use of the automobile is in her business. The invoices from her business indicate that it continued at the same rate during the subsequent weeks of each month, so that her weekly records are representative of each month's business use of the automobile.

**Read from:** 26 CFR 1.274-5T(c)(3)(ii)(C), Example 2 — "the determination that the business/investment use of the automobile for the taxable year is 75 percent is based on sufficient corroborative evidence."

---

## VE12 · The one week of the month that is not like the others

**Citation:** 26 CFR 1.274-5T(c)(3)(ii)(A)

**Answer:** not based on sufficient corroborative evidence

**Facts:** A sole proprietor and calendar year taxpayer is a salesman in a large metropolitan area for a company that manufactures household products. For the first three weeks of each month he uses his own automobile occasionally to travel within the metropolitan area on business, and during those three weeks his business use does not follow a consistent pattern from day to day or week to week. During the fourth week of each month he delivers to his customers all the orders taken during the previous month. His use of the automobile for business purposes during that fourth week, as substantiated by adequate records, is 70 percent of the total use. He proposes to determine the business/investment use of the automobile for the taxable year from the records kept during those fourth weeks.

**Read from:** 26 CFR 1.274-5T(c)(3)(ii)(C), Example 3 — "a determination based on the records maintained during that fourth week that the business/investment use of the automobile for the taxable year is 70 percent is not based on sufficient corroborative evidence because use during this week is not representative of use during other periods."

---

## VE13 · A contractor's car that is not only used for the business

**Citation:** IRS Pub. 463 (2025), "Business and personal use"

**Answer:** 60%

**Facts:** A contractor drives a car 20,000 miles during the year: 12,000 miles for business use and 8,000 miles for personal use. How much of the cost of operating the car is a business expense?

**Read from:** IRS Pub. 463 (2025), under "Business and personal use", the example — "You can claim only 60% (12,000 ÷ 20,000) of the cost of operating your car as a business expense."

---

## VE14 · Five vehicles, never on the road together

**Citation:** IRS Pub. 463 (2025), "Five or more cars"

**Answer:** the standard mileage rate

**Facts:** A salesperson owns three cars and two vans, alternating between them to call on customers. They are never used at the same time. Which method may the salesperson use for their business mileage?

**Read from:** IRS Pub. 463 (2025), under "Five or more cars", Example 1 — "The salesperson can use the standard mileage rate for the business mileage of the three cars and the two vans because they don't use them at the same time."

---

## VE15 · Five vehicles, all on the road together

**Citation:** IRS Pub. 463 (2025), "Five or more cars"

**Answer:** actual expenses

**Facts:** A housecleaning business owns a car and four vans, all used in the business. The employees use the vans, and the owner uses the car to travel to various customers. Which method must the business use for these five vehicles?

**Read from:** IRS Pub. 463 (2025), under "Five or more cars", Example 4 — "You can't use the standard mileage rate for the car or the vans. This is because all five vehicles are used in your business at the same time. You must use actual expenses for all vehicles."
