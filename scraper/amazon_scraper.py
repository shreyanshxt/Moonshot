"""
Amazon India scraper using Playwright.

Usage:
    python scraper/amazon_scraper.py                    # scrape all brands
    python scraper/amazon_scraper.py --brand safari     # single brand

Data saved to:
    data/raw/{brand}/products.json
    data/raw/{brand}/reviews/{asin}.json
"""

import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional
import httpx
from urllib.parse import quote_plus, urlparse

from playwright.async_api import async_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.config import (
    BRANDS, AMAZON_BASE, SEARCH_URL,
    MAX_PRODUCTS_PER_BRAND, MAX_REVIEWS_PER_PRODUCT, MAX_SEARCH_PAGES,
    DELAY_MIN, DELAY_MAX, USER_AGENTS, VIEWPORT, DATA_RAW, SCRAPER_API_KEY, SERPER_API_KEY
)

load_dotenv()
_api_key = os.getenv("SCRAPER_API_KEY", SCRAPER_API_KEY)
_serper_key = os.getenv("SERPER_API_KEY", SERPER_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("scraper.log")],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _discover_products_via_serper(query: str) -> list[str]:
    """Find Amazon product URLs using Serper.dev (Google Search)."""
    if not _serper_key:
        return []

    log.info("Using Serper.dev to find product links for: %s", query)
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": f"site:amazon.in {query}",
        "gl": "in",
        "num": 20
    })
    headers = {
        'X-API-KEY': _serper_key,
        'Content-Type': 'application/json'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=payload, timeout=20.0)
            response.raise_for_status()
            data = response.json()

            asins = []
            for result in data.get("organic", []):
                link = result.get("link", "")
                # Extract ASIN using regex: /dp/B0... or /gp/product/B0...
                match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", link)
                if match:
                    asin = match.group(1)
                    if asin not in asins:
                        asins.append(asin)
            
            log.info("Serper found %d unique ASINs", len(asins))
            return asins
    except Exception as e:
        log.error("Serper discovery failed: %s", e)
        return []


def _jitter():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def _scraper_url(url: str) -> str:
    """Optionally route through ScraperAPI residential proxies."""
    if _api_key:
        return f"http://api.scraperapi.com?api_key={_api_key}&url={quote_plus(url)}&country_code=in"
    return url


