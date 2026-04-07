"""CLI entrypoint for nutrition-cli."""

import json
import re

import click

from . import config, format, log as log_module, search
from .rda import MET_TABLE, get_rda
from .usda import RateLimitError


@click.group()
def cli():
    """Nutrition data lookup from USDA and Open Food Facts."""


# --- config ---


@cli.group("config")
def config_cmd():
    """Manage nutrition-cli configuration."""


@config_cmd.command("set")
@click.option("--usda-key", default=None, help="Personal USDA FoodData Central API key.")
@click.option("--default-grams", default=None, type=float, help="Default serving size in grams.")
@click.option("--kcal", default=None, type=int, help="Daily calorie target.")
@click.option("--protein", default=None, type=int, help="Daily protein goal in grams.")
@click.option("--timezone", default=None, help="Timezone string (e.g. UTC, America/New_York).")
@click.option("--start-date", default=None, help="Tracking start date (YYYY-MM-DD).")
def config_set(usda_key, default_grams, kcal, protein, timezone, start_date):
    """Save configuration values."""
    if not any([usda_key, default_grams, kcal, protein, timezone, start_date]):
        data = config.load_config()
        has_key = "usda_key" in data
        click.echo(f"  USDA key : {'configured' if has_key else 'not set (using DEMO_KEY)'}")
        click.echo(f"  Default g: {data.get('default_grams', 100)}")
        if "kcal" in data:
            click.echo(f"  Calories : {data['kcal']} kcal/day")
        if "protein" in data:
            click.echo(f"  Protein  : {data['protein']}g/day")
        return

    if usda_key is not None:
        config.set("usda_key", usda_key)
        click.echo("  USDA API key saved.")
    if default_grams is not None:
        config.set("default_grams", default_grams)
        click.echo(f"  Default serving size set to {default_grams}g.")
    if kcal is not None:
        config.set("kcal", kcal)
        click.echo(f"  Daily calorie target set to {kcal} kcal.")
    if protein is not None:
        config.set("protein", protein)
        click.echo(f"  Daily protein goal set to {protein}g.")
    if timezone is not None:
        config.set("timezone", timezone)
        click.echo(f"  Timezone set to {timezone}.")
    if start_date is not None:
        config.set("start_date", start_date)
        click.echo(f"  Tracking start date set to {start_date}.")


@config_cmd.command("status")
def config_status():
    """Return 'Configured' if a nutrition profile exists, else 'Not configured'."""
    data = config.load_config()
    if "kcal" in data:
        click.echo("Configured")
    else:
        click.echo("Not configured")


@config_cmd.command("show")
def config_show():
    """Show full current nutrition profile."""
    data = config.load_config()
    if "kcal" not in data:
        click.echo("  No nutrition profile set up.")
        click.echo("  Run: nutrition config set --kcal 2000 --protein 150")
        return

    click.echo("  Nutrition profile")
    click.echo("  " + "\u2500" * 35)
    click.echo(f"  Daily calories : {data.get('kcal')} kcal")
    click.echo(f"  Protein goal   : {data.get('protein', '\u2014')}g/day")
    click.echo(f"  Default grams  : {data.get('default_grams', 100)}g")
    click.echo(f"  Timezone       : {data.get('timezone', '\u2014')}")
    click.echo(f"  Tracking since : {data.get('start_date', '\u2014')}")
    click.echo(f"  USDA key       : {'configured' if data.get('usda_key') else 'using DEMO_KEY'}")


# --- search ---


@cli.command("search")
@click.argument("query")
@click.option("--grams", "-g", default=None, type=float, help="Serving size in grams.")
@click.option("--format", "fmt", type=click.Choice(["summary", "json"]), default="summary")
@click.option("--rda", "show_rda", is_flag=True, help="Show daily intake percentage.")
@click.option("--sex", type=click.Choice(["male", "female"]), default="male")
@click.option("--age", type=int, default=30)
def search_cmd(query, grams, fmt, show_rda, sex, age):
    """Look up nutrition data for a food."""
    if grams is None:
        grams = config.get("default_grams", 100)

    try:
        result = search.lookup(query, grams)
    except RateLimitError as e:
        click.echo(format.format_error_rate_limit(e.retry_after), err=True)
        raise SystemExit(1)

    if fmt == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(format.nutrition_block(result))
        if show_rda:
            rda = get_rda(sex, age)
            click.echo()
            click.echo(format.rda_progress(result, rda))



# --- barcode ---


@cli.command()
@click.argument("barcode")
@click.option("--grams", "-g", default=None, type=float, help="Serving size in grams.")
@click.option("--format", "fmt", type=click.Choice(["summary", "json"]), default="summary")
def barcode(barcode, grams, fmt):
    """Look up a product by barcode (EAN-8/EAN-13/UPC-A)."""
    if grams is None:
        grams = config.get("default_grams", 100)

    from . import openfoodfacts
    product = openfoodfacts.get_by_barcode(barcode)
    if product is None:
        raise click.ClickException(
            f"Barcode '{barcode}' not found in Open Food Facts. "
            "Try searching by name: nutrition search <name>"
        )

    result = openfoodfacts.parse_product(product, grams)

    if fmt == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(format.nutrition_block(result))


