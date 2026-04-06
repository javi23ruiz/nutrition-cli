"""Tests for output formatting."""

from nutrition_cli.format import (
    compare_table,
    format_error_rate_limit,
    nutrition_block,
    rda_progress,
)


SAMPLE_FOOD = {
    "name": "Chicken breast",
    "source": "USDA",
    "data_type": "SR Legacy",
    "grams": 100,
    "kcal": 120.0,
    "protein": 22.5,
    "fat": 2.6,
    "saturated_fat": 0.7,
    "carbs": 0.0,
    "fiber": 0.0,
    "sugar": 0.0,
    "sodium_mg": 74.0,
}


def test_nutrition_block_contains_all_fields():
    output = nutrition_block(SAMPLE_FOOD)
    assert "120.0" in output  # kcal
    assert "22.5" in output  # protein
    assert "2.6" in output  # fat
    assert "0.0" in output  # carbs
    assert "Chicken breast" in output
    assert "USDA" in output
    assert "100g" in output


def test_nutrition_block_none_fields_show_as_dash():
    food = {
        "name": "Test food",
        "source": "USDA",
        "grams": 100,
        "kcal": 100.0,
        "protein": 10.0,
        "fat": None,
        "saturated_fat": None,
        "carbs": 5.0,
        "fiber": None,
        "sugar": None,
    }
    output = nutrition_block(food)
    assert "\u2014" in output  # em dash for None values
    assert "None" not in output


def test_compare_table_aligns_columns():
    food1 = {**SAMPLE_FOOD, "name": "Chicken breast"}
    food2 = {**SAMPLE_FOOD, "name": "Tofu", "kcal": 76.0, "protein": 8.0, "fat": 4.8}
    output = compare_table([food1, food2])
    lines = output.strip().split("\n")

    # Header + separator + 6 nutrient rows = 8 lines
    assert len(lines) == 8

    # All nutrient rows should have same length (aligned)
    row_lengths = [len(line) for line in lines[2:]]
    assert len(set(row_lengths)) == 1


def test_rda_progress_bar_length():
    rda = {"calories": 2500, "protein_g": 56, "fat_g": 83, "carbs_g": 325, "fiber_g": 38}
    output = rda_progress(SAMPLE_FOOD, rda)
    lines = output.strip().split("\n")

    # Each bar line should contain exactly 20 bar chars (█ + ░)
    for line in lines[1:]:  # skip header line
        bar_chars = line.count("\u2588") + line.count("\u2591")
        assert bar_chars == 20, f"Bar not 20 chars wide in: {line}"


def test_format_error_rate_limit_contains_url():
    output = format_error_rate_limit(2820)
    assert "https://fdc.nal.usda.gov/api-key-signup" in output
    assert "nutrition config set --usda-key YOUR_KEY" in output
    assert "47 minutes" in output
