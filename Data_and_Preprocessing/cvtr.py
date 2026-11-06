# This code is authored by Raghav 
import pandas as pd
import re

INPUT_FILE = "Dataset2.xlsx"
OUTPUT_FILE = "ingredient_dish_edges.csv"
SHEET_NAME = "Cleaned_Indian_Food_Dataset"

# Code to remove incosistencies in ingredient name to lessen the number of ingredients and to increase correlation

def normalize_ingredient(ingredient):
    """Map preparation variants to a canonical ingredient name."""

    ingredient = str(ingredient).strip().lower()
    ingredient = re.sub(r"\s+", " ", ingredient)

    ingredient = re.sub(
        r"\s*\([^)]*\)\s*", " ", ingredient
    )

    prep_pattern = (
        r"\s*[-–—]\s*"
        r"(?:"
        r"finely\s+chopped|roughly\s+chopped|"
        r"chopped|thinly\s+sliced|sliced|slit|"
        r"crushed|crush|minced|mince|"
        r"grated|grate|ground|grind|"
        r"pounded|pound|blended|blend|"
        r"pureed|puree|"
        r"make\s+(?:a\s+)?paste|"
        r"made\s+into\s+(?:a\s+)?paste|"
        r"to\s+(?:make\s+)?(?:a\s+)?paste|"
        r"paste|"
        r"tighten|"
        r"deseeded|"
        r"picked\s+and\s+chopped|"
        r"for\s+garnishing|"
        r"for\s+garnish|"
        r"for\s+tempering"
        r")\s*$"
    )

    ingredient = re.sub(
        prep_pattern, "", ingredient, flags=re.IGNORECASE
    )

    ingredient = re.sub(
        r"\s*,?\s*(?:finely chopped|roughly chopped|"
        r"chopped|crushed|minced|grated|sliced|"
        r"thinly sliced|ground|pounded|deseeded)\s*$",
        "",
        ingredient,
        flags=re.IGNORECASE,
    )
    ingredient = re.split(r"\s*[-–—]\s*", ingredient, maxsplit=1)[0].strip()

    ingredient = re.sub(r"\s+", " ", ingredient)
    ingredient = ingredient.strip(" -–—,.")

    aliases = {
        "garlic cloves": "garlic",
        "cloves garlic": "garlic",
        "ginger garlic": "ginger garlic",
        "ginger-garlic": "ginger garlic",
        "green chillies": "green chili",
        "green chilli": "green chili",
        "green chilies": "green chili",
        "red chillies": "red chili",
        "red chilli": "red chili",
        "red chilies": "red chili",
    }

    ingredient = aliases.get(ingredient, ingredient)

    return ingredient if ingredient else None


def parse_ingredient_item(item):
    item = str(item).strip()

    if not item or item.lower() in {"nan", "none"}:
        return None, None

    qty_pattern = r"""
        ^\s*
        (?P<qty>
            (?:(?:\d+\s*-\s*)?\d+\s*/\s*\d+|\d+(?:\.\d+)?)
            (?:\s*-\s*(?:\d+\s*/\s*\d+|\d+(?:\.\d+)?))?
            (?:\s*(?:to\s+taste|as\s+required))?
        )
    """

    match = re.match(
        qty_pattern, item,
        flags=re.IGNORECASE | re.VERBOSE
    )

    if match:
        quantity = match.group("qty").strip()
        rest = item[match.end():].strip()

        unit_pattern = r"""
            ^(?:tablespoons?|teaspoons?|tbsp|tsp|
            cups?|grams?|g|kg|ml|litres?|liters?|
            cloves?|inches?|inch|sprigs?|pieces?|
            piece|whole|medium|small|large)\b\.?\s*
        """

        unit_match = re.match(
            unit_pattern, rest,
            flags=re.IGNORECASE | re.VERBOSE
        )

        if unit_match:
            unit = unit_match.group(0).strip().rstrip(".")
            quantity = f"{quantity} {unit}"
            rest = rest[unit_match.end():].strip()

        ingredient = rest

    else:
        lower = item.lower()

        if "to taste" in lower:
            quantity = "to taste"
            ingredient = re.sub(
                r"\s*-\s*to taste", "", item,
                flags=re.IGNORECASE
            ).strip()

        elif (
            "as required" in lower
            or "as per use" in lower
        ):
            quantity = "as required"
            ingredient = re.sub(
                r"\s*-\s*(?:as required|as per use)",
                "", item, flags=re.IGNORECASE
            ).strip()

        else:
            quantity = ""
            ingredient = item

    ingredient = normalize_ingredient(ingredient)

    return ingredient, quantity


df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

rows = []

for idx, row in df.iterrows():
    dish_id = f"D{idx + 1:05d}"

    raw_ingredients = row["TranslatedIngredients"]

    if pd.isna(raw_ingredients):
        continue

    for item in str(raw_ingredients).split(","):
        ingredient, quantity = parse_ingredient_item(item)

        if ingredient:
            rows.append({
                "Dish_ID": dish_id,
                "Dish": row["TranslatedRecipeName"],
                "Ingredient": ingredient,
                "Quantity": quantity,
                "Region": row["Cuisine"],
            })

result = pd.DataFrame(rows)

result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print(f"Saved {len(result)} dish-ingredient edges")
print(f"Unique dishes: {result['Dish_ID'].nunique()}")
print(f"Unique ingredients: {result['Ingredient'].nunique()}")

print("\nMost common normalized ingredients:")
print(result["Ingredient"].value_counts().head(30))