async def _stealth_context(playwright) -> tuple:
    """Launch browser with stealth settings."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    ua = random.choice(USER_AGENTS)
    context = await browser.new_context(
        viewport=VIEWPORT,
        user_agent=ua,
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        },
    )
    # Mask navigator.webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)
    return browser, context


async def _safe_goto(page: Page, url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            await page.goto(_scraper_url(url), wait_until="load", timeout=60_000)
            log.debug("Navigated to: %s", page.url)
            # Check for CAPTCHA
            if "captcha" in (await page.title()).lower() or await page.locator("form[action*='captcha']").count() > 0:
                log.warning("CAPTCHA detected on attempt %d — waiting before retry", attempt + 1)
                await asyncio.sleep(random.uniform(15, 30))
                continue
            return True
        except PlaywrightTimeout:
            log.warning("Timeout on attempt %d for %s", attempt + 1, url)
            await asyncio.sleep(random.uniform(5, 10))
    log.error("All retries failed for %s", url)
    return False


# ---------------------------------------------------------------------------
# Product listing scraper
# ---------------------------------------------------------------------------

async def scrape_search_page(page: Page, query: str, page_num: int = 1) -> list[dict]:
    """Scrape one page of Amazon search results."""
    url = SEARCH_URL.format(query=quote_plus(query))
    if page_num > 1:
        url += f"&page={page_num}"

    if not await _safe_goto(page, url):
        return []

    await page.wait_for_selector('.s-result-item[data-asin]', timeout=20_000)

    products = []
    cards = await page.locator('.s-result-item[data-asin]').all()

    for card in cards:
        try:
            asin = await card.get_attribute("data-asin")
            if not asin:
                continue

            # Title
            title_el = card.locator("h2 a span")
            title = (await title_el.first.text_content() or "").strip() if await title_el.count() > 0 else ""

            # Selling price
            price_whole = card.locator(".a-price .a-price-whole")
            price_fraction = card.locator(".a-price .a-price-fraction")
            price = None
            if await price_whole.count() > 0:
                whole = (await price_whole.first.text_content() or "0").replace(",", "").strip()
                frac = (await price_fraction.first.text_content() or "0").strip() if await price_fraction.count() > 0 else "0"
                try:
                    price = float(f"{whole}.{frac}")
                except ValueError:
                    pass

            # MRP / list price
            mrp_el = card.locator(".a-price.a-text-price .a-offscreen")
            mrp = None
            if await mrp_el.count() > 0:
                raw = (await mrp_el.first.text_content() or "").replace("₹", "").replace(",", "").strip()
                try:
                    mrp = float(raw)
                except ValueError:
                    pass

            # Discount badge
            discount_el = card.locator(".a-badge-text")
            discount_pct = None
            for el in await discount_el.all():
                txt = (await el.text_content() or "").strip()
                match = re.search(r"(\d+)%", txt)
                if match:
                    discount_pct = int(match.group(1))
                    break

            # Rating
            rating_el = card.locator(".a-icon-alt")
            rating = None
            if await rating_el.count() > 0:
                raw = await rating_el.first.text_content() or ""
                match = re.search(r"([\d.]+) out of", raw)
                if match:
                    rating = float(match.group(1))

            # Review count
            review_el = card.locator("span[aria-label*='ratings']")
            review_count = None
            if await review_el.count() > 0:
                raw = (await review_el.first.get_attribute("aria-label") or "").replace(",", "")
                match = re.search(r"([\d]+)", raw)
                if match:
                    review_count = int(match.group(1))

            # Product URL
            link_el = card.locator("h2 a")
            product_url = ""
            if await link_el.count() > 0:
                href = await link_el.first.get_attribute("href") or ""
                product_url = AMAZON_BASE + href if href.startswith("/") else href

            # Thumbnail
            img_el = card.locator("img.s-image")
            image_url = ""
            if await img_el.count() > 0:
                image_url = await img_el.first.get_attribute("src") or ""

            if title and asin:
                products.append({
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "mrp": mrp,
                    "discount_pct": discount_pct or (round((1 - price / mrp) * 100) if price and mrp and mrp > 0 else None),
                    "rating": rating,
                    "review_count": review_count,
                    "product_url": product_url,
                    "image_url": image_url,
                })

        except Exception as e:
            log.debug("Error parsing card: %s", e)
            continue

    log.info("Found %d products on page %d for query '%s'", len(products), page_num, query)
    return products


# ---------------------------------------------------------------------------
# Review scraper
# ---------------------------------------------------------------------------

async def scrape_reviews(page: Page, product: dict) -> list[dict]:
    """Scrape reviews and missing metadata from the product page."""
    asin = product["asin"]
    reviews = []
    page_num = 1
    # Use the product page URL instead of /product-reviews/ to bypass login walls
    reviews_url = f"{AMAZON_BASE}/dp/{asin}"

    while len(reviews) < MAX_REVIEWS_PER_PRODUCT:
        url = reviews_url # Only one page if scraping from /dp/ directly
        if not await _safe_goto(page, url):
            break
        
        # Scroll down to ensure reviews are loaded
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(2)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        # Scrape missing product metadata if needed (for Serper fallback)
        try:
            if not product.get("title") or product.get("title").startswith("Product B"):
                t_el = page.locator("#productTitle")
                if await t_el.count() > 0:
                    product["title"] = (await t_el.first.text_content() or "").strip()

            if product.get("price") is None:
                p_el = page.locator('.a-price.aok-align-center .a-offscreen, #corePriceDisplay_desktop_feature_div .a-price-whole')
                if await p_el.count() > 0:
                    raw = (await p_el.first.text_content() or "").replace("₹", "").replace(",", "").strip()
                    try: product["price"] = float(raw)
                    except: pass

            if product.get("mrp") is None:
                m_el = page.locator('.a-text-strike')
                if await m_el.count() > 0:
                    raw = (await m_el.first.text_content() or "").replace("₹", "").replace(",", "").strip()
                    try: product["mrp"] = float(raw)
                    except: pass

            if product.get("rating") is None:
                r_el = page.locator('#acrPopover')
                if await r_el.count() > 0:
                    raw = await r_el.first.get_attribute("title") or ""
                    m = re.search(r"([\d.]+) out of", raw)
                    if m: product["rating"] = float(m.group(1))

            if product.get("review_count") is None:
                rc_el = page.locator('#acrCustomerReviewText')
                if await rc_el.count() > 0:
                    raw = (await rc_el.first.text_content() or "").replace(",", "")
                    m = re.search(r"(\d+)", raw)
                    if m: product["review_count"] = int(m.group(1))
                    
            if product.get("discount_pct") is None and product.get("price") and product.get("mrp") and product["mrp"] > 0:
                product["discount_pct"] = round((1 - product["price"] / product["mrp"]) * 100)
        except Exception as e:
            log.debug("Error scraping product metadata on DP page: %s", e)

        try:
            await page.wait_for_selector('[data-hook="review"]', timeout=30_000)
        except PlaywrightTimeout:
            log.info("No more reviews or timeout for ASIN %s at page %d (URL: %s)", asin, page_num, page.url)
            break

        review_cards = await page.locator('[data-hook="review"]').all()
        if not review_cards:
            break

        for card in review_cards:
            try:
                # Star rating
                star_el = card.locator('[data-hook="review-star-rating"] .a-icon-alt')
                stars = None
                if await star_el.count() > 0:
                    raw = await star_el.first.text_content() or ""
                    match = re.search(r"([\d.]+) out of", raw)
                    if match:
                        stars = float(match.group(1))

                # Title
                title_el = card.locator('[data-hook="review-title"] span:not(.a-icon-alt)')
                title = ""
                if await title_el.count() > 0:
                    title = (await title_el.first.text_content() or "").strip()

                # Body
                body_el = card.locator('[data-hook="review-body"] span')
                body = ""
                if await body_el.count() > 0:
                    body = (await body_el.first.text_content() or "").strip()

                # Date
                date_el = card.locator('[data-hook="review-date"]')
                date_str = ""
                if await date_el.count() > 0:
                    date_str = (await date_el.first.text_content() or "").strip()

                # Verified purchase
                verified = await card.locator('[data-hook="avp-badge"]').count() > 0

                # Helpful votes
                helpful_el = card.locator('[data-hook="helpful-vote-statement"]')
                helpful_votes = 0
                if await helpful_el.count() > 0:
                    raw = await helpful_el.first.text_content() or ""
                    match = re.search(r"(\d+)", raw.replace(",", ""))
                    if match:
                        helpful_votes = int(match.group(1))

                if body:
                    reviews.append({
                        "asin": asin,
                        "stars": stars,
                        "title": title,
                        "body": body,
                        "date": date_str,
                        "verified": verified,
                        "helpful_votes": helpful_votes,
                    })

            except Exception as e:
                log.debug("Error parsing review: %s", e)
                continue

        log.info("Scraped %d reviews from product page for ASIN %s", len(reviews), asin)
        break # Product page only has one "page" of top reviews

    return reviews[:MAX_REVIEWS_PER_PRODUCT]


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def scrape_brand(brand_key: str, query: str):
    """Full pipeline for one brand: search → product list → reviews."""
    out_dir = DATA_RAW / brand_key
    reviews_dir = out_dir / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    reviews_dir.mkdir(parents=True, exist_ok=True)

    products_file = out_dir / "products.json"
    if products_file.exists():
        log.info("Loading cached products for %s", brand_key)
        products = json.loads(products_file.read_text())
    else:
        products = []
        # Try Serper first if available
        serper_asins = await _discover_products_via_serper(query)
        if serper_asins:
            for asin in serper_asins:
                products.append({
                    "asin": asin,
                    "title": f"Product {asin}",  # placeholder until detailed scrape
                    "brand": brand_key,
                    "product_url": f"{AMAZON_BASE}/dp/{asin}"
                })
        
        # If Serper failed or missing, fall back to direct Amazon search
        if not products:
            async with async_playwright() as pw:
                browser, context = await _stealth_context(pw)
                page = await context.new_page()
                for pg in range(1, MAX_SEARCH_PAGES + 1):
                    batch = await scrape_search_page(page, query, pg)
                    products.extend(batch)
                    if len(products) >= MAX_PRODUCTS_PER_BRAND:
                        break
                    _jitter()
                await browser.close()

        products = products[:MAX_PRODUCTS_PER_BRAND]
        # Attach brand key
        for p in products:
            p["brand"] = brand_key
        products_file.write_text(json.dumps(products, indent=2, ensure_ascii=False))
        log.info("Saved %d products for %s", len(products), brand_key)

    # Scrape reviews per product
    async with async_playwright() as pw:
        browser, context = await _stealth_context(pw)
        page = await context.new_page()
        for product in products:
            asin = product["asin"]
            review_file = reviews_dir / f"{asin}.json"
            if review_file.exists():
                log.info("Reviews cached for ASIN %s", asin)
                continue
            log.info("Scraping reviews for %s — %s", brand_key, asin)
            reviews = await scrape_reviews(page, product)
            review_file.write_text(json.dumps(reviews, indent=2, ensure_ascii=False))
            log.info("Saved %d reviews for ASIN %s", len(reviews), asin)
            _jitter()
        
        # Save products again to capture any missing metadata scraped from DP pages
        products_file.write_text(json.dumps(products, indent=2, ensure_ascii=False))

        await browser.close()


async def main(target_brand: Optional[str] = None):
    brands = {target_brand: BRANDS[target_brand]} if target_brand else BRANDS
    for brand_key, query in brands.items():
        log.info("=== Scraping brand: %s ===", brand_key)
        await scrape_brand(brand_key, query)
    log.info("Scraping complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", choices=list(BRANDS.keys()), default=None)
    args = parser.parse_args()
    asyncio.run(main(args.brand))
