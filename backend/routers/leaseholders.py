from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import Leaseholder
import uuid

router = APIRouter(prefix="/api/{year}/leaseholders", tags=["leaseholders"])


def _col(year: str):
    return get_db().collection("years").document(year).collection("leaseholders")


@router.get("/")
async def list_leaseholders(year: str):
    docs = _col(year).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_leaseholder(year: str, lh: Leaseholder):
    lh.id = str(uuid.uuid4())
    _col(year).document(lh.id).set(lh.model_dump(exclude={"id"}))
    return lh


@router.put("/{lh_id}")
async def update_leaseholder(year: str, lh_id: str, lh: Leaseholder):
    ref = _col(year).document(lh_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Leaseholder not found")
    ref.set(lh.model_dump(exclude={"id"}))
    return {"id": lh_id, **lh.model_dump(exclude={"id"})}


@router.delete("/{lh_id}")
async def delete_leaseholder(year: str, lh_id: str):
    ref = _col(year).document(lh_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Leaseholder not found")
    ref.delete()
    return {"deleted": lh_id}
