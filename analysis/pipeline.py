"""
Analysis pipeline.

Reads data/raw/ → processes → writes data/processed/

Outputs:
  data/processed/brands.json     — brand-level aggregates
  data/processed/products.json   — product-level records with review synthesis
  data/processed/insights.json   — agent insights (non-obvious conclusions)

Usage:
  python analysis/pipeline.py
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper.config import DATA_RAW, DATA_PROCESSED, BRANDS
from analysis.sentiment import score_review, aggregate_brand_sentiment
from analysis.themes import extract_themes, aspect_sentiment, detect_anomalies

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_brand_data(brand_key: str) -> tuple[list[dict], list[dict]]:
    """Load products and all reviews for a brand from raw JSON files."""
    brand_dir = DATA_RAW / brand_key
    products_file = brand_dir / "products.json"
    reviews_dir = brand_dir / "reviews"

    if not products_file.exists():
        log.warning("No products file for %s — skipping", brand_key)
        return [], []

    products = json.loads(products_file.read_text())
    all_reviews = []

    for p in products:
        review_file = reviews_dir / f"{p['asin']}.json"
        if review_file.exists():
            revs = json.loads(review_file.read_text())
            for r in revs:
                r["brand"] = brand_key
                r["product_title"] = p.get("title", "")
            all_reviews.extend(revs)

    return products, all_reviews


# ---------------------------------------------------------------------------
# Product-level processing
# ---------------------------------------------------------------------------

def process_product(product: dict, reviews: list[dict]) -> dict:
    """Score reviews, extract themes, compute product-level sentiment."""
    scored = [score_review(r) for r in reviews]
    sentiment_agg = aggregate_brand_sentiment(scored)
    themes = extract_themes(scored)
    aspects = aspect_sentiment(scored)

    # Star distribution
    star_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in scored:
        s = int(r.get("stars") or 0)
        if s in star_dist:
            star_dist[s] += 1

    # Review synthesis snippet — top 3 most helpful positive + negative
    helpful_pos = sorted(
        [r for r in scored if r.get("sentiment") == "positive"],
        key=lambda x: x.get("helpful_votes", 0), reverse=True
    )[:3]
    helpful_neg = sorted(
        [r for r in scored if r.get("sentiment") == "negative"],
        key=lambda x: x.get("helpful_votes", 0), reverse=True
    )[:3]

    return {
        **product,
        "review_count_scraped": len(scored),
        "sentiment": sentiment_agg,
        "themes": themes,
        "aspects": aspects,
        "star_distribution": star_dist,
        "top_positive_reviews": [{"title": r.get("title"), "body": r.get("body", "")[:300]} for r in helpful_pos],
        "top_negative_reviews": [{"title": r.get("title"), "body": r.get("body", "")[:300]} for r in helpful_neg],
    }


# ---------------------------------------------------------------------------
# Brand-level aggregation
# ---------------------------------------------------------------------------

def process_brand(brand_key: str, products: list[dict], all_reviews: list[dict]) -> dict:
    """Compute brand-level pricing, rating, sentiment aggregates."""
    if not products:
        return {}

    # Pricing stats
    prices = [p["price"] for p in products if p.get("price")]
    mrps = [p["mrp"] for p in products if p.get("mrp")]
    discounts = [p["discount_pct"] for p in products if p.get("discount_pct")]
    ratings = [p["rating"] for p in products if p.get("rating")]
    review_counts = [p["review_count"] for p in products if p.get("review_count")]

    def _safe_avg(lst): return round(float(np.mean(lst)), 2) if lst else None
    def _safe_median(lst): return round(float(np.median(lst)), 2) if lst else None

    # Price bands
    price_band = "unknown"
    avg_price = _safe_avg(prices)
    if avg_price:
        if avg_price >= 5000:
            price_band = "premium"
        elif avg_price >= 2500:
            price_band = "mid-range"
        else:
            price_band = "budget"

    # Sentiment across all reviews
    scored_all = [score_review(r) for r in tqdm(all_reviews, desc=f"Scoring {brand_key}", leave=False)]
    sentiment_agg = aggregate_brand_sentiment(scored_all)
    themes = extract_themes(scored_all)
    aspects = aspect_sentiment(scored_all)
    anomalies = detect_anomalies(brand_key, _safe_avg(ratings), aspects)

    return {
        "brand_key": brand_key,
        "brand_name": brand_key.replace("_", " ").title(),
        "pricing": {
            "avg_price": avg_price,
            "median_price": _safe_median(prices),
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "avg_mrp": _safe_avg(mrps),
            "avg_discount_pct": _safe_avg(discounts),
            "price_band": price_band,
        },
        "ratings": {
            "avg_rating": _safe_avg(ratings),
            "total_reviews": sum(review_counts) if review_counts else 0,
            "products_count": len(products),
        },
        "sentiment": sentiment_agg,
        "themes": themes,
        "aspects": aspects,
        "anomalies": anomalies,
    }


# ---------------------------------------------------------------------------
# Agent Insights generator
# ---------------------------------------------------------------------------

def generate_insights(brands: list[dict]) -> list[dict]:
    """
    Generate 5–8 non-obvious insights from cross-brand analysis.
    Uses heuristics + anomaly data.
    """
    insights = []
    if not brands:
        return insights

    df = pd.DataFrame([{
        "brand": b["brand_key"],
        "name": b["brand_name"],
        "avg_price": b["pricing"].get("avg_price") or 0,
        "avg_discount": b["pricing"].get("avg_discount_pct") or 0,
        "avg_rating": b["ratings"].get("avg_rating") or 0,
        "sentiment_score": b["sentiment"].get("score") or 0,
        "pos_pct": b["sentiment"].get("positive_pct") or 0,
        "neg_pct": b["sentiment"].get("negative_pct") or 0,
        "total_reviews": b["ratings"].get("total_reviews") or 0,
        "price_band": b["pricing"].get("price_band") or "unknown",
    } for b in brands])

    # 1. Value-for-money: high sentiment relative to price
    df["vfm"] = df["sentiment_score"] / (df["avg_price"].clip(lower=1) ** 0.3)
    best_vfm = df.loc[df["vfm"].idxmax()]
    insights.append({
        "type": "value_for_money",
        "headline": f"{best_vfm['name']} delivers the best value-for-money",
        "detail": (
            f"Sentiment score of {best_vfm['sentiment_score']:.1f} at an avg price "
            f"of ₹{best_vfm['avg_price']:,.0f} — the best sentiment-per-rupee ratio across all brands."
        ),
        "brand": best_vfm["brand"],
    })

    # 2. Discount dependency
    high_discount = df.loc[df["avg_discount"].idxmax()]
    low_discount = df.loc[df["avg_discount"].idxmin()]
    if high_discount["avg_rating"] < low_discount["avg_rating"]:
        insights.append({
            "type": "discount_dependency",
            "headline": f"{high_discount['name']} relies heavily on discounting",
            "detail": (
                f"Avg discount of {high_discount['avg_discount']:.0f}% but only "
                f"{high_discount['avg_rating']:.1f}★ rating — heavy discounting may signal "
                f"product perception issues rather than demand generation."
            ),
            "brand": high_discount["brand"],
        })

    # 3. Rating–sentiment gap (hidden dissatisfaction)
    df["rs_gap"] = df["avg_rating"] / 5 * 100 - df["sentiment_score"]
    worst_gap = df.loc[df["rs_gap"].idxmax()]
    if worst_gap["rs_gap"] > 5:
        insights.append({
            "type": "hidden_dissatisfaction",
            "headline": f"{worst_gap['name']} has a rating–sentiment gap",
            "detail": (
                f"Star rating implies {worst_gap['avg_rating']:.1f}★ satisfaction but review "
                f"sentiment score is only {worst_gap['sentiment_score']:.1f}/100. "
                f"Customers may rate generously but write critically."
            ),
            "brand": worst_gap["brand"],
        })

    # 4. Anomaly-based insights
    all_anomalies = [a for b in brands for a in b.get("anomalies", [])]
    for anomaly in all_anomalies[:3]:
        insights.append({
            "type": "anomaly",
            "headline": "Aspect anomaly detected",
            "detail": anomaly,
            "brand": None,
        })

    # 5. Premium vs budget sentiment convergence
    premium = df[df["price_band"] == "premium"]
    budget = df[df["price_band"] == "budget"]
    if not premium.empty and not budget.empty:
        p_score = premium["sentiment_score"].mean()
        b_score = budget["sentiment_score"].mean()
        if abs(p_score - b_score) < 5:
            insights.append({
                "type": "price_parity",
                "headline": "Budget and premium brands score similarly on sentiment",
                "detail": (
                    f"Premium brands avg sentiment: {p_score:.1f}/100. "
                    f"Budget brands: {b_score:.1f}/100. "
                    f"The gap is only {abs(p_score - b_score):.1f} points — premium pricing may not be justified by customer satisfaction."
                ),
                "brand": None,
            })

    # 6. Review volume leader
    most_reviewed = df.loc[df["total_reviews"].idxmax()]
    insights.append({
        "type": "market_presence",
        "headline": f"{most_reviewed['name']} dominates review volume",
        "detail": (
            f"{most_reviewed['total_reviews']:,} total ratings — "
            f"{(most_reviewed['total_reviews'] / df['total_reviews'].sum() * 100):.0f}% of all reviews "
            f"in the dataset. High market penetration but check if sentiment holds."
        ),
        "brand": most_reviewed["brand"],
    })

    return insights


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    all_brands_processed = []
    all_products_processed = []

    for brand_key in BRANDS:
        log.info("Processing brand: %s", brand_key)
        products, all_reviews = load_brand_data(brand_key)

        if not products:
            log.warning("No data for %s — skipping", brand_key)
            continue

        # Product-level
        asin_to_reviews = {}
        for r in all_reviews:
            asin_to_reviews.setdefault(r["asin"], []).append(r)

        for p in tqdm(products, desc=f"Products: {brand_key}"):
            revs = asin_to_reviews.get(p["asin"], [])
            processed_p = process_product(p, revs)
            all_products_processed.append(processed_p)

        # Brand-level
        brand_data = process_brand(brand_key, products, all_reviews)
        all_brands_processed.append(brand_data)
        log.info("Brand %s: sentiment=%.1f, avg_price=₹%.0f",
                 brand_key, brand_data["sentiment"]["score"],
                 brand_data["pricing"]["avg_price"] or 0)

    # Insights
    insights = generate_insights(all_brands_processed)

    # Write output
    (DATA_PROCESSED / "brands.json").write_text(
        json.dumps(all_brands_processed, indent=2, ensure_ascii=False)
    )
    (DATA_PROCESSED / "products.json").write_text(
        json.dumps(all_products_processed, indent=2, ensure_ascii=False)
    )
    (DATA_PROCESSED / "insights.json").write_text(
        json.dumps(insights, indent=2, ensure_ascii=False)
    )
    log.info("Pipeline complete. Output written to data/processed/")


if __name__ == "__main__":
    run()
