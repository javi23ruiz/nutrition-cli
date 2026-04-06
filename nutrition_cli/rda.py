"""Hardcoded RDA/nutrition constants. No API calls."""

# Recommended Daily Allowances keyed by (sex, age_group)
# Sources: WHO/NIH dietary guidelines
RDA_TABLE = {
    ("male", "adult"): {
        "calories": 2500,
        "protein_g": 56,
        "fat_g": 83,
        "carbs_g": 325,
        "fiber_g": 38,
    },
    ("female", "adult"): {
        "calories": 2000,
        "protein_g": 46,
        "fat_g": 67,
        "carbs_g": 260,
        "fiber_g": 25,
    },
    ("male", "teen"): {
        "calories": 2800,
        "protein_g": 52,
        "fat_g": 93,
        "carbs_g": 364,
        "fiber_g": 38,
    },
    ("female", "teen"): {
        "calories": 2200,
        "protein_g": 46,
        "fat_g": 73,
        "carbs_g": 286,
        "fiber_g": 26,
    },
    ("male", "child"): {
        "calories": 1400,
        "protein_g": 19,
        "fat_g": 47,
        "carbs_g": 182,
        "fiber_g": 25,
    },
    ("female", "child"): {
        "calories": 1400,
        "protein_g": 19,
        "fat_g": 47,
        "carbs_g": 182,
        "fiber_g": 25,
    },
}

# Calories per gram of macronutrient
KCAL_PER_GRAM = {
    "fat": 9,
    "protein": 4,
    "carbs": 4,
    "alcohol": 7,
}

# Grams per cup for common cooking ingredients
COOKING_DENSITY = {
    "flour": 125,
    "bread flour": 130,
    "whole wheat flour": 128,
    "sugar": 200,
    "brown sugar": 220,
    "powdered sugar": 120,
    "rice": 185,
    "basmati rice": 190,
    "brown rice": 190,
    "butter": 227,
    "oil": 218,
    "olive oil": 216,
    "milk": 244,
    "cream": 240,
    "sour cream": 230,
    "yogurt": 245,
    "honey": 340,
    "maple syrup": 315,
    "oats": 80,
    "cocoa powder": 86,
    "cornstarch": 128,
    "baking powder": 230,
    "salt": 292,
    "peanut butter": 258,
    "almonds": 143,
    "walnuts": 120,
    "chocolate chips": 170,
    "raisins": 165,
    "shredded coconut": 93,
    "breadcrumbs": 108,
}

# MET (Metabolic Equivalent of Task) values for common activities
MET_TABLE = {
    "running": 9.8,
    "jogging": 7.0,
    "cycling": 7.5,
    "walking": 3.5,
    "swimming": 8.0,
    "hiking": 6.0,
    "rowing": 7.0,
    "jump rope": 12.3,
    "dancing": 5.5,
    "yoga": 3.0,
    "pilates": 3.0,
    "weightlifting": 6.0,
    "climbing": 8.0,
    "tennis": 7.3,
    "basketball": 6.5,
    "soccer": 7.0,
    "volleyball": 4.0,
    "skiing": 7.0,
    "skateboarding": 5.0,
    "elliptical": 5.0,
}


def get_age_group(age: int) -> str:
    """Map numeric age to age group key."""
    if age < 9:
        return "child"
    if age < 19:
        return "teen"
    return "adult"


def get_rda(sex: str = "male", age: int = 30) -> dict:
    """Return RDA dict for given sex and age."""
    age_group = get_age_group(age)
    return RDA_TABLE.get((sex, age_group), RDA_TABLE[("male", "adult")])
