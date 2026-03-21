from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import Flat
import uuid

router = APIRouter(prefix="/api/flats", tags=["flats"])


def _col():
    return get_db().collection("flats")


@router.get("/")
async def list_flats():
    docs = _col().stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_flat(flat: Flat):
    flat.id = str(uuid.uuid4())
    _col().document(flat.id).set(flat.model_dump(exclude={"id"}))
    return flat


@router.put("/{flat_id}")
async def update_flat(flat_id: str, flat: Flat):
    ref = _col().document(flat_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Flat not found")
    ref.set(flat.model_dump(exclude={"id"}))
    return {"id": flat_id, **flat.model_dump(exclude={"id"})}


@router.delete("/{flat_id}")
async def delete_flat(flat_id: str):
    ref = _col().document(flat_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Flat not found")
    ref.delete()
    return {"deleted": flat_id}
