"""
One-time migration: flat top-level Firestore collections -> blocks/{block_id}/...

Run while the app is offline (Cloud Run scaled to zero or IAP blocking requests).

Usage:
    gcloud auth application-default login
    GCP_PROJECT_ID=lahiff-management python scripts/migrate_to_blocks.py

Set DRY_RUN=1 to preview without writing:
    DRY_RUN=1 GCP_PROJECT_ID=lahiff-management python scripts/migrate_to_blocks.py
"""

import os
import sys

from google.cloud import firestore

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lahiff-management")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

BLOCK_ID = "eagle-court"
BLOCK_DATA = {
    "name": "Eagle Court Management (Hornsey) Limited",
    "address": None,
    "company_number": None,
    "url": None,
}

# Old integer-year strings that exist in Firestore, e.g. ["2024", "2025", "2026"]
# The script discovers these automatically by listing the years/ collection.

db = firestore.Client(project=PROJECT_ID)


def slug_from_int_year(y: str) -> str:
    """'2025' -> '2025-26'"""
    n = int(y)
    return f"{n}-{str(n + 1)[2:]}"


def label_from_int_year(y: str) -> str:
    """'2025' -> '2025/26'"""
    n = int(y)
    return f"{n}/{str(n + 1)[2:]}"


def copy_collection(src_ref, dst_ref, transform=None):
    """Copy all documents from src collection ref to dst collection ref."""
    docs = list(src_ref.stream())
    src_path = "/".join(src_ref._path)
    dst_path = "/".join(dst_ref._path)
    print(f"    Copying {len(docs)} docs: {src_path} -> {dst_path}")
    for doc in docs:
        data = doc.to_dict()
        if transform:
            data = transform(data)
        if not DRY_RUN:
            dst_ref.document(doc.id).set(data)
    return len(docs)


def migrate():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Migrating to blocks/{BLOCK_ID}\n")

    block_ref = db.collection("blocks").document(BLOCK_ID)

    # --- 1. Create block document ---
    print(f"1. Creating block document blocks/{BLOCK_ID}")
    if not DRY_RUN:
        block_ref.set(BLOCK_DATA)

    # --- 2. Copy flats ---
    print("\n2. Copying flats/")
    n = copy_collection(
        db.collection("flats"),
        block_ref.collection("flats"),
    )
    print(f"   {n} flats copied")

    # --- 3. Copy leaseholders ---
    print("\n3. Copying leaseholders/")
    n = copy_collection(
        db.collection("leaseholders"),
        block_ref.collection("leaseholders"),
    )
    print(f"   {n} leaseholders copied")

    # --- 4. Copy years and their subcollections ---
    print("\n4. Copying years/")
    old_years = list(db.collection("years").stream())
    if not old_years:
        print("   No year documents found in top-level years/ collection.")
    for year_doc in old_years:
        old_id = year_doc.id  # e.g. "2025"
        new_id = slug_from_int_year(old_id)
        label = label_from_int_year(old_id)
        print(f"\n   years/{old_id}  ->  blocks/{BLOCK_ID}/years/{new_id}")

        old_data = year_doc.to_dict() or {}
        year_meta = {
            "label": label,
            "start_date": f"{old_id}-04-01",
            "end_date": f"{int(old_id) + 1}-03-31",
        }
        # Carry over the budget map if it exists on the year document
        if "budget" in old_data:
            year_meta["budget"] = old_data["budget"]

        new_year_ref = block_ref.collection("years").document(new_id)
        if not DRY_RUN:
            new_year_ref.set(year_meta)

        # 4a. Expenditure
        copy_collection(
            db.collection("years").document(old_id).collection("expenditure"),
            new_year_ref.collection("expenditure"),
        )

        # 4b. Income — rewrite charge_year field from "2025" -> "2025-26"
        def rewrite_charge_year(data):
            cy = data.get("charge_year")
            if cy and cy.isdigit():
                data["charge_year"] = slug_from_int_year(cy)
            return data

        copy_collection(
            db.collection("years").document(old_id).collection("income"),
            new_year_ref.collection("income"),
            transform=rewrite_charge_year,
        )

        # 4c. Payment transactions (if present)
        copy_collection(
            db.collection("years").document(old_id).collection("payment_transactions"),
            new_year_ref.collection("payment_transactions"),
            transform=rewrite_charge_year,
        )

        # 4d. Legacy payments
        copy_collection(
            db.collection("years").document(old_id).collection("payments"),
            new_year_ref.collection("payments"),
        )

    # --- 5. Summary ---
    print("\n\nMigration complete.")
    if DRY_RUN:
        print("DRY RUN — no data was written.")
    else:
        print("Verify the new data at:")
        print(f"  https://console.cloud.google.com/firestore/databases/-default-/data/blocks/{BLOCK_ID}?project={PROJECT_ID}")
        print("\nOnce verified, you can delete the old top-level collections (optional):")
        print("  flats/  leaseholders/  years/")
        print("They are no longer read by the new app code.")


if __name__ == "__main__":
    migrate()
