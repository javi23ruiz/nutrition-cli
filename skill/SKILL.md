---
name: nutrition-cli
description: >
  Use this skill when the user asks about nutrition, calories, macros,
  protein, fat, carbohydrates, fiber, sugar, or any food-related health
  question. Trigger on: food names ("calories in chicken"), packaged
  products ("nutella nutrition facts"), barcodes (8-13 digit numbers),
  meal questions ("macros for my lunch"), comparisons ("which has more
  protein, beef or tofu?"), calorie burn ("how many calories does running
  burn?"), or daily intake questions ("what should my daily protein be?").
  Also triggers on: "is this vegan?", "allergens in X", "nutri-score of X",
  "how processed is X", "what are the macros in X".
metadata:
  clawdbot:
    emoji: "🥗"
    requires:
      bins: ["nutrition"]
    install:
      - id: pip
        kind: pip
        package: nutrition-cli
        bins: ["nutrition"]
        label: "Install nutrition-cli (pip)"
---

# nutrition-cli

Look up nutrition data for any food, compare foods, calculate meal macros, estimate calorie burn, and check daily intake targets — all from the command line.

## Setup (optional — works without this)

The skill works immediately with no configuration. If you ever see a rate limit error, upgrade in 30 seconds:

1. Get a free key: https://fdc.nal.usda.gov/api-key-signup
2. Run: `nutrition config set --usda-key YOUR_KEY`

## Commands

### Search for a food

**When to use:** The user asks about nutrition info, calories, protein, fat, carbs, or macros for a specific food.

```bash
nutrition search "chicken breast" --grams 200
nutrition search "brown rice" --grams 150 --format json
nutrition search "avocado" --rda --sex female --age 25
```

- `--grams` (default 100): serving size
- `--format summary|json`: use `json` when you need to process the output programmatically, `summary` when displaying to the user
- `--rda`: show percentage of daily recommended intake
- `--sex male|female` and `--age`: adjust RDA targets (default: male, 30)

### Look up by barcode

**When to use:** The user provides a barcode number (8-13 digits), asks about a specific packaged product by barcode, or wants to scan a product.

```bash
nutrition barcode 3017624010701
nutrition barcode 5000159459228 --grams 50
```

- Returns Nutri-Score, NOVA group, allergens, and vegan/vegetarian status
- If not found, suggest using `nutrition search` by name instead

### Compare foods

**When to use:** The user asks which food has more/less of a nutrient, or wants to compare two or more foods side by side.

```bash
nutrition compare "chicken breast" "tofu" "salmon"
nutrition compare "white rice" "brown rice" --grams 200
```

- Accepts 2-5 food names or barcodes (can mix both)
- Shows an aligned table with all key nutrients

### Calculate meal nutrition

**When to use:** The user describes a meal with multiple foods, asks about total macros for a combination of foods, or wants to know the nutrition of their lunch/dinner/breakfast.

```bash
nutrition meal "200g chicken breast" "150g brown rice" "1 avocado"
nutrition meal "200g chicken" "100g rice" --rda --sex female
```

- Use `Xg food` syntax to specify per-item portions (e.g., `"200g chicken"`)
- Items without a gram prefix use the `--grams` default (100g)
- Shows each item's breakdown plus a meal total

### Estimate calorie burn

**When to use:** The user asks how many calories an activity burns, or wants to know exercise equivalents.

```bash
nutrition burn running 30
nutrition burn cycling 45 --weight 80
```

- `ACTIVITY`: one of running, jogging, cycling, walking, swimming, hiking, rowing, jump rope, dancing, yoga, pilates, weightlifting, climbing, tennis, basketball, soccer, volleyball, skiing, skateboarding, elliptical
- `DURATION`: minutes
- `--weight`: body weight in kg (default 75)

### Show daily targets

**When to use:** The user asks what their daily calorie or macro intake should be, or wants personalized nutrition targets.

```bash
nutrition daily --sex female --age 25 --weight 60 --height 165 --activity moderate
nutrition daily --activity active
```

- Uses Harris-Benedict formula for TDEE
- Shows recommended calories, protein, fat, carbs, and fiber

### Configuration

**When to use:** The user wants to set their USDA API key or change defaults.

```bash
nutrition config set --usda-key YOUR_KEY
nutrition config set --default-grams 150
nutrition config set  # shows current config status
```

## Output format guidance

- Use `--format json` when you need to process the output programmatically (e.g., to do your own calculations or comparisons with more than 5 items).
- Use `--format summary` (default) when displaying results directly to the user.

## Rate limit handling

When you see a rate limit error message from the CLI, you **must surface the upgrade instructions to the user exactly as printed** — do not paraphrase or retry silently. The error message contains the exact URL and steps the user needs.

## Data source transparency

Always mention whether data came from **USDA** or **Open Food Facts** when presenting results to the user, so they know the source and can judge reliability. The source is included in the `summary` output and in the `source` field of `json` output.