# --- compare ---


@cli.command()
@click.argument("foods", nargs=-1, required=True)
@click.option("--grams", "-g", default=None, type=float, help="Serving size in grams.")
@click.option("--format", "fmt", type=click.Choice(["summary", "json"]), default="summary")
def compare(foods, grams, fmt):
    """Compare nutrition data for 2-5 foods."""
    if len(foods) < 2:
        raise click.ClickException("Provide at least 2 foods to compare.")
    if len(foods) > 5:
        raise click.ClickException("Compare supports up to 5 foods.")

    if grams is None:
        grams = config.get("default_grams", 100)

    try:
        results = search.lookup_multi(list(foods), grams)
    except RateLimitError as e:
        click.echo(format.format_error_rate_limit(e.retry_after), err=True)
        raise SystemExit(1)

    if fmt == "json":
        click.echo(json.dumps(results, indent=2))
    else:
        click.echo(format.compare_table(results))


# --- meal ---


def _parse_meal_arg(arg: str, default_grams: float) -> tuple[str, float]:
    """Parse '200g chicken' into (query, grams). Falls back to default_grams."""
    m = re.match(r"^(\d+\.?\d*)\s*g\s+(.+)$", arg, re.IGNORECASE)
    if m:
        return m.group(2), float(m.group(1))
    return arg, default_grams


@cli.command()
@click.argument("items", nargs=-1, required=True)
@click.option("--grams", "-g", default=None, type=float, help="Default serving size in grams.")
@click.option("--rda", "show_rda", is_flag=True, help="Show daily intake percentage.")
@click.option("--format", "fmt", type=click.Choice(["summary", "json"]), default="summary")
@click.option("--sex", type=click.Choice(["male", "female"]), default="male")
@click.option("--age", type=int, default=30)
def meal(items, grams, show_rda, fmt, sex, age):
    """Calculate nutrition for a full meal. Use '200g chicken' syntax for portions."""
    if grams is None:
        grams = config.get("default_grams", 100)

    results = []
    errors = []
    for item in items:
        query, item_grams = _parse_meal_arg(item, grams)
        try:
            results.append(search.lookup(query, item_grams))
        except RateLimitError as e:
            click.echo(format.format_error_rate_limit(e.retry_after), err=True)
            raise SystemExit(1)
        except click.ClickException as e:
            errors.append(f"  - {query}: {e.format_message()}")

    if errors:
        click.echo("Some lookups failed:", err=True)
        for err in errors:
            click.echo(err, err=True)

    if not results:
        raise click.ClickException("No foods could be looked up.")

    if fmt == "json":
        click.echo(json.dumps(results, indent=2))
    else:
        for r in results:
            click.echo(format.nutrition_block(r))
            click.echo()
        click.echo(format.meal_summary(results))
        if show_rda:
            # Build combined food dict for RDA
            keys = ["kcal", "protein", "fat", "carbs", "fiber"]
            combined = {}
            for key in keys:
                values = [r.get(key) for r in results if r.get(key) is not None]
                combined[key] = round(sum(values), 1) if values else None
            rda = get_rda(sex, age)
            click.echo()
            click.echo(format.rda_progress(combined, rda))


# --- burn ---


@cli.command()
@click.argument("activity")
@click.argument("duration", type=float)
@click.option("--weight", "-w", default=None, type=float, help="Body weight in kg.")
def burn(activity, duration, weight):
    """Estimate calories burned for an activity."""
    if weight is None:
        weight = config.get("default_weight", 75)

    activity_lower = activity.lower()
    met = MET_TABLE.get(activity_lower)
    if met is None:
        available = ", ".join(sorted(MET_TABLE.keys()))
        raise click.ClickException(
            f"Unknown activity '{activity}'. Available: {available}"
        )

    calories = round(met * weight * (duration / 60), 1)
    click.echo(f"  {activity.capitalize()} for {duration:.0f} min ({weight}kg)")
    click.echo(f"  Estimated burn: {calories} kcal")

    # Show equivalent in another activity
    walking_met = MET_TABLE["walking"]
    walking_min = round(calories / (walking_met * weight) * 60, 0)
    click.echo(f"  Equivalent to {walking_min:.0f} min of walking")


# --- daily ---


