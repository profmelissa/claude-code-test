#!/usr/bin/env python3
"""
Product matcher for the port guide outfit grid pipeline.

Matches products from data/amazon_products.json to a given port using:
  1. Port-specific tags (highest priority)
  2. Climate tags matching the port's region
  3. Activity tags matching what people do at the port
  4. Falls back to most-recently-added active products if needed

Always returns exactly 4 products for the outfit grid.
"""

import json
import os
from typing import Optional

# Path relative to the repo root
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "amazon_products.json")

# Map of port region keywords to climate tags used in the catalog
CLIMATE_MAP = {
    "mediterranean": ["mediterranean", "warm"],
    "caribbean":     ["tropical", "warm"],
    "tropical":      ["tropical", "warm"],
    "alaska":        ["alaska", "cool"],
    "northern_europe": ["cool"],
    "baltic":        ["cool"],
    "bermuda":       ["warm", "tropical"],
    "mexico":        ["tropical", "warm"],
    "bahamas":       ["tropical", "warm"],
    "hawaii":        ["tropical", "warm"],
    "australia":     ["warm"],
    "new_zealand":   ["cool", "warm"],
    "asia":          ["tropical", "warm"],
    "south_america": ["tropical", "warm"],
    "canada":        ["cool"],
    "new_england":   ["cool"],
}


def load_catalog(catalog_path: str = CATALOG_PATH) -> list[dict]:
    """Load and return only active products from the catalog."""
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [p for p in data.get("products", []) if p.get("active", True)]


def score_product(product: dict, port_slug: str, climate_tags: list[str], activity_tags: list[str]) -> tuple[int, str]:
    """
    Score a single product for relevance to this port.

    Returns (score, match_reason):
      score 3 = port-specific tag match
      score 2 = climate tag match
      score 1 = activity tag match only
      score 0 = no match
    """
    port_slug_lower = port_slug.lower()

    # Port-specific tag match (highest priority)
    if port_slug_lower in [t.lower() for t in product.get("port_tags", [])]:
        return 3, "port-specific"

    product_climate = [t.lower() for t in product.get("climate_tags", [])]
    product_activity = [t.lower() for t in product.get("activity_tags", [])]

    climate_match = any(ct.lower() in product_climate for ct in climate_tags)
    activity_match = any(at.lower() in product_activity for at in activity_tags)

    if climate_match and activity_match:
        return 2, "climate+activity"
    if climate_match:
        return 2, "climate"
    if activity_match:
        return 1, "activity"

    return 0, "none"


def match_products(
    port_slug: str,
    port_region: str,
    port_activities: Optional[list[str]] = None,
    catalog_path: str = CATALOG_PATH,
    grid_size: int = 4,
) -> list[dict]:
    """
    Return exactly `grid_size` products matched to the given port.

    Args:
        port_slug:       URL-safe port name, e.g. "sicily", "nassau", "cozumel"
        port_region:     Region key from CLIMATE_MAP, e.g. "mediterranean", "caribbean"
        port_activities: List of activity tags typical for this port,
                         e.g. ["walking", "sightseeing", "beach"]
        catalog_path:    Path to amazon_products.json (defaults to repo data dir)
        grid_size:       How many products to return (default 4)

    Returns:
        List of product dicts, length == grid_size.
    """
    products = load_catalog(catalog_path)
    if not products:
        return []

    climate_tags = CLIMATE_MAP.get(port_region.lower(), ["warm"])
    activity_tags = port_activities or ["walking", "sightseeing"]

    # Score every product
    scored = []
    for product in products:
        score, reason = score_product(product, port_slug, climate_tags, activity_tags)
        scored.append((score, product["date_added"], product, reason))

    # Sort: highest score first, then most-recently-added as tiebreaker
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    selected = [entry[2] for entry in scored[:grid_size]]

    # Pad with remaining products (by recency) if catalog is small
    if len(selected) < grid_size:
        remaining = [entry[2] for entry in scored[grid_size:]]
        selected.extend(remaining[: grid_size - len(selected)])

    return selected[:grid_size]


def get_grid_products_for_port(port_config: dict, catalog_path: str = CATALOG_PATH) -> list[dict]:
    """
    Convenience wrapper that accepts a port config dict as used in the pipeline.

    Expected port_config keys:
        slug       (str)  – e.g. "sicily"
        region     (str)  – e.g. "mediterranean"
        activities (list) – e.g. ["walking", "sightseeing"]

    Returns list of 4 matched products.
    """
    return match_products(
        port_slug=port_config.get("slug", ""),
        port_region=port_config.get("region", "mediterranean"),
        port_activities=port_config.get("activities", ["walking", "sightseeing"]),
        catalog_path=catalog_path,
    )


# ---------------------------------------------------------------------------
# CLI usage: python scripts/product_matcher.py --port sicily --region mediterranean
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Match products to a port for the outfit grid.")
    parser.add_argument("--port", required=True, help="Port slug, e.g. sicily")
    parser.add_argument("--region", default="mediterranean", help="Region key, e.g. mediterranean, caribbean, alaska")
    parser.add_argument("--activities", nargs="+", default=["walking", "sightseeing"],
                        help="Activity tags for this port")
    parser.add_argument("--catalog", default=CATALOG_PATH, help="Path to amazon_products.json")
    args = parser.parse_args()

    results = match_products(args.port, args.region, args.activities, args.catalog)
    print(f"\nTop {len(results)} products matched to port '{args.port}' ({args.region}):\n")
    for i, p in enumerate(results, 1):
        print(f"  {i}. [{p['category']}] {p['name']}")
        print(f"     Climate tags : {p['climate_tags']}")
        print(f"     Activity tags: {p['activity_tags']}")
        print(f"     Port tags    : {p['port_tags']}")
        print(f"     ASIN         : {p['asin'] or '(not yet filled in)'}")
        print()
