"""Smart routing layer between USDA and Open Food Facts."""

import re

import click

from . import openfoodfacts, usda


def detect_barcode(query: str) -> bool:
    """Return True if query looks like an EAN-8/EAN-13/UPC-A barcode."""
    return bool(re.match(r"^\d{8,13}$", query.strip()))


def lookup(query: str, grams: float, api_key: str | None = None) -> dict:
    """Look up a single food, routing between APIs automatically."""
    if detect_barcode(query):
        product = openfoodfacts.get_by_barcode(query.strip())
        if product is not None:
            return openfoodfacts.parse_product(product, grams)
        raise click.ClickException(
            f"Barcode '{query}' not found in Open Food Facts. "
            "Try searching by name with: nutrition search <name>"
        )

    # Try USDA first — prefer SR Legacy / Foundation results
    try:
        foods = usda.search(query, api_key)
        for food in foods:
            if food.get("dataType") in ("SR Legacy", "Foundation"):
                return usda.parse_food(food, grams)
    except (usda.RateLimitError, usda.InvalidKeyError):
        raise
    except click.ClickException:
        foods = []

    # Fall back to Open Food Facts
    try:
        products = openfoodfacts.search(query)
        if products:
            return openfoodfacts.parse_product(products[0], grams)
    except click.ClickException:
        pass

    # If USDA had branded results, use the first one
    if foods:
        return usda.parse_food(foods[0], grams)

    raise click.ClickException(
        f"No nutrition data found for '{query}'. "
        "Try a more specific name or use a barcode."
    )


def lookup_multi(queries: list[str], grams: float, api_key: str | None = None) -> list[dict]:
    """Look up multiple foods, collecting errors rather than failing fast."""
    results = []
    errors = []

    for query in queries:
        try:
            results.append(lookup(query, grams, api_key))
        except click.ClickException as e:
            errors.append(f"  - {query}: {e.format_message()}")

    if errors:
        error_msg = "Some lookups failed:\n" + "\n".join(errors)
        if results:
            click.echo(error_msg, err=True)
        else:
            raise click.ClickException(error_msg)

    return results
