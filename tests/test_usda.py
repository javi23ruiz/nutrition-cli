"""Tests for USDA FoodData Central API wrapper."""

import responses

from nutrition_cli.usda import DEMO_KEY, RateLimitError, parse_food, search


SAMPLE_FOOD = {
    "fdcId": 171077,
    "description": "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw",
    "dataType": "SR Legacy",
    "foodNutrients": [
        {"nutrientName": "Energy", "value": 120.0},
        {"nutrientName": "Protein", "value": 22.5},
        {"nutrientName": "Total lipid (fat)", "value": 2.6},
        {"nutrientName": "Fatty acids, total saturated", "value": 0.7},
        {"nutrientName": "Carbohydrate, by difference", "value": 0.0},
        {"nutrientName": "Fiber, total dietary", "value": 0.0},
        {"nutrientName": "Sugars, total including NLEA", "value": 0.0},
        {"nutrientName": "Sodium, Na", "value": 74.0},
        {"nutrientName": "Cholesterol", "value": 64.0},
    ],
}

SAMPLE_FOOD_2 = {
    "fdcId": 171078,
    "description": "Beef, ground, 85% lean",
    "dataType": "Foundation",
    "foodNutrients": [
        {"nutrientName": "Energy", "value": 215.0},
        {"nutrientName": "Protein", "value": 18.6},
        {"nutrientName": "Total lipid (fat)", "value": 15.0},
    ],
}

SAMPLE_FOOD_3 = {
    "fdcId": 171079,
    "description": "Salmon, Atlantic, raw",
    "dataType": "Branded",
    "foodNutrients": [
        {"nutrientName": "Energy", "value": 208.0},
        {"nutrientName": "Protein", "value": 20.4},
    ],
}


@responses.activate
def test_search_returns_parsed_foods():
    responses.add(
        responses.GET,
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        json={"foods": [SAMPLE_FOOD, SAMPLE_FOOD_2, SAMPLE_FOOD_3]},
        status=200,
    )

    results = search("chicken", api_key="TEST_KEY")
    assert len(results) == 3
    assert results[0]["description"] == SAMPLE_FOOD["description"]
    assert results[1]["fdcId"] == 171078


@responses.activate
def test_search_scales_grams_correctly():
    responses.add(
        responses.GET,
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        json={"foods": [SAMPLE_FOOD]},
        status=200,
    )

    results = search("chicken", api_key="TEST_KEY")
    parsed = parse_food(results[0], grams=200)

    # Energy is 120 per 100g -> 240 per 200g
    assert parsed["kcal"] == 240.0
    assert parsed["protein"] == 45.0
    assert parsed["grams"] == 200


@responses.activate
def test_search_rate_limit_raises():
    responses.add(
        responses.GET,
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        headers={"Retry-After": "3600"},
        status=429,
    )

    try:
        search("chicken", api_key="TEST_KEY")
        assert False, "Should have raised RateLimitError"
    except RateLimitError as e:
        assert e.retry_after == 3600


@responses.activate
def test_search_falls_back_to_demo_key():
    responses.add(
        responses.GET,
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        json={"foods": []},
        status=200,
    )

    # Don't pass api_key — should use DEMO_KEY
    search("chicken")

    assert f"api_key={DEMO_KEY}" in responses.calls[0].request.url


def test_parse_food_missing_nutrients_are_none():
    food = {
        "fdcId": 999,
        "description": "Test food",
        "dataType": "SR Legacy",
        "foodNutrients": [
            {"nutrientName": "Energy", "value": 100.0},
            {"nutrientName": "Protein", "value": 10.0},
            # No fiber, no fat, etc.
        ],
    }

    parsed = parse_food(food)
    assert parsed["kcal"] == 100.0
    assert parsed["protein"] == 10.0
    assert parsed["fiber"] is None
    assert parsed["fat"] is None
    assert parsed["sugar"] is None
