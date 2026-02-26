#!/usr/bin/env python3
"""
Creates a Notion database called 'Redirect Mapping — profmelissa.com'
with columns: Source URL, Target URL, Status (Pending/Complete), Notes
Then populates it from C:\Temp\redirect-mapping-clean.csv
"""

import csv
import os
import sys
import argparse
import requests
import json

NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"
DB_TITLE = "Redirect Mapping \u2014 profmelissa.com"
CSV_PATH = r"C:\Temp\redirect-mapping-clean.csv"


def headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def create_database(token: str, parent_page_id: str) -> str:
    """Create the Redirect Mapping database and return its ID."""
    url = f"{NOTION_API_BASE}/databases"
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": DB_TITLE}}],
        "properties": {
            "Source URL": {"title": {}},
            "Target URL": {"rich_text": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Pending", "color": "yellow"},
                        {"name": "Complete", "color": "green"},
                    ]
                }
            },
            "Notes": {"rich_text": {}},
        },
    }

    resp = requests.post(url, headers=headers(token), json=payload)
    if not resp.ok:
        print(f"ERROR creating database: {resp.status_code} {resp.text}")
        sys.exit(1)

    db_id = resp.json()["id"]
    print(f"Database created: {DB_TITLE}  (id={db_id})")
    return db_id


def add_row(token: str, db_id: str, source: str, target: str, status: str, notes: str):
    """Add a single row to the Notion database."""
    url = f"{NOTION_API_BASE}/pages"

    # Normalise status value to match select options
    status = status.strip().capitalize() if status.strip() else "Pending"
    if status not in ("Pending", "Complete"):
        status = "Pending"

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Source URL": {
                "title": [{"text": {"content": source}}]
            },
            "Target URL": {
                "rich_text": [{"text": {"content": target}}]
            },
            "Status": {
                "select": {"name": status}
            },
            "Notes": {
                "rich_text": [{"text": {"content": notes}}]
            },
        },
    }

    resp = requests.post(url, headers=headers(token), json=payload)
    if not resp.ok:
        print(f"  WARNING: failed to add row '{source}': {resp.status_code} {resp.text}")
    else:
        print(f"  Added: {source} -> {target}  [{status}]")


def populate_from_csv(token: str, db_id: str, csv_path: str):
    """Read the CSV and create a Notion page for each row."""
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Normalise header names (strip whitespace, lower-case for matching)
        fieldnames = [name.strip() for name in reader.fieldnames or []]
        print(f"CSV columns detected: {fieldnames}")

        # Map flexible header names to expected columns
        def find_col(candidates):
            for c in candidates:
                for fn in fieldnames:
                    if fn.lower() == c.lower():
                        return fn
            return None

        col_source = find_col(["Source URL", "source_url", "source", "from"])
        col_target = find_col(["Target URL", "target_url", "target", "to", "redirect"])
        col_status = find_col(["Status", "status"])
        col_notes  = find_col(["Notes", "notes", "note", "comment"])

        if not col_source or not col_target:
            print(
                f"ERROR: Could not identify Source URL / Target URL columns.\n"
                f"Found columns: {fieldnames}"
            )
            sys.exit(1)

        count = 0
        for row in reader:
            # Re-read with original fieldnames so lookups work
            source = row.get(col_source, "").strip()
            target = row.get(col_target, "").strip()
            status = row.get(col_status, "Pending").strip() if col_status else "Pending"
            notes  = row.get(col_notes,  "").strip()        if col_notes  else ""

            if not source:
                continue  # skip empty rows

            add_row(token, db_id, source, target, status, notes)
            count += 1

    print(f"\nDone. {count} rows added to '{DB_TITLE}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Create a Notion redirect-mapping database and populate it from CSV."
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("NOTION_TOKEN"),
        help="Notion integration token (or set NOTION_TOKEN env var)",
    )
    parser.add_argument(
        "--parent-page-id",
        required=True,
        help="ID of the Notion page that will contain the new database",
    )
    parser.add_argument(
        "--csv",
        default=CSV_PATH,
        help=f"Path to the CSV file (default: {CSV_PATH})",
    )
    parser.add_argument(
        "--db-id",
        default=None,
        help="Skip database creation and populate an existing database by this ID",
    )

    args = parser.parse_args()

    if not args.token:
        print(
            "ERROR: Notion token is required.\n"
            "Pass --token <TOKEN> or set the NOTION_TOKEN environment variable."
        )
        sys.exit(1)

    if args.db_id:
        db_id = args.db_id
        print(f"Using existing database id={db_id}")
    else:
        db_id = create_database(args.token, args.parent_page_id)

    populate_from_csv(args.token, db_id, args.csv)


if __name__ == "__main__":
    main()