@cli.command()
@click.option("--sex", type=click.Choice(["male", "female"]), default="male")
@click.option("--age", type=int, default=30)
@click.option("--weight", "-w", type=float, default=75, help="Body weight in kg.")
@click.option("--height", type=float, default=175, help="Height in cm.")
@click.option(
    "--activity",
    type=click.Choice(["sedentary", "light", "moderate", "active"]),
    default="moderate",
)
def daily(sex, age, weight, height, activity):
    """Show recommended daily nutrition intake (Harris-Benedict TDEE)."""
    # Harris-Benedict BMR
    if sex == "male":
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
    }
    tdee = round(bmr * multipliers[activity])

    # Macro split: 30% protein, 25% fat, 45% carbs
    protein_g = round(tdee * 0.30 / 4, 1)
    fat_g = round(tdee * 0.25 / 9, 1)
    carbs_g = round(tdee * 0.45 / 4, 1)

    rda = get_rda(sex, age)
    fiber_g = rda["fiber_g"]

    click.echo(f"  Daily targets ({sex}, age {age}, {weight}kg, {height}cm, {activity}):")
    click.echo(f"  {'=' * 40}")
    click.echo(f"  Calories : {tdee} kcal")
    click.echo(f"  Protein  : {protein_g}g")
    click.echo(f"  Fat      : {fat_g}g")
    click.echo(f"  Carbs    : {carbs_g}g")
    click.echo(f"  Fiber    : {fiber_g}g")


# --- log ---


@cli.command("log")
@click.argument("food", required=False, default=None)
@click.option("--grams", "-g", default=None, type=float, help="Serving size in grams.")
@click.option("--check-today", is_flag=True, help="Print number of meals logged today.")
@click.option("--update-streak", "do_update_streak", is_flag=True, help="Update and print streak counter.")
@click.option("--check-yesterday", is_flag=True, help="Print 'true' if meals were logged yesterday.")
def log_cmd(food, grams, check_today, do_update_streak, check_yesterday):
    """Log a meal or query today's log status."""
    if check_today:
        click.echo(str(log_module.check_today()))
        return

    if check_yesterday:
        click.echo("true" if log_module.check_yesterday() else "false")
        return

    if do_update_streak:
        click.echo(str(log_module.update_streak()))
        return

    if food is None:
        raise click.ClickException(
            "Provide a food name to log, or use --check-today / --check-yesterday / --update-streak."
        )

    if grams is None:
        grams = config.get("default_grams", 100)

    try:
        result = search.lookup(food, grams)
    except RateLimitError as e:
        click.echo(format.format_error_rate_limit(e.retry_after), err=True)
        raise SystemExit(1)

    day_data = log_module.add_meal(result, food, grams)
    totals = day_data["totals"]
    target_kcal = day_data["target_kcal"]
    meals_count = len(day_data["meals"])

    click.echo(f"  Logged: {result['name']} ({grams:.0f}g)")
    kcal = result.get("kcal")
    if kcal is not None:
        running = totals.get("kcal") or 0
        click.echo(
            f"  {kcal:.0f} kcal  |  Running total: {running:.0f} / {target_kcal} kcal"
            f"  ({meals_count} meal{'s' if meals_count != 1 else ''} today)"
        )


# --- summary ---


@cli.command("summary")
@click.option("--today", "mode", flag_value="today", default=True, help="Show today's log.")
@click.option("--yesterday", "mode", flag_value="yesterday", help="Show yesterday's log.")
@click.option("--week", "mode", flag_value="week", help="Show current Mon–Sun week.")
@click.option("--date", "date_str", default=None, metavar="YYYY-MM-DD", help="Show a specific date.")
@click.option("--days", "num_days", default=None, type=int, metavar="N", help="Show last N days as sparkline.")
def summary_cmd(mode, date_str, num_days):
    """Show nutrition summary for today, yesterday, a week, or a date range."""
    if date_str:
        day_data = log_module.get_day_summary(date_str)
        if day_data is None:
            raise click.ClickException(f"No data logged for {date_str}.")
        click.echo(format.daily_summary({"date": date_str, **day_data}))
        return

    if num_days is not None:
        days_data = log_module.get_date_range_summaries(num_days)
        target_kcal = config.get("kcal", 2000)
        click.echo(format.trend_sparkline(days_data, target_kcal))
        return

    if mode == "week":
        click.echo(format.week_summary(log_module.get_week_summary()))
        return

    if mode == "yesterday":
        key = log_module.yesterday_key()
        day_data = log_module.get_day_summary(key)
        if day_data is None:
            click.echo("  No meals logged yesterday.")
            return
        click.echo(format.daily_summary({"date": key, **day_data}, label="Yesterday"))
        return

    # default: today
    key = log_module.today_key()
    day_data = log_module.get_day_summary(key)
    if day_data is None:
        click.echo("  No meals logged today.")
        return
    click.echo(format.daily_summary({"date": key, **day_data}, label="Today"))


# --- trend ---


@cli.command("trend")
@click.option("--days", default=7, type=int, show_default=True, help="Number of days to show.")
def trend_cmd(days):
    """Show calorie intake trend as ASCII sparkline."""
    days_data = log_module.get_date_range_summaries(days)
    target_kcal = config.get("kcal", 2000)
    click.echo(format.trend_sparkline(days_data, target_kcal))


# --- top-foods ---


@cli.command("top-foods")
@click.option("--days", default=30, type=int, show_default=True, help="Look-back window in days.")
def top_foods_cmd(days):
    """List the most frequently logged foods."""
    foods = log_module.get_top_foods(days)
    click.echo(format.top_foods_table(foods))


if __name__ == "__main__":
    cli()
