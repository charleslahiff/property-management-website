"""
Seed reserve fund income for 2025/26 for Eagle Court.

Source: Metrobank reserve fund account statement.
All transactions are tagged to charge year 2025-26 (including the two
March 2025 advance payments from Charles Lahiff).

Run from the project root:
    gcloud auth application-default login
    GCP_PROJECT_ID=lahiff-management python scripts/seed_rf_2025_26.py

Dry run (preview only):
    $env:DRY_RUN="1"; $env:GCP_PROJECT_ID="lahiff-management"; python scripts/seed_rf_2025_26.py
"""

import os
import re
import uuid
from datetime import datetime
from google.cloud import firestore

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lahiff-management")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

BLOCK_ID = "eagle-court"
YEAR_ID = "2025-26"

db = firestore.Client(project=PROJECT_ID)


def iso(date_str):
    """Convert DD/MM/YYYY to YYYY-MM-DD."""
    return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Leaseholder RF payments
# Flat numbers derived from the payment reference codes in the bank statement.
# Note: two 06/03/2025 entries by Charles Lahiff (£100 each) are both assigned
# to Flat 5. The first has reference RFF12LAH which may contain a typo — check
# bank statement if uncertain.
# ---------------------------------------------------------------------------

RF_PAYMENTS = [
    # March 2025 advance payments (charge year 2025-26)
    {"date": iso("06/03/2025"), "flat_num": 5,  "amount": 100.00,  "reference": "P7QSETF1B8LM520BUE", "note": "Advance — ref RFF12LAH (possible typo, assigned Flat 5)"},
    {"date": iso("06/03/2025"), "flat_num": 5,  "amount": 100.00,  "reference": "PP5XXBGHHFX3MER3R6"},

    # April 2025
    {"date": iso("02/04/2025"), "flat_num": 5,  "amount": 800.00,  "reference": "PCPSV4W1K5NDDWH3VK"},
    {"date": iso("02/04/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "400000001540375171"},
    {"date": iso("09/04/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBPNDHY"},
    {"date": iso("11/04/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "100000001531609685"},
    {"date": iso("15/04/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},

    # May 2025
    {"date": iso("01/05/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "P7F7MHUFH29EB3ML9N"},
    {"date": iso("06/05/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKPLGL"},
    {"date": iso("06/05/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "300000001558100468"},
    {"date": iso("08/05/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBPPYFQ"},
    {"date": iso("15/05/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("27/05/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "400000001569762692"},

    # June 2025
    {"date": iso("02/06/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "PEL45747J998ZKJMQQ"},
    {"date": iso("03/06/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "300000001574412792"},
    {"date": iso("04/06/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBPRQHR"},
    {"date": iso("06/06/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKQRTB"},
    {"date": iso("16/06/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("26/06/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "100000001574522570"},

    # July 2025
    {"date": iso("01/07/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "PQVIRY757JJ295D72B"},
    {"date": iso("02/07/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBPTJTH"},
    {"date": iso("07/07/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKRYLV"},
    {"date": iso("09/07/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "100000001582381266"},
    {"date": iso("14/07/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKSGCW"},
    {"date": iso("15/07/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("21/07/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKSMTH"},

    # August 2025
    {"date": iso("01/08/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "P1XH19MYQOJVFEBELP"},
    {"date": iso("05/08/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "500000001606704399"},
    {"date": iso("06/08/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBPWNQF"},
    {"date": iso("08/08/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKTGLP"},
    {"date": iso("15/08/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("20/08/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "100000001605620895"},
    {"date": iso("27/08/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKTXPS"},

    # September 2025
    {"date": iso("01/09/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "P15ZV1WGGZCGSW164N"},
    {"date": iso("01/09/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "100000001612478476"},
    {"date": iso("04/09/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBPYHTW"},
    {"date": iso("15/09/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("18/09/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKVVLK"},
    {"date": iso("19/09/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "100000001622762986"},
    {"date": iso("24/09/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "300000001637924204"},

    # October 2025
    {"date": iso("01/10/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "PJ88GR8L2AQV6ER791"},
    {"date": iso("06/10/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKWPMM"},
    {"date": iso("08/10/2025"), "flat_num": 11, "amount": 1000.00, "reference": "00151281632BBQBKXJ"},
    {"date": iso("14/10/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "600000001646326074"},
    {"date": iso("15/10/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "400000001651748497"},
    {"date": iso("15/10/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("20/10/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "00151287632BBKXCKG"},
    {"date": iso("30/10/2025"), "flat_num": 11, "amount": 1000.00, "reference": "HUBX9B1A4A31A8A75B"},

    # November 2025
    {"date": iso("03/11/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "PZTHRZECMYNFQYPH7H"},
    {"date": iso("10/11/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "500000001661442902"},
    {"date": iso("17/11/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "HUBX21AD6619C7C2F4"},
    {"date": iso("17/11/2025"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},
    {"date": iso("21/11/2025"), "flat_num": 1,  "amount": 1000.00, "reference": "600000001667803753"},

    # December 2025
    {"date": iso("01/12/2025"), "flat_num": 5,  "amount": 1000.00, "reference": "PJ5Z2D6IYNHTML86MA"},
    {"date": iso("01/12/2025"), "flat_num": 11, "amount": 1000.00, "reference": "HUBXB6219A584F05EC"},
    {"date": iso("11/12/2025"), "flat_num": 3,  "amount": 1000.00, "reference": "600000001680049390"},
    {"date": iso("29/12/2025"), "flat_num": 9,  "amount": 1000.00, "reference": "HUBX93F35C900577CB"},

    # January 2026
    {"date": iso("02/01/2026"), "flat_num": 5,  "amount": 1000.00, "reference": "PXSYB0HXK89DINIA40"},
    {"date": iso("05/01/2026"), "flat_num": 1,  "amount": 1000.00, "reference": "500000001693891254"},
    {"date": iso("08/01/2026"), "flat_num": 3,  "amount": 1000.00, "reference": "600000001695584067"},
    {"date": iso("14/01/2026"), "flat_num": 11, "amount": 1000.00, "reference": "HUBXF439EB1595BB1F"},
    {"date": iso("22/01/2026"), "flat_num": 1,  "amount": 1000.00, "reference": "100000001693494497"},
    {"date": iso("26/01/2026"), "flat_num": 9,  "amount": 1000.00, "reference": "HUBXEBA8D0E8AAEEEC"},
    {"date": iso("26/01/2026"), "flat_num": 12, "amount": 1000.00, "reference": "OWEN NC RF F12 OWE"},

    # February 2026
    {"date": iso("02/02/2026"), "flat_num": 5,  "amount": 1000.00, "reference": "PXSYB0HXK89DINIA40"},
    {"date": iso("04/02/2026"), "flat_num": 3,  "amount": 1000.00, "reference": "200000001706649715"},
    {"date": iso("05/02/2026"), "flat_num": 11, "amount": 1000.00, "reference": "HUBXCF7C2202C2BD18"},
    {"date": iso("06/02/2026"), "flat_num": 3,  "amount": 1000.00, "reference": "200000001707820853"},
    {"date": iso("12/02/2026"), "flat_num": 1,  "amount": 1000.00, "reference": "500000001714718840"},
]

# ---------------------------------------------------------------------------
# Interest income
# ---------------------------------------------------------------------------

RF_INTEREST = [
    {"date": iso("31/03/2025"), "amount": 0.17,  "description": "Metrobank interest — Mar 2025"},
    {"date": iso("30/04/2025"), "amount": 3.69,  "description": "Metrobank interest — Apr 2025"},
    {"date": iso("30/05/2025"), "amount": 8.05,  "description": "Metrobank interest — May 2025"},
    {"date": iso("30/06/2025"), "amount": 13.99, "description": "Metrobank interest — Jun 2025"},
    {"date": iso("31/07/2025"), "amount": 19.88, "description": "Metrobank interest — Jul 2025"},
    {"date": iso("29/08/2025"), "amount": 23.54, "description": "Metrobank interest — Aug 2025"},
    {"date": iso("30/09/2025"), "amount": 32.28, "description": "Metrobank interest — Sep 2025"},
    {"date": iso("31/10/2025"), "amount": 36.62, "description": "Metrobank interest — Oct 2025"},
    {"date": iso("28/11/2025"), "amount": 35.50, "description": "Metrobank interest — Nov 2025"},
    {"date": iso("31/12/2025"), "amount": 46.09, "description": "Metrobank interest — Dec 2025"},
    {"date": iso("30/01/2026"), "amount": 45.90, "description": "Metrobank interest — Jan 2026"},
]


def get_flat_map():
    flats = db.collection("blocks").document(BLOCK_ID).collection("flats").stream()
    flat_map = {}
    for doc in flats:
        name = doc.to_dict().get("name", "")
        m = re.search(r"\d+", name)
        if m:
            flat_map[int(m.group())] = doc.id
    return flat_map


def seed():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Seeding RF income 2025/26 for block '{BLOCK_ID}'\n")

    year_ref = (db.collection("blocks").document(BLOCK_ID)
                  .collection("years").document(YEAR_ID))
    if not year_ref.get().exists:
        print(f"Creating year document {YEAR_ID}...")
        if not DRY_RUN:
            year_ref.set({"label": "2025/26", "start_date": "2025-04-01", "end_date": "2026-03-31"})
    else:
        print(f"Year {YEAR_ID} already exists.")

    income_col = year_ref.collection("income")
    flat_map = get_flat_map()
    print(f"Found {len(flat_map)} flats: { {k: v[:8]+'...' for k, v in sorted(flat_map.items())} }\n")

    # ---- Leaseholder RF payments ----
    print(f"Creating {len(RF_PAYMENTS)} leaseholder RF payment records...")
    skipped = []
    for p in RF_PAYMENTS:
        flat_id = flat_map.get(p["flat_num"])
        note = p.get("note", "")
        if not flat_id:
            print(f"  WARNING: No flat found for Flat {p['flat_num']} — skipping {p['date']} £{p['amount']:.2f}")
            skipped.append(p)
            continue
        flag = " ⚠" if note else ""
        print(f"  {p['date']}  Flat {p['flat_num']:<3}  £{p['amount']:>8.2f}  {p['reference'][:30]}{flag}")
        if note:
            print(f"           NOTE: {note}")
        if not DRY_RUN:
            income_col.document(str(uuid.uuid4())).set({
                "type": "leaseholder",
                "fund": "rf",
                "flat_id": flat_id,
                "amount": p["amount"],
                "date": p["date"],
                "charge_year": YEAR_ID,
                "description": None,
                "reference": p["reference"],
            })

    # ---- Interest ----
    print(f"\nCreating {len(RF_INTEREST)} interest records...")
    for i in RF_INTEREST:
        print(f"  {i['date']}  {i['description']:<45}  £{i['amount']:>7.2f}")
        if not DRY_RUN:
            income_col.document(str(uuid.uuid4())).set({
                "type": "interest",
                "fund": "rf",
                "flat_id": None,
                "amount": i["amount"],
                "date": i["date"],
                "charge_year": YEAR_ID,
                "description": i["description"],
                "reference": None,
            })

    # ---- Summary ----
    total_lh = sum(p["amount"] for p in RF_PAYMENTS if flat_map.get(p["flat_num"]))
    total_int = sum(i["amount"] for i in RF_INTEREST)

    by_flat = {}
    for p in RF_PAYMENTS:
        if flat_map.get(p["flat_num"]):
            by_flat[p["flat_num"]] = by_flat.get(p["flat_num"], 0) + p["amount"]

    print(f"""
Summary by flat
---------------""")
    for fn in sorted(by_flat):
        print(f"  Flat {fn:<3}  £{by_flat[fn]:,.2f}")
    print(f"""
Leaseholder payments: £{total_lh:,.2f}  ({len(RF_PAYMENTS) - len(skipped)} records)
Interest:             £{total_int:,.2f}  ({len(RF_INTEREST)} records)
Skipped:              {len(skipped)} records
""")

    if skipped:
        print("Skipped entries (flat not found):")
        for p in skipped:
            print(f"  Flat {p['flat_num']}  {p['date']}  £{p['amount']:.2f}")

    if DRY_RUN:
        print("\nDRY RUN — no data was written.")
    else:
        print("Done. Refresh the app to see the data.")


if __name__ == "__main__":
    seed()
