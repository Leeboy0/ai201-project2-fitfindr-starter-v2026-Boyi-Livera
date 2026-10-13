# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr takes a plain-language thrift request like "vintage graphic tee size M under $30" and finds the best-matching secondhand listing from Depop, thredUp and Poshmark data, respecting the size and price ceiling. It then suggests one or two outfits that pair the find with pieces the user already owns (or general styling advice if their wardrobe is empty), and writes a short social-media caption about it. If nothing matches, it stops before calling the model and tells the user what to change: raise the price, drop the size, or use different keywords.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters `data/listings.json` by price and size, then ranks what's left by how many of the description's keywords appear in each listing (no model call).
- **Inputs:** `description` (str) — keywords like "vintage graphic tee"; `size` (str or None) — None skips size filtering; `max_price` (float or None) — inclusive ceiling, None skips price filtering.
- **Returns:** A `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) listing dicts, best match first. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`. Scoring: the description is lowercased and split into unique alphanumeric words; a trailing plural "s" is dropped from words longer than 3 letters ("tees" = "tee"); these stopwords are removed: a, an, and, the, for, of, in, on, with, to, my, me, i, im, looking, want, need, find, some, something, any, under, below, less, than, size, sized, around, about. Each remaining keyword must match a whole word (not a substring): it scores 2 if it's in the title or style tags, otherwise 1 if it's in the description, category, colors or brand. Ties go to the listing whose title contains more keywords, then to dataset order. **Size match rule:** the size strings are split into tokens on spaces, `/` and parentheses (case-insensitive), and a listing matches only if every token of the requested size is a whole token of its size. So "M" matches "M", "S/M", "M/L"; "L" does not match "XL"; "S" does not match "US 7"; "W30" matches "W30 L30"; "One Size" matches every "One Size …" listing.
- **When it has nothing:** An empty list `[]` — never None, never an exception. This happens when no listing passes the filters with a score above zero, or when the description has no usable keywords (empty, or only stopwords).

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the thrifted item, using pieces from the user's wardrobe when there are any.
- **Inputs:** `new_item` (dict) — one listing dict from `search_listings`; `wardrobe` (dict) — has an `items` key holding a list of wardrobe item dicts (`id`, `name`, `category`, `colors`, `style_tags`, `notes`), and the list may be empty.
- **Returns:** A non-empty `str` of under ~120 words describing one or two outfits. With a non-empty wardrobe, it names owned pieces exactly as they appear in `wardrobe["items"][i]["name"]`.
- **When it has nothing:** If the wardrobe is empty (or `items` is missing or None), it still returns a non-empty string: general styling advice using common staple pieces instead of owned ones. If the model returns blank text, it returns `"Couldn't generate an outfit suggestion for this item — try again."` It never returns `""`. If the model can't be reached, `generate()` raises `ModelUnavailable` and the loop handles it.

### `create_fit_card`

