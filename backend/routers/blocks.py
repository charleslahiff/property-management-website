from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import Block
import uuid

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


def _col():
    return get_db().collection("blocks")


@router.get("/")
async def list_blocks():
    docs = _col().stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_block(block: Block):
    block.id = str(uuid.uuid4())
    _col().document(block.id).set(block.model_dump(exclude={"id"}))
    return block


@router.put("/{block_id}")
async def update_block(block_id: str, block: Block):
    ref = _col().document(block_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Block not found")
    ref.update(block.model_dump(exclude={"id"}, exclude_none=False))
    return {"id": block_id, **block.model_dump(exclude={"id"})}


@router.delete("/{block_id}")
async def delete_block(block_id: str):
    ref = _col().document(block_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Block not found")
    block_ref = _col().document(block_id)
    if next(block_ref.collection("flats").limit(1).stream(), None):
        raise HTTPException(status_code=409, detail="Block still has flats — remove them first")
    ref.delete()
    return {"deleted": block_id}


@router.get("/{block_id}/opening_arrears")
async def get_opening_arrears(block_id: str):
    doc = _col().document(block_id).get()
    if not doc.exists:
        return {}
    return doc.to_dict().get("opening_arrears", {})


@router.put("/{block_id}/opening_arrears")
async def save_opening_arrears(block_id: str, data: dict):
    _col().document(block_id).update({"opening_arrears": data})
    return data


@router.get("/{block_id}/arrears")
async def get_arrears(block_id: str, exclude_year: str = None):
    """Return outstanding balances per flat per year across all financial years.

    Optionally exclude a year (e.g. the current year) to show only prior-year arrears.
    """
    db = get_db()
    block_ref = _col().document(block_id)

    # Load flats
    flat_docs = block_ref.collection("flats").stream()
    flats = {d.id: d.to_dict() for d in flat_docs}

    # Load all years
    year_docs = block_ref.collection("years").stream()

    results = []
    for yd in year_docs:
        year_id = yd.id
        if exclude_year and year_id >= exclude_year:
            continue
        year_data = yd.to_dict() or {}
        budget = year_data.get("budget", {})
        sc_budget = float(budget.get("sc", 0))
        rf_budget = float(budget.get("rf", 0))

        # Load income for this year
        income_docs = block_ref.collection("years").document(year_id).collection("income").stream()
        income_by_flat: dict[str, dict] = {}
        for inc in income_docs:
            d = inc.to_dict()
            if d.get("type") != "leaseholder" or not d.get("flat_id"):
                continue
            fid = d["flat_id"]
            fund = d.get("fund", "")
            amt = float(d.get("amount", 0))
            if fid not in income_by_flat:
                income_by_flat[fid] = {"sc": 0.0, "rf": 0.0}
            if fund in ("sc", "rf"):
                income_by_flat[fid][fund] += amt

        # Compute outstanding per flat
        for flat_id, flat in flats.items():
            sc_share = float(flat.get("sc_share", 0))
            rf_share = float(flat.get("rf_share", 0))
            sc_owed = sc_budget * sc_share / 100
            rf_owed = rf_budget * rf_share / 100
            sc_paid = income_by_flat.get(flat_id, {}).get("sc", 0.0)
            rf_paid = income_by_flat.get(flat_id, {}).get("rf", 0.0)
            sc_out = round(sc_owed - sc_paid, 2)
            rf_out = round(rf_owed - rf_paid, 2)
            if sc_out > 0.005 or rf_out > 0.005:
                results.append({
                    "flat_id": flat_id,
                    "year_id": year_id,
                    "year_label": year_data.get("label", year_id),
                    "sc_owed": round(sc_owed, 2),
                    "sc_paid": round(sc_paid, 2),
                    "sc_outstanding": sc_out,
                    "rf_owed": round(rf_owed, 2),
                    "rf_paid": round(rf_paid, 2),
                    "rf_outstanding": rf_out,
                })

    return results
