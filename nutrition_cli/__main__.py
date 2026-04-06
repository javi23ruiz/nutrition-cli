"""CLI entrypoint for nutrition-cli."""

import json
import re

import click

from . import config, format, search
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
def config_set(usda_key, default_grams):
    """Save configuration values."""
    if usda_key is None and default_grams is None:
        # Show current config status
        data = config.load_config()
        has_key = "usda_key" in data
        grams = data.get("default_grams", 100)
        click.echo(f"  USDA key : {'configured' if has_key else 'not set (using DEMO_KEY)'}")
        click.echo(f"  Default g: {grams}")
        return

    if usda_key is not None:
        config.set("usda_key", usda_key)
        click.echo("  USDA API key saved.")
    if default_grams is not None:
        config.set("default_grams", default_grams)
        click.echo(f"  Default serving size set to {default_grams}g.")


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


if __name__ == "__main__":
    cli()
