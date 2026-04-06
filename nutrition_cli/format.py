"""All output formatting. Returns strings — never prints directly."""


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
