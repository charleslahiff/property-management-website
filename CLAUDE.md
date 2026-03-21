# Block Management — CLAUDE.md

Private property management tool for service charges and reserve fund tracking.
Single block (Lahiff Management), single deployment, small number of leaseholders (~12).

## Stack

- **Backend**: FastAPI (Python), `backend/main.py` entry point
- **Frontend**: Vanilla JS, single-page app served as static files by FastAPI (`frontend/index.html`)
- **Database**: Firestore (Native mode, `europe-west2`)
- **File storage**: GCS bucket `lahiff-management-docs`
- **Auth**: Cloud IAP (Google login, allowlist-based — no custom auth code)
- **Deployment**: Cloud Run via Cloud Build on push to `main`
- **GCP project**: `lahiff-management` (project number: 1037443599500)
- **Secrets**: GCS_BUCKET_NAME and ANTHROPIC_API_KEY stored in Secret Manager, mounted as env vars by Cloud Run

## Running locally

```bash
pip install -r requirements.txt
gcloud auth application-default login
cp .env.example .env  # set GCP_PROJECT_ID, GCS_BUCKET_NAME, ANTHROPIC_API_KEY
uvicorn backend.main:app --reload --port 8080
```

## Project structure

```
backend/
  main.py           # FastAPI app, mounts routers and serves frontend/index.html
  firestore.py      # Firestore client singleton
  models.py         # Pydantic models
  routers/
    charges.py      # Budget, expenditure, payments, invoice upload/parse
    flats.py        # Flat CRUD (building-level, prefix /api/flats)
    leaseholders.py # Leaseholder CRUD (building-level, prefix /api/leaseholders)
frontend/
  index.html        # Entire frontend — HTML, CSS, and JS in one file
  src/              # (unused)
```

## Data models

### Flat
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `name` | string | e.g. "Flat 3" |
| `sc_share` | float | % of SC budget (0–100) |
| `rf_share` | float | % of RF budget (0–100) |
| `share_of_freehold` | bool | default false |

### Leaseholder
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `flat_id` | string | References a Flat by ID |
| `name` | string | |
| `email` | string? | |
| `effective_date` | string? | ISO date — when the lease/tenure began |
| `expiry_date` | string? | ISO date — when the lease/tenure ends |

### Budget _(stored as a map on the year document)_
| Field | Type | Notes |
| --- | --- | --- |
| `sc` | float | Annual SC budget (£) |
| `rf` | float | Annual RF contribution target (£) |
| `sc_notes` | string? | |
| `rf_notes` | string? | |
| `billing_freq` | string | `"annual"` \| `"quarterly"` |
| `due_date` | string? | ISO date |
| `sc_categories` | string[] | Expenditure categories for SC |
| `rf_categories` | string[] | Expenditure categories for RF |

### Expenditure
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `date` | string | ISO date — invoice date (when billed) |
| `payment_date` | string? | ISO date — when cash left the account |
| `fund` | string | `"sc"` \| `"rf"` |
| `description` | string | |
| `category` | string? | Must match a budget category |
| `amount` | float | Must be > 0 |
| `supplier` | string? | Renders as clickable link to invoice if `invoice_gcs_path` is set |
| `invoice_gcs_path` | string? | `gs://bucket/year/invoices/{id}.ext` — signed URL generated on demand |

> When a PDF invoice is uploaded, `POST /api/{year}/expenditure/parse-invoice` uses pdfplumber + Claude Haiku to extract fields and auto-populate the form.

### Payment _(keyed by flat ID)_
| Field | Type | Notes |
| --- | --- | --- |
| `flat_id` | string | References a Flat by ID |
| `sc_status` | string | `"unpaid"` \| `"partial"` \| `"paid"` |
| `rf_status` | string | `"unpaid"` \| `"partial"` \| `"paid"` |
| `sc_received_date` | string? | ISO date payment was received |
| `rf_received_date` | string? | ISO date payment was received |

> If the budget for a fund is £0, its status is treated as `"paid"` automatically in the UI (see module-level `effSC`/`effRF` helpers).

## Firestore structure

```
flats/{id}            # Flat documents (building-level, not year-scoped)
leaseholders/{id}     # Leaseholder documents (building-level, flat_id references a flat)
years/{year}/
  budget              # Budget map (see above)
  expenditure/{id}    # Expenditure documents
  payments/{flat_id}  # Payment documents, keyed by flat ID
```

## API routes

| Method | Path | Description |
| --- | --- | --- |
| GET/POST | `/api/flats/` | List / create flats |
| PUT/DELETE | `/api/flats/{id}` | Update / delete flat |
| GET/POST | `/api/leaseholders/` | List / create leaseholders |
| PUT/DELETE | `/api/leaseholders/{id}` | Update / delete leaseholder |
| GET/PUT | `/api/{year}/budget` | Get / save budget |
| GET/POST | `/api/{year}/expenditure` | List / create expenditure |
| DELETE | `/api/{year}/expenditure/{id}` | Delete expenditure |
| POST | `/api/{year}/expenditure/parse-invoice` | Extract fields from PDF via Claude |
| POST | `/api/{year}/expenditure/{id}/invoice` | Upload invoice to GCS |
| GET | `/api/{year}/expenditure/{id}/invoice-url` | Get fresh signed URL for invoice |
| GET/PUT | `/api/{year}/payments/{flat_id}` | Get / update payment status |

## GCS layout

```
{year}/invoices/{exp_id}.{ext}       # Invoice files
```

Invoices are stored by GCS path in Firestore (`invoice_gcs_path`). Signed URLs (1 hour expiry) are generated on demand via `GET /api/{year}/expenditure/{exp_id}/invoice-url`.

## Key frontend conventions

- All state lives in five module-level variables: `budget`, `flats`, `leaseholders`, `expenditure`, `payments`
- `loadBuilding()` fetches `flats` and `leaseholders` (building-level, called once on init)
- `loadYear()` fetches `budget`, `expenditure`, `payments` (year-scoped, called on year change)
- `loadAll()` calls `loadBuilding()` then `loadYear()`
- `changeYear(y)` calls `loadYear()` only — flats/leaseholders are not reloaded
- Each page has a `render*()` function called from `showPage()`
- `sortFlats(arr)` sorts flats by numeric name — apply to all flat lists
- `activeLH(flatId)` returns the current active leaseholder for a flat (not expired, most recent effective date)
- `effSC(p)` / `effRF(p)` are module-level helpers — return `'paid'` automatically when the fund budget is £0
- `fmt(n)` formats £ values; `fmtK(n)` abbreviates to £12.3k
- Charts use Chart.js 4 + chartjs-adapter-date-fns (loaded via CDN)
- Payments are keyed by flat ID; charges/reconciliation iterate over flats, not leaseholders

## Fund terminology

- **SC** — Service charge fund (recurring annual costs: insurance, maintenance, etc.)
- **RF** — Reserve fund (long-term savings for major works)
- Each flat has an independent `sc_share` and `rf_share` (% of total)

## Deployment

Push to `main` — Cloud Build triggers automatically via `cloudbuild.yaml`.
Secrets (`GCS_BUCKET_NAME`, `ANTHROPIC_API_KEY`) are pulled from Secret Manager at deploy time.
