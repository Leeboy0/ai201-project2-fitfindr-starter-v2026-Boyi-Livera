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
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

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
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



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

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



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
