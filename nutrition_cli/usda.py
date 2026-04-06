"""USDA FoodData Central API wrapper."""

import click
import requests

from . import config

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
DEMO_KEY = "DEMO_KEY"
USER_AGENT = "nutrition-cli/1.0 (github.com/javierruiz/nutrition-cli)"

NUTRIENT_MAP = {
    "Energy": "kcal",
    "Protein": "protein",
    "Total lipid (fat)": "fat",
    "Fatty acids, total saturated": "saturated_fat",
    "Carbohydrate, by difference": "carbs",
    "Fiber, total dietary": "fiber",
    "Sugars, total including NLEA": "sugar",
    "Sodium, Na": "sodium_mg",
    "Cholesterol": "cholesterol_mg",
    "Calcium, Ca": "calcium_mg",
    "Iron, Fe": "iron_mg",
}


class RateLimitError(Exception):
    """Raised when USDA returns HTTP 429."""

    def __init__(self, retry_after: int = 3600):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s.")


class InvalidKeyError(Exception):
    """Raised when USDA returns HTTP 403."""

    def __init__(self):
        super().__init__("Invalid or expired USDA API key.")


def _get_api_key() -> str:
    """Return configured USDA key or DEMO_KEY."""
    return config.get("usda_key", DEMO_KEY)


def search(query: str, api_key: str | None = None, data_types: list[str] | None = None, page_size: int = 5) -> list[dict]:
    """Search USDA FoodData Central. Returns list of raw food dicts."""
    if api_key is None:
        api_key = _get_api_key()
    if data_types is None:
        data_types = ["SR Legacy", "Foundation", "Branded"]

    params = {
        "query": query,
        "api_key": api_key,
        "dataType": ",".join(data_types),
        "pageSize": page_size,
    }

    try:
        resp = requests.get(
            f"{BASE_URL}/foods/search",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
    except requests.RequestException as e:
        raise click.ClickException(f"Network error contacting USDA: {e}")

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 3600))
        raise RateLimitError(retry_after)
    if resp.status_code == 403:
        raise InvalidKeyError()
    if resp.status_code != 200:
        raise click.ClickException(f"USDA API error: HTTP {resp.status_code}")

    data = resp.json()
    return data.get("foods", [])


def parse_food(food: dict, grams: float = 100) -> dict:
    """Extract and scale nutrients from a raw USDA food dict."""
    nutrients = {}
    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName", "")
        if name in NUTRIENT_MAP:
            key = NUTRIENT_MAP[name]
            value = nutrient.get("value")
            if value is not None:
                nutrients[key] = round(value * grams / 100, 1)
            else:
                nutrients[key] = None

    result = {
        "name": food.get("description", "Unknown"),
        "fdc_id": food.get("fdcId"),
        "data_type": food.get("dataType", "Unknown"),
        "source": "USDA",
        "grams": grams,
    }

    for key in ["kcal", "protein", "fat", "saturated_fat", "carbs", "fiber",
                "sugar", "sodium_mg", "cholesterol_mg", "calcium_mg", "iron_mg"]:
        result[key] = nutrients.get(key)

    return result


def get_by_id(fdc_id: int, api_key: str | None = None) -> dict:
    """Fetch a single food by FDC ID and return parsed dict."""
    if api_key is None:
        api_key = _get_api_key()

    try:
        resp = requests.get(
            f"{BASE_URL}/food/{fdc_id}",
            params={"api_key": api_key},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
    except requests.RequestException as e:
        raise click.ClickException(f"Network error contacting USDA: {e}")

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 3600))
        raise RateLimitError(retry_after)
    if resp.status_code == 403:
        raise InvalidKeyError()
    if resp.status_code != 200:
        raise click.ClickException(f"USDA API error: HTTP {resp.status_code}")

    return parse_food(resp.json())