- **What it does:** Asks the model for a short social-media caption about the find and how it's styled.
- **Inputs:** `outfit` (str) — the string returned by `suggest_outfit`; `new_item` (dict) — the same listing dict passed to `suggest_outfit`.
- **Returns:** A `str` caption of 2–4 sentences, written as the buyer showing off their find (not the seller). It mentions the item, its `price` (as a dollar amount, e.g. "$38") and its `platform` once each, and mentions a brand only when `brand` is not None. It varies between runs (`TEMPERATURE` = 0.9).
- **When it has nothing:** If `outfit` is empty or only whitespace, it skips the model and returns exactly `"Can't write a fit card: no outfit suggestion was provided. Run suggest_outfit first and pass its result in."` If the model returns blank text, it returns `"Couldn't generate a fit card for this item — try again."` It never returns `""`. If the model can't be reached, `generate()` raises `ModelUnavailable` and the loop handles it.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that tells the user what to change (raise the price, drop the size, or use fewer or different keywords) and return the session without calling `suggest_outfit`. Otherwise, put the first result in `session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. A price is the number after "under", "below", "max", "less than", "up to" or a `$` (→ `max_price` float). A size is the word after "size", optionally "US 9"-style, with small/medium/large mapped to S/M/L (→ `size` str). Whatever text is left, with commas removed, is the `description`. A missing price or size becomes None.

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` (list of listing dicts) → `selected_item` (`search_results[0]`) → `outfit_suggestion` (read back with `selected_item` and `wardrobe`) → `fit_card` (read back with `outfit_suggestion` and `selected_item`). On an empty search, `error` is set and every field after `search_results` stays None.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Y2K Baby Tee — Butterfly Print … +7 more
      →    branch: found, selected lst_006
[3] suggest_outfit
      in:  new_item=lst_006, wardrobe_items=10
      out: **Outfit 1 (Grunge Streetwear)** * New Item: Graphic Tee — 2003 Tour Bootleg Style * Owned Bottoms: Baggy stra…
[4] create_fit_card
      in:  new_item=lst_006
      out: Scored this 2003 tour bootleg tee on depop for just $24 and I'm honestly obsessed with the fade on it. Paired …

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   **Outfit 1 (Grunge Streetwear)**
* New Item: Graphic Tee — 2003 Tour Bootleg Style
* Owned Bottoms: Baggy straight-leg jeans, dark wash
* Owned Outerwear: Vintage black denim jacket
* Owned Shoes: Black combat boots
* Owned Accessories: Black crossbody bag

**Outfit 2 (Y2K Casual)**
* New Item: Graphic Tee — 2003 Tour Bootleg Style
* Owned Bottoms: Wide-leg khaki trousers
* Owned Tops: Black cropped zip hoodie (worn open)
* Owned Shoes: Chunky white sneakers
* Owned Accessories: Black crossbody bag

  Fit card: Scored this 2003 tour bootleg tee on depop for just $24 and I'm honestly obsessed with the fade on it. Paired it with baggy denim and combat boots today for the ultimate grunge streetwear look. Can't wait to style it a million more ways.

0 model calls this session, 2 served from cache
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
**Outfit 1: Casual Streetwear**
Pair the Vintage Levi's 501 Jeans with the white ribbed tank top, layered under the oversized grey crewneck sweatshirt. Add the chunky white sneakers and the black crossbody bag for an effortless, classic look. 

**Outfit 2: Edgy Contrast**
Style the Vintage Levi's 501 Jeans with the black cropped zip hoodie and the vintage black denim jacket on top. Cinch the waist with the brown leather belt and finish the outfit with the black combat boots for a tough, textured aesthetic.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501 jeans on depop for just $38 and I'm obsessed. The medium wash has that 90s streetwear vibe down to a science. Honestly just living in these with my favorite white sneakers from now on.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I pasted the output of my three per-tool tests into Claude and asked whether the results were correct.
- *What came back:* Search and outfits were fine, but the fit card for the Levi's 501s said "just waiting in my Depop shop for thirty-eight bucks. Grab them before I change my mind and keep them." It was written as the seller, not someone showing off a find, and the price was in words, so a check for "$38" would miss it.
- *What I changed:* I had the `create_fit_card` prompt changed to say the poster is the buyer, not the seller, and to write the price as a dollar amount (e.g. $38). Two re-runs with the cache off both opened "Scored these vintage Levi's 501 jeans on Depop for just $38". I also noticed those two captions were almost word-for-word the same, which is why criterion 4 checks first sentences.

**Moment 2**

- *What I asked for:* I asked Claude to build `run_agent` with trace steps, so I could check that the item search found is the same item `suggest_outfit` received (criterion 3).
- *What came back:* The loop worked, but the trace printed `in: dict with keys: new_item_id, wardrobe_items` instead of the id. `trace.py::_short` shortens any dict to its key names, so the trace couldn't prove what criterion 3 asks.
- *What I changed:* The trace inputs are now passed as strings (`new_item=lst_006, wardrobe_items=10`), so the trace shows `lst_006` selected by search, then `lst_006` going into both `suggest_outfit` and `create_fit_card`.

**Moment 3**

- *What I asked for:* I asked AI for the requirement of each milestones and how do I approach will be the best.
- *What came back:* For Milestone 2 it triggered the three failures one at a time. Empty search and empty wardrobe were already handled. The bad key wasn't: run with a broken `GEMINI_API_KEY` and the cache off, `ModelUnavailable` escaped `run_agent`. `app.py`'s catch-all printed `ModelUnavailable: The model rejected your API key…` and exited with code 1, so the session was lost and the trace didn't show which step failed.
- *What I changed:* I had a `try/except ModelUnavailable` added around steps 3–4 in `agent.py::run_agent`. It puts a message in `session["error"]` naming the found item, what broke and what to do, and adds a trace step `branch: model unavailable, stopping`. Re-run with the bad key, the trace now stops at `[3] suggest_outfit` and the run exits cleanly. I also had step 2 relabelled `search_listings (via MCP)`, because the trace had looked identical to a direct call.

**Moment 4**

- *What I asked for:* I asked Claude to score my before run (`results/run_2026-10-12_2057_before.md`) against the exact wording of each criterion in `criteria.md` and show the evidence for each PASS.
- *What came back:* All five criteria were MET 5/5. It pointed out that this was suspicious for criterion 4: four of the five Levi's cards opened "Scored these vintage Levi's 501 jeans…" and passed only because a word or two differed. When it compared the first five words instead, every scenario had a repeated opening and 17 of 25 cards started with "Scored". It also flagged a judgment call I hadn't made: the data says `depop` and the cards say `Depop`, so the platform check had to ignore case.
- *What I changed:* I kept the verdicts as MET, because that's what my criteria said, and wrote the repetition up as diagnosis 1. My improvement went after that: a new `create_fit_card` prompt with a random opening angle. Scored the same way, "Scored" openings went from 17 of 25 to 0 of 25. The after run also showed the AI's fix only moved the template, to "coffee run" and "snagged", which is in What's Still Broken.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item the later tools received | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is an acceptable caption | 4 of 5, and no repeated first sentence | PASS | PASS | PASS | PASS | PASS | MET (5/5, 5 distinct first sentences) |
| 5. The search respects the price ceiling and size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Produced by `python run_eval.py --label before` (`run_eval.py::main`, caching off, temperature 0.9), which calls `agent.py::run_agent` for every try. Full output: `results/run_2026-10-12_2057_before.md`.

**Real output from one try**, pasted as text, naming the file and function
that produced it:

**Criterion 1**: try 1 of "vintage graphic tee under $30". Loop: `agent.py::run_agent`; fit card: `tools.py::create_fit_card`.

```
- stopped early: no
- selected_item: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
- search_results: 10

