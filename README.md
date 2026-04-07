# nutrition-pro

> The AI nutrition coach that actually gets to know you.

Just say what you ate. No grams required. **nutrition-pro** figures out the portion, looks it up against USDA and Open Food Facts data, and logs it — all from your terminal. The longer you use it, the better it knows you.

---

## What makes it different

Most nutrition trackers are glorified spreadsheets. nutrition-pro is an agent with memory.

- **Remembers your meals** — log chicken and rice 3 times and it never asks you about the portion again. It saves your confirmed weight and uses it forever.
- **Builds a picture of you** — every Sunday it reads your week and rewrites a synthesized profile: your patterns, your weak spots, when you tend to skip meals, how weekends affect your numbers.
- **Knows your why** — you tell it your goal in plain English ("lose 8kg before my sister's wedding") and it frames every summary and check-in through that lens.
- **Smart portion guessing** — say "I had chicken and broccoli" and it offers three calorie options (light / regular / large) with its best guess marked. Restaurant meal? It tries branded data first, then estimates by dish type.
- **Proactive check-ins via cron** — morning summary, evening log, weekly digest. It checks in with you, not the other way around.
- **Respects real life** — tell it you're traveling, sick, or it's a holiday weekend and it won't flag your calories as failures or break your streak.

---

## Install

### Via ClawHub (recommended — includes the AI skill)

```
claw install nutrition-pro
```

Installs the CLI and the OpenClaw skill. Your AI agent will automatically handle nutrition questions, log meals from conversation, and set up proactive reminders.

### Via pip (CLI only)

```
pip install nutrition-cli
```

---

## Quick start

```bash
# Look up a food
nutrition search "chicken breast" --grams 200

# Scan a barcode
nutrition barcode 3017624010701

# Log a meal
nutrition log "salmon fillet" --grams 180

# Today's summary
nutrition summary

# Weekly report
nutrition summary --week

# Compare foods
nutrition compare "white rice" "brown rice" "quinoa"

# Calculate a full meal
nutrition meal "200g chicken breast" "150g rice" "1 avocado" --rda

# Calories burned
nutrition burn running 30 --weight 70

# Trends
nutrition trend --days 14
nutrition top-foods --days 30

# Daily targets
nutrition daily --sex female --age 25 --weight 60 --activity moderate
```

---

## Commands

| Command | Description |
|---|---|
| `nutrition search QUERY` | Look up any food — USDA + Open Food Facts |
| `nutrition barcode CODE` | Look up by barcode (EAN-8/13, UPC-A) |
| `nutrition log FOOD` | Log a meal to your daily tracker |
| `nutrition summary` | Today's totals vs. your target |
| `nutrition summary --week` | Full week breakdown |
| `nutrition trend --days N` | Calorie trend over time |
| `nutrition top-foods --days N` | Most-logged foods |
| `nutrition compare FOOD1 FOOD2` | Side-by-side macro comparison |
| `nutrition meal "Xg food" ...` | Sum nutrition across a meal |
| `nutrition burn ACTIVITY MINS` | Estimate calories burned |
| `nutrition daily` | Personalized daily intake targets |
| `nutrition config set` | Set calorie target, protein goal, API key |
| `nutrition config status` | Check if configured |

All commands support `--format json` and `--grams` for custom serving sizes.

---

## Memory system (AI skill)

When used as an OpenClaw skill, nutrition-pro maintains a persistent memory across sessions:

**What it remembers:**
- Your goal — in your own words
- Your calorie and macro targets
- Food intolerances and preferences it picks up from conversation
- Trusted meals with their confirmed weights (never asks twice)
- Your actual meal timing (updates if your habits drift from what you said)
- Lifecycle events — travel, illness, holidays — so deviations aren't penalized

**What it learns over time:**
- Weekly pattern synthesis every Sunday: which days you skip meals, how weekends affect your numbers, whether you hit protein on training vs. rest days
- A "Who you are" paragraph it rewrites as its understanding deepens
- Calorie and timing drift — it updates your profile to match reality, not the plan

**Proactive cron jobs (set up during onboarding):**
- Morning summary — yesterday's totals, current streak, one insight
- Evening check-in — asks what you ate, logs it, shows today's total
- Weekly digest — every Monday, framed through your personal goal
- Sunday synthesis — silent background job that rewrites your profile and patterns

---

## Data sources

- **USDA FoodData Central** — generic and branded foods. Government data, high quality.
- **Open Food Facts** — barcode lookup, Nutri-Score, NOVA group, allergens, vegan/vegetarian status.

The CLI prefers USDA SR Legacy/Foundation for generic queries and falls back to Open Food Facts automatically. Source is always shown so you know where the data came from.

---

## Rate limits

No API key required to start. Uses USDA's `DEMO_KEY` (50 requests/day per IP). For heavier use, get a free personal key in 30 seconds:

1. Sign up at [fdc.nal.usda.gov/api-key-signup](https://fdc.nal.usda.gov/api-key-signup)
2. Run: `nutrition config set --usda-key YOUR_KEY`

Raises your limit to 1,000 requests/hour.

---

## License

MIT
