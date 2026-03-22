from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.firestore import get_db
from backend.models import Budget, Expenditure, Payment, InvoiceUploadResponse, Income
from google.cloud import storage
import os, uuid, datetime

router = APIRouter(prefix="/api/blocks/{block_id}/years/{year_id}", tags=["charges"])

GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "lahiff-management-docs")


def _year_doc(block_id: str, year_id: str):
    return (get_db().collection("blocks").document(block_id)
            .collection("years").document(year_id))


# ---- Prior year closing balance ----

@router.get("/prior_closing")
async def get_prior_closing(block_id: str, year_id: str):
    """Return the closing balance of the year immediately before year_id.

    closing = opening_balance + income - expenditure for that year.
    Returns {sc: 0, rf: 0} if there is no prior year.
    """
    block_ref = get_db().collection("blocks").document(block_id)

    # Find the highest year_id strictly less than the current one
    year_docs = block_ref.collection("years").stream()
    prior_id = None
    for yd in year_docs:
        if yd.id < year_id:
            if prior_id is None or yd.id > prior_id:
                prior_id = yd.id

    if prior_id is None:
        return {"sc": 0.0, "rf": 0.0}

    prior_ref = block_ref.collection("years").document(prior_id)
    prior_data = (prior_ref.get().to_dict() or {})
    budget = prior_data.get("budget", {})
    sc = float(budget.get("sc_opening_balance", 0))
    rf = float(budget.get("rf_opening_balance", 0))

    for inc in prior_ref.collection("income").stream():
        d = inc.to_dict()
        amt = float(d.get("amount", 0))
        if d.get("fund") == "sc":
            sc += amt
        elif d.get("fund") == "rf":
            rf += amt

    for exp in prior_ref.collection("expenditure").stream():
        d = exp.to_dict()
        amt = float(d.get("amount", 0))
        if d.get("fund") == "sc":
            sc -= amt
        elif d.get("fund") == "rf":
            rf -= amt

    return {"sc": round(sc, 2), "rf": round(rf, 2)}


# ---- Budget ----

@router.get("/budget")
async def get_budget(block_id: str, year_id: str):
    doc = _year_doc(block_id, year_id).get()
    if not doc.exists:
        return Budget().model_dump()
    return doc.to_dict().get("budget", Budget().model_dump())


@router.put("/budget")
async def save_budget(block_id: str, year_id: str, budget: Budget):
    _year_doc(block_id, year_id).set({"budget": budget.model_dump()}, merge=True)
    return budget


# ---- Expenditure ----

def _exp_col(block_id: str, year_id: str):
    return _year_doc(block_id, year_id).collection("expenditure")


@router.get("/expenditure")
async def list_expenditure(block_id: str, year_id: str, fund: str = None):
    q = _exp_col(block_id, year_id)
    if fund:
        q = q.where("fund", "==", fund)
    docs = q.order_by("date", direction="DESCENDING").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/expenditure")
async def create_expenditure(block_id: str, year_id: str, exp: Expenditure):
    exp.id = str(uuid.uuid4())
    _exp_col(block_id, year_id).document(exp.id).set(exp.model_dump(exclude={"id"}))
    return exp


@router.put("/expenditure/{exp_id}")
async def update_expenditure(block_id: str, year_id: str, exp_id: str, exp: Expenditure):
    ref = _exp_col(block_id, year_id).document(exp_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    ref.update(exp.model_dump(exclude={"id"}, exclude_none=False))
    return {"id": exp_id, **exp.model_dump(exclude={"id"})}


@router.delete("/expenditure/{exp_id}")
async def delete_expenditure(block_id: str, year_id: str, exp_id: str):
    ref = _exp_col(block_id, year_id).document(exp_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    ref.delete()
    return {"deleted": exp_id}


# ---- Invoice parsing ----

@router.post("/expenditure/parse-invoice")
async def parse_invoice(block_id: str, year_id: str, file: UploadFile = File(...)):
    """Extract invoice fields from a PDF using the Claude API."""
    import pdfplumber, io, anthropic, json as _json

    contents = await file.read()
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception:
        return {}

    if not text.strip():
        return {}  # scanned/image-only PDF — caller falls back to manual entry

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                "Extract fields from this invoice text. "
                "Reply with JSON only, no explanation: "
                '{"invoice_date": "YYYY-MM-DD or null", '
                '"amount": number_or_null, '
                '"supplier": "string or null", '
                '"description": "string or null"}\n\n'
                + text[:4000]
            )
        }]
    )
    try:
        return _json.loads(msg.content[0].text)
    except Exception:
        return {}


# ---- Invoice upload ----

@router.post("/expenditure/{exp_id}/invoice", response_model=InvoiceUploadResponse)
async def upload_invoice(block_id: str, year_id: str, exp_id: str, file: UploadFile = File(...)):
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf"
    blob_name = f"{block_id}/{year_id}/invoices/{exp_id}.{ext}"
    blob = bucket.blob(blob_name)
    contents = await file.read()
    blob.upload_from_string(contents, content_type=file.content_type)

    signed_url = blob.generate_signed_url(
        expiration=datetime.timedelta(days=7),
        method="GET",
        version="v4",
    )

    gcs_path = f"gs://{GCS_BUCKET}/{blob_name}"
    _exp_col(block_id, year_id).document(exp_id).update({"invoice_gcs_path": gcs_path})

    return InvoiceUploadResponse(
        upload_url=signed_url,
        invoice_url=gcs_path,
        expenditure_id=exp_id,
    )


@router.get("/expenditure/{exp_id}/invoice-url")
async def get_invoice_url(block_id: str, year_id: str, exp_id: str):
    """Generate a fresh signed URL for viewing a stored invoice."""
    doc = _exp_col(block_id, year_id).document(exp_id).get()
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


# ---- Payments (legacy — kept for backwards compatibility) ----

def _pay_col(block_id: str, year_id: str):
    return _year_doc(block_id, year_id).collection("payments")


@router.get("/payments")
async def list_payments(block_id: str, year_id: str):
    docs = _pay_col(block_id, year_id).stream()
    return {d.id: d.to_dict() for d in docs}


@router.put("/payments/{flat_id}")
async def update_payment(block_id: str, year_id: str, flat_id: str, payment: Payment):
    _pay_col(block_id, year_id).document(flat_id).set(payment.model_dump(exclude={"flat_id"}))
    return payment


# ---- Income ----

def _income_col(block_id: str, year_id: str):
    return _year_doc(block_id, year_id).collection("income")


@router.get("/income")
async def list_income(block_id: str, year_id: str):
    return [{"id": d.id, **d.to_dict()} for d in _income_col(block_id, year_id).stream()]


@router.post("/income")
async def create_income(block_id: str, year_id: str, item: Income):
    item.id = str(uuid.uuid4())
    _income_col(block_id, year_id).document(item.id).set(item.model_dump(exclude={"id"}))
    return item


@router.delete("/income/{income_id}")
async def delete_income(block_id: str, year_id: str, income_id: str):
    ref = _income_col(block_id, year_id).document(income_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Income item not found")
    ref.delete()
    return {"deleted": income_id}
