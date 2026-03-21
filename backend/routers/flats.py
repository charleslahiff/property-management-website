from fastapi import APIRouter, HTTPException
from backend.firestore import get_db
from backend.models import Flat
import uuid

router = APIRouter(prefix="/api/{year}/flats", tags=["flats"])


def _col(year: str):
    return get_db().collection("years").document(year).collection("flats")


@router.get("/")
async def list_flats(year: str):
    docs = _col(year).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
async def create_flat(year: str, flat: Flat):
    flat.id = str(uuid.uuid4())
    _col(year).document(flat.id).set(flat.model_dump(exclude={"id"}))
    return flat


@router.put("/{flat_id}")
async def update_flat(year: str, flat_id: str, flat: Flat):
    ref = _col(year).document(flat_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Flat not found")
    ref.set(flat.model_dump(exclude={"id"}))
    return {"id": flat_id, **flat.model_dump(exclude={"id"})}


@router.delete("/{flat_id}")
async def delete_flat(year: str, flat_id: str):
    ref = _col(year).document(flat_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Flat not found")
    ref.delete()
    return {"deleted": flat_id}
