from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import Leaseholder
import uuid

router = APIRouter(prefix="/api/leaseholders", tags=["leaseholders"])


def _col():
    return get_db().collection("leaseholders")


@router.get("/")
async def list_leaseholders():
    docs = _col().stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_leaseholder(lh: Leaseholder):
    lh.id = str(uuid.uuid4())
    _col().document(lh.id).set(lh.model_dump(exclude={"id"}))
    return lh


@router.put("/{lh_id}")
async def update_leaseholder(lh_id: str, lh: Leaseholder):
    ref = _col().document(lh_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Leaseholder not found")
    ref.set(lh.model_dump(exclude={"id"}))
    return {"id": lh_id, **lh.model_dump(exclude={"id"})}


@router.delete("/{lh_id}")
async def delete_leaseholder(lh_id: str):
    ref = _col().document(lh_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Leaseholder not found")
    ref.delete()
    return {"deleted": lh_id}
