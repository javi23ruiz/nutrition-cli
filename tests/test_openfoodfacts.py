"""Tests for Open Food Facts API wrapper."""

import responses

from nutrition_cli.openfoodfacts import parse_product, get_by_barcode


SAMPLE_PRODUCT = {
    "product_name": "Nutella",
    "brands": "Ferrero",
    "serving_size": "15g",
    "nutrition_grades": "e",
    "nova_group": 4,
    "nutriments": {
        "energy-kcal_100g": 539.0,
        "proteins_100g": 6.3,
        "fat_100g": 30.9,
        "saturated-fat_100g": 10.6,
        "carbohydrates_100g": 57.5,
        "fiber_100g": 0.0,
        "sugars_100g": 56.3,
        "salt_100g": 0.107,
    },
    "allergens_tags": ["en:gluten", "en:milk", "en:soybeans"],
    "ingredients_analysis_tags": ["en:vegetarian"],
}


@responses.activate
def test_barcode_lookup_returns_product():
    responses.add(
        responses.GET,
        "https://world.openfoodfacts.org/api/v2/product/3017624010701.json",
        json={"status": 1, "product": SAMPLE_PRODUCT},
        status=200,
    )

    product = get_by_barcode("3017624010701")
    assert product is not None
    assert product["product_name"] == "Nutella"
    assert product["brands"] == "Ferrero"


@responses.activate
def test_barcode_not_found_returns_none():
    responses.add(
        responses.GET,
        "https://world.openfoodfacts.org/api/v2/product/0000000000000.json",
        json={"status": 0},
        status=200,
    )

    result = get_by_barcode("0000000000000")
    assert result is None


def test_parse_product_extracts_nutriscore():
    parsed = parse_product(SAMPLE_PRODUCT)
    assert parsed["nutriscore"] == "E (bad)"
    assert parsed["nova_group"] == "Ultra-processed"
    assert parsed["kcal"] == 539.0
    assert parsed["protein"] == 6.3


def test_parse_product_vegan_flag():
    vegan_product = {
        "product_name": "Soy Milk",
        "nutriments": {"energy-kcal_100g": 40.0},
        "ingredients_analysis_tags": ["en:vegan", "en:vegetarian"],
    }

    parsed = parse_product(vegan_product)
    assert parsed["is_vegan"] is True
    assert parsed["is_vegetarian"] is True


def test_parse_product_non_vegan():
    parsed = parse_product(SAMPLE_PRODUCT)
    assert parsed["is_vegan"] is False
    assert parsed["is_vegetarian"] is True


def test_parse_product_allergens_cleaned():
    parsed = parse_product(SAMPLE_PRODUCT)
    assert parsed["allergens"] == ["gluten", "milk", "soybeans"]
