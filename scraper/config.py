"""
Scraper configuration — brands, search queries, paths, and request settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
DATA_SAMPLE = BASE_DIR / "data" / "sample"

BRANDS = {
    "safari": "Safari luggage trolley bag",
    "skybags": "Skybags trolley bag luggage",
    "american_tourister": "American Tourister luggage trolley",
    "vip": "VIP luggage trolley bag",
    "aristocrat": "Aristocrat trolley bag",
    "nasher_miles": "Nasher Miles luggage trolley bag",
}

AMAZON_BASE = "https://www.amazon.in"
SEARCH_URL = "https://www.amazon.in/s?k={query}&rh=n%3A1375424031&sort=review-rank"

# Products to scrape per brand (set lower if hitting CAPTCHAs)
MAX_PRODUCTS_PER_BRAND = 12
# Reviews to scrape per product
MAX_REVIEWS_PER_PRODUCT = 200
# Pages of search results to scan
MAX_SEARCH_PAGES = 3

# Random delay range between requests (seconds)
DELAY_MIN = 3.0
DELAY_MAX = 8.0

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

VIEWPORT = {"width": 1366, "height": 768}

# Set SCRAPER_API_KEY in .env to route through ScraperAPI residential proxies
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
