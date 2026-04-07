"""All output formatting. Returns strings — never prints directly."""

from datetime import datetime


def _val(value, unit="g", width=7) -> str:
    """Format a nutrient value, showing dash for None."""
    if value is None:
        return "\u2014".rjust(width)
    return f"{value}{unit}".rjust(width)


def _source_label(food: dict) -> str:
    """Build source label from food dict."""
    source = food.get("source", "")
    data_type = food.get("data_type", "")
    brand = food.get("brand", "")
    if data_type:
        return f"{source} ({data_type})"
    if brand:
        return f"{source} ({brand})"
    return source


def nutrition_block(food: dict) -> str:
    """Format a single food lookup result."""
    lines = []
    lines.append(f"  {food['name']}")
    lines.append(f"  Source   : {_source_label(food)}")

    if food.get("nutriscore"):
        lines.append(f"  Nutri-Score: {food['nutriscore']}")
    if food.get("nova_group"):
        lines.append(f"  NOVA     : {food['nova_group']}")

    lines.append(f"  Serving  : {food['grams']}g")
    lines.append("  " + "\u2500" * 35)

    lines.append(f"  Calories : {_val(food.get('kcal'), ' kcal')}")
    lines.append(f"  Protein  : {_val(food.get('protein'))}")

    fat_str = _val(food.get("fat"))
    sat = food.get("saturated_fat")
    if sat is not None:
        fat_str += f"  (sat. {sat}g)"
    lines.append(f"  Fat      : {fat_str}")

    lines.append(f"  Carbs    : {_val(food.get('carbs'))}")
    lines.append(f"  Fiber    : {_val(food.get('fiber'))}")
    lines.append(f"  Sugar    : {_val(food.get('sugar'))}")

    sodium_key = "sodium_mg" if "sodium_mg" in food else "salt_mg"
    sodium_label = "Sodium" if sodium_key == "sodium_mg" else "Salt"
    lines.append(f"  {sodium_label:9s}: {_val(food.get(sodium_key), ' mg')}")

    allergens = food.get("allergens", [])
    if allergens:
        lines.append(f"  Allergens: {', '.join(allergens)}")

    return "\n".join(lines)


def compare_table(foods: list[dict]) -> str:
    """Aligned comparison table for 2-5 foods."""
    label_width = 12
    col_width = 20

    # Truncate food names
    names = [f["name"][:18] for f in foods]

    lines = []
    header = " " * label_width + "".join(n.rjust(col_width) for n in names)
    lines.append(header)
    lines.append("\u2500" * (label_width + col_width * len(foods)))

    rows = [
        ("Calories", "kcal", " kcal"),
        ("Protein", "protein", "g"),
        ("Fat", "fat", "g"),
        ("Carbs", "carbs", "g"),
        ("Fiber", "fiber", "g"),
        ("Sugar", "sugar", "g"),
    ]

    for label, key, unit in rows:
        row = label.ljust(label_width)
        for f in foods:
            val = f.get(key)
            if val is None:
                row += "\u2014".rjust(col_width)
            else:
                row += f"{val}{unit}".rjust(col_width)
        lines.append(row)

    return "\n".join(lines)


def meal_summary(foods: list[dict], label: str = "Meal total") -> str:
    """Sum nutrients across foods and format as a totals block."""
    keys = ["kcal", "protein", "fat", "saturated_fat", "carbs", "fiber", "sugar"]
    totals = {}
    total_grams = 0.0

    for key in keys:
        values = [f.get(key) for f in foods if f.get(key) is not None]
        totals[key] = round(sum(values), 1) if values else None

    for f in foods:
        total_grams += f.get("grams", 0)

    total_food = {
        "name": label,
        "source": f"{len(foods)} items",
        "grams": total_grams,
        **totals,
    }
    return nutrition_block(total_food)


def rda_progress(food: dict, rda: dict) -> str:
    """Show percentage of daily recommended intake with ASCII bars."""
    bar_width = 20
    lines = []

    target_cal = rda["calories"]
    lines.append(f"  Daily intake contribution ({target_cal} kcal target):")

    rows = [
        ("Calories", "kcal", rda["calories"], " kcal"),
        ("Protein", "protein", rda["protein_g"], "g"),
        ("Fat", "fat", rda["fat_g"], "g"),
        ("Carbs", "carbs", rda["carbs_g"], "g"),
        ("Fiber", "fiber", rda["fiber_g"], "g"),
    ]

    for label, key, daily, unit in rows:
        val = food.get(key)
        if val is None:
            pct = 0.0
        else:
            pct = (val / daily * 100) if daily > 0 else 0.0

        filled = min(int(pct / 100 * bar_width), bar_width)
        empty = bar_width - filled
        bar = "\u2588" * filled + "\u2591" * empty

        val_str = f"{val}{unit}" if val is not None else "\u2014"
        lines.append(f"  {label:9s} {bar}  {val_str:>10s}  ({pct:.1f}%)")

    return "\n".join(lines)


