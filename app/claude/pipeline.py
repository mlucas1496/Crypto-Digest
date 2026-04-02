import json
import re
from dataclasses import dataclass
from app.scrapers.base import RawArticle
from app.claude.client import call_claude, call_claude_json
from app.claude.prompts import FILTER_AND_SUMMARIZE_PROMPT, EXEC_SUMMARY_PROMPT

# Send at most 2 batches of 20 = 40 articles to Claude total
BATCH_SIZE = 20
MAX_BATCHES = 2

# ── Keyword pre-scorer ────────────────────────────────────────────────────────
# Articles scoring above 0 are prioritized before sending to Claude.
# This catches things like "NYSE + Securitize" that RSS feeds miss.

HIGH_VALUE_KEYWORDS = {
    # Deal signals (+3 each)
    "acqui": 3, "merger": 3, "acquis": 3, "deal": 3, "partner": 3,
    "invest": 3, "funding": 3, "raise": 3, "series": 3, "round": 2,
    "ipo": 3, "spac": 3, "tokenize": 3, "tokenized": 3, "tokenization": 3,
    # Regulatory (+3)
    "sec ": 3, "cftc": 3, "bill": 3, "legislation": 3, "regulation": 3,
    "lawsuit": 3, "enforcement": 3, "approve": 2, "ban": 2,
    # Key companies (+2)
    "coinbase": 2, "kraken": 2, "gemini": 2, "circle": 2, "binance": 2,
    "ripple": 2, "chainlink": 2, "grayscale": 2, "galaxy": 2, "bitgo": 2,
    "securitize": 3, "anchorage": 2, "fireblocks": 2,
    # Institutions (+2)
    "nyse": 3, "blackrock": 3, "fidelity": 2, "franklin": 2, "cme": 2,
    "nasdaq": 2, "jpmorgan": 2, "goldman": 2, "bank": 1,
    # Assets (+1)
    "bitcoin": 1, "ethereum": 1, "solana": 1, "xrp": 1, "usdc": 1,
    "stablecoin": 2, "defi": 1, "nft": 1, "etf": 2,
}


SOURCE_BONUS = {
    "milkroad": 5,
    "coindesk": 5,
    "theblock": 5,
    "googlenews": 4,
    "globenewswire": 4,
    "wsj": 4,
    "cointelegraph": 2,
    "decrypt": 2,
    "bitcoinmagazine": 1,
}


def _keyword_score(article: RawArticle) -> int:
    text = (article.title + " " + (article.snippet or "")).lower()
    score = SOURCE_BONUS.get(article.source, 0)
    for kw, pts in HIGH_VALUE_KEYWORDS.items():
        if kw in text:
            score += pts
    return score


_STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "for",
              "on", "by", "as", "at", "with", "from", "its", "it", "be", "are",
              "was", "were", "has", "have", "had", "that", "this", "will", "not"}


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def _title_words(title: str) -> frozenset[str]:
    """Return meaningful words from a title, ignoring stopwords."""
    return frozenset(
        w for w in _normalize_title(title).split()
        if w and w not in _STOPWORDS and len(w) > 2
    )


_ENTITY_KEYWORDS = frozenset(HIGH_VALUE_KEYWORDS.keys())


def _entity_words(title: str) -> frozenset[str]:
    """Return only the HIGH_VALUE_KEYWORDS found in the title."""
    text = _normalize_title(title)
    return frozenset(kw for kw in _ENTITY_KEYWORDS if kw in text)


def _is_duplicate(candidate_words: frozenset[str], seen_word_sets: list[frozenset[str]],
                  candidate_entities: frozenset[str], seen_entity_sets: list[frozenset[str]]) -> bool:
    """Return True if candidate is a near-duplicate of any seen article.

    Two articles are duplicates if:
    - They share ≥40% of their meaningful title words, OR
    - They share ≥2 named entities (company names, deal keywords, etc.)
    """
    if not candidate_words:
        return False
    for seen_words, seen_entities in zip(seen_word_sets, seen_entity_sets):
        if not seen_words:
            continue
        # Entity check: same story if they both mention 2+ specific entities
        if len(candidate_entities & seen_entities) >= 2:
            return True
        # Word overlap check
        overlap = len(candidate_words & seen_words) / min(len(candidate_words), len(seen_words))
        if overlap > 0.4:
            return True
    return False


def _select_best(articles: list[RawArticle]) -> list[RawArticle]:
    """
    Score articles by keyword relevance, deduplicate by title similarity,
    return best BATCH_SIZE * MAX_BATCHES articles.
    """
    scored = sorted(articles, key=_keyword_score, reverse=True)
    seen_word_sets: list[frozenset[str]] = []
    seen_entity_sets: list[frozenset[str]] = []
    result: list[RawArticle] = []
    for a in scored:
        words = _title_words(a.title)
        entities = _entity_words(a.title)
        if words and not _is_duplicate(words, seen_word_sets, entities, seen_entity_sets):
            seen_word_sets.append(words)
            seen_entity_sets.append(entities)
            result.append(a)
        if len(result) >= BATCH_SIZE * MAX_BATCHES:
            break
    return result


