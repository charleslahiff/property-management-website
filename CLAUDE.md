# Block Management — CLAUDE.md

Private property management tool for service charges and reserve fund tracking.
Single block, single deployment, small number of leaseholders (~12).

## Stack

- **Backend**: FastAPI (Python), `backend/main.py` entry point
- **Frontend**: Vanilla JS, single-page app served as static files by FastAPI (`frontend/index.html`)
- **Database**: Firestore (Native mode, `europe-west2`)
- **File storage**: GCS bucket `block-management-docs`
- **Auth**: Cloud IAP (Google login, allowlist-based — no custom auth code)
- **Deployment**: Cloud Run via Cloud Build on push to `main`

## Running locally

```bash
pip install -r requirements.txt
gcloud auth application-default login
cp .env.example .env  # set GCP_PROJECT_ID and GCS_BUCKET_NAME
uvicorn backend.main:app --reload --port 8080
```

## Project structure

```
backend/
  main.py           # FastAPI app, mounts routers and serves frontend/index.html
  firestore.py      # Firestore client singleton
  models.py         # Pydantic models
  routers/
    charges.py      # Budget, expenditure, payments, invoice/supplier uploads
    leaseholders.py # Leaseholder CRUD
frontend/
  index.html        # Entire frontend — HTML, CSS, and JS in one file
  src/              # (unused)
```

## Data models

### Leaseholder
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `flat` | string | e.g. "Flat 3" |
| `name` | string | |
| `email` | string? | |
| `sc_share` | float | % of SC budget (0–100) |
| `rf_share` | float | % of RF budget (0–100) |
| `share_of_freehold` | bool | default false |
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
| `date` | string | ISO date |
| `fund` | string | `"sc"` \| `"rf"` |
| `description` | string | |
| `category` | string? | Must match a budget category |
| `amount` | float | Must be > 0 |
| `supplier` | string? | Name or reference; renders as clickable link in table if a URL |
| `invoice_gcs_path` | string? | `gs://bucket/year/invoices/{id}.ext` — signed URL generated on demand |

### Payment _(keyed by leaseholder ID)_
| Field | Type | Notes |
| --- | --- | --- |
| `sc_status` | string | `"unpaid"` \| `"partial"` \| `"paid"` |
| `rf_status` | string | `"unpaid"` \| `"partial"` \| `"paid"` |
| `sc_received_date` | string? | ISO date payment was received |
| `rf_received_date` | string? | ISO date payment was received |

> If the budget for a fund is £0, its status is treated as `"paid"` automatically in the UI (see `effSC`/`effRF` in `renderCharges`).

## Firestore structure

```
years/{year}/
  budget            # Budget map (see above)
  leaseholders/{id} # Leaseholder documents
  expenditure/{id}  # Expenditure documents
  payments/{lh_id}  # Payment documents, keyed by leaseholder ID
```

## GCS layout

```
{year}/invoices/{exp_id}.{ext}       # Invoice files
```

Invoices are stored by GCS path in Firestore (`invoice_gcs_path`). Signed URLs (1 hour expiry) are generated on demand via `GET /api/{year}/expenditure/{exp_id}/invoice-url`.

## Key frontend conventions

- All state lives in four module-level variables: `budget`, `leaseholders`, `expenditure`, `payments`
- `loadAll()` fetches all four in parallel and calls `renderDashboard()`
- Each page has a `render*()` function called from `showPage()`
- `sortByFlat(arr)` sorts leaseholders by numeric flat number — apply to all leaseholder lists
- `fmt(n)` formats £ values; `fmtK(n)` abbreviates to £12.3k
- Charts use Chart.js 4 + chartjs-adapter-date-fns (loaded via CDN)
- Payment status display uses `effSC(p)` / `effRF(p)` helpers in `renderCharges()` — returns `'paid'` automatically when the fund budget is £0

## Fund terminology

- **SC** — Service charge fund (recurring annual costs: insurance, maintenance, etc.)
- **RF** — Reserve fund (long-term savings for major works)
- Each leaseholder has an independent `sc_share` and `rf_share` (% of total)

## Deployment

Push to `main` — Cloud Build triggers automatically via `cloudbuild.yaml`.
