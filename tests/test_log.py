"""Tests for meal logging and streak tracking."""

import json
from datetime import date, timedelta

import pytest

from nutrition_cli.log import (
    add_meal,
    check_today,
    check_yesterday,
    get_date_range_summaries,
    get_top_foods,
    get_week_summary,
    infer_meal_type,
    today_key,
    update_streak,
    yesterday_key,
)


# --- helpers ---

SAMPLE_FOOD = {
    "name": "Chicken breast",
    "source": "USDA",
    "kcal": 200.0,
    "protein": 30.0,
    "fat": 5.0,
    "carbs": 0.0,
    "fiber": 0.0,
    "grams": 100,
}


def _mock_config(monkeypatch, kcal=2000, protein=50):
    """Patch config.get to return test defaults."""
    values = {"kcal": kcal, "protein": protein}
    monkeypatch.setattr("nutrition_cli.log.config.get", lambda k, d=None: values.get(k, d))


def _use_tmp_log(monkeypatch, tmp_path):
    """Redirect log.json to a temp directory."""
    log_path = tmp_path / "log.json"
    monkeypatch.setattr("nutrition_cli.log.get_log_path", lambda: log_path)
    return log_path


# --- infer_meal_type ---


def test_infer_meal_type_breakfast():
    assert infer_meal_type("07:00") == "breakfast"
    assert infer_meal_type("10:29") == "breakfast"


def test_infer_meal_type_lunch():
    assert infer_meal_type("10:30") == "lunch"
    assert infer_meal_type("14:59") == "lunch"


def test_infer_meal_type_snack():
    assert infer_meal_type("15:00") == "snack"
    assert infer_meal_type("17:59") == "snack"


def test_infer_meal_type_dinner():
    assert infer_meal_type("18:00") == "dinner"
    assert infer_meal_type("21:30") == "dinner"


# --- check_today (no meals) ---


def test_check_today_empty(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    assert check_today() == 0


# --- add_meal and check_today ---


def test_add_meal_increments_count(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    add_meal(SAMPLE_FOOD, "chicken", 100)
    assert check_today() == 1

    add_meal(SAMPLE_FOOD, "chicken", 100)
    assert check_today() == 2


def test_add_meal_updates_totals(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    day_data = add_meal(SAMPLE_FOOD, "chicken", 100)
    assert day_data["totals"]["kcal"] == 200.0
    assert day_data["totals"]["protein"] == 30.0


def test_add_meal_cumulates_totals(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    add_meal(SAMPLE_FOOD, "chicken", 100)
    day_data = add_meal(SAMPLE_FOOD, "chicken", 100)
    assert day_data["totals"]["kcal"] == 400.0


def test_add_meal_sets_target_met(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch, kcal=200)  # very low target for test

    day_data = add_meal(SAMPLE_FOOD, "chicken", 100)
    assert day_data["target_met"] is True


def test_add_meal_stores_pct_of_target(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch, kcal=2000)

    day_data = add_meal(SAMPLE_FOOD, "chicken", 100)
    meal = day_data["meals"][0]
    assert meal["pct_of_daily_target"] == 10.0  # 200 / 2000 * 100


def test_add_meal_infers_meal_type(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    day_data = add_meal(SAMPLE_FOOD, "chicken", 100)
    meal = day_data["meals"][0]
    # meal_type must be one of the known values
    assert meal["meal_type"] in ("breakfast", "lunch", "snack", "dinner", "meal")


# --- check_yesterday ---


def test_check_yesterday_empty(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    assert check_yesterday() is False


def test_check_yesterday_with_data(monkeypatch, tmp_path):
    log_path = _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    # Write a fake yesterday entry directly
    ykey = yesterday_key()
    log_data = {
        ykey: {
            "target_kcal": 2000,
            "target_protein": 50,
            "streak_day": 1,
            "meals": [{"food_name": "Egg", "kcal": 80}],
            "totals": {"kcal": 80},
            "target_met": False,
            "notes": "",
        }
    }
    log_path.write_text(json.dumps(log_data))

    assert check_yesterday() is True


# --- update_streak ---


def test_update_streak_no_meals(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)
    assert update_streak() == 0


def test_update_streak_first_day(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    add_meal(SAMPLE_FOOD, "chicken", 100)
    streak = update_streak()
    assert streak == 1


def test_update_streak_consecutive_days(monkeypatch, tmp_path):
    log_path = _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    # Seed yesterday with streak_day=3
    ykey = yesterday_key()
    log_data = {
        ykey: {
            "target_kcal": 2000,
            "target_protein": 50,
            "streak_day": 3,
            "meals": [{"food_name": "Egg", "kcal": 80}],
            "totals": {"kcal": 80},
            "target_met": False,
            "notes": "",
        }
    }
    log_path.write_text(json.dumps(log_data))

    add_meal(SAMPLE_FOOD, "chicken", 100)
    streak = update_streak()
    assert streak == 4


# --- get_date_range_summaries ---


def test_get_date_range_summaries_returns_n_days(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    result = get_date_range_summaries(7)
    assert len(result) == 7


def test_get_date_range_summaries_oldest_first(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    result = get_date_range_summaries(3)
    assert result[0]["date"] < result[1]["date"] < result[2]["date"]


def test_get_date_range_summaries_includes_today(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    result = get_date_range_summaries(7)
    assert result[-1]["date"] == today_key()


# --- get_week_summary ---


def test_get_week_summary_returns_7_days(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    result = get_week_summary()
    assert len(result) == 7


def test_get_week_summary_starts_on_monday(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    from datetime import datetime
    result = get_week_summary()
    first_day = datetime.fromisoformat(result[0]["date"]).weekday()
    assert first_day == 0  # Monday


# --- get_top_foods ---


def test_get_top_foods_empty(monkeypatch, tmp_path):
    _use_tmp_log(monkeypatch, tmp_path)
    assert get_top_foods(30) == []


def test_get_top_foods_counts_correctly(monkeypatch, tmp_path):
    log_path = _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    add_meal(SAMPLE_FOOD, "chicken", 100)
    add_meal({**SAMPLE_FOOD, "name": "Rice", "kcal": 150}, "rice", 100)
    add_meal(SAMPLE_FOOD, "chicken", 100)  # chicken appears twice

    foods = get_top_foods(1)
    assert foods[0]["food_name"] == "Chicken breast"
    assert foods[0]["times"] == 2


def test_get_top_foods_max_10(monkeypatch, tmp_path):
    log_path = _use_tmp_log(monkeypatch, tmp_path)
    _mock_config(monkeypatch)

    for i in range(15):
        add_meal({**SAMPLE_FOOD, "name": f"Food {i}"}, f"food{i}", 100)

    foods = get_top_foods(1)
    assert len(foods) <= 10