@dataclass
class ProcessedArticle:
    url: str
    title: str
    source: str
    snippet: str
    category: str
    importance: int
    summary: str = ""


def _call_batch(batch: list[RawArticle]) -> list[ProcessedArticle]:
    from datetime import date
    today = date.today().isoformat()

    def _article_text(a: RawArticle) -> str:
        pub = a.published_at.strftime("%Y-%m-%d") if a.published_at else "unknown"
        return f"URL: {a.url}\nPublished: {pub}\nTitle: {a.title}\nSnippet: {(a.snippet or '')[:200]}"

    batch_text = "\n\n".join(_article_text(a) for a in batch)
    batch_text = f"Today's date: {today}\n\n{batch_text}"
    prompt = FILTER_AND_SUMMARIZE_PROMPT.format(articles=batch_text)
    url_map = {a.url: a for a in batch}

    try:
        results = call_claude_json(prompt)
    except Exception as e:
        print(f"[pipeline] batch error: {e}")
        return []

    processed = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        raw = url_map.get(url)
        if not raw:
            continue
        category = item.get("category", "headlines")
        if category not in ("ma", "regulatory", "trends", "headlines"):
            category = "headlines"
        importance = max(1, min(10, int(item.get("importance", 5))))
        summary = str(item.get("summary", raw.snippet[:200] if raw.snippet else raw.title))
        processed.append(ProcessedArticle(
            url=url, title=raw.title, source=raw.source,
            snippet=raw.snippet, category=category,
            importance=importance, summary=summary,
        ))
    return processed


def filter_summarize(articles: list[RawArticle]) -> list[ProcessedArticle]:
    best = _select_best(articles)
    print(f"[pipeline] keyword pre-filter: {len(articles)} → {len(best)} articles to review")

    all_processed: list[ProcessedArticle] = []
    total_batches = (len(best) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(best), BATCH_SIZE):
        batch = best[i: i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"[pipeline] Claude batch {batch_num}/{total_batches} ({len(batch)} articles)...")
        results = _call_batch(batch)
        all_processed.extend(results)
        print(f"[pipeline] batch {batch_num} → {len(results)} relevant")

    print(f"[pipeline] total relevant: {len(all_processed)}")
    return all_processed


def generate_executive_summary(top_articles: list[ProcessedArticle]) -> str:
    if not top_articles:
        return "No significant crypto news today."
    stories = "\n".join(
        f"{i+1}. [{a.category.upper()}] {a.title} — {a.summary}"
        for i, a in enumerate(top_articles)
    )
    prompt = EXEC_SUMMARY_PROMPT.format(stories=stories)
    try:
        return call_claude(prompt).strip()
    except Exception as e:
        print(f"[pipeline] exec summary error: {e}")
        return "Today's digest covers key developments across crypto M&A, regulatory, and market news."


MIN_DIGEST_ITEMS = 3


def run_pipeline(
    articles: list[RawArticle], max_per_category: int = 5
) -> tuple[list[ProcessedArticle], str]:
    relevant = filter_summarize(articles)

    # Deduplicate Claude results by title similarity before selecting top per category
    deduped_relevant: list[ProcessedArticle] = []
    seen_relevant_words: list[frozenset[str]] = []
    seen_relevant_entities: list[frozenset[str]] = []
    for a in sorted(relevant, key=lambda x: x.importance, reverse=True):
        words = _title_words(a.title)
        entities = _entity_words(a.title)
        if not _is_duplicate(words, seen_relevant_words, entities, seen_relevant_entities):
            seen_relevant_words.append(words)
            seen_relevant_entities.append(entities)
            deduped_relevant.append(a)

    categories = ["ma", "regulatory", "trends", "headlines"]
    selected: list[ProcessedArticle] = []
    for cat in categories:
        cat_articles = sorted(
            [a for a in deduped_relevant if a.category == cat],
            key=lambda x: x.importance, reverse=True,
        )
        selected.extend(cat_articles[:max_per_category])

    # Guarantee a minimum number of items — fall back to top keyword-scored articles
    if len(selected) < MIN_DIGEST_ITEMS and articles:
        existing_urls = {a.url for a in selected}
        best = _select_best(articles)  # already deduped
        for raw in best:
            if raw.url not in existing_urls and len(selected) >= MIN_DIGEST_ITEMS:
                break
            if raw.url not in existing_urls:
                selected.append(ProcessedArticle(
                    url=raw.url,
                    title=raw.title,
                    source=raw.source,
                    snippet=raw.snippet,
                    category="headlines",
                    importance=3,
                    summary=raw.snippet[:300] if raw.snippet else raw.title,
                ))
                existing_urls.add(raw.url)
        print(f"[pipeline] filled to {len(selected)} items using keyword fallback")

    top_10 = sorted(selected, key=lambda x: x.importance, reverse=True)[:10]
    exec_summary = generate_executive_summary(top_10)
    return selected, exec_summary
