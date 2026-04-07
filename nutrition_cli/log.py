"""Meal logging, streak tracking, and summary queries for nutrition-cli."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config


def get_log_path() -> Path:
    """Return log file path, creating parent dirs if missing."""
    path = Path.home() / ".config" / "nutrition-cli" / "log.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_log() -> dict:
    """Read log.json. Returns {} if file missing or invalid."""
    path = get_log_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_log(data: dict) -> None:
    """Write log dict as JSON with indent=2."""
    path = get_log_path()
    path.write_text(json.dumps(data, indent=2) + "\n")


def today_key() -> str:
    """Return today's date as YYYY-MM-DD."""
    return date.today().isoformat()


def yesterday_key() -> str:
    """Return yesterday's date as YYYY-MM-DD."""
    return (date.today() - timedelta(days=1)).isoformat()


def infer_meal_type(time_str: str) -> str:
    """Infer meal type from HH:MM string.

    before 10:30 → breakfast
    10:30–15:00  → lunch
    15:00–18:00  → snack
    after 18:00  → dinner
    """
    try:
        h = int(time_str[:2])
        m = int(time_str[3:5])
        total = h * 60 + m
        if total < 10 * 60 + 30:
            return "breakfast"
        elif total < 15 * 60:
            return "lunch"
        elif total < 18 * 60:
            return "snack"
        else:
            return "dinner"
    except (ValueError, IndexError):
        return "meal"


def _current_streak(log: dict) -> int:
    """Return streak from the most recently populated day entry."""
    if not log:
        return 0
    for key in sorted(log.keys(), reverse=True):
        if log[key].get("meals"):
            return log[key].get("streak_day", 0)
    return 0


def _init_day(log: dict, key: str) -> None:
    """Add an empty day entry to log if it doesn't exist yet."""
    if key not in log:
        log[key] = {
            "target_kcal": config.get("kcal", 2000),
            "target_protein": config.get("protein", 50),
            "streak_day": _current_streak(log),
            "meals": [],
            "totals": {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0},
            "target_met": False,
            "notes": "",
        }


def add_meal(food: dict, query: str, grams: float) -> dict:
    """Append a meal entry to today's log. Returns updated day data."""
    log = load_log()
    key = today_key()
    _init_day(log, key)

    now = datetime.now()
    time_str = now.strftime("%H:%M")
    meal_id = f"meal_{now.strftime('%Y%m%d_%H%M%S')}"
    meal_type = infer_meal_type(time_str)

    target_kcal = log[key]["target_kcal"]
    kcal = food.get("kcal") or 0

    meal_entry = {
        "id": meal_id,
        "time": time_str,
        "meal_type": meal_type,
        "food_name": food.get("name", query),
        "query_used": query,
        "grams": grams,
        "source": food.get("source", ""),
        "fdc_id": food.get("fdc_id"),
        "barcode": food.get("barcode"),
        "kcal": food.get("kcal"),
        "protein": food.get("protein"),
        "fat": food.get("fat"),
        "saturated_fat": food.get("saturated_fat"),
        "carbs": food.get("carbs"),
        "fiber": food.get("fiber"),
        "sugar": food.get("sugar"),
        "sodium_mg": food.get("sodium_mg"),
        "pct_of_daily_target": round(kcal / target_kcal * 100, 1) if target_kcal else None,
    }

    log[key]["meals"].append(meal_entry)

    # Update running totals
    for nk in ("kcal", "protein", "fat", "carbs", "fiber"):
        val = food.get(nk)
        if val is not None:
            log[key]["totals"][nk] = round(log[key]["totals"].get(nk, 0) + val, 1)

    total_kcal = log[key]["totals"].get("kcal", 0)
    log[key]["target_met"] = bool(total_kcal >= target_kcal)

    save_log(log)
    return log[key]


def check_today() -> int:
    """Return number of meals logged today (reads log.json only, no API)."""
    log = load_log()
    return len(log.get(today_key(), {}).get("meals", []))


def check_yesterday() -> bool:
    """Return True if any meals were logged yesterday."""
    log = load_log()
    return len(log.get(yesterday_key(), {}).get("meals", [])) > 0


def update_streak() -> int:
    """Increment streak if today has meals and yesterday did too. Returns current streak."""
    log = load_log()
    key = today_key()

    # No meals today — nothing to update
    if not log.get(key, {}).get("meals"):
        return 0

    _init_day(log, key)

    if log.get(yesterday_key(), {}).get("meals"):
        prev_streak = log[yesterday_key()].get("streak_day", 0)
        new_streak = prev_streak + 1
    else:
        new_streak = 1

    log[key]["streak_day"] = new_streak
    save_log(log)
    return new_streak


def get_day_summary(date_key: str) -> dict | None:
    """Return a day entry from log.json, or None if absent."""
    return load_log().get(date_key)


def get_date_range_summaries(days: int) -> list[dict]:
    """Return day summaries for the last N days (oldest first, gaps included)."""
    log = load_log()
    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        key = (today - timedelta(days=i)).isoformat()
        if key in log:
            result.append({"date": key, **log[key]})
        else:
            result.append({"date": key, "meals": [], "totals": {}})
    return result


def get_week_summary() -> list[dict]:
    """Return day summaries for the current Mon–Sun week."""
    log = load_log()
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    result = []
    for i in range(7):
        key = (monday + timedelta(days=i)).isoformat()
        if key in log:
            result.append({"date": key, **log[key]})
        else:
            result.append({"date": key, "meals": [], "totals": {}})
    return result


def get_top_foods(days: int) -> list[dict]:
    """Return up to 10 most-logged foods across the last N days."""
    log = load_log()
    today = date.today()
    counts: dict[str, dict] = {}

    for i in range(days):
        key = (today - timedelta(days=i)).isoformat()
        day = log.get(key)
        if not day:
            continue
        for meal in day.get("meals", []):
            fname = meal.get("food_name", "")
            if not fname:
                continue
            if fname not in counts:
                counts[fname] = {"food_name": fname, "times": 0, "total_kcal": 0.0}
            counts[fname]["times"] += 1
            counts[fname]["total_kcal"] += meal.get("kcal") or 0

    return sorted(counts.values(), key=lambda x: x["times"], reverse=True)[:10]
