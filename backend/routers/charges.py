from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.firestore import get_db
from backend.models import Budget, Expenditure, Payment, InvoiceUploadResponse
from google.cloud import storage
import os, uuid, datetime

router = APIRouter(prefix="/api/{year}", tags=["charges"])

GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "block-management-docs")


def _year_doc(year: str):
    return get_db().collection("years").document(year)


# ---- Budget ----

@router.get("/budget")
async def get_budget(year: str):
    doc = _year_doc(year).get()
    if not doc.exists:
        return Budget().model_dump()
    return doc.to_dict().get("budget", Budget().model_dump())


@router.put("/budget")
async def save_budget(year: str, budget: Budget):
    _year_doc(year).set({"budget": budget.model_dump()}, merge=True)
    return budget


# ---- Expenditure ----

def _exp_col(year: str):
    return _year_doc(year).collection("expenditure")


@router.get("/expenditure")
async def list_expenditure(year: str, fund: str = None):
    q = _exp_col(year)
    if fund:
        q = q.where("fund", "==", fund)
    docs = q.order_by("date", direction="DESCENDING").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/expenditure")
async def create_expenditure(year: str, exp: Expenditure):
    exp.id = str(uuid.uuid4())
    _exp_col(year).document(exp.id).set(exp.model_dump(exclude={"id"}))
    return exp


@router.delete("/expenditure/{exp_id}")
async def delete_expenditure(year: str, exp_id: str):
    ref = _exp_col(year).document(exp_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    ref.delete()
    return {"deleted": exp_id}


# ---- Invoice upload ----

@router.post("/expenditure/{exp_id}/invoice", response_model=InvoiceUploadResponse)
async def upload_invoice(year: str, exp_id: str, file: UploadFile = File(...)):
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf"
    blob_name = f"{year}/invoices/{exp_id}.{ext}"
    blob = bucket.blob(blob_name)
    contents = await file.read()
    blob.upload_from_string(contents, content_type=file.content_type)

    # Generate a signed URL valid for 7 days for immediate viewing
    signed_url = blob.generate_signed_url(
        expiration=datetime.timedelta(days=7),
        method="GET",
        version="v4",
    )

    # Store the GCS path (not signed URL) permanently in Firestore
    gcs_path = f"gs://{GCS_BUCKET}/{blob_name}"
    _exp_col(year).document(exp_id).update({"invoice_gcs_path": gcs_path})

    return InvoiceUploadResponse(
        upload_url=signed_url,
        invoice_url=gcs_path,
        expenditure_id=exp_id,
    )


@router.get("/expenditure/{exp_id}/invoice-url")
async def get_invoice_url(year: str, exp_id: str):
    """Generate a fresh signed URL for viewing a stored invoice."""
    doc = _exp_col(year).document(exp_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    gcs_path = doc.to_dict().get("invoice_gcs_path")
    if not gcs_path:
        raise HTTPException(status_code=404, detail="No invoice attached")

    blob_name = gcs_path.replace(f"gs://{GCS_BUCKET}/", "")
    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(blob_name)
    signed_url = blob.generate_signed_url(
        expiration=datetime.timedelta(hours=1),
        method="GET",
        version="v4",
    )
    return {"url": signed_url}


# ---- Payments ----

def _pay_col(year: str):
    return _year_doc(year).collection("payments")


@router.get("/payments")
async def list_payments(year: str):
    docs = _pay_col(year).stream()
    return {d.id: d.to_dict() for d in docs}


@router.put("/payments/{flat_id}")
async def update_payment(year: str, flat_id: str, payment: Payment):
    _pay_col(year).document(flat_id).set(payment.model_dump(exclude={"flat_id"}))
    return payment
