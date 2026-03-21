from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import Leaseholder
import uuid

router = APIRouter(prefix="/api/blocks/{block_id}/leaseholders", tags=["leaseholders"])


def _col(block_id: str):
    return get_db().collection("blocks").document(block_id).collection("leaseholders")


@router.get("/")
async def list_leaseholders(block_id: str):
    docs = _col(block_id).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_leaseholder(block_id: str, lh: Leaseholder):
    lh.id = str(uuid.uuid4())
    _col(block_id).document(lh.id).set(lh.model_dump(exclude={"id"}))
    return lh


@router.put("/{lh_id}")
async def update_leaseholder(block_id: str, lh_id: str, lh: Leaseholder):
    ref = _col(block_id).document(lh_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Leaseholder not found")
    ref.set(lh.model_dump(exclude={"id"}))
    return {"id": lh_id, **lh.model_dump(exclude={"id"})}


@router.delete("/{lh_id}")
async def delete_leaseholder(block_id: str, lh_id: str):
    ref = _col(block_id).document(lh_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Leaseholder not found")
    ref.delete()
    return {"deleted": lh_id}
