# Redirect Mapping → Notion

Creates a Notion database **"Redirect Mapping — profmelissa.com"** with the
columns below, then populates it from a CSV file.

| Column | Type | Notes |
|---|---|---|
| Source URL | Title | Old URL path |
| Target URL | Rich text | New URL to redirect to |
| Status | Select | `Pending` (yellow) or `Complete` (green) |
| Notes | Rich text | Free-form notes |

---

## Prerequisites

1. Python 3.8+
2. A [Notion internal integration](https://www.notion.so/my-integrations) with
   **Insert content** permission.
3. Share the parent page with the integration (open the page → ··· menu →
   **Add connections** → pick your integration).

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
# Windows — PowerShell
$env:NOTION_TOKEN = "secret_xxxxxxxxxxxx"
python create_notion_redirect_db.py `
    --parent-page-id <PAGE_ID> `
    --csv "C:\Temp\redirect-mapping-clean.csv"

# macOS / Linux
export NOTION_TOKEN="secret_xxxxxxxxxxxx"
python create_notion_redirect_db.py \
    --parent-page-id <PAGE_ID> \
    --csv /path/to/redirect-mapping-clean.csv
```

### Arguments

| Flag | Required | Description |
|---|---|---|
| `--token` | Yes* | Notion integration token (`secret_…`). Can also be set via `NOTION_TOKEN` env var. |
| `--parent-page-id` | Yes | ID of the Notion page that will **contain** the new database. Copy it from the page URL: `notion.so/<workspace>/<PAGE_ID>`. |
| `--csv` | No | Path to the CSV (default: `C:\Temp\redirect-mapping-clean.csv`). |
| `--db-id` | No | Skip creation and populate an **existing** database instead. |

### Finding the Parent Page ID

Open the destination Notion page in your browser. The URL looks like:

```
https://www.notion.so/My-Workspace-abc123def456...
```

The long hex string at the end (with or without hyphens) is the page ID.

---

## CSV format

The script auto-detects column names (case-insensitive). Supported aliases:

| Expected column | Accepted header names |
|---|---|
| Source URL | `Source URL`, `source_url`, `source`, `from` |
| Target URL | `Target URL`, `target_url`, `target`, `to`, `redirect` |
| Status | `Status`, `status` |
| Notes | `Notes`, `notes`, `note`, `comment` |

If `Status` is missing or blank it defaults to **Pending**.
