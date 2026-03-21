from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class Block(BaseModel):
    id: Optional[str] = None
    name: str
    building_name: Optional[str] = None  # e.g. "Eagle Court" — used in demand letter addresses
    address: Optional[str] = None
    company_number: Optional[str] = None
    url: Optional[str] = None
    sc_bank_account_name: Optional[str] = None
    sc_bank_sort_code: Optional[str] = None
    sc_bank_account_number: Optional[str] = None
    rf_bank_account_name: Optional[str] = None
    rf_bank_sort_code: Optional[str] = None
    rf_bank_account_number: Optional[str] = None


class FinancialYear(BaseModel):
    id: Optional[str] = None   # slug e.g. "2025-26"
    label: str                 # display label e.g. "2025/26"
    start_date: str            # ISO date e.g. "2025-04-01"
    end_date: str              # ISO date e.g. "2026-03-31"


class Flat(BaseModel):
    id: Optional[str] = None
    name: str
    sc_share: float = Field(ge=0, le=100)
    rf_share: float = Field(ge=0, le=100)
    share_of_freehold: bool = False


class Leaseholder(BaseModel):
    id: Optional[str] = None
    flat_id: str
    name: str
    email: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None


class Budget(BaseModel):
    sc: float = 0
    rf: float = 0
    sc_opening_balance: float = 0
    rf_opening_balance: float = 0
    sc_notes: Optional[str] = None
    rf_notes: Optional[str] = None
    billing_freq: str = "annual"
    due_date: Optional[str] = None
    sc_categories: list[str] = ["Insurance", "Repairs", "Cleaning", "Utilities", "Management", "Other"]
    rf_categories: list[str] = ["Major works", "Contingency", "Other"]


class Expenditure(BaseModel):
    id: Optional[str] = None
    date: str
    fund: str  # "sc" or "rf"
    description: str
    category: Optional[str] = None
    amount: float = Field(gt=0)
    supplier: Optional[str] = None
    invoice_url: Optional[str] = None  # GCS signed URL stored after upload
    payment_date: Optional[str] = None  # ISO date — when cash left the account


class Payment(BaseModel):
    flat_id: str
    sc_status: str = "unpaid"  # "unpaid" | "partial" | "paid"
    rf_status: str = "unpaid"
    sc_received_date: Optional[str] = None
    rf_received_date: Optional[str] = None


class Income(BaseModel):
    id: Optional[str] = None
    type: str          # "leaseholder" | "interest" | "other"
    fund: str          # "sc" | "rf"
    flat_id: Optional[str] = None  # required for leaseholder type
    amount: float = Field(gt=0)
    date: str          # ISO date — when cash was received
    charge_year: str   # which financial year this income relates to
    description: Optional[str] = None
    reference: Optional[str] = None


class InvoiceUploadResponse(BaseModel):
    upload_url: str   # signed URL for direct browser → GCS upload
    invoice_url: str  # permanent reference stored in Firestore
    expenditure_id: str