def format_error_rate_limit(retry_after: int) -> str:
    """Format rate limit error with upgrade instructions."""
    minutes = max(1, retry_after // 60)
    return (
        f"  Rate limit reached (USDA DEMO_KEY: 50 requests/day).\n"
        f"  Try again in {minutes} minutes, or upgrade in 30 seconds:\n"
        f"  \u2192 Get a free key: https://fdc.nal.usda.gov/api-key-signup\n"
        f"  \u2192 Then run: nutrition config set --usda-key YOUR_KEY"
    )


def trend_sparkline(days_data: list[dict], target_kcal: int) -> str:
    """ASCII bar chart of daily calorie intake for N days."""
    bar_width = 16
    lines = [f"  Last {len(days_data)} days (kcal):   target: {target_kcal}"]

    on_target_count = 0
    for day in days_data:
        try:
            day_name = datetime.fromisoformat(day["date"]).strftime("%a")
        except (ValueError, KeyError):
            day_name = "???"

        totals = day.get("totals") or {}
        kcal = totals.get("kcal") or 0

        pct = min(kcal / target_kcal, 1.0) if target_kcal and kcal else 0.0
        filled = int(pct * bar_width)
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)

        arrow = ""
        if kcal > target_kcal * 1.05:
            arrow = " \u2191"
        elif kcal > 0:
            on_target_count += 1

        kcal_str = str(int(kcal)) if kcal > 0 else "\u2014"
        lines.append(f"  {day_name:3s}  {bar}  {kcal_str}{arrow}")

    days_with_data = [d for d in days_data if (d.get("totals") or {}).get("kcal")]
    if days_with_data:
        avg = sum((d["totals"].get("kcal") or 0) for d in days_with_data) / len(days_with_data)
        lines.append(
            f"  Avg  {int(avg)} kcal/day \u00b7 {on_target_count}/{len(days_data)} days on target"
        )

    return "\n".join(lines)


def daily_summary(day_data: dict, label: str | None = None) -> str:
    """Format a single day's meal log as a readable summary."""
    date_key = day_data.get("date", "")
    totals = day_data.get("totals") or {}
    meals = day_data.get("meals") or []
    target_kcal = day_data.get("target_kcal", 2000) or 2000
    target_protein = day_data.get("target_protein", 50) or 50

    if label is None:
        label = date_key

    lines = [f"  {label}"]
    lines.append("  " + "\u2500" * 35)

    if not meals:
        lines.append("  No meals logged.")
        return "\n".join(lines)

    for meal in meals:
        kcal = meal.get("kcal")
        kcal_str = f"{kcal:.0f} kcal" if kcal is not None else "\u2014"
        lines.append(f"  {meal.get('time', '??:??')} \u00b7 {meal.get('food_name', '?')} \u00b7 {kcal_str}")

    lines.append("  " + "\u2500" * 35)
    total_kcal = totals.get("kcal") or 0
    total_protein = totals.get("protein") or 0
    pct = int(total_kcal / target_kcal * 100) if target_kcal else 0
    check = "\u2713" if day_data.get("target_met") else "\u2717"
    lines.append(f"  Total    : {total_kcal:.0f} / {target_kcal} kcal ({pct}%) {check}")
    lines.append(f"  Protein  : {total_protein:.1f}g  (target: {target_protein}g)")
    streak = day_data.get("streak_day")
    if streak:
        lines.append(f"  Streak   : {streak} days")

    return "\n".join(lines)


def week_summary(week_data: list[dict]) -> str:
    """Format a Mon–Sun weekly report."""
    lines = ["  Weekly Report"]
    lines.append("  " + "\u2500" * 35)

    days_with_data = [d for d in week_data if d.get("meals")]
    if not days_with_data:
        lines.append("  No meals logged this week.")
        return "\n".join(lines)

    target_kcal = (days_with_data[0].get("target_kcal") or 2000) if days_with_data else 2000
    days_on_target = sum(1 for d in week_data if d.get("target_met"))
    total_kcal_all = sum((d.get("totals") or {}).get("kcal") or 0 for d in week_data)
    avg_kcal = total_kcal_all / len(days_with_data) if days_with_data else 0

    for day in week_data:
        try:
            day_name = datetime.fromisoformat(day["date"]).strftime("%a %d")
        except (ValueError, KeyError):
            day_name = "???"
        kcal = (day.get("totals") or {}).get("kcal") or 0
        n_meals = len(day.get("meals") or [])
        if n_meals > 0:
            check = "\u2713" if day.get("target_met") else "\u2717"
        else:
            check = "\u2014"
        lines.append(f"  {day_name:6s}  {kcal:>6.0f} kcal  {check}")

    lines.append("  " + "\u2500" * 35)
    lines.append(f"  Avg: {avg_kcal:.0f} kcal/day \u00b7 {days_on_target}/{len(week_data)} days on target")

    best = max(days_with_data, key=lambda d: (d.get("totals") or {}).get("kcal") or 0)
    worst = min(days_with_data, key=lambda d: (d.get("totals") or {}).get("kcal") or 0)
    try:
        best_name = datetime.fromisoformat(best["date"]).strftime("%a")
        worst_name = datetime.fromisoformat(worst["date"]).strftime("%a")
    except (ValueError, KeyError):
        best_name = worst_name = "???"
    best_kcal = (best.get("totals") or {}).get("kcal") or 0
    worst_kcal = (worst.get("totals") or {}).get("kcal") or 0
    lines.append(
        f"  Best: {best_name} ({best_kcal:.0f} kcal) \u00b7 Worst: {worst_name} ({worst_kcal:.0f} kcal)"
    )

    streak = max((d.get("streak_day") or 0 for d in week_data), default=0)
    if streak > 0:
        lines.append(f"  Current streak: {streak} days")

    return "\n".join(lines)


def top_foods_table(foods: list[dict]) -> str:
    """Format top-foods list."""
    if not foods:
        return "  No foods logged yet."

    lines = ["  Top foods:"]
    lines.append("  " + "\u2500" * 40)
    for i, food in enumerate(foods, 1):
        avg_kcal = food["total_kcal"] / food["times"] if food["times"] else 0
        name = food["food_name"][:25]
        lines.append(f"  {i:2d}. {name:<25}  {food['times']}x  ~{avg_kcal:.0f} kcal avg")
    return "\n".join(lines)
