"""
Theme extraction for luggage reviews.

1. Global themes — KeyBERT extracts top N keyphrases from the review corpus,
   grouped into positive and negative by sentence-level VADER.

2. Aspect-level sentiment — for each aspect (wheels, handle, zipper, material,
   durability, size, lock, capacity) we extract sentences mentioning that aspect
   and score the average sentiment.

3. Anomaly detection — flag brands where a specific aspect has high negative
   sentiment despite an overall high rating (e.g. "durability complaints despite 4★").
"""

import re
import logging
from collections import Counter, defaultdict
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

log = logging.getLogger(__name__)
vader = SentimentIntensityAnalyzer()

ASPECTS = {
    "wheels": ["wheel", "wheels", "roller", "rolling", "rolls", "caster"],
    "handle": ["handle", "handles", "grip", "telescopic", "trolley handle"],
    "zipper": ["zipper", "zip", "zips", "zippers", "closure"],
    "material": ["material", "fabric", "polycarbonate", "abs", "hardshell", "softside", "cloth"],
    "durability": ["durable", "durability", "lasted", "broke", "cracked", "strong", "flimsy", "sturdy", "quality"],
    "size": ["size", "capacity", "spacious", "fits", "fitting", "cabin", "check-in", "large", "small"],
    "lock": ["lock", "tsa", "combination", "locked", "security"],
    "weight": ["weight", "heavy", "lightweight", "light", "kg", "kilos"],
}

# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

_sentence_end = re.compile(r'(?<=[.!?])\s+')


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _sentence_end.split(text) if len(s.strip()) > 10]


# ---------------------------------------------------------------------------
# Aspect-level sentiment
# ---------------------------------------------------------------------------

def aspect_sentiment(reviews: list[dict]) -> dict:
    """
    For each aspect, return avg vader compound score from all sentences
    that mention any keyword for that aspect.
    Returns:
        {
          "wheels": {"score": 0.12, "mentions": 43, "sample_pos": [...], "sample_neg": [...]},
          ...
        }
    """
    aspect_sentences: dict[str, list[tuple[float, str]]] = defaultdict(list)

    for r in reviews:
        text = (r.get("title") or "") + " " + (r.get("body") or "")
        sentences = _split_sentences(text.lower())
        for sentence in sentences:
            for aspect, keywords in ASPECTS.items():
                if any(kw in sentence for kw in keywords):
                    score = vader.polarity_scores(sentence)["compound"]
                    aspect_sentences[aspect].append((score, sentence))

    result = {}
    for aspect in ASPECTS:
        items = aspect_sentences.get(aspect, [])
        if not items:
            result[aspect] = {"score": None, "mentions": 0, "sample_pos": [], "sample_neg": []}
            continue
        scores = [s for s, _ in items]
        avg = sum(scores) / len(scores)
        positive_sents = [t for s, t in items if s >= 0.05]
        negative_sents = [t for s, t in items if s <= -0.05]
        result[aspect] = {
            "score": round(avg, 3),
            "mentions": len(items),
            "sample_pos": positive_sents[:3],
            "sample_neg": negative_sents[:3],
        }
    return result


# ---------------------------------------------------------------------------
# Global theme extraction (KeyBERT-based)
# ---------------------------------------------------------------------------

_kw_model = None


def _get_kw_model():
    global _kw_model
    if _kw_model is None:
        try:
            from keybert import KeyBERT
            _kw_model = KeyBERT()
            log.info("KeyBERT model loaded.")
        except Exception as e:
            log.warning("KeyBERT unavailable (%s) — using frequency fallback", e)
    return _kw_model


def _frequency_keyphrases(texts: list[str], top_n: int = 20) -> list[str]:
    """Simple word-frequency fallback when KeyBERT is unavailable."""
    stopwords = {"the", "a", "an", "is", "was", "it", "this", "i", "my", "very",
                 "and", "or", "but", "in", "on", "for", "to", "of", "with", "are",
                 "have", "has", "not", "no", "at", "be", "bag", "luggage", "product"}
    words = re.findall(r"\b[a-z]{4,}\b", " ".join(texts).lower())
    freq = Counter(w for w in words if w not in stopwords)
    return [w for w, _ in freq.most_common(top_n)]


def extract_themes(reviews: list[dict], top_n: int = 8) -> dict:
    """
    Extract top positive and negative themes from review text.
    Returns:
        {
            "positive": ["good wheels", "spacious compartment", ...],
            "negative": ["zipper broke", "bad quality", ...],
        }
    """
    positive_texts = []
    negative_texts = []

    for r in reviews:
        body = (r.get("body") or "").strip()
        if not body:
            continue
        sentiment = r.get("sentiment") or ("positive" if (r.get("stars") or 3) >= 4 else "negative")
        if sentiment == "positive":
            positive_texts.append(body)
        elif sentiment == "negative":
            negative_texts.append(body)

    model = _get_kw_model()

    def _extract(texts: list[str]) -> list[str]:
        if not texts:
            return []
        combined = " ".join(texts[:300])[:8000]  # cap to avoid OOM
        if model:
            try:
                kws = model.extract_keywords(
                    combined, keyphrase_ngram_range=(1, 2),
                    stop_words="english", top_n=top_n * 2, diversity=0.6
                )
                return [kw for kw, _ in kws[:top_n]]
            except Exception:
                pass
        return _frequency_keyphrases(texts, top_n)

    return {
        "positive": _extract(positive_texts),
        "negative": _extract(negative_texts),
    }


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

def detect_anomalies(brand_key: str, avg_rating: Optional[float], aspect_data: dict) -> list[str]:
    """
    Surface non-obvious contradictions, e.g.:
    - High overall rating but negative aspect sentiment
    - One aspect strongly negative despite positive overall
    """
    anomalies = []
    if avg_rating is None:
        return anomalies

    for aspect, data in aspect_data.items():
        score = data.get("score")
        mentions = data.get("mentions", 0)
        if score is None or mentions < 5:
            continue
        if avg_rating >= 4.0 and score <= -0.15:
            anomalies.append(
                f"{brand_key.replace('_', ' ').title()}: strong {aspect} complaints "
                f"(avg VADER {score:.2f}) despite high overall rating ({avg_rating:.1f}★)"
            )
        if avg_rating < 3.5 and score >= 0.25:
            anomalies.append(
                f"{brand_key.replace('_', ' ').title()}: customers praise {aspect} "
                f"(avg VADER {score:.2f}) even with low overall rating ({avg_rating:.1f}★)"
            )
    return anomalies
