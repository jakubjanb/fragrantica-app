"""Constants for fragrance shelf features."""

from __future__ import annotations

ENABLE_RECOMMENDATION_LOG = False
RECOMMENDER_V2_ENABLED = True
RECOMMENDER_ARTIFACTS_DIR = "Data/recommender_artifacts"
RECOMMENDER_MIN_SEED_RATING = 7
RECOMMENDER_NEIGHBOR_K = 80
RECOMMENDER_TOP_CATEGORY_K = 80
RECOMMENDER_GLOBAL_K = 250
RECOMMENDER_DEFAULT_DIVERSITY_LAMBDA = 0.75
RECOMMENDER_DEBUG_DEFAULT = False
TOTAL_WHEEL_CATEGORIES = 33

FAMILY_ORDER = [
    "Floral",
    "Woody",
    "Citrus",
    "Oriental",
    "Aromatic",
    "Chypre",
    "Leather",
    "Fruity",
    "Gourmand",
    "Fresh",
    "Other",
]

WHEEL_EXCLUDED_FAMILIES = {"Fruity", "Gourmand", "Fresh"}
WHEEL_FAMILY_ORDER = [family for family in FAMILY_ORDER if family not in WHEEL_EXCLUDED_FAMILIES]

FAMILY_KEYWORDS: dict[str, list[str]] = {
    "Floral": ["floral", "flower", "rose", "white floral", "iris", "violet", "jasmine"],
    "Woody": ["woody", "wood", "sandalwood", "cedar", "oud", "vetiver", "patchouli"],
    "Citrus": ["citrus", "bergamot", "lemon", "orange", "grapefruit", "lime", "mandarin"],
    "Oriental": ["oriental", "amber", "spicy", "incense", "resin", "balsamic"],
    "Aromatic": ["aromatic", "herbal", "lavender", "green", "fougere"],
    "Chypre": ["chypre", "oakmoss", "mossy"],
    "Leather": ["leather", "suede", "animalic"],
    "Fruity": ["fruity", "fruit", "apple", "pear", "berry", "peach", "plum"],
    "Gourmand": ["gourmand", "vanilla", "caramel", "chocolate", "sweet", "coffee", "cacao"],
    "Fresh": ["fresh", "aquatic", "marine", "ozonic", "clean", "aldehydic", "soapy"],
}

FAMILY_COLORS: dict[str, str] = {
    "Floral": "#e879a0",
    "Woody": "#a0714f",
    "Citrus": "#d4a017",
    "Oriental": "#9b59b6",
    "Fresh": "#38bdf8",
    "Aromatic": "#6b9e5e",
    "Chypre": "#2d7d4f",
    "Fruity": "#f4845f",
    "Gourmand": "#c9882a",
    "Leather": "#8b6914",
    "Other": "#94a3b8",
}
