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
