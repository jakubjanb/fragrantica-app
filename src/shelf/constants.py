"""Constants for fragrance shelf features."""

from __future__ import annotations

ENABLE_RECOMMENDATION_LOG = False

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

# Subcategory keyword mapping for the sunburst outer ring.
# Order of keys matters: first match wins.
SUBCATEGORY_MAP: dict[str, dict[str, list[str]]] = {
    "Floral": {
        "White Floral": ["white floral", "white flower"],
        "Rose": ["rose"],
        "Fresh Floral": ["fresh floral"],
        "Soft Floral": ["soft floral", "powdery"],
        "Green Floral": ["green floral", "iris", "violet"],
    },
    "Woody": {
        "Woody Aromatic": ["woody aromatic", "aromatic woody"],
        "Woody Oriental": ["woody oriental"],
        "Sandalwood": ["sandalwood"],
        "Cedar/Oud": ["cedar", "oud"],
        "Dry Wood": ["dry wood", "vetiver", "patchouli"],
    },
    "Oriental": {
        "Oriental Floral": ["oriental floral", "floral oriental"],
        "Oriental Woody": ["oriental woody"],
        "Soft Oriental": ["soft oriental"],
        "Spicy Oriental": ["spicy oriental", "spice"],
    },
    "Fresh": {
        "Aquatic/Marine": ["aquatic", "marine", "ozonic", "water"],
        "Aldehydic": ["aldehydic", "soapy"],
        "Citrus Fresh": ["citrus"],
        "Green Fresh": ["green"],
    },
    "Citrus": {
        "Aromatic Citrus": ["aromatic citrus"],
        "Fruity Citrus": ["fruity citrus"],
        "Hesperidic": ["bergamot", "lemon", "orange", "grapefruit", "lime", "mandarin", "hesperidic"],
    },
    "Aromatic": {
        "Aromatic Fougère": ["fougere", "fougère"],
        "Aromatic Herbal": ["herbal", "lavender"],
        "Aromatic Spicy": ["spicy"],
    },
    "Chypre": {
        "Floral Chypre": ["floral chypre"],
        "Fruity Chypre": ["fruity chypre"],
        "Aromatic Chypre": ["aromatic chypre"],
    },
    "Fruity": {
        "Tropical Fruity": ["tropical", "mango", "passion"],
        "Berry Fruity": ["berry", "strawberry", "raspberry", "blackcurrant"],
        "Peach/Apple": ["peach", "apple", "pear", "apricot"],
    },
    "Gourmand": {
        "Sweet/Vanilla": ["vanilla", "sweet"],
        "Chocolate/Coffee": ["chocolate", "coffee", "cacao"],
        "Caramel": ["caramel", "butterscotch"],
    },
    "Leather": {
        "Smoky Leather": ["smoky", "tobacco"],
        "Suede": ["suede"],
        "Animalic": ["animalic", "musk"],
    },
    "Other": {
        "Uncategorized": [],
    },
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
