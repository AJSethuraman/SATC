# Subjects — what brings this desk into play

`Answered from <source id>` is what makes routing deterministic AND what makes a
citation checkable: it names the subjects that bring a desk into play, and which
source answers each of them. Their union is what routing fires on, so there is no
second list to drift. It matches **whole words only** — substring matching once made
*"extension"* fire on *"extensive"*.

**It under-fires, and that is worth knowing.** The list matches a question's
subject, not its shape, so an inflected form is missed: `travel` does not fire on
`travels`, and `meal` does not fire on `meals`. Both forms are listed where both
occur; anything not listed simply does not route, and `Served.checked_subject`
then says the subject could not be checked rather than that it was fine.

**Six sources, and the split between them is the whole answer.** A line in a card
feed is a food-or-beverage question (S1), an entertainment question (S2), a
was-this-a-business-trip question (S3), or a can-you-prove-it question (S4/S5) —
and the same charge is often two of them at once. S6 is secondary and is the only
source here that can make a question escalate.

---

## meals-and-entertainment · What share of a meal, an entertainment cost or a travel cost is deductible, and what has to be substantiated for it

**Answered from S1:** meal, meals, food, beverage, beverages, drink, drinks, lunch, dinner, breakfast, snack, snacks, coffee, refreshments, groceries, grocery, supermarket, cafeteria, restaurant, catering, buffet, break room, holiday party, picnic, per diem

**Answered from S2:** entertainment, entertaining, amusement, recreation, ticket, tickets, game, concert, theater, theatre, golf, country club, club dues, sporting event, suite, bar, taproom, brewery, nightclub

**Answered from S3:** travel, traveling, travelling, trip, airfare, air fare, fare, fares, lodging, hotel, motel, convention, commuting, commute, vacation, destination, away from home

**Answered from S4:** documentary evidence, receipt, receipts, paid bill, paid bills, canceled check, cancelled check, adequate accounting

**Answered from S5:** substantiation, substantiate, substantiated, adequate records, account book, diary, log, business purpose, business relationship, elements

**Answered from S6:** take turns, takes turns, taking turns, picking up, hours of service, standard meal allowance, lavish, extravagant
