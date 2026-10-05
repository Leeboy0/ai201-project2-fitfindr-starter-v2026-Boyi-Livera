# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
Search doesn't use the model, so the same query finds the same listing every
time: a phrasing my keyword match missed would fail all 5 tries, not 1. What
can go wrong in a single try is the two model calls (`suggest_outfit` and
`create_fit_card`), such as a rate-limit wait, a timeout, or a blank response.
4 of 5 allows one such failure; 5 of 5 would assume the model service never fails.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never reaches the model. `search_listings` gives the same result
every time, and the branch is a plain `if not results:` check. The same input
produces the same output, so any failure is a bug in my code, not bad luck.

---

## 3. The item search found is the item the later tools received

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

For a matching query, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and the trace shows that same id going
into both `suggest_outfit` and `create_fit_card` — in 5 of 5 tries.

**Why this target:**
Passing the item along is plain code with no model involved, so it should
never vary. If the ids don't match, it's a state bug, such as overwriting
`selected_item` or passing the wrong variable. That kind of bug would otherwise
look like a bad outfit suggestion, which is why it's worth checking directly.

---

## 4. The fit card is an acceptable caption

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

Each fit card is 2–4 sentences and contains the selected item's price written
as `$<price>` (e.g. `$24`) and its `platform` name — in at least 4 of 5 tries.
Across those 5 tries of the same query, no two cards have the same first sentence.

**Why this target:**
The prompt asks for all of this, but the model doesn't always follow it. In my
own test it wrote the price as "thirty-eight bucks" and wrote as the seller
until I tightened the prompt. 4 of 5 allows one slip like that. The
first-sentence rule is strict on purpose: two runs with the cache off both
opened with "Scored these vintage Levi's 501 jeans on Depop for just $38." I
expect this part to be hard to meet, and I'd rather measure that than hide it.

---

## 5. The search respects the price ceiling and size

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

For the query "graphic tee size S under $20", every listing in
`session["search_results"]` costs $20 or less and has a size that contains "S"
as a separate piece (so "S/M" counts, but "US 7" doesn't) — in 5 of 5 tries.

**Why this target:**
Both filters are plain code with no model, so they should never slip. The real
risk is my query parser in `run_agent`. If it misses "$20" or "size S", that
filter is skipped silently and the results look plausible but are wrong.
Because the parser gives the same result every time, it will either pass all 5
tries or fail all 5.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. The fit card is an acceptable caption

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