Fit card:
Scored this 2003 tour bootleg style graphic tee on Depop for just $24 and I'm obsessed. Threw it on with baggy denim and combat boots for the ultimate effortless grunge fit. Honestly the best kind of find.
```

**Criterion 2**: try 1 of "designer ballgown size XXS under $5". Branch: `agent.py::run_agent`; message: `agent.py::_no_results_message`.

```
- stopped early: yes — No listings matched "designer ballgown" in size XXS under $5. Try to raise your max price, or drop the size or try a neighbouring one, or use fewer or more common keywords (e.g. "dress" instead of "ballgown").
- selected_item: (none)
- search_results: 0

[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit
```

**Criterion 3**: try 1 of "vintage graphic tee under $30" (the state scenario). Trace written by `agent.py::run_agent` through `trace.py::step`. `search_results[0]` is `lst_006`, and the same id is selected and passed to both later tools.

```
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Y2K Baby Tee — Butterfly Print … +7 more
      →    branch: found, selected lst_006
[3] suggest_outfit
      in:  new_item=lst_006, wardrobe_items=10
[4] create_fit_card
      in:  new_item=lst_006
```

**Criterion 4**: "vintage levi's 501 jeans" (lst_001, $38, depop), from `tools.py::create_fit_card`. Try 1 in full, then the first sentence of all five tries:

```
Honestly can't believe I scored these vintage Levi's 501 jeans for only $38 on Depop. The medium wash is literal perfection and they fit like an absolute dream. Already planning to live in them with chunky sneakers and oversized crews all season long.

Try 1: Honestly can't believe I scored these vintage Levi's 501 jeans for only $38 on Depop.
Try 2: scored these vintage 501s on depop for just $38 and I am never taking them off.
Try 3: Scored these vintage Levi's 501 jeans on Depop for just $38 and I am obsessed.
Try 4: Scored these vintage Levi's 501 jeans for just $38 on Depop and I am officially obsessed.
Try 5: Scored these vintage Levi's 501 jeans on Depop for just $38 and I am never taking them off.
```

Every card is 3 sentences and contains `$38` and the platform. I matched the platform case-insensitively, because the data says `depop` and the cards say `Depop`.

**Criterion 5**: try 1 of "graphic tee size S under $20". Search: `tools.py::search_listings`, called over MCP from `agent.py::run_agent`. The run log only records titles, so I printed each result's price and size with a direct call; search doesn't use the model, so these are the same two items in all five tries.

```
[2] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': 'S', 'max_price': 20.0}
      out: 2 items: Y2K Baby Tee — Butterfly Print, Mesh Long-Sleeve Top — Black
      →    branch: found, selected lst_002

$ python -c "from tools import search_listings; ..."
lst_002 Y2K Baby Tee — Butterfly Print 18.0 'S/M'
lst_017 Mesh Long-Sleeve Top — Black 15.0 'S/M'
```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All 5 tries of "vintage graphic tee under $30" ended with `error` None and a non-empty `fit_card`. No try crashed or stopped early. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All 5 traces end at `[2] search_listings (via MCP)` with `branch: empty`, there is no `[3] suggest_outfit`, and `error` names three things to change (price, size, keywords). |
| 3 | The item search found is the item the later tools received | 5 of 5 | MET (5/5) | In all 5 traces the first search result is `lst_006`, step 2 says `selected lst_006`, and steps 3 and 4 both show `new_item=lst_006`. |
| 4 | The fit card is an acceptable caption | 4 of 5, and no repeated first sentence | MET (5/5) | Every card was 3 sentences and contained `$38` and the platform. I matched "depop" case-insensitively, because the data says `depop` and the cards say `Depop`. All 5 first sentences differ, but only by a few words (see below). |
| 5 | The search respects the price ceiling and size | 5 of 5 | MET (5/5) | Every try returned the same 2 listings: `lst_002` ($18, `S/M`) and `lst_017` ($15, `S/M`). Both are ≤ $20 and have `S` as a whole size token. |

**Diagnoses**

No criterion missed, so there is no miss to diagnose. Two things in the output are still wrong, though, and both point at a criterion that measured less than I meant it to.

**1. The fit cards all open with the same template.** *Place:* the model's output, driven by the prompt in `tools.py::create_fit_card`. *Mechanism:* the prompt fixes what the caption contains: a buyer showing off a find, mentioning the item, price and platform exactly once each, price written as a dollar amount. The model fills that in with one sentence shape: "Scored [item] on [platform] for just $[price] and I'm obsessed." Four of the five Levi's cards open like that. They pass my criterion only because a word or two differs ("I am obsessed" vs "I am never taking them off"). In the empty-wardrobe diagnostic run, tries 1 and 5 had exactly the same first sentence: "Scored this cropped Wrangler jacket on Poshmark for $42 and honestly haven't taken it off since it arrived." That would have been a FAIL if the scenario had been scored against criterion 4. Temperature 0.9 changes the wording but not the structure, because the structure is set by the prompt. The tool works; my "no identical first sentence" check is too loose to catch the repetition I wrote criterion 4 to measure.

**2. "graphic tee" returns a top that isn't a graphic tee.** *Place:* the tool, `tools.py::search_listings`. *Mechanism:* the scoring counts a keyword found in a listing's description, not just its title or style tags. `lst_017` "Mesh Long-Sleeve Top — Black" says "Great for layering under a graphic tee" in its description, so it scores for both "graphic" and "tee". That puts it in the results for criterion 5's query. It passes criterion 5 because that criterion checks only price and size, which were both correct. Whether a result is the kind of item the user asked for isn't measured by any of my five criteria.

**Pattern:** both problems are ones my criteria don't measure. Every hard rule (branch, state, filters, price, platform) held 5 of 5, because each is plain code or an explicit prompt instruction. The quality problems slipped through the gaps between them.

**Were my targets too low?** Partly, yes. Criteria 2, 3 and 5 test code with no model in it, so 5 of 5 was always the expected result. Those targets are right, but they couldn't tell me much beyond "the code is correct". Criterion 1 at 4 of 5 left room for a model failure that didn't happen. The one I'd tighten is **criterion 4**. Its "no two cards share a first sentence" rule measured the wrong thing: an opening that changes by one word still counts as different. I re-scored the same before run comparing the first five words of each card instead. Every scenario that produced fit cards had a repeated opening. Criterion 4's own Levi's scenario had only 3 different openings out of 5 ("scored these vintage levi's 501" three times), and 17 of the 25 cards start with the word "Scored". Under a check that measures what I meant, criterion 4 would have been MISSED.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Y2K Baby Tee — Butterfly Print … +7 more
      →    branch: found, selected lst_006
[3] suggest_outfit
      in:  new_item=lst_006, wardrobe_items=10
      out: **Outfit 1 (Grunge Streetwear)** * New Item: Graphic Tee — 2003 Tour Bootleg Style * Owned Bottoms: Baggy stra…
[4] create_fit_card
      in:  new_item=lst_006
      out: Scored this 2003 tour bootleg tee on depop for just $24 and I'm honestly obsessed with the fade on it. Paired …
```

**Empty search**

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit
```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

I registered `search_listings` in `mcp_server.py` with FastMCP, with the same three typed inputs as my Tool Inventory: `description: str`, `size: str | None`, `max_price: float | None`. They already matched, so nothing needed fixing. `python mcp_client.py` lists the tool with `description: string`, `size: string (optional)` and `max_price: number (optional)`. In `agent.py::run_agent` the direct `search_listings(...)` call became `call_tool("search_listings", {...})`; that's the only line of the loop that changed. Nothing behaved differently afterwards. I called both versions with the same arguments and compared them in Python: "vintage graphic tee" under $30 gave the same 10 listings in the same order, and an impossible query gave `[]` both ways, not `None`. The tool already returned plain JSON-friendly values (lists, dicts, strings, floats, `None`), so nothing changed going over MCP. Step 2 of the trace is labelled `search_listings (via MCP)` so you can see the call went over MCP.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One prompt, in `tools.py::create_fit_card`. Each call to the model is independent, so it can't see the captions it wrote before, and telling it to "be varied" can't stop five separate calls from landing on the same opener. Now every call picks one opening angle at random from `_FIT_CARD_OPENINGS` (how the outfit feels, one detail of the item, the occasion, a short reaction, or the vibe/era). The prompt says "Open the first sentence with {that angle}" and adds: *Do not start the caption with "Scored", "Found", "Finally", "Just" or any other word about buying it.* Every other rule is unchanged: buyer voice, 2–4 sentences, item, `$price` and platform once each, no brand unless listed. Nothing else in the agent changed.

**Which failure it was meant to fix:** Diagnosis 1, fit cards that all open with the same template ("Scored [item] on [platform] for just $[price]…"). I didn't touch diagnosis 2 (search relevance), so any change in the results comes from this one prompt.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item the later tools received | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is an acceptable caption | 4 of 5, and no repeated first sentence | PASS | PASS | PASS | PASS | PASS | MET (5/5, 5 distinct first sentences) |
| 5. The search respects the price ceiling and size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Produced by `python run_eval.py --label after` (`run_eval.py::main`, caching off, temperature 0.9), same scenarios as the before run. Full output: `results/run_2026-10-12_2202_after.md`. I scored both runs with the same checks.

**Did it help, and how do I know:**

Yes for the problem it targeted, and it didn't break anything else. All five criteria are still MET 5/5. Every card is still 3 sentences with the right `$price` and platform, criterion 3 still shows the same id in every step, and search returned the same two listings for criterion 5 in all 5 tries.

My five criteria were already MET before the change, so the table alone can't show a difference. The difference shows up in the measure my diagnosis used: the first five words of each card, compared across the 5 tries of each scenario.

| Scenario (5 tries each) | Different 5-word openings, before | After |
|---|---|---|
| Criterion 1: "vintage graphic tee under $30" | 4 of 5 | 5 of 5 |
| Criterion 3: same query, state scenario | 3 of 5 | 5 of 5 |
| Criterion 4: "vintage levi's 501 jeans" | 3 of 5 | 5 of 5 |
| Criterion 5: "graphic tee size S under $20" | 4 of 5 | 4 of 5 |
| Empty wardrobe (diagnostic) | 4 of 5 | 5 of 5 |
| **Cards starting with "Scored"** | **17 of 25** (18 counting "Scoreeeed") | **0 of 25** |
| **Exact repeated first sentence** | **1 pair** (empty wardrobe) | **none** |

Criterion 4's own scenario, first sentence of each try. Before, four of the five opened "Scored these vintage…":

```
Before                                                                  After
Honestly can't believe I scored these vintage Levi's 501 jeans ...      Obsessed is an understatement.
scored these vintage 501s on depop for just $38 and I am never ...      Total effortless 90s street style.
Scored these vintage Levi's 501 jeans on Depop for just $38 and ...     Running errands around the city in my new Vintage Levi's 501 Jeans from depop.
Scored these vintage Levi's 501 jeans for just $38 on Depop and ...     Omg, obsession is an understatement.
Scored these vintage Levi's 501 jeans on Depop for just $38 and ...     So broken-in and comfortable right out of the box.
```

**What it didn't fix, honestly:** the template moved instead of disappearing. The "occasion" angle almost always becomes a coffee run: 5 of the 25 cards mention one. "Coffee run uniform sorted with this…" opened a graphic-tee card *and* a butterfly-tee card, and tries 3 and 4 of criterion 5 both open "Coffee run this morning called for…". That's why criterion 5's scenario is still 4 of 5. "Scored" moved out of the opening but didn't go away: 14 of the 25 cards say "snag" or "snagged" later on, and three Levi's cards say they "fit like an absolute dream". So the openings vary now, but the model still reaches for the same handful of phrases once it has a fixed slot to fill.

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

No criterion is MISSED, before or after. That doesn't mean nothing is broken. These are the problems the runs showed that my criteria didn't catch:

**1. Fit cards still repeat themselves, just in new places.** After the prompt change, no card opens with "Scored", but 5 of 25 mention a "coffee run", criterion 5's tries 3 and 4 both open "Coffee run this morning called for…", and 14 of 25 say "snag"/"snagged". *What I'd do:* show the model a few of the captions already written for the same item and tell it not to reuse their phrases. Or drop the "occasion" angle, which is the one that keeps turning into a coffee run. *Why I stopped:* the improvement was meant to be one change measured properly. A second prompt change would have made the after run impossible to attribute to either one.

**2. Criterion 4 measures the wrong thing.** "No two cards share a first sentence" passed before *and* after, even when four openings differed by one word. The five-word comparison in The Improvement is what showed the actual difference. *What I'd do:* add a revision under criterion 4 in `criteria.md` (keeping the original) that compares the first five words, and re-score both runs with it. *Why I stopped:* I'd rather show the gap honestly here than change the criterion after seeing results.

**3. Search returns items that aren't what was asked for.** "graphic tee size S under $20" also returns "Mesh Long-Sleeve Top — Black", because `tools.py::search_listings` scores keywords found in the description ("Great for layering under a graphic tee"). *What I'd do:* count a description match only when no title or style-tag match exists, or require every keyword to match somewhere. Then add a criterion for it, such as "every result's title or style tags contain the requested item type". *Why I stopped:* it's diagnosis 2, and I fixed diagnosis 1 first because it was the bigger problem in my own data. None of my five criteria measures relevance, so I couldn't have shown a fix working anyway.

**4. The random opening angle can repeat.** With 5 angles and 5 tries, two tries usually get the same angle, which is probably why criterion 5's scenario still had a repeated opening (4 of 5 different). I can't confirm it, because the run doesn't record which angle each try got. *What I'd do:* cycle through the angles instead of picking at random. *Why I stopped:* same reason as 1, one change per run.


<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
