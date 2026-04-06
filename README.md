# nutrition-cli

CLI tool for nutrition data lookup, powered by [USDA FoodData Central](https://fdc.nal.usda.gov/) and [Open Food Facts](https://world.openfoodfacts.org/). Also ships as an [OpenClaw](https://github.com/openclaw) skill for AI-assisted nutrition queries.

## Install

### Via ClawHub (recommended for OpenClaw users)

```
claw install nutrition-cli
```

This installs both the CLI tool and the OpenClaw skill that lets your agent answer nutrition questions automatically.

### Via pip

```
pip install nutrition-cli
```

## Quick start

```bash
# Look up a food
nutrition search "chicken breast" --grams 200

# Scan a barcode
nutrition barcode 3017624010701

# Compare foods
nutrition compare "white rice" "brown rice" "quinoa"

# Calculate a meal
nutrition meal "200g chicken breast" "150g rice" "1 avocado" --rda

# Calories burned
nutrition burn running 30 --weight 70

# Daily targets
nutrition daily --sex female --age 25 --weight 60 --activity moderate
```

## Commands

| Command | Description |
|---------|-------------|
| `nutrition search QUERY` | Look up nutrition for any food |
| `nutrition barcode CODE` | Look up by barcode (EAN-8/13, UPC-A) |
| `nutrition compare FOOD1 FOOD2 ...` | Side-by-side comparison (2-5 foods) |
| `nutrition meal "Xg food" ...` | Sum nutrition across a meal |
| `nutrition burn ACTIVITY MINUTES` | Estimate calories burned |
| `nutrition daily` | Personalized daily intake targets |
| `nutrition config set` | Set API key or defaults |

All commands support `--format json` for machine-readable output and `--grams` for custom serving sizes.

## Rate limits

No API key is required. The tool uses USDA's `DEMO_KEY` (50 requests/day per IP) and Open Food Facts (unlimited, no key needed).

If you hit the USDA rate limit, get a free personal key in 30 seconds:

1. Sign up at https://fdc.nal.usda.gov/api-key-signup
2. Run: `nutrition config set --usda-key YOUR_KEY`

This raises your limit to 1,000 requests/hour.

## Data sources

- **USDA FoodData Central** — generic foods (SR Legacy, Foundation) and branded products. US government data, high quality.
- **Open Food Facts** — community-contributed product database with barcode lookup, Nutri-Score, NOVA classification, allergen data, and vegan/vegetarian status.

The CLI prefers USDA SR Legacy/Foundation results for generic food queries and falls back to Open Food Facts automatically.

## License

MIT
