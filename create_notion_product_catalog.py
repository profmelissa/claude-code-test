#!/usr/bin/env python3
"""
Creates a Notion database called 'Amazon Product Catalog' nested under your
Website/Blog section, then populates it with products from data/amazon_products.json.

The JSON file is the source of truth for the pipeline.
Notion is your visual UI for browsing and adding products.

## Setup
    pip install -r requirements.txt
    export NOTION_TOKEN="secret_xxxxxxxxxxxx"

## Create the database and seed it from JSON
    python create_notion_product_catalog.py --parent-page-id <PAGE_ID>

## Re-sync after editing products in Notion (export Notion → JSON)
    python create_notion_product_catalog.py --export --db-id <DB_ID> --out data/amazon_products.json

## Update Notion from JSON (after editing the JSON directly)
    python create_notion_product_catalog.py --parent-page-id <PAGE_ID> --db-id <DB_ID> --sync

---

HOW TO SYNC NOTION → JSON
--------------------------
1. In Notion, open the Amazon Product Catalog database.
2. Use this script with --export to pull all Notion rows back to JSON:
       python create_notion_product_catalog.py --db-id <DB_ID> --export
   This regenerates data/amazon_products.json with every product in Notion,
   preserving the field structure the pipeline expects.
3. Commit the updated JSON to your repo so the pipeline picks it up.

Tip: When you add a new product in Notion, run --export to capture it,
then commit the updated JSON. No manual editing of the JSON is needed.
"""

import json
import os
import sys
import argparse
import requests

NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"
DB_TITLE = "Amazon Product Catalog"
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "amazon_products.json")

# Multi-select option colors (cycles through these for new tags)
TAG_COLORS = ["blue", "green", "orange", "pink", "purple", "red", "yellow", "gray", "brown"]


def headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


# ---------------------------------------------------------------------------
# Database creation
# ---------------------------------------------------------------------------

def _all_options(products: list[dict], field: str) -> list[str]:
    """Collect all unique tag values across all products for a given list field."""
    seen = set()
    for p in products:
        for tag in p.get(field, []):
            seen.add(tag)
    return sorted(seen)


def _multi_select_schema(options: list[str]) -> dict:
    return {
        "multi_select": {
            "options": [
                {"name": opt, "color": TAG_COLORS[i % len(TAG_COLORS)]}
                for i, opt in enumerate(options)
            ]
        }
    }


def create_database(token: str, parent_page_id: str, products: list[dict]) -> str:
    """Create the Amazon Product Catalog database and return its ID."""
    climate_opts = _all_options(products, "climate_tags")
    activity_opts = _all_options(products, "activity_tags")
    port_opts = _all_options(products, "port_tags")
    season_opts = _all_options(products, "seasons")

    url = f"{NOTION_API_BASE}/databases"
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": DB_TITLE}}],
        "properties": {
            "Product Name": {"title": {}},
            "Category": {
                "select": {
                    "options": [
                        {"name": "Dress",      "color": "pink"},
                        {"name": "Top",        "color": "blue"},
                        {"name": "Bottom",     "color": "purple"},
                        {"name": "Layer",      "color": "gray"},
                        {"name": "Swimwear",   "color": "yellow"},
                        {"name": "Footwear",   "color": "orange"},
                        {"name": "Accessory",  "color": "green"},
                        {"name": "Bag",        "color": "brown"},
                        {"name": "Outerwear",  "color": "red"},
                    ]
                }
            },
            "ASIN": {"rich_text": {}},
            "Affiliate URL": {"url": {}},
            "My Photo Path": {"rich_text": {}},
            "Description": {"rich_text": {}},
            "Climate Tags": _multi_select_schema(climate_opts or ["warm", "tropical", "mediterranean", "cool", "alaska"]),
            "Activity Tags": _multi_select_schema(activity_opts or ["walking", "sightseeing", "beach", "dining", "hiking"]),
            "Port Tags": _multi_select_schema(port_opts or []),
            "Seasons": _multi_select_schema(season_opts or ["spring", "summer", "fall", "winter"]),
            "Notes": {"rich_text": {}},
            "Active": {"checkbox": {}},
            "Product ID": {"rich_text": {}},
        },
    }

    resp = requests.post(url, headers=headers(token), json=payload)
    if not resp.ok:
        print(f"ERROR creating database: {resp.status_code} {resp.text}")
        sys.exit(1)

    db_id = resp.json()["id"]
    print(f"Database created: '{DB_TITLE}'  (id={db_id})")
    return db_id


# ---------------------------------------------------------------------------
# Populate rows
# ---------------------------------------------------------------------------

def _rich_text(value: str) -> list:
    return [{"text": {"content": str(value)}}] if value else []


def _multi_select_value(tags: list) -> list:
    return [{"name": str(t)} for t in tags if t]


