"""Generate service charge demand letters as PDF.

Endpoints:
  GET /api/blocks/{block_id}/years/{year_id}/demands/{flat_id}
      → single demand PDF for one flat

  GET /api/blocks/{block_id}/years/{year_id}/demands
      → zip archive containing one PDF per flat
"""

import datetime
import io
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.firestore import get_db

router = APIRouter(prefix="/api/blocks/{block_id}/years/{year_id}", tags=["demands"])

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _fmt_date(d: datetime.date) -> str:
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def _fmt_money(n: float) -> str:
    return f"\xa3{n:,.2f}"  # £ sign


def _active_lh(all_lh: list, flat_id: str) -> dict | None:
    today = datetime.date.today().isoformat()
    candidates = [
        lh for lh in all_lh
        if lh.get("flat_id") == flat_id
        and not (lh.get("expiry_date") and lh["expiry_date"] < today)
    ]
    candidates.sort(key=lambda x: x.get("effective_date") or "", reverse=True)
    return candidates[0] if candidates else None


def _build_pdf(block: dict, year_id: str, year_data: dict, flat: dict, lh: dict | None) -> bytes:
    from fpdf import FPDF

    budget = year_data.get("budget", {})
    year_label = year_data.get("label", year_id)
    due_date_raw = budget.get("due_date") or ""
    billing_freq = budget.get("billing_freq", "annual")

    block_name = block.get("name", "")
    block_address = (block.get("address") or "").replace("\r", "")
    bank_name = block.get("bank_account_name") or ""
    sort_code = block.get("bank_sort_code") or ""
    account_number = block.get("bank_account_number") or ""

    lh_name = lh.get("name", "The Leaseholder") if lh else "The Leaseholder"
    flat_name = flat.get("name", "")
    sc_share = float(flat.get("sc_share") or 0)
    rf_share = float(flat.get("rf_share") or 0)
    sc_budget = float(budget.get("sc") or 0)
    rf_budget = float(budget.get("rf") or 0)
    sc_amount = sc_budget * sc_share / 100
    rf_amount = rf_budget * rf_share / 100
    total = sc_amount + rf_amount

    today_str = _fmt_date(datetime.date.today())

    due_display = ""
    if due_date_raw:
        try:
            due_display = _fmt_date(datetime.date.fromisoformat(due_date_raw))
        except ValueError:
            due_display = due_date_raw

    freq_text = "annually" if billing_freq == "annual" else "quarterly"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(25, 22, 25)
    pdf.set_auto_page_break(auto=True, margin=22)

    # ── Block header ──────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, block_name, new_x="LMARGIN", new_y="NEXT")
    if block_address:
        pdf.set_font("Helvetica", "", 9)
        for line in block_address.split("\n"):
            if line.strip():
                pdf.cell(0, 5, line.strip(), new_x="LMARGIN", new_y="NEXT")

    # Date — right-aligned
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, today_str, align="R", new_x="LMARGIN", new_y="NEXT")

    # Separator
    pdf.ln(2)
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 160, pdf.get_y())
    pdf.ln(6)

    # ── Addressee ─────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, lh_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, flat_name, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Subject ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"SERVICE CHARGE DEMAND \u2014 {year_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Intro ─────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 6,
        f"We hereby demand payment of the service charges and reserve fund contributions "
        f"payable {freq_text} in respect of your lease of {flat_name} "
        f"for the financial year {year_label}.",
    )
    pdf.ln(5)

    # ── Charge table ──────────────────────────────────────────────
    col = [95, 30, 35]
    pdf.set_fill_color(240, 240, 238)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col[0], 8, "Charge", border=1, fill=True)
    pdf.cell(col[1], 8, "Share", border=1, fill=True, align="C")
    pdf.cell(col[2], 8, "Amount", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    if sc_budget > 0:
        pdf.cell(col[0], 8, "Service charge", border=1)
        pdf.cell(col[1], 8, f"{sc_share:g}%", border=1, align="C")
        pdf.cell(col[2], 8, _fmt_money(sc_amount), border=1, align="R")
        pdf.ln()
    if rf_budget > 0:
        pdf.cell(col[0], 8, "Reserve fund contribution", border=1)
        pdf.cell(col[1], 8, f"{rf_share:g}%", border=1, align="C")
        pdf.cell(col[2], 8, _fmt_money(rf_amount), border=1, align="R")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 238)
    pdf.cell(col[0] + col[1], 8, "Total payable", border=1, fill=True)
    pdf.cell(col[2], 8, _fmt_money(total), border=1, fill=True, align="R")
    pdf.ln()
    pdf.ln(6)

    # ── Due date ──────────────────────────────────────────────────
    if due_display:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"Payment due: {due_display}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ── Payment details ───────────────────────────────────────────
    if bank_name or sort_code or account_number:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Payment details", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        if bank_name:
            pdf.cell(0, 6, f"Account name:     {bank_name}", new_x="LMARGIN", new_y="NEXT")
        if sort_code:
            pdf.cell(0, 6, f"Sort code:            {sort_code}", new_x="LMARGIN", new_y="NEXT")
        if account_number:
            pdf.cell(0, 6, f"Account number:  {account_number}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Please use '{flat_name}' as your payment reference.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── Statutory summary ─────────────────────────────────────────
    pdf.ln(3)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 160, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "SUMMARY OF TENANTS' RIGHTS AND OBLIGATIONS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Service Charges (Summary of Rights and Obligations, and Transitional Provision) (England) Regulations 2007", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    paras = [
        (
            "1. Right to challenge service charges",
            "If you consider that a service charge is not payable or the amount is unreasonable, "
            "you have the right to apply to the First-tier Tribunal (Property Chamber) for a determination.",
        ),
        (
            "2. Right to information",
            "You have the right to request a written summary of costs incurred and to inspect the accounts, "
            "receipts and other documents supporting that summary.",
        ),
        (
            "3. Right to appoint a manager",
            "You may have the right to apply to the tribunal for the appointment of a manager if the landlord "
            "has failed to comply with their management obligations.",
        ),
        (
            "4. Right to acquire the freehold",
            "If the required number of qualifying tenants wish to do so, they may have the right to acquire "
            "the freehold of the premises (collective enfranchisement).",
        ),
        (
            "5. Withholding payment",
            "If you withhold payment of a service charge, the landlord may bring proceedings to recover the "
            "outstanding amount. You may also be liable for interest and costs if the tribunal finds the charge payable.",
        ),
    ]
    for title, body in paras:
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 5, body)
        pdf.ln(1)

    return bytes(pdf.output())


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/demands/{flat_id}")
async def generate_demand(block_id: str, year_id: str, flat_id: str):
    """Generate a demand letter PDF for a single flat."""
    db = get_db()
    block_ref = db.collection("blocks").document(block_id)

    block_doc = block_ref.get()
    if not block_doc.exists:
        raise HTTPException(404, "Block not found")
    block = block_doc.to_dict()

    year_doc = block_ref.collection("years").document(year_id).get()
    if not year_doc.exists:
        raise HTTPException(404, "Year not found")
    year_data = year_doc.to_dict()

    flat_doc = block_ref.collection("flats").document(flat_id).get()
    if not flat_doc.exists:
        raise HTTPException(404, "Flat not found")
    flat = {"id": flat_id, **flat_doc.to_dict()}

    all_lh = [{"id": d.id, **d.to_dict()} for d in block_ref.collection("leaseholders").stream()]
    lh = _active_lh(all_lh, flat_id)

    pdf_bytes = _build_pdf(block, year_id, year_data, flat, lh)
    flat_slug = flat.get("name", flat_id).replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="demand_{year_id}_{flat_slug}.pdf"'},
    )


@router.get("/demands")
async def generate_all_demands(block_id: str, year_id: str):
    """Download a zip archive containing one demand PDF per flat."""
    db = get_db()
    block_ref = db.collection("blocks").document(block_id)

    block_doc = block_ref.get()
    if not block_doc.exists:
        raise HTTPException(404, "Block not found")
    block = block_doc.to_dict()

    year_doc = block_ref.collection("years").document(year_id).get()
    if not year_doc.exists:
        raise HTTPException(404, "Year not found")
    year_data = year_doc.to_dict()

    flats = [{"id": d.id, **d.to_dict()} for d in block_ref.collection("flats").stream()]
    all_lh = [{"id": d.id, **d.to_dict()} for d in block_ref.collection("leaseholders").stream()]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for flat in flats:
            lh = _active_lh(all_lh, flat["id"])
            pdf_bytes = _build_pdf(block, year_id, year_data, flat, lh)
            flat_slug = flat.get("name", flat["id"]).replace(" ", "_")
            zf.writestr(f"demand_{year_id}_{flat_slug}.pdf", pdf_bytes)

    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="demands_{year_id}.zip"'},
    )
