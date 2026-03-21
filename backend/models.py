from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class Leaseholder(BaseModel):
    id: Optional[str] = None
    flat: str
    name: str
    email: Optional[str] = None
    sc_share: float = Field(ge=0, le=100)
    rf_share: float = Field(ge=0, le=100)
    share_of_freehold: bool = False
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None


class Budget(BaseModel):
    sc: float = 0
    rf: float = 0
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


class Payment(BaseModel):
    leaseholder_id: str
    sc_status: str = "unpaid"  # "unpaid" | "partial" | "paid"
    rf_status: str = "unpaid"
    sc_received_date: Optional[str] = None
    rf_received_date: Optional[str] = None


class InvoiceUploadResponse(BaseModel):
    upload_url: str   # signed URL for direct browser → GCS upload
    invoice_url: str  # permanent reference stored in Firestore
    expenditure_id: str
