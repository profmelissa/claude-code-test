#!/usr/bin/env python3
"""
Outfit grid HTML generator for port guide pages.

Generates a 4-product outfit grid using the existing `.outfit-grid` CSS class
already present in the stylesheet. No AAWP plugin required — uses personal
product photos and direct Amazon affiliate links from the local catalog.

Usage (standalone):
    python scripts/outfit_grid.py --port sicily --region mediterranean

Usage (in pipeline):
    from scripts.outfit_grid import generate_outfit_grid_html
    html = generate_outfit_grid_html(port_config)
"""

import os
import html as html_lib
from typing import Optional

# Allow running as a module from repo root or from scripts/ directory
try:
    from scripts.product_matcher import get_grid_products_for_port, match_products, CATALOG_PATH
except ImportError:
    from product_matcher import get_grid_products_for_port, match_products, CATALOG_PATH

# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

OUTFIT_GRID_WRAPPER = """\
<!-- Outfit Grid: {port_name} -->
<div class="outfit-grid">
{items}
</div>
<!-- /Outfit Grid -->
"""

OUTFIT_GRID_ITEM_WITH_LINK = """\
  <div class="outfit-grid__item">
    <a href="{affiliate_url}" target="_blank" rel="nofollow noopener sponsored">
      <img src="{photo_url}" alt="{name_escaped}" loading="lazy" />
      <span class="outfit-grid__item-name">{name_escaped}</span>
    </a>
  </div>"""

OUTFIT_GRID_ITEM_NO_LINK = """\
  <div class="outfit-grid__item outfit-grid__item--placeholder">
    <img src="{photo_url}" alt="{name_escaped}" loading="lazy" />
    <span class="outfit-grid__item-name">{name_escaped}</span>
  </div>"""

PLACEHOLDER_PHOTO = "/wp-content/themes/profmelissa/images/product-placeholder.jpg"


def _item_html(product: dict, base_photo_url: str = "") -> str:
    """Render a single outfit grid item."""
    name_escaped = html_lib.escape(product["name"])

    # Resolve photo URL: use the my_photo path relative to site root,
    # or fall back to a placeholder if the field is empty.
    photo_path = product.get("my_photo", "")
    if photo_path:
        photo_url = f"{base_photo_url.rstrip('/')}/{photo_path.lstrip('/')}"
    else:
        photo_url = PLACEHOLDER_PHOTO

    affiliate_url = product.get("affiliate_url", "")

    if affiliate_url:
        return OUTFIT_GRID_ITEM_WITH_LINK.format(
            affiliate_url=affiliate_url,
            photo_url=photo_url,
            name_escaped=name_escaped,
        )
    else:
        return OUTFIT_GRID_ITEM_NO_LINK.format(
            photo_url=photo_url,
            name_escaped=name_escaped,
        )


def generate_outfit_grid_html(
    port_config: dict,
    catalog_path: str = CATALOG_PATH,
    base_photo_url: str = "",
) -> str:
    """
    Generate the complete outfit grid HTML block for a port guide.

    Args:
        port_config: Dict with keys:
            slug       (str)  – e.g. "sicily"
            name       (str)  – display name, e.g. "Sicily"
            region     (str)  – e.g. "mediterranean"
            activities (list) – e.g. ["walking", "sightseeing"]
        catalog_path:   Path to amazon_products.json
        base_photo_url: Base URL prefix for product photos, e.g.
                        "https://profmelissa.com". Leave empty for
                        site-root-relative paths.

    Returns:
        HTML string for the outfit grid section.
    """
    products = get_grid_products_for_port(port_config, catalog_path=catalog_path)

    if not products:
        return "<!-- Outfit Grid: no products matched -->"

    items_html = "\n".join(_item_html(p, base_photo_url) for p in products)
    port_name = html_lib.escape(port_config.get("name", port_config.get("slug", "Port")))

    return OUTFIT_GRID_WRAPPER.format(port_name=port_name, items=items_html)


def generate_outfit_grid_for_port(
    port_slug: str,
    port_region: str,
    port_name: Optional[str] = None,
    port_activities: Optional[list] = None,
    catalog_path: str = CATALOG_PATH,
    base_photo_url: str = "",
) -> str:
    """Thin wrapper accepting individual keyword arguments instead of a dict."""
    port_config = {
        "slug": port_slug,
        "name": port_name or port_slug.replace("-", " ").title(),
        "region": port_region,
        "activities": port_activities or ["walking", "sightseeing"],
    }
    return generate_outfit_grid_html(port_config, catalog_path=catalog_path, base_photo_url=base_photo_url)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate outfit grid HTML for a port guide.")
    parser.add_argument("--port", required=True, help="Port slug, e.g. sicily")
    parser.add_argument("--name", help="Port display name (defaults to slug title-cased)")
    parser.add_argument("--region", default="mediterranean",
                        help="Region key: mediterranean, caribbean, alaska, …")
    parser.add_argument("--activities", nargs="+", default=["walking", "sightseeing"],
                        help="Activity tags for this port")
    parser.add_argument("--catalog", default=CATALOG_PATH, help="Path to amazon_products.json")
    parser.add_argument("--base-url", default="", help="Base URL for photo paths")
    args = parser.parse_args()

    output = generate_outfit_grid_for_port(
        port_slug=args.port,
        port_region=args.region,
        port_name=args.name,
        port_activities=args.activities,
        catalog_path=args.catalog,
        base_photo_url=args.base_url,
    )
    print(output)
