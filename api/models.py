"""Pydantic response models for the FastAPI backend."""

from typing import Optional
from pydantic import BaseModel


class PricingStats(BaseModel):
    avg_price: Optional[float] = None
    median_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    avg_mrp: Optional[float] = None
    avg_discount_pct: Optional[float] = None
    price_band: str = "unknown"


class RatingStats(BaseModel):
    avg_rating: Optional[float] = None
    total_reviews: int = 0
    products_count: int = 0


class SentimentStats(BaseModel):
    score: float
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    total_reviews_scored: int


class AspectData(BaseModel):
    score: Optional[float]
    mentions: int
    sample_pos: list[str]
    sample_neg: list[str]


class ThemeData(BaseModel):
    positive: list[str]
    negative: list[str]


class BrandSummary(BaseModel):
    brand_key: str
    brand_name: str
    pricing: PricingStats
    ratings: RatingStats
    sentiment: SentimentStats
    themes: ThemeData
    aspects: dict[str, AspectData]
    anomalies: list[str]


class ReviewSnippet(BaseModel):
    title: Optional[str]
    body: str


class ProductDetail(BaseModel):
    asin: str
    brand: str
    title: str
    price: Optional[float] = None
    mrp: Optional[float] = None
    discount_pct: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    review_count_scraped: Optional[int] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    sentiment: Optional[SentimentStats] = None
    themes: Optional[ThemeData] = None
    aspects: Optional[dict[str, AspectData]] = None
    star_distribution: Optional[dict[str, int]] = None
    top_positive_reviews: Optional[list[ReviewSnippet]] = None
    top_negative_reviews: Optional[list[ReviewSnippet]] = None


class Insight(BaseModel):
    type: str
    headline: str
    detail: str
    brand: Optional[str]
