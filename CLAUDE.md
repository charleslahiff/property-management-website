# Block Management — CLAUDE.md

Private property management tool for service charges and reserve fund tracking.
Supports multiple blocks. First block: "Eagle Court Management (Hornsey) Limited" (block_id: `eagle-court`), ~12 leaseholders.

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
    blocks.py       # Block CRUD (prefix /api/blocks)
    years.py        # Financial year CRUD (prefix /api/blocks/{block_id}/years)
    flats.py        # Flat CRUD (prefix /api/blocks/{block_id}/flats)
    leaseholders.py # Leaseholder CRUD (prefix /api/blocks/{block_id}/leaseholders)
    charges.py      # Budget, expenditure, income, invoice upload/parse
                    #   (prefix /api/blocks/{block_id}/years/{year_id})
scripts/
  migrate_to_blocks.py  # One-time migration from old flat structure
frontend/
  index.html        # Entire frontend — HTML, CSS, and JS in one file
  src/              # (unused)
```

## Data models

### Block
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `name` | string | e.g. "Eagle Court Management (Hornsey) Limited" |
| `address` | string? | |
| `company_number` | string? | Companies House number |
| `url` | string? | Website URL |

### FinancialYear
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Slug e.g. "2025-26", set from label on create |
| `label` | string | Display label e.g. "2025/26" |
| `start_date` | string | ISO date e.g. "2025-04-01" |
| `end_date` | string | ISO date e.g. "2026-03-31" |

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

### PaymentTransaction
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `flat_id` | string | References a Flat by ID |
| `fund` | string | `"sc"` \| `"rf"` |
| `amount` | float | Must be > 0 |
| `date` | string | ISO date — when cash was received |
| `charge_year` | string | Which year's charge this settles (can differ from year received — supports late payment) |
| `reference` | string? | e.g. bank ref, cheque number |

> Stored under `years/{charge_year}/payment_transactions/{id}`. Status (unpaid/partial/paid) is derived in the frontend via `derivePayments()` from transaction sums vs. charge amounts. `effSC(p)` / `effRF(p)` helpers still work as `payments` dict is recomputed from transactions.

## Firestore structure

```
blocks/{block_id}               # Block documents (e.g. "eagle-court")
  flats/{id}                    # Flat documents
  leaseholders/{id}             # Leaseholder documents
  years/{year_id}/              # Financial year documents (e.g. "2025-26")
    budget                      # Budget map (on year document)
    expenditure/{id}            # Expenditure documents
    income/{id}                 # Income documents
```

GCS layout: `{block_id}/{year_id}/invoices/{exp_id}.{ext}`

## API routes

All routes are prefixed with `/api/blocks/{block_id}`.

| Method | Path | Description |
| --- | --- | --- |
| GET/POST | `/api/blocks/` | List / create blocks |
| PUT/DELETE | `/api/blocks/{block_id}` | Update / delete block |
| GET/POST | `/api/blocks/{block_id}/years/` | List / create financial years |
| PUT/DELETE | `/api/blocks/{block_id}/years/{year_id}` | Update / delete year |
| GET/POST | `/api/blocks/{block_id}/flats/` | List / create flats |
| PUT/DELETE | `/api/blocks/{block_id}/flats/{id}` | Update / delete flat |
| GET/POST | `/api/blocks/{block_id}/leaseholders/` | List / create leaseholders |
| PUT/DELETE | `/api/blocks/{block_id}/leaseholders/{id}` | Update / delete leaseholder |
| GET/PUT | `/api/blocks/{block_id}/years/{year_id}/budget` | Get / save budget |
| GET/POST | `/api/blocks/{block_id}/years/{year_id}/expenditure` | List / create expenditure |
| PUT/DELETE | `/api/blocks/{block_id}/years/{year_id}/expenditure/{id}` | Update / delete expenditure |
| POST | `/api/blocks/{block_id}/years/{year_id}/expenditure/parse-invoice` | Extract fields from PDF via Claude |
| POST | `/api/blocks/{block_id}/years/{year_id}/expenditure/{id}/invoice` | Upload invoice to GCS |
| GET | `/api/blocks/{block_id}/years/{year_id}/expenditure/{id}/invoice-url` | Get fresh signed URL |
| GET/POST | `/api/blocks/{block_id}/years/{year_id}/income` | List / create income |
| DELETE | `/api/blocks/{block_id}/years/{year_id}/income/{id}` | Delete income |

## GCS layout

```
{year}/invoices/{exp_id}.{ext}       # Invoice files
```

Invoices are stored by GCS path in Firestore (`invoice_gcs_path`). Signed URLs (1 hour expiry) are generated on demand via `GET /api/{year}/expenditure/{exp_id}/invoice-url`.

## Key frontend conventions

- All state: `block`, `blocks`, `years`, `year`, `budget`, `flats`, `leaseholders`, `expenditure`, `payments`, `income`
- `year` is a year slug string e.g. `"2025-26"` (not a bare integer)
- `blockBase()` returns `/api/blocks/${block.id}` — use for flat/leaseholder routes
- `yearBase()` returns `${blockBase()}/years/${year}` — use for budget/expenditure/income routes
- `loadAll()` → `loadBlock(blockId)` → `loadBuilding()` + `loadYear()`
- `changeYear(y)` calls `loadYear()` only — flats/leaseholders are not reloaded
- `changeBlock(blockId)` resets all state and calls `loadBlock()`
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
