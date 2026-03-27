"""
FastAPI backend for the Luggage Intelligence Dashboard.

Endpoints:
  GET /brands                      — all brand summaries
  GET /brands/{brand_key}          — single brand detail
  GET /products                    — all products (filterable)
  GET /products/{asin}             — single product detail
  GET /insights                    — agent insights
  GET /compare?brands=a,b,c        — side-by-side brand comparison

Run: uvicorn api.main:app --reload --port 8000
"""

import json
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper.config import DATA_PROCESSED, DATA_SAMPLE
from api.models import BrandSummary, ProductDetail, Insight
from analysis.sentiment import score_review

app = FastAPI(title="Luggage Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Data loading (cached at startup)
# ---------------------------------------------------------------------------

def _load_json(name: str) -> list | dict:
    """Try processed data first, fall back to sample data."""
    processed_path = DATA_PROCESSED / f"{name}.json"
    sample_path = DATA_SAMPLE / f"{name}.json"

    for path in [processed_path, sample_path]:
        if path.exists():
            return json.loads(path.read_text())

    raise FileNotFoundError(
        f"{name}.json not found in data/processed/ or data/sample/. "
        "Run `python analysis/pipeline.py` to generate processed data."
    )


def _brands() -> list[dict]:
    return _load_json("brands")


def _products() -> list[dict]:
    return _load_json("products")


def _insights() -> list[dict]:
    return _load_json("insights")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "Luggage Intelligence API"}


@app.get("/brands", response_model=list[BrandSummary])
def list_brands(
    price_band: Optional[str] = Query(None, description="Filter by price band: budget|mid-range|premium"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
):
    brands = _brands()
    if price_band:
        brands = [b for b in brands if b.get("pricing", {}).get("price_band") == price_band]
    if min_rating is not None:
        brands = [b for b in brands if (b.get("ratings", {}).get("avg_rating") or 0) >= min_rating]
    return brands


@app.get("/brands/{brand_key}", response_model=BrandSummary)
def get_brand(brand_key: str):
    brands = _brands()
    match = next((b for b in brands if b["brand_key"] == brand_key), None)
    if not match:
        raise HTTPException(404, f"Brand '{brand_key}' not found")
    return match


@app.get("/products", response_model=list[ProductDetail])
def list_products(
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_sentiment: Optional[float] = Query(None, ge=0, le=100),
    sort_by: Optional[str] = Query("rating", description="rating|price|sentiment|discount"),
    order: Optional[str] = Query("desc", description="asc|desc"),
):
    products = _products()

    if brand:
        products = [p for p in products if p.get("brand") == brand]
    if min_price is not None:
        products = [p for p in products if (p.get("price") or 0) >= min_price]
    if max_price is not None:
        products = [p for p in products if (p.get("price") or float("inf")) <= max_price]
    if min_rating is not None:
        products = [p for p in products if (p.get("rating") or 0) >= min_rating]
    if min_sentiment is not None:
        products = [p for p in products if (p.get("sentiment", {}).get("score") or 0) >= min_sentiment]

    # Sorting
    sort_key_map = {
        "rating": lambda p: p.get("rating") or 0,
        "price": lambda p: p.get("price") or 0,
        "sentiment": lambda p: (p.get("sentiment") or {}).get("score") or 0,
        "discount": lambda p: p.get("discount_pct") or 0,
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["rating"])
    products = sorted(products, key=key_fn, reverse=(order == "desc"))

    return products


@app.get("/products/{asin}", response_model=ProductDetail)
def get_product(asin: str):
    products = _products()
    match = next((p for p in products if p["asin"] == asin), None)
    if not match:
        raise HTTPException(404, f"Product '{asin}' not found")
    return match


@app.get("/insights", response_model=list[Insight])
def get_insights():
    return _insights()


@app.post("/sentiment/score")
def live_sentiment_score(
    text: str = Query(..., description="Review text to score"),
    verified: bool = Query(True),
    helpful_votes: int = Query(0)
):
    """
    Real-time sentiment scoring for arbitrary text.
    Useful for testing the 'Agent' logic on new reviews.
    """
    if not text.strip():
        raise HTTPException(400, "Text cannot be empty")
    
    review_mock = {
        "body": text,
        "verified": verified,
        "helpful_votes": helpful_votes,
        "date": datetime.now().strftime("Reviewed in India on %d %B %Y")
    }
    
    return score_review(review_mock)


@app.get("/compare")
def compare_brands(brands: str = Query(..., description="Comma-separated brand keys")):
    """Return side-by-side comparison data for requested brands."""
    requested = [b.strip() for b in brands.split(",")]
    all_brands = _brands()
    result = {b["brand_key"]: b for b in all_brands if b["brand_key"] in requested}
    missing = [k for k in requested if k not in result]
    if missing:
        raise HTTPException(404, f"Brands not found: {missing}")
    return list(result.values())


@app.get("/stats/overview")
def overview():
    """Dashboard overview stats."""
    brands = _brands()
    products = _products()
    insights = _insights()

    total_reviews = sum(b.get("ratings", {}).get("total_reviews", 0) for b in brands)
    avg_sentiment = sum(b.get("sentiment", {}).get("score", 0) for b in brands) / len(brands) if brands else 0
    prices = [p.get("price") for p in products if p.get("price")]

    return {
        "total_brands": len(brands),
        "total_products": len(products),
        "total_reviews": total_reviews,
        "avg_sentiment_score": round(avg_sentiment, 1),
        "avg_price_overall": round(sum(prices) / len(prices), 0) if prices else None,
        "insight_count": len(insights),
    }
