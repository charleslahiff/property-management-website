"""Generate service charge demand letters as PDF.

Endpoints:
  GET /api/blocks/{block_id}/years/{year_id}/demands/{flat_id}
      -> single demand PDF for one flat

  GET /api/blocks/{block_id}/years/{year_id}/demands
      -> zip archive containing one PDF per flat
"""

import datetime
import io
import re
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.firestore import get_db

router = APIRouter(prefix="/api/blocks/{block_id}/years/{year_id}", tags=["demands"])

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Full prescribed statutory summary — Service Charges (Summary of Rights and
# Obligations, and Transitional Provision) (England) Regulations 2007
_STATUTORY_POINTS = [
    (
        "1.",
        "This summary, which briefly sets out your rights and obligations in relation to "
        "variable service charges, must by law accompany a demand for service charges. Unless "
        "a summary is sent to you with a demand, you may withhold the service charge. The "
        "summary does not give a full interpretation of the law and if you are in any doubt "
        "about your rights and obligations you should seek independent advice.",
    ),
    (
        "2.",
        "Your lease sets out your obligations to pay service charges to your landlord in "
        "addition to your rent. Service charges are amounts payable for services, repairs, "
        "maintenance, improvements, insurance or the landlord's costs of management, to the "
        "extent that the costs have been reasonably incurred.",
    ),
    (
        "3.",
        "You have the right to ask the First-tier Tribunal to determine whether you are "
        "liable to pay service charges for services, repairs, maintenance, improvements, "
        "insurance or management. You may make a request before or after you have paid the "
        "service charge. If the tribunal determines that the service charge is payable, it "
        "may also determine who should pay it and to whom, the amount, the date it should be "
        "paid by, and how it should be paid. However, you do not have these rights where a "
        "matter has been agreed or admitted by you, has already been referred to arbitration "
        "and you agreed to go to arbitration after the disagreement arose, or has been "
        "decided by a court.",
    ),
    (
        "4.",
        "If your lease allows your landlord to recover costs incurred or that may be incurred "
        "in legal proceedings as service charges, you may ask the court or tribunal, before "
        "which those proceedings were brought, to rule that your landlord may not do so.",
    ),
    (
        "5.",
        "Where you seek a determination from a First-tier Tribunal, you will have to pay an "
        "application fee and, where the matter proceeds to a hearing, a hearing fee, unless "
        "you qualify for a waiver or reduction. The total fees payable will not exceed "
        "\xa3500, but making an application may incur additional costs, such as professional "
        "fees, which you may also have to pay.",
    ),
    (
        "6.",
        "The First-tier Tribunal has the power to award costs, not exceeding \xa3500, against "
        "a party to any proceedings where it dismisses a matter because it is frivolous, "
        "vexatious or an abuse of process, or where it considers a party has acted "
        "frivolously, vexatiously, abusively, disruptively or unreasonably. The Upper "
        "Tribunal (Lands Chamber) has similar powers when hearing an appeal.",
    ),
    (
        "7.",
        "If your landlord proposes works on a building that will cost you or any other tenant "
        "more than \xa3250, or proposes to enter into an agreement for works or services which "
        "will last for more than 12 months and will cost you or any other tenant more than "
        "\xa3100 in any 12 month accounting period, your contribution will be limited to these "
        "amounts unless your landlord has properly consulted on the proposed works or "
        "agreement or the First-tier Tribunal has agreed that consultation is not required.",
    ),
    (
        "8.",
        "You have the right to apply to a First-tier Tribunal to ask it to determine whether "
        "your lease should be varied on the grounds that it does not make satisfactory "
        "provision in respect of the calculation of a service charge payable under the lease.",
    ),
    (
        "9.",
        "You have the right to write to your landlord to request a written summary of the "
        "costs which make up the service charges. The summary must cover the last 12 month "
        "period used for making up the accounts relating to the service charge ending no "
        "later than the date of your request, or the 12 month period ending with the date of "
        "your request where accounts are not made up for 12 month periods. The summary must "
        "be given to you within 1 month of your request or 6 months of the end of the period "
        "to which the summary relates, whichever is the later.",
    ),
    (
        "10.",
        "You have the right, within 6 months of receiving a written summary of costs, to "
        "require the landlord to provide you with reasonable facilities to inspect the "
        "accounts, receipts and other documents supporting the summary and for taking copies "
        "or extracts from them.",
    ),
    (
        "11.",
        "You have the right to ask an accountant or surveyor to carry out an audit of the "
        "financial management of the premises containing your dwelling, to establish the "
        "obligations of your landlord and the extent to which the service charges you pay are "
        "being used efficiently. It will depend on your circumstances whether you can "
        "exercise this right alone or only with the support of others living in the premises. "
        "You are strongly advised to seek independent advice before exercising this right.",
    ),
    (
        "12.",
        "Your lease may give your landlord a right of re-entry or forfeiture where you have "
        "failed to pay charges which are properly due under the lease. However, to exercise "
        "this right, the landlord must meet all the legal requirements and obtain a court "
        "order. A court order will only be granted if you have admitted you are liable to pay "
        "the amount or it is finally determined by a court, tribunal or by arbitration that "
        "the amount is due. The court has a wide discretion in granting such an order and it "
        "will take into account all the circumstances of the case.",
    ),
]


def _ordinal(n: int) -> str:
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _fmt_date(d: datetime.date) -> str:
    return f"{_ordinal(d.day)} {_MONTHS[d.month - 1]} {d.year}"


def _fmt_money(n: float) -> str:
    return f"\xa3{n:,.2f}"


def _make_ref(fund: str, flat_name: str, lh_name: str | None) -> str:
    fund_code = "SC" if fund == "sc" else "RF"
    m = re.search(r"\d+", flat_name)
    flat_code = f"F{m.group()}" if m else flat_name.replace(" ", "")[:4].upper()
    if lh_name:
        surname = lh_name.strip().split()[-1][:3].upper()
    else:
        surname = "???"
    return f"{fund_code} {flat_code} {surname}"


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

    block_name = block.get("name", "")
    building_name = block.get("building_name") or ""
    block_address = (block.get("address") or "").replace("\r", "")
    address_lines = [l.strip() for l in block_address.split("\n") if l.strip()]

    sc_bank = {
        "name": block.get("sc_bank_account_name") or "",
        "sort_code": block.get("sc_bank_sort_code") or "",
        "account": block.get("sc_bank_account_number") or "",
    }
    rf_bank = {
        "name": block.get("rf_bank_account_name") or "",
        "sort_code": block.get("rf_bank_sort_code") or "",
        "account": block.get("rf_bank_account_number") or "",
    }

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

    try:
        fy_start = datetime.date.fromisoformat(year_data.get("start_date", ""))
        fy_end = datetime.date.fromisoformat(year_data.get("end_date", ""))
        date_range = f"{fy_start.strftime('%d/%m/%y')} to {fy_end.strftime('%d/%m/%y')}"
    except (ValueError, TypeError):
        date_range = year_label

    # ── Build PDF ─────────────────────────────────────────────────
    pdf = FPDF()
    pdf.set_margins(25, 22, 25)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    # ── Block name (left) + date (right) ─────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(120, 8, block_name)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(40, 8, today_str, align="R", new_x="LMARGIN", new_y="NEXT")

    if address_lines:
        pdf.set_font("Helvetica", "", 9)
        for line in address_lines:
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")

    # Separator
    pdf.ln(3)
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ── Addressee ─────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, lh_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    flat_line = f"{flat_name} {building_name}" if building_name else flat_name
    pdf.cell(0, 6, flat_line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Subject ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"SERVICE CHARGE DEMAND - {year_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Charge table ──────────────────────────────────────────────
    col = [125, 35]  # description, amount
    pdf.set_fill_color(240, 240, 238)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col[0], 8, "Charge", border=1, fill=True)
    pdf.cell(col[1], 8, "Amount", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    if sc_budget > 0:
        pdf.cell(col[0], 8, f"Service charge ({date_range})", border=1)
        pdf.cell(col[1], 8, _fmt_money(sc_amount), border=1, align="R")
        pdf.ln()
    if rf_budget > 0:
        pdf.cell(col[0], 8, f"Reserve fund contribution ({date_range})", border=1)
        pdf.cell(col[1], 8, _fmt_money(rf_amount), border=1, align="R")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 238)
    pdf.cell(col[0], 8, "Total payable", border=1, fill=True)
    pdf.cell(col[1], 8, _fmt_money(total), border=1, fill=True, align="R")
    pdf.ln()
    pdf.ln(6)

    # ── Due date ──────────────────────────────────────────────────
    if due_display:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"Payment due: {due_display}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── BACS payment section ──────────────────────────────────────
    def _print_bacs(label: str, bank: dict, fund: str):
        if not any(bank.values()):
            return
        ref = _make_ref(fund, flat_name, lh_name)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        if bank["name"]:
            pdf.cell(0, 6, f"Name: {bank['name']}", new_x="LMARGIN", new_y="NEXT")
        if bank["sort_code"]:
            pdf.cell(0, 6, f"Sort Code: {bank['sort_code']}", new_x="LMARGIN", new_y="NEXT")
        if bank["account"]:
            pdf.cell(0, 6, f"Account Number: {bank['account']}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Reference: {ref}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    if sc_budget > 0:
        _print_bacs("Please make BACS payment to (service charge):", sc_bank, "sc")
    if rf_budget > 0:
        _print_bacs("Please make BACS payment to (reserve fund):", rf_bank, "rf")

    # ── Statutory Information (s.47/48 and s.42) ──────────────────
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Statutory Information", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0, 6,
        "In accordance with Sections 47 and 48 of the Landlord and Tenant Act 1987, "
        "the landlord's name and address for service of notices (including notices of "
        "proceedings) is:",
    )
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 6, block_name, new_x="LMARGIN", new_y="NEXT")
    for line in address_lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0, 6,
        "The service charge monies are held in a dedicated trust account in accordance "
        "with Section 42 of the Landlord and Tenant Act 1987.",
    )

    # ── Page 2: Full prescribed statutory summary ─────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, "Service Charges - Summary of Tenants' Rights and Obligations")
    pdf.ln(2)

    for number, text in _STATUTORY_POINTS:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, f"{number} {text}")
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
