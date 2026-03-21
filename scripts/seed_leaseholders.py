"""
Seed flats and leaseholders for Eagle Court from the owners spreadsheet.

Run from the project root:
    gcloud auth application-default login
    GCP_PROJECT_ID=lahiff-management python scripts/seed_leaseholders.py

Set DRY_RUN=1 to preview without writing:
    $env:DRY_RUN="1"; $env:GCP_PROJECT_ID="lahiff-management"; python scripts/seed_leaseholders.py

NOTE: sc_share and rf_share are set to 0 for all flats.
      Update them in the app (Flats page) once you have the lease percentages.
"""

import os
import uuid
from google.cloud import firestore

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lahiff-management")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

BLOCK_ID = "eagle-court"

db = firestore.Client(project=PROJECT_ID)

# ---------------------------------------------------------------------------
# Source data
# ---------------------------------------------------------------------------

OWNERS = [
    {"name": "Helen Anne Mcfall",       "flat": "Flat 1",  "sof": False, "email": "helen-mcfall@hotmail.co.uk"},
    {"name": "Andrew Lamont",           "flat": "Flat 2",  "sof": True,  "email": "lamont.andrew@me.com"},
    {"name": "Dean Williamson",         "flat": "Flat 3",  "sof": True,  "email": "deanwilliamson@tiscali.co.uk"},
    {"name": "Maria Cristina Refolo",   "flat": "Flat 4",  "sof": False, "email": "crefolo@hotmail.com"},
    {"name": "Charles Lahiff",          "flat": "Flat 5",  "sof": True,  "email": "charleslahiff@hotmail.co.uk"},
    {"name": "Maria Arroyave",          "flat": "Flat 6",  "sof": True,  "email": "maria@mariaarroyave.co.uk"},
    {"name": "Carmen Marie",            "flat": "Flat 7",  "sof": True,  "email": "carmen.lb@mac.com"},
    {"name": "Paul Adrian Munro",       "flat": "Flat 8",  "sof": False, "email": "statgill@hotmail.com"},
    {"name": "Deborah Irene Thompson",  "flat": "Flat 9",  "sof": False, "email": "deb49thompson@gmail.com"},
    {"name": "Simon Reynolds",          "flat": "Flat 10", "sof": True,  "email": "simonreynoldscommando@gmail.com"},
    {"name": "David Charles",           "flat": "Flat 11", "sof": True,  "email": "charlie200@btinternet.com"},
    {"name": "Nick Owen",               "flat": "Flat 12", "sof": True,  "email": "nowen@doctors.org.uk"},
]


def seed():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Seeding flats and leaseholders for block '{BLOCK_ID}'\n")

    block_ref = db.collection("blocks").document(BLOCK_ID)
    flats_col = block_ref.collection("flats")
    lh_col = block_ref.collection("leaseholders")

    # Check block exists
    if not block_ref.get().exists:
        print(f"ERROR: Block '{BLOCK_ID}' not found in Firestore.")
        print("Run the migration script first, or create the block in the app.")
        return

    # Build map of existing flats by name so we don't duplicate
    existing_flats = {d.to_dict().get("name"): d.id for d in flats_col.stream()}
    print(f"Existing flats: {list(existing_flats.keys()) or 'none'}\n")

    flat_id_map = {}  # flat name -> flat_id

    for row in OWNERS:
        flat_name = row["flat"]

        # ---- Create flat if it doesn't exist ----
        if flat_name in existing_flats:
            flat_id = existing_flats[flat_name]
            print(f"  Flat exists:  {flat_name} ({flat_id[:8]}...)")
        else:
            flat_id = str(uuid.uuid4())
            flat_doc = {
                "name": flat_name,
                "sc_share": 0.0,   # set correct shares in the app
                "rf_share": 0.0,
                "share_of_freehold": row["sof"],
            }
            print(f"  Creating flat: {flat_name}  SOF={'Yes' if row['sof'] else 'No'}")
            if not DRY_RUN:
                flats_col.document(flat_id).set(flat_doc)

        flat_id_map[flat_name] = flat_id

        # ---- Create leaseholder ----
        lh_doc = {
            "flat_id": flat_id,
            "name": row["name"],
            "email": row["email"],
            "effective_date": None,
            "expiry_date": None,
        }
        print(f"             -> {row['name']} ({row['email']})")
        if not DRY_RUN:
            lh_col.document(str(uuid.uuid4())).set(lh_doc)

    print(f"""
Summary
-------
Flats:        {len(OWNERS)} (created or confirmed)
Leaseholders: {len(OWNERS)}

Next step: open the Flats page in the app and set sc_share / rf_share
for each flat. Shares must total 100%.
""")
    if DRY_RUN:
        print("DRY RUN — no data was written.")
    else:
        print("Done. Refresh the app to see the data.")


if __name__ == "__main__":
    seed()
