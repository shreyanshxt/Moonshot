"""
Sentiment analysis for luggage reviews.

Two-layer approach:
  1. VADER  — fast, lexicon-based, returns compound score (−1 to +1)
  2. RoBERTa — cardiffnlp/twitter-roberta-base-sentiment, 3-class confidence

Brand score = weighted average of RoBERTa positive confidence across all reviews,
              weighted by (1 + log(1 + helpful_votes)) for verified reviews.
"""

import logging
import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

log = logging.getLogger(__name__)

# Lazy-load heavy transformer model
_roberta = None
_roberta_tokenizer = None
_roberta_failed = False


def _get_roberta():
    global _roberta, _roberta_tokenizer, _roberta_failed
    if _roberta is None and not _roberta_failed:
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            log.info("Loading RoBERTa sentiment model (first run downloads ~500 MB)...")
            _roberta_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _roberta = AutoModelForSequenceClassification.from_pretrained(model_name)
            _roberta.eval()
            log.info("RoBERTa model loaded.")
        except Exception as e:
            log.warning("Could not load RoBERTa (%s) — falling back to VADER only", e)
            _roberta_failed = True
    return _roberta, _roberta_tokenizer


vader = SentimentIntensityAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_amazon_date(date_str: str) -> Optional[datetime]:
    """
    Parse Amazon India date format: 'Reviewed in India on 27 March 2024'
    Returns datetime object or None if parsing fails.
    """
    if not date_str:
        return None
    
    # Extract date part using regex
    match = re.search(r'on (\d+ \w+ \d{4})', date_str)
    if not match:
        return None
    
    try:
        return datetime.strptime(match.group(1), "%d %B %Y")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Single-review scoring
# ---------------------------------------------------------------------------

def vader_score(text: str) -> float:
    """Return VADER compound score in [-1, 1]."""
    return vader.polarity_scores(text)["compound"]


def roberta_score(text: str) -> dict:
    """
    Return {'neg': float, 'neu': float, 'pos': float} from RoBERTa.
    Falls back to VADER-mapped scores if model unavailable.
    """
    model, tokenizer = _get_roberta()
    if model is None or tokenizer is None:
        # Map VADER compound to 3-class
        v = vader_score(text)
        if v >= 0.05:
            return {"neg": 0.05, "neu": 0.15, "pos": 0.8}
        elif v <= -0.05:
            return {"neg": 0.8, "neu": 0.15, "pos": 0.05}
        else:
            return {"neg": 0.1, "neu": 0.8, "pos": 0.1}

    import torch
    # Truncate to 512 tokens
    enc = tokenizer(text[:512], return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        out = model(**enc)
    probs = torch.softmax(out.logits, dim=-1).squeeze().tolist()
    # Model label order: 0=neg, 1=neu, 2=pos (cardiffnlp latest)
    return {"neg": probs[0], "neu": probs[1], "pos": probs[2]}


def score_review(review: dict) -> dict:
    """Attach sentiment scores to a single review dict."""
    text = (review.get("title") or "") + " " + (review.get("body") or "")
    text = text.strip()
    if not text:
        return {**review, "vader_score": 0.0, "sentiment": "neutral", "pos": 0.33, "neu": 0.34, "neg": 0.33}

    v = vader_score(text)
    rb = roberta_score(text)

    # Weighted blend: 30% VADER, 70% RoBERTa
    blended_pos = 0.3 * ((v + 1) / 2) + 0.7 * rb["pos"]

    if blended_pos >= 0.6:
        sentiment = "positive"
    elif blended_pos <= 0.35:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        **review,
        "vader_score": round(v, 4),
        "pos": round(rb["pos"], 4),
        "neu": round(rb["neu"], 4),
        "neg": round(rb["neg"], 4),
        "sentiment": sentiment,
        "blended_pos": round(blended_pos, 4),
    }


# ---------------------------------------------------------------------------
# Brand-level aggregation
# ---------------------------------------------------------------------------

def aggregate_brand_sentiment(scored_reviews: list[dict], decay_rate: float = 0.5) -> dict:
    """
    Compute brand sentiment score (0–100) and distribution from scored reviews.
    Includes time-decay: recent reviews (last 365 days) carry more weight.
    """
    if not scored_reviews:
        return {"score": 50.0, "positive_pct": 0, "neutral_pct": 0, "negative_pct": 0, "total": 0}

    now = datetime.now()
    weights = []
    pos_scores = []
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}

    for r in scored_reviews:
        # 1. Base weight
        w = 1.0
        
        # 2. Verified status weight (30% boost)
        if r.get("verified"):
            w *= 1.3
            
        # 3. Helpfulness weight (logarithmic)
        helpful = r.get("helpful_votes", 0) or 0
        w *= (1 + np.log1p(helpful))
        
        # 4. Time-decay dynamic weight
        review_date = _parse_amazon_date(r.get("date", ""))
        if review_date:
            days_old = (now - review_date).days
            # Exponential decay: weight reduces by half every ~year at default decay_rate
            time_weight = np.exp(-decay_rate * (days_old / 365.25))
            w *= max(0.1, time_weight) # Keep at least 10% weight regardless of age

        weights.append(w)
        pos_scores.append(r.get("blended_pos", 0.5))
        sentiments[r.get("sentiment", "neutral")] += 1

    weights = np.array(weights)
    pos_scores = np.array(pos_scores)
    
    # Avoid division by zero if weights all zero
    sum_weights = np.sum(weights)
    if sum_weights > 0:
        brand_score = float(np.average(pos_scores, weights=weights) * 100)
    else:
        brand_score = float(np.mean(pos_scores) * 100)

    total = len(scored_reviews)
    return {
        "score": round(brand_score, 1),
        "positive_pct": round(sentiments["positive"] / total * 100, 1),
        "neutral_pct": round(sentiments["neutral"] / total * 100, 1),
        "negative_pct": round(sentiments["negative"] / total * 100, 1),
        "total_reviews_scored": total,
    }
