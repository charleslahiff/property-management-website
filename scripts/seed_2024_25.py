"""
Seed 2024/25 income and expenditure for Eagle Court from the Metrobank account statement.

Run from the project root:
    gcloud auth application-default login
    GCP_PROJECT_ID=lahiff-management python scripts/seed_2024_25.py

Set DRY_RUN=1 to preview without writing:
    $env:DRY_RUN="1"; $env:GCP_PROJECT_ID="lahiff-management"; python scripts/seed_2024_25.py
"""

import os
import uuid
from datetime import datetime
from google.cloud import firestore

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lahiff-management")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

BLOCK_ID = "eagle-court"
YEAR_ID = "2024-25"

db = firestore.Client(project=PROJECT_ID)


def iso(date_str):
    """Convert D/M/YYYY to YYYY-MM-DD."""
    return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Expenditure
# Refs 27/28 (error + error correction, cancel out) are omitted.
# Ref 10 (Traynor loan repayment) included as Other — reclassify if needed.
# ---------------------------------------------------------------------------

EXPENDITURE = [
    {"date": iso("4/4/2024"),   "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 54.88,   "supplier": "EDF",              "reference": "Ref 1"},
    {"date": iso("4/4/2024"),   "description": "Prestige Cleaning inv 2041",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 2"},
    {"date": iso("4/4/2024"),   "description": "D&S Builders — panic bolts",              "category": "Repairs",    "amount": 165.00,  "supplier": "D&S Builders",     "reference": "Ref 3"},
    {"date": iso("3/5/2024"),   "description": "Prestige Cleaning inv 2054",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 5"},
    {"date": iso("15/5/2024"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 78.12,   "supplier": "EDF",              "reference": "Ref 6"},
    {"date": iso("12/6/2024"),  "description": "Prestige Cleaning inv 2065",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 7"},
    {"date": iso("12/6/2024"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 39.34,   "supplier": "EDF",              "reference": "Ref 8"},
    {"date": iso("28/6/2024"),  "description": "Prestige Cleaning inv 2081",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 9"},
    {"date": iso("1/7/2024"),   "description": "Payback Traynor loan account",            "category": "Other",      "amount": 2605.58, "supplier": None,               "reference": "Ref 10"},
    {"date": iso("10/7/2024"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 46.02,   "supplier": "EDF",              "reference": "Ref 15"},
    {"date": iso("2/8/2024"),   "description": "Prestige Cleaning inv 3007",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 17"},
    {"date": iso("13/8/2024"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 48.09,   "supplier": "EDF",              "reference": "Ref 18"},
    {"date": iso("30/8/2024"),  "description": "Prestige Cleaning inv 3022",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 19"},
    {"date": iso("6/9/2024"),   "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 51.06,   "supplier": "EDF",              "reference": "Ref 20"},
    {"date": iso("11/10/2024"), "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 51.50,   "supplier": "EDF",              "reference": "Ref 21"},
    {"date": iso("13/11/2024"), "description": "Prestige Cleaning inv 3023",              "category": "Cleaning",   "amount": 192.00,  "supplier": "Prestige Cleaning","reference": "Ref 22"},
    {"date": iso("15/11/2024"), "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 51.89,   "supplier": "EDF",              "reference": "Ref 23"},
    {"date": iso("5/12/2024"),  "description": "Millennium FP — fire alarm test & service","category": "Other",   "amount": 240.00,  "supplier": "Millenium FP",     "reference": "Ref 24"},
    {"date": iso("6/12/2024"),  "description": "Prestige Cleaning inv 3035",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 25"},
    {"date": iso("6/12/2024"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 51.10,   "supplier": "EDF",              "reference": "Ref 26"},
    {"date": iso("22/1/2025"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 62.03,   "supplier": "EDF",              "reference": "Ref 29"},
    {"date": iso("22/1/2025"),  "description": "Prestige Cleaning inv 5046",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 30"},
    {"date": iso("31/1/2025"),  "description": "Prestige Cleaning inv 5062",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 31"},
    {"date": iso("7/2/2025"),   "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 87.81,   "supplier": "EDF",              "reference": "Ref 32"},
    {"date": iso("7/2/2025"),   "description": "Haringey Council — bin collection",      "category": "Cleaning",   "amount": 343.20,  "supplier": "Haringey",         "reference": "Ref 33"},
    {"date": iso("10/2/2025"),  "description": "Buildings insurance 540979517",           "category": "Insurance",  "amount": 297.98,  "supplier": "Howdens",          "reference": "Ref 34"},
    {"date": iso("27/2/2025"),  "description": "Prestige Cleaning inv 5094",              "category": "Cleaning",   "amount": 96.00,   "supplier": "Prestige Cleaning","reference": "Ref 35"},
    {"date": iso("10/3/2025"),  "description": "EDF electricity — communal lighting",    "category": "Utilities",  "amount": 78.99,   "supplier": "EDF",              "reference": "Ref 36"},
    {"date": iso("31/3/2025"),  "description": "Prestige Cleaning inv 5120",              "category": "Cleaning",   "amount": 80.00,   "supplier": "Prestige Cleaning","reference": "Ref 37"},
]

# ---------------------------------------------------------------------------
# SC income — payments received from leaseholders
# Flat numbers extracted from the Tenant column (EAGLE 1, EAGLE 3, etc.)
# Note: ref 11 (Flat 11) paid £1,916.76 — slightly more than standard, likely
# includes a top-up or arrears component.
# ---------------------------------------------------------------------------

SC_PAYMENTS = [
    {"date": iso("3/7/2024"),  "flat_num": 11, "amount": 1916.76, "reference": "Ref 11"},
    {"date": iso("8/7/2024"),  "flat_num": 5,  "amount": 1508.58, "reference": "Ref 12"},
    {"date": iso("9/7/2024"),  "flat_num": 1,  "amount": 1508.58, "reference": "Ref 13"},
    {"date": iso("10/7/2024"), "flat_num": 3,  "amount": 1508.58, "reference": "Ref 14"},
    {"date": iso("11/7/2024"), "flat_num": 12, "amount": 1508.58, "reference": "Ref 16"},
]

# ---------------------------------------------------------------------------
# Interest income
# ---------------------------------------------------------------------------

INTEREST = [
    {"date": iso("18/4/2024"), "amount": 107.36, "description": "Bank account interest — Metrobank"},
]


def get_flat_map():
    """Return {flat_number: flat_id} by scanning flat names for digits."""
    flats = db.collection("blocks").document(BLOCK_ID).collection("flats").stream()
    flat_map = {}
    for doc in flats:
        name = doc.to_dict().get("name", "")
        import re
        m = re.search(r"\d+", name)
        if m:
            flat_map[int(m.group())] = doc.id
    return flat_map


def seed():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Seeding 2024/25 data for block '{BLOCK_ID}'\n")

    # Ensure year document exists
    year_ref = (db.collection("blocks").document(BLOCK_ID)
                  .collection("years").document(YEAR_ID))
    year_doc = year_ref.get()
    if not year_doc.exists:
        print(f"Creating year document {YEAR_ID}...")
        if not DRY_RUN:
            year_ref.set({
                "label": "2024/25",
                "start_date": "2024-04-01",
                "end_date": "2025-03-31",
            })
    else:
        print(f"Year {YEAR_ID} already exists — skipping year creation.")

    exp_col = year_ref.collection("expenditure")
    income_col = year_ref.collection("income")

    # ---- Expenditure ----
    print(f"\nCreating {len(EXPENDITURE)} expenditure records...")
    for e in EXPENDITURE:
        doc = {
            "date": e["date"],
            "payment_date": e["date"],  # cash account — date is both invoice and payment date
            "fund": "sc",
            "description": e["description"],
            "category": e["category"],
            "amount": e["amount"],
            "supplier": e.get("supplier"),
            "invoice_url": None,
            "invoice_gcs_path": None,
        }
        print(f"  {e['date']}  {e['description'][:50]:<50}  £{e['amount']:>8.2f}  ({e['reference']})")
        if not DRY_RUN:
            exp_col.document(str(uuid.uuid4())).set(doc)

    # ---- Flat map for SC payments ----
    flat_map = get_flat_map()
    print(f"\nFound {len(flat_map)} flats: { {k: v[:8]+'...' for k,v in flat_map.items()} }")

    # ---- SC income ----
    print(f"\nCreating {len(SC_PAYMENTS)} leaseholder income records...")
    for p in SC_PAYMENTS:
        flat_id = flat_map.get(p["flat_num"])
        if not flat_id:
            print(f"  WARNING: No flat found with number {p['flat_num']} — skipping {p['reference']}")
            continue
        doc = {
            "type": "leaseholder",
            "fund": "sc",
            "flat_id": flat_id,
            "amount": p["amount"],
            "date": p["date"],
            "charge_year": YEAR_ID,
            "description": None,
            "reference": p["reference"],
        }
        print(f"  {p['date']}  Flat {p['flat_num']:<3}  £{p['amount']:>8.2f}  ({p['reference']})")
        if not DRY_RUN:
            income_col.document(str(uuid.uuid4())).set(doc)

    # ---- Interest income ----
    print(f"\nCreating {len(INTEREST)} interest income records...")
    for i in INTEREST:
        doc = {
            "type": "interest",
            "fund": "sc",
            "flat_id": None,
            "amount": i["amount"],
            "date": i["date"],
            "charge_year": YEAR_ID,
            "description": i["description"],
            "reference": None,
        }
        print(f"  {i['date']}  {i['description']:<50}  £{i['amount']:>8.2f}")
        if not DRY_RUN:
            income_col.document(str(uuid.uuid4())).set(doc)

    # ---- Summary ----
    total_exp = sum(e["amount"] for e in EXPENDITURE)
    total_sc  = sum(p["amount"] for p in SC_PAYMENTS)
    total_int = sum(i["amount"] for i in INTEREST)
    print(f"""
Summary
-------
Expenditure:  £{total_exp:,.2f}  ({len(EXPENDITURE)} records)
SC income:    £{total_sc:,.2f}  ({len(SC_PAYMENTS)} records)
Interest:     £{total_int:,.2f}  ({len(INTEREST)} records)
""")
    if DRY_RUN:
        print("DRY RUN — no data was written.")
    else:
        print("Done. Refresh the app to see the data.")


if __name__ == "__main__":
    seed()
