from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import FinancialYear

router = APIRouter(prefix="/api/blocks/{block_id}/years", tags=["years"])


def _col(block_id: str):
    return get_db().collection("blocks").document(block_id).collection("years")


@router.get("/")
async def list_years(block_id: str):
    docs = _col(block_id).order_by("start_date").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_year(block_id: str, fy: FinancialYear):
    slug = fy.label.replace("/", "-").strip()
    if not fy.id:
        fy.id = slug
    if fy.start_date >= fy.end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    ref = _col(block_id).document(fy.id)
    if ref.get().exists:
        raise HTTPException(status_code=409, detail="A year with this ID already exists")
    ref.set(fy.model_dump(exclude={"id"}))
    return fy


@router.put("/{year_id}")
async def update_year(block_id: str, year_id: str, fy: FinancialYear):
    ref = _col(block_id).document(year_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Year not found")
    if fy.start_date >= fy.end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    ref.update(fy.model_dump(exclude={"id"}, exclude_none=False))
    return {"id": year_id, **fy.model_dump(exclude={"id"})}


@router.delete("/{year_id}")
async def delete_year(block_id: str, year_id: str):
    ref = _col(block_id).document(year_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Year not found")
    if next(ref.collection("expenditure").limit(1).stream(), None):
        raise HTTPException(status_code=409, detail="Year has expenditure — delete it first")
    if next(ref.collection("income").limit(1).stream(), None):
        raise HTTPException(status_code=409, detail="Year has income — delete it first")
    ref.delete()
    return {"deleted": year_id}