def add_product(token: str, db_id: str, product: dict):
    """Add a single product row to the Notion database."""
    url = f"{NOTION_API_BASE}/pages"

    affiliate_url = product.get("affiliate_url") or None

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Product Name": {
                "title": _rich_text(product.get("name", ""))
            },
            "Category": {
                "select": {"name": product.get("category", "Accessory")}
            },
            "ASIN": {
                "rich_text": _rich_text(product.get("asin", ""))
            },
            "Affiliate URL": {
                "url": affiliate_url
            },
            "My Photo Path": {
                "rich_text": _rich_text(product.get("my_photo", ""))
            },
            "Description": {
                "rich_text": _rich_text(product.get("description", ""))
            },
            "Climate Tags": {
                "multi_select": _multi_select_value(product.get("climate_tags", []))
            },
            "Activity Tags": {
                "multi_select": _multi_select_value(product.get("activity_tags", []))
            },
            "Port Tags": {
                "multi_select": _multi_select_value(product.get("port_tags", []))
            },
            "Seasons": {
                "multi_select": _multi_select_value(product.get("seasons", []))
            },
            "Notes": {
                "rich_text": _rich_text(product.get("notes", ""))
            },
            "Active": {
                "checkbox": product.get("active", True)
            },
            "Product ID": {
                "rich_text": _rich_text(product.get("id", ""))
            },
        },
    }

    resp = requests.post(url, headers=headers(token), json=payload)
    if not resp.ok:
        print(f"  WARNING: failed to add '{product.get('name')}': {resp.status_code} {resp.text}")
    else:
        print(f"  Added: {product.get('name')}  [{product.get('category')}]")


def populate_from_json(token: str, db_id: str, catalog_path: str):
    """Seed the Notion database from the JSON catalog."""
    if not os.path.exists(catalog_path):
        print(f"ERROR: catalog not found at {catalog_path}")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    print(f"\nSeeding {len(products)} products into Notion...")

    for product in products:
        add_product(token, db_id, product)

    print(f"\nDone. {len(products)} products added to '{DB_TITLE}'.")


# ---------------------------------------------------------------------------
# Export: Notion → JSON
# ---------------------------------------------------------------------------

def _extract_rich_text(prop) -> str:
    return "".join(block["text"]["content"] for block in prop.get("rich_text", []))


def _extract_title(prop) -> str:
    return "".join(block["text"]["content"] for block in prop.get("title", []))


def _extract_multi_select(prop) -> list:
    return [opt["name"] for opt in prop.get("multi_select", [])]


def _extract_select(prop) -> str:
    sel = prop.get("select")
    return sel["name"] if sel else ""


def export_to_json(token: str, db_id: str, out_path: str):
    """
    Pull all rows from the Notion database and write them to the JSON catalog.
    This is how you sync Notion → JSON after adding products in Notion.
    """
    url = f"{NOTION_API_BASE}/databases/{db_id}/query"
    products = []
    has_more = True
    start_cursor = None

    print(f"Exporting Notion database {db_id} → {out_path} ...")

    while has_more:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = requests.post(url, headers=headers(token), json=body)
        if not resp.ok:
            print(f"ERROR querying database: {resp.status_code} {resp.text}")
            sys.exit(1)

        result = resp.json()
        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

        for page in result.get("results", []):
            props = page["properties"]

            # Re-assemble the product dict in the canonical JSON shape
            affiliate_url_prop = props.get("Affiliate URL", {})
            affiliate_url = affiliate_url_prop.get("url") or ""

            product = {
                "id": _extract_rich_text(props.get("Product ID", {})) or page["id"],
                "name": _extract_title(props.get("Product Name", {})),
                "category": _extract_select(props.get("Category", {})),
                "asin": _extract_rich_text(props.get("ASIN", {})),
                "affiliate_url": affiliate_url,
                "my_photo": _extract_rich_text(props.get("My Photo Path", {})),
                "description": _extract_rich_text(props.get("Description", {})),
                "climate_tags": _extract_multi_select(props.get("Climate Tags", {})),
                "activity_tags": _extract_multi_select(props.get("Activity Tags", {})),
                "port_tags": _extract_multi_select(props.get("Port Tags", {})),
                "seasons": _extract_multi_select(props.get("Seasons", {})),
                "notes": _extract_rich_text(props.get("Notes", {})),
                "active": props.get("Active", {}).get("checkbox", True),
                "date_added": page["created_time"][:10],
            }
            products.append(product)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(products)} products to {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create / sync the Amazon Product Catalog Notion database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("NOTION_TOKEN"),
        help="Notion integration token (or set NOTION_TOKEN env var)",
    )
    parser.add_argument(
        "--parent-page-id",
        help="ID of the Notion page that will contain the new database (required for creation)",
    )
    parser.add_argument(
        "--db-id",
        default=None,
        help="Skip creation and use an existing database by this ID",
    )
    parser.add_argument(
        "--catalog",
        default=CATALOG_PATH,
        help=f"Path to amazon_products.json (default: {CATALOG_PATH})",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export Notion database → JSON file (Notion-to-JSON sync direction)",
    )
    parser.add_argument(
        "--out",
        default=CATALOG_PATH,
        help="Output path for --export (default: same as --catalog)",
    )

    args = parser.parse_args()

    if not args.token:
        print(
            "ERROR: Notion token is required.\n"
            "Pass --token <TOKEN> or set the NOTION_TOKEN environment variable."
        )
        sys.exit(1)

    # ---- Export direction: Notion → JSON ----
    if args.export:
        if not args.db_id:
            print("ERROR: --db-id is required for --export")
            sys.exit(1)
        export_to_json(args.token, args.db_id, args.out)
        return

    # ---- Seed direction: JSON → Notion ----
    if args.db_id:
        db_id = args.db_id
        print(f"Using existing database id={db_id}")
    else:
        if not args.parent_page_id:
            print("ERROR: --parent-page-id is required when creating a new database")
            sys.exit(1)
        with open(args.catalog, "r", encoding="utf-8") as f:
            products = json.load(f).get("products", [])
        db_id = create_database(args.token, args.parent_page_id, products)

    populate_from_json(args.token, db_id, args.catalog)


if __name__ == "__main__":
    main()
