"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── helpers ───────────────────────────────────────────────────────────────────

# Words that carry no meaning for matching ("looking for a tee under $30").
_STOPWORDS = {
    "a", "an", "and", "the", "for", "of", "in", "on", "with", "to", "my", "me",
    "i", "im", "looking", "want", "need", "find", "some", "something", "any",
    "under", "below", "less", "than", "size", "sized", "around", "about",
}


def _words(text: str) -> list[str]:
    """Lowercase alphanumeric words, with a trailing plural 's' dropped."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]


def _size_tokens(size: str) -> set[str]:
    """'S/M' -> {'S', 'M'};  'US 8.5' -> {'US', '8.5'};  'XL (oversized)' -> {'XL', 'OVERSIZED'}."""
    return {t for t in re.split(r"[\s/()]+", size.upper()) if t}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    A listing matches when every token of the wanted size is a whole token of
    the listing's size. So "M" matches "M", "S/M", "M/L" but not "US 7";
    "L" matches "L/XL" but not "XL"; "W30" matches "W30 L30".
    """
    wanted_tokens = _size_tokens(wanted)
    return bool(wanted_tokens) and wanted_tokens <= _size_tokens(listing_size)


def _score(listing: dict, keywords: set[str]) -> int:
    """Keyword overlap: hits in title and style tags count double."""
    strong = set(_words(listing["title"])) | set(_words(" ".join(listing["style_tags"])))
    weak = set(_words(" ".join([
        listing["description"],
        listing["category"],
        " ".join(listing["colors"]),
        listing.get("brand") or "",
    ])))
    return sum(2 if k in strong else 1 if k in weak else 0 for k in keywords)


def _describe_item(item: dict) -> str:
    """One readable block about a listing, skipping brand when there isn't one."""
    lines = [
        f"Title: {item.get('title')}",
        f"Category: {item.get('category')}",
        f"Colors: {', '.join(item.get('colors') or [])}",
        f"Style: {', '.join(item.get('style_tags') or [])}",
        f"Size: {item.get('size')}",
        f"Condition: {item.get('condition')}",
        f"Price: ${item.get('price'):.2f}" if item.get("price") is not None else "Price: unknown",
        f"Platform: {item.get('platform')}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = {w for w in _words(description or "") if w not in _STOPWORDS}
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(listing, keywords)
        if score > 0:
            title_hits = len(keywords & set(_words(listing["title"])))
            scored.append((score, title_hits, listing))

    # Highest score first; ties go to the listing whose title names more of the
    # keywords. sort() is stable, so remaining ties keep dataset order.
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [listing for _, _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    items = (wardrobe or {}).get("items") or []
    item_block = _describe_item(new_item)

    if not items:
        prompt = (
            "A shopper is considering this thrifted item but hasn't told us "
            "what's in their wardrobe:\n\n"
            f"{item_block}\n\n"
            "Suggest one or two outfits built around it, using common staple "
            "pieces (name the type, color and fit of each piece). Keep it under "
            "120 words."
        )
    else:
        owned = "\n".join(
            f"- {w.get('name')} ({w.get('category')}; colors: "
            f"{', '.join(w.get('colors') or [])})"
            + (f" — {w['notes']}" if w.get("notes") else "")
            for w in items
        )
        prompt = (
            "A shopper is considering this thrifted item:\n\n"
            f"{item_block}\n\n"
            f"Here is what they already own:\n{owned}\n\n"
            "Suggest one or two complete outfits that pair the new item with "
            "pieces from their wardrobe. Name the owned pieces exactly as "
            "listed. Keep it under 120 words."
        )

    system = "You are a practical personal stylist. Be specific and concise; no preamble."
    response = generate(prompt, system=system).strip()
    return response or "Couldn't generate an outfit suggestion for this item — try again."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "Can't write a fit card: no outfit suggestion was provided. "
            "Run suggest_outfit first and pass its result in."
        )

    prompt = (
        "Write a caption for a social post by someone who just bought this "
        "thrift find and is showing it off. They are the buyer, not the seller.\n\n"
        f"{_describe_item(new_item)}\n\n"
        f"How it's being styled:\n{outfit}\n\n"
        "Rules: 2 to 4 sentences. Sound like a real person posting, not a "
        "product listing. Mention the item, its price and its platform exactly "
        "once each, writing the price as a dollar amount (e.g. $38). Be specific "
        "about the vibe. Don't mention a brand unless one is listed above."
    )
    system = "You write short, casual, authentic outfit captions."
    response = generate(prompt, system=system).strip()
    return response or "Couldn't generate a fit card for this item — try again."
