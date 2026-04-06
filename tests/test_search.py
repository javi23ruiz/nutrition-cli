"""Tests for smart search routing."""

from unittest.mock import patch

import click
import pytest

from nutrition_cli.search import detect_barcode, lookup, lookup_multi


def test_detect_barcode_true():
    assert detect_barcode("3017624010701") is True
    assert detect_barcode("50001594") is True


def test_detect_barcode_false():
    assert detect_barcode("chicken breast") is False
    assert detect_barcode("123") is False
    assert detect_barcode("abc12345678") is False


@patch("nutrition_cli.search.usda")
def test_lookup_prefers_usda_sr_legacy(mock_usda):
    sr_food = {
        "fdcId": 1,
        "description": "Chicken SR",
        "dataType": "SR Legacy",
        "foodNutrients": [{"nutrientName": "Energy", "value": 120.0}],
    }
    branded_food = {
        "fdcId": 2,
        "description": "Chicken Branded",
        "dataType": "Branded",
        "foodNutrients": [{"nutrientName": "Energy", "value": 150.0}],
    }
    mock_usda.search.return_value = [branded_food, sr_food]
    mock_usda.parse_food.side_effect = lambda f, g: {"name": f["description"], "grams": g, "data_type": f["dataType"]}
    mock_usda.RateLimitError = Exception
    mock_usda.InvalidKeyError = Exception

    result = lookup("chicken", 100)
    assert result["name"] == "Chicken SR"


@patch("nutrition_cli.search.openfoodfacts")
@patch("nutrition_cli.search.usda")
def test_lookup_falls_back_to_off_when_usda_empty(mock_usda, mock_off):
    mock_usda.search.return_value = []
    mock_usda.RateLimitError = Exception
    mock_usda.InvalidKeyError = Exception

    off_product = {
        "product_name": "Chicken OFF",
        "nutriments": {"energy-kcal_100g": 110.0},
    }
    mock_off.search.return_value = [off_product]
    mock_off.parse_product.return_value = {"name": "Chicken OFF", "grams": 100, "source": "Open Food Facts"}

    result = lookup("chicken", 100)
    assert result["name"] == "Chicken OFF"


@patch("nutrition_cli.search.openfoodfacts")
@patch("nutrition_cli.search.usda")
def test_lookup_raises_when_both_empty(mock_usda, mock_off):
    mock_usda.search.return_value = []
    mock_usda.RateLimitError = Exception
    mock_usda.InvalidKeyError = Exception
    mock_off.search.return_value = []

    with pytest.raises(click.ClickException, match="No nutrition data found"):
        lookup("nonexistent_food_xyz", 100)
