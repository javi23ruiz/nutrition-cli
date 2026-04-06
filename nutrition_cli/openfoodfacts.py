"""Open Food Facts API wrapper. No API key required."""

import click
import requests

BASE_URL = "https://world.openfoodfacts.org"
USER_AGENT = "nutrition-cli/1.0 (github.com/javierruiz/nutrition-cli)"

NUTRISCORE_LABELS = {
    "a": "A (excellent)",
    "b": "B (good)",
    "c": "C (average)",
    "d": "D (poor)",
    "e": "E (bad)",
}

NOVA_LABELS = {
    1: "Unprocessed",
    2: "Processed ingredients",
    3: "Processed",
    4: "Ultra-processed",
}


def search(query: str, page_size: int = 5) -> list[dict]:
    """Search Open Food Facts. Returns list of raw product dicts."""
    try:
        resp = requests.get(
            f"{BASE_URL}/cgi/search.pl",
            params={"search_terms": query, "json": 1, "page_size": page_size},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
    except requests.RequestException as e:
        raise click.ClickException(f"Network error contacting Open Food Facts: {e}")

    if resp.status_code != 200:
        raise click.ClickException(f"Open Food Facts API error: HTTP {resp.status_code}")

    data = resp.json()
    products = data.get("products", [])
    return [p for p in products if "nutriments" in p]


def get_by_barcode(barcode: str) -> dict | None:
    """Fetch a product by barcode. Returns None if not found."""
    fields = (
        "product_name,brands,serving_size,nutrition_grades,"
        "nova_group,nutriments,allergens_tags,ingredients_analysis_tags"
    )
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/product/{barcode}.json",
            params={"fields": fields},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
    except requests.RequestException as e:
        raise click.ClickException(f"Network error contacting Open Food Facts: {e}")

    data = resp.json()
    if data.get("status") == 0:
        return None
    return data.get("product")


def parse_product(product: dict, grams: float = 100) -> dict:
    """Extract and scale nutrients from a raw OFF product dict."""
    n = product.get("nutriments", {})
    scale = grams / 100

    def _get(key):
        val = n.get(key)
        if val is not None:
            return round(float(val) * scale, 1)
        return None

    analysis_tags = product.get("ingredients_analysis_tags", [])
    allergens_raw = product.get("allergens_tags", [])

    nutriscore_raw = product.get("nutrition_grades", "")
    nova_raw = product.get("nova_group")

    return {
        "name": product.get("product_name", "Unknown"),
        "brand": product.get("brands", ""),
        "serving_size": product.get("serving_size", ""),
        "source": "Open Food Facts",
        "grams": grams,
        "nutriscore": NUTRISCORE_LABELS.get(nutriscore_raw, nutriscore_raw) if nutriscore_raw else None,
        "nova_group": NOVA_LABELS.get(nova_raw, nova_raw) if nova_raw else None,
        "kcal": _get("energy-kcal_100g"),
        "protein": _get("proteins_100g"),
        "fat": _get("fat_100g"),
        "saturated_fat": _get("saturated-fat_100g"),
        "carbs": _get("carbohydrates_100g"),
        "fiber": _get("fiber_100g"),
        "sugar": _get("sugars_100g"),
        "salt_mg": _get("salt_100g"),
        "is_vegan": "en:vegan" in analysis_tags,
        "is_vegetarian": "en:vegetarian" in analysis_tags,
        "allergens": [a.replace("en:", "") for a in allergens_raw],
    }
