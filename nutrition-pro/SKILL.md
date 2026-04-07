---
name: nutrition-pro
description: >
  The AI nutrition coach that actually gets to know you. Just say what you ate
  — nutrition-pro figures out the portion, looks it up, and logs it. No grams
  required. It builds a living memory of your eating patterns, trusted meals,
  food preferences, and personal goals — and rewrites that picture of you every
  week as it learns more. Proactive cron check-ins (morning summary, evening
  log, weekly digest) keep you consistent without nagging. Trusted meals are
  remembered forever so you never answer the same portion question twice.
  Powered by USDA + Open Food Facts. Barcode scanning, food comparison, calorie
  burn estimates, and macro tracking included. No app. No account. No BS — just
  your terminal and a coach that pays attention. Triggers on: food names, meal
  logging ("I just had X", "log my lunch"), nutrition questions ("how many
  calories in X", "macros for Y"), diet setup ("track my calories", "help me
  eat better"), barcode scans (8-13 digit numbers), and daily/weekly summaries.
  Also triggers when the user casually mentions food in passing.
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
        label: "Install nutrition-pro (pip)"
---

# nutrition-pro

Look up nutrition data for any food, log meals, track daily intake against your goals, compare foods, estimate calorie burn, and view trends — all from the command line.

---

## First run

On the very first message that triggers this skill, check if nutrition tracking is configured:

Run: `nutrition config status`

If output is "Not configured":
  Read and follow `nutrition-pro/ONBOARDING.md` exactly.

If output is "Configured":
  Continue normally. Do not re-run onboarding.

---

## Logging meals

**Triggers:** "I had X", "I ate X", "just had X", "log X", "add X to my food log",
any food mentioned in passing.

Steps:

### Step 1 — Extract food and resolve portion

Extract food name(s) from the message. Then determine grams using the priority order below:

**A. Explicit weight → use it directly**
- "200g chicken breast" → grams=200
- "half a kilo of pasta" → grams=500

**B. Countable units → map to grams**

| What user says | Estimated grams |
|---|---|
| 1 egg / 2 eggs / 3 eggs | 55g / 110g / 165g |
| 1 slice bread | 30g |
| 1 cup rice (cooked) | 200g |
| 1 bowl rice / pasta | 250g |
| 1 banana / apple / orange | 120g / 180g / 150g |
| 1 glass milk | 240g |
| 1 tablespoon olive oil | 14g |
| 1 handful nuts | 30g |

**C. Portion language → map to gram range, then ask**

When the user says "some", "a bit of", "a little", or gives no quantity at all,
map to three tiers and ask before logging:

| Tier | Typical serving | Use when |
|---|---|---|
| Light | ~60–80% of standard | "a small X", "a little X", "just had some X" |
| Regular | 100% standard portion | no modifier given |
| Large | ~130–150% of standard | "a big X", "a lot of X", "a huge plate of X" |

Standard reference portions (grams):
- Chicken breast: 120g / 180g / 250g
- Fish fillet: 100g / 150g / 200g
- Red meat (steak, beef): 120g / 180g / 250g
- Cooked pasta / rice: 150g / 220g / 300g
- Salad (no protein): 100g / 200g / 350g
- Soup / stew: 200g / 350g / 500g
- Bread / roll: 30g / 60g / 90g
- Vegetables (side): 60g / 120g / 200g
- Fruit: 80g / 150g / 250g

When tier is ambiguous, present the three options with calorie estimates and let
the user pick:

> "Chicken breast — which is closest?
>  • Light (~120g): ~200 kcal
>  • Regular (~180g): ~300 kcal ← my guess
>  • Large (~250g): ~415 kcal
>  Or tell me the weight if you know it."

Mark your guess as ← my guess based on meal context (time of day, whether it's
a main or side). Wait for the user to confirm or correct before logging.

**D. Restaurant / eating out → use branded data or meal bracket**

Detect restaurant context from phrases like: "went to", "ordered", "ate out",
"takeaway", "delivery", "at [restaurant name]".

1. Try `nutrition search "{dish or brand name}" --format json` first.
   Open Food Facts often has branded and restaurant items.

2. If found with good confidence → show result, flag as `(restaurant estimate)`,
   ask to confirm.

3. If not found or confidence is low → use meal bracket:

| Meal type | Calorie bracket |
|---|---|
| Light dish (salad, soup, sushi) | 300–500 kcal |
| Regular main (pasta, burger, rice dish) | 600–900 kcal |
| Heavy main (pizza, ribs, fried food) | 900–1,400 kcal |

Present the bracket to the user:
> "I couldn't find exact data for that restaurant dish. Based on a typical
>  [meal type], I'd estimate around [LOW]–[HIGH] kcal. Want me to log
>  [MID] kcal as an estimate? You can adjust the number."

Always append `(estimated)` to the food name when logging uncertain portions:
`nutrition log "chicken tikka masala (estimated)" --grams 400`

---

### Step 2 — Look up and confirm

Use the following priority order. Only call the API when necessary.

**Priority 1 — Trusted meals (zero API calls)**
Check MEMORY.md `## Trusted meals` first. If the food name matches a saved meal,
use the stored values directly. Skip all other steps and go straight to Step 3.

**Priority 2 — Agent knowledge (zero API calls)**
Use this for whole, unprocessed, or common foods where macro profiles are
well-established:
- Meats: chicken breast, beef, pork, fish, eggs
- Grains: rice, pasta, oats, bread, quinoa
- Vegetables and fruits (all common ones)
- Dairy: milk, yogurt, cheese
- Legumes: lentils, chickpeas, beans
- Nuts and seeds

For these foods, compute calories from standard macro data (e.g. cooked chicken
breast ≈ 165 kcal/100g, 31g protein, 3.6g fat, 0g carbs). Scale to the resolved
grams. Label source as `(agent estimate)`.

**Priority 3 — API lookup (use for branded and packaged foods)**
Use `nutrition search` only when:
- The food is branded or packaged (e.g. "Activia yogurt", "Häagen-Dazs ice cream")
- The user names a specific restaurant dish and wants verified data
- The food is processed or composite and macros are genuinely uncertain

Run: `nutrition search "{FOOD}" --grams {GRAMS} --format json`

**Priority 4 — API fallback (rate limit or error)**
If the API call fails with a rate limit error or any error response:
- Fall back immediately to agent knowledge
- Label as `(estimated — API unavailable)`
- Do NOT tell the user the API failed unless they ask; just present the estimate naturally

Show a clean summary regardless of source:
> **{FOOD_NAME}** · {GRAMS}g
> {KCAL} kcal · Protein {P}g · Fat {F}g · Carbs {C}g
> Source: {USDA|Open Food Facts|agent estimate}

Ask: "Should I log this?" — wait for confirmation before writing.
If the user corrects the weight or portion, recompute or re-run search with the new grams.

---

### Step 3 — Log

On confirmation: `nutrition log "{FOOD}" --grams {GRAMS}`

For multi-food meals ("chicken, rice, and broccoli"), resolve each food's portion
separately in one message, then log each with a single confirmation:
> "Here's what I've got:
>  • Chicken breast (~180g): 300 kcal
>  • Brown rice (~200g): 220 kcal
>  • Broccoli (~120g): 42 kcal
>  Total: ~562 kcal · P: 58g · F: 8g · C: 45g
>  Log all three?"

---

### Step 4 — Write to daily memory note

Append one line to today's daily memory note (memory/YYYY-MM-DD.md):
```
- {TIME} · {FOOD_NAME}{estimated_flag} · {KCAL} kcal (P:{P}g F:{F}g C:{C}g)
```
Then update running total:
```
**Running total: {TOTAL_KCAL} / {TARGET} kcal**
```

For estimated entries, use `~` prefix on calories: `~562 kcal`

This write is mandatory — it's what makes "what have I eaten today?" instant.

---

### Step 5 — Check for patterns (see Learning section below)

**Memory note:** Only write nutrition data to MEMORY.md and memory/ files in private/DM
sessions. In group contexts, skip the memory write step and log only to log.json.

---

## Answering questions without API calls

Use the cheapest source that can answer the question. Check in order:

### 1. Already in context (no tool call needed)
- "How many calories today?" / "What did I eat today?" / "What did I have for lunch?"
  → Read today's memory/YYYY-MM-DD.md — running total and all meals are already there
- "What's my target?" / "Am I on track today?"
  → Read MEMORY.md nutrition profile, compute from daily note total vs target
- "How many meals today?"
  → Run: `nutrition log --check-today`

### 2. Semantic / fuzzy recall (memory_search, no CLI call)
- "What did I eat last Tuesday?" / "What did I have on [specific date]?"
  → Search memory/YYYY-MM-DD.md for that date and read it directly
- "That pasta dish I made last month" / "The meal I had after the gym"
  → Run: `memory_search "{phrase}"` across memory/ daily notes — do NOT call the CLI

### 3. Structured math or trends (CLI reads log.json)
- "Average calories last 30 days" → `nutrition summary --days 30`
- "What's my protein been like this week?" → `nutrition summary --week`
- "Show me my trend" → `nutrition trend --days 14`
- "How many times have I had chicken?" → `nutrition top-foods --days 90`
- Historical date query → `nutrition summary --date YYYY-MM-DD`
- Weekly report → `nutrition summary --week`

### 4. New data only (USDA API call via CLI)
- Food lookup → `nutrition search "{FOOD}" --grams {GRAMS} --format json`
- Barcode → `nutrition barcode {CODE}`

Never jump to step 3 or 4 if step 1 or 2 can answer it.

---

## What to learn and when to write it

Write silently — do not announce "I've updated your memory." Update memory when you
observe patterns. Do not wait to be asked.

The one exception: when rewriting "Who you are" or "Patterns", say one sentence
so the user feels seen, not surveilled. Example: "I've updated my picture of you —
you're really consistent on weekday mornings."

---

### Who you are
Trigger: end of every Sunday, or after 7+ days of data since last rewrite.

Action: read the past 4 weeks of memory/YYYY-MM-DD.md daily notes + MEMORY.md.
Synthesize into one paragraph (3–5 sentences) that captures:
- Demographics / diet type / intolerances (from profile)
- Primary goal and why (from goal narrative)
- Eating patterns and personality (from logs)
- Current streak and consistency

Rewrite the `## Who you are` section in MEMORY.md in full. Do not append — replace.

Read this section at the start of every session. Use it to frame tone, suggestions,
and feedback without the user having to re-explain themselves.

---

### Goal narrative
Trigger: onboarding step 2, or any time the user says why they're tracking
("I want to lose X", "I'm trying to build muscle", "my doctor told me to", etc.)

Action: write one sentence in their words (not a paraphrase) to
`## Goal narrative` in MEMORY.md. Update it if they ever restate a new goal.

Use this to frame every weekly summary and every time they're discouraged.
Example: if goal is "lose 8kg before September", lead weekly summaries with
progress toward that, not generic calorie math.

---

### Trusted meals
Trigger: the same meal (same food name or very similar) is logged 3+ times
with a confirmed gram weight.

Action: add a row to the `## Trusted meals` table in MEMORY.md:
```
| {MEAL_NAME} | {GRAMS_DESCRIPTION} | {KCAL} | {P}g | {F}g | {C}g | {N}x |
```

When a meal is in the trusted meals table:
- Skip the portion-guessing flow entirely
- Skip the search + confirm step
- Log immediately and say:
  > "{MEAL_NAME} — logged {GRAMS} like usual. {KCAL} kcal."
- Update the `Times logged` count in the table after each log

If the user corrects the weight ("actually I had more today"), log with the
corrected weight but keep the trusted default unchanged unless they say
"update my usual" or "save this as my new default."

---

### Patterns
Trigger: every Sunday (same trigger as "Who you are" rewrite).

Action: read the past 4 weeks of daily notes. Look for:
- Days of the week where logging is skipped most often
- Weekend vs. weekday calorie delta
- Macro compliance by day type (training vs. rest, weekday vs. weekend)
- Meals that are frequently missed (e.g. dinner rarely logged)
- Underrating or overrating patterns relative to target
- Any correlation with lifecycle events (travel, stress mentions)

Rewrite the `## Patterns` section in MEMORY.md in full. 4–7 bullet points.
Do not append — replace the whole section each Sunday.

Surface one insight proactively on Monday morning:
> "One thing I noticed this week: you hit your protein goal every day you
>  logged lunch. On the 3 days you skipped it, you came up short."

---

### Food preferences
Trigger: user declines a suggested food, expresses dislike, or asks for an alternative
("I don't eat X", "I'm not a fan of Y", "can I have Z instead")

Action: append to `## Learned food preferences` in MEMORY.md:
  `- Dislikes: {FOOD} (noted {DATE})`
  or `- Prefers {FOOD_A} over {FOOD_B} (noted {DATE})`

Trigger: user asks for the same food 3+ times across different days

Action: append: `- Frequently eats: {FOOD} (logged {N} times)`

Never suggest a food the user has said they dislike. Check this list before
making any food suggestions.

---

### Meal timing drift
Trigger: after 7 days of tracking, actual meal times differ from stated times
by >45 min on average

Action: update meal times in MEMORY.md "Nutrition profile" to match observed times.
Say: "I've updated your meal times to match when you actually eat."

---

### Calorie patterns
Trigger: user consistently goes over or under target by >15% for 5+ days

Action: note this in `## Patterns` at the next Sunday rewrite.
Do NOT suggest changing the target without being asked.
Do NOT comment on individual days being over — only surface multi-week patterns.

---

### Health context
Trigger: user mentions health conditions, fitness goals, or medications
("I'm trying to lose weight", "I have diabetes", "I'm training for a marathon")

Action: append to `## Health context` in MEMORY.md:
  `- {HEALTH_NOTE} (mentioned {DATE})`

Only write what the user explicitly stated. Never infer diagnoses.
Use health context to adjust tone — e.g. never say "cheat meal" if they're
managing a medical condition.

---

### Lifecycle events
Trigger: user mentions upcoming or current travel, illness, holidays, special
events, or any temporary change in routine.
("I'm traveling next week", "I'm sick", "it's my birthday weekend",
"I have a wedding coming up", "work trip")

Action: append to `## Lifecycle events` in MEMORY.md:
  `- {EVENT}: {DATE_OR_RANGE} ({CONTEXT_NOTE})`

During active lifecycle events:
- Do not flag calorie deviations as failures
- Do not break streaks for illness days (mark as `[sick - excluded]` in daily note)
- Adjust restaurant meal expectations for travel days
- After event ends: resume normal tracking without comment

---

### Streak tracking
Trigger: every time a meal is logged

Action: Run: `nutrition log --update-streak`

Trigger: user misses a full day (no meals by 10pm)

Action: check `## Lifecycle events` first — if an active event covers today,
do not reset streak. Otherwise reset next morning. Do not mention it unless asked.

---

## Contextual callbacks — making memory feel alive

The goal is for the agent to feel like it *remembers you*, not like it's reading
a database. Apply these rules in every response:

**Reference trusted meals by name**
Don't ask "how many grams?" for a meal you've seen before. Say:
> "Chicken and rice — I'll use your usual 180g + 200g. That's 520 kcal."

**Frame progress through the goal narrative**
When showing summaries, tie the number to what they're working toward:
> "1,840 kcal today — you're 160 under target. Good day toward September."
Not just: "1,840 kcal logged."

**Surface patterns without being preachy**
When you notice a recurring situation, mention it once, lightly:
> "Thursday again — you tend to skip lunch today. Want me to remind you at 1pm?"
Never repeat the same observation two weeks in a row unless asked.

**Acknowledge streaks and milestones naturally**
> "That's 14 days in a row. You've never gone this long before."
Not a notification — woven into the confirmation after logging.

**Adjust tone to lifecycle events**
If the user is traveling: "Restaurant week — I'll estimate loosely, no pressure."
If they just came back from holiday: "Welcome back. Want to ease back in or go full tracking?"

**Never read back memory robotically**
Don't say "According to my records, you dislike dairy." Say "No dairy — got it."
Don't say "I have noted that your goal is weight loss." Just use it.

---

## Setting up proactive reminders

**Triggers:** "set up reminders", "remind me to log meals", "set up daily tracking",
or during onboarding step 6.

Ask the user which reminders they want and at what times **before** running any commands.
Do not assume default times. Only create the cron jobs for the reminders they selected.

Available reminders:

**Morning summary:**
Ask: "What time do you want your morning summary?" (e.g. 7am, 8:30am)
Parse to hour H and minute M. Then run:
```
openclaw cron add \
  --name "nutrition-morning" \
  --cron "{M} {H} * * *" \
  --tz "{TIMEZONE}" \
  --session nutrition-tracker \
  --message "Run: nutrition summary --yesterday and present it clearly. \
    Compare totals to target from MEMORY.md. \
    If they hit their calorie goal yesterday, say so specifically. \
    If they're on a streak of 3+ days, mention it." \
  --announce
```

**Evening check-in:**
Ask: "What time do you want your evening check-in?" (e.g. 7pm, 9pm)
Parse to hour H and minute M (24h). Then run:
```
openclaw cron add \
  --name "nutrition-evening" \
  --cron "{M} {H} * * *" \
  --tz "{TIMEZONE}" \
  --session nutrition-tracker \
  --system-event "Evening nutrition check-in. Ask the user what they ate today. \
    For each food they mention, run: nutrition search '{food}' to get calories, \
    confirm with user, then run: nutrition log '{food}'. \
    After all meals logged, run: nutrition summary --today and show the result." \
  --wake now
```

**Sunday synthesis (always Sunday night):**
This runs automatically — no user setup needed. Always create this cron during onboarding.
```
openclaw cron add \
  --name "nutrition-synthesis" \
  --cron "0 21 * * 0" \
  --tz "{TIMEZONE}" \
  --session nutrition-tracker \
  --message "Run nutrition summary --week and read the past 4 weeks of memory/ daily notes. \
    Then: 1) Rewrite the 'Who you are' section in MEMORY.md with a 3-5 sentence \
    synthesized paragraph. 2) Rewrite the 'Patterns' section with 4-7 bullets from \
    observed data. Do not announce these writes. Prepare one pattern insight to surface \
    Monday morning." \
  --announce
```

**Weekly report (always Monday):**
Ask: "What time on Monday do you want your weekly report?" (e.g. 9am)
Parse to hour H and minute M. Then run:
```
openclaw cron add \
  --name "nutrition-weekly" \
  --cron "{M} {H} * * 1" \
  --tz "{TIMEZONE}" \
  --session nutrition-tracker \
  --message "Read MEMORY.md. Run: nutrition summary --week and nutrition top-foods --days 7. \
    Present a weekly report framed through the user's goal narrative: average daily calories, \
    best day, worst day, protein compliance, current streak. \
    Surface one pattern insight from the Sunday synthesis. \
    Keep it short — 5-8 lines max, no bullet-point overload." \
  --announce
```

After setup: confirm which jobs were created and when they'll fire next.
To view: `openclaw cron list`
To disable a specific job: `openclaw cron disable nutrition-evening` (or -morning, -weekly)

---

## Commands reference

### Search for a food

**When to use:** User asks about nutrition info, calories, macros for a specific food.

```bash
nutrition search "chicken breast" --grams 200
nutrition search "brown rice" --grams 150 --format json
nutrition search "avocado" --rda --sex female --age 25
```

- `--grams` (default 100): serving size
- `--format summary|json`: `json` when processing programmatically
- `--rda`: show percentage of daily recommended intake
- `--sex male|female` and `--age`: adjust RDA targets

### Look up by barcode

**When to use:** User provides a barcode (8-13 digits) or wants to scan a product.

```bash
nutrition barcode 3017624010701
nutrition barcode 5000159459228 --grams 50
```

Returns Nutri-Score, NOVA group, allergens, and vegan/vegetarian status.

### Log a meal

**When to use:** User confirms logging a food after seeing search results.

```bash
nutrition log "chicken breast" --grams 200
nutrition log --check-today          # returns meal count (integer)
nutrition log --update-streak        # updates and returns streak
nutrition log --check-yesterday      # returns true/false
```

### View summary

**When to use:** User asks what they've eaten, daily totals, or trends.

```bash
nutrition summary                    # today
nutrition summary --yesterday
nutrition summary --week
nutrition summary --date 2026-04-01
nutrition summary --days 14
```

### View trends

**When to use:** User asks about their progress over time.

```bash
nutrition trend --days 7
nutrition top-foods --days 30
```

### Compare foods

**When to use:** User wants to compare nutrients side by side.

```bash
nutrition compare "chicken breast" "tofu" "salmon"
nutrition compare "white rice" "brown rice" --grams 200
```

### Calculate meal nutrition

**When to use:** User describes a multi-food meal.

```bash
nutrition meal "200g chicken breast" "150g brown rice" "1 avocado"
nutrition meal "200g chicken" "100g rice" --rda --sex female
```

### Estimate calorie burn

**When to use:** User asks how many calories an activity burns.

```bash
nutrition burn running 30
nutrition burn cycling 45 --weight 80
```

Activities: running, jogging, cycling, walking, swimming, hiking, rowing, jump rope,
dancing, yoga, pilates, weightlifting, climbing, tennis, basketball, soccer,
volleyball, skiing, skateboarding, elliptical

### Daily targets

**When to use:** User asks what their daily intake should be.

```bash
nutrition daily --sex female --age 25 --weight 60 --height 165 --activity moderate
```

### Configuration

```bash
nutrition config set --kcal 2000 --protein 150
nutrition config set --usda-key YOUR_KEY
nutrition config set --default-grams 150
nutrition config set --timezone America/New_York --start-date 2026-04-01
nutrition config status              # returns "Configured" or "Not configured"
nutrition config show                # full profile display
```

---

## Rate limit handling

When you see a rate limit error from the CLI, surface it to the user exactly as printed —
do not paraphrase or retry silently. The error contains the URL and steps needed.

Also append to today's daily note: `- [RATE LIMIT HIT - {TIME}]`

---

## Data source transparency

Always mention whether data came from **USDA** or **Open Food Facts** when presenting
results. The source is in the `summary` output and the `source` field of `json` output.
