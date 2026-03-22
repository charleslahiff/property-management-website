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
    blocks.py       # Block CRUD + arrears + opening_arrears (prefix /api/blocks)
    years.py        # Financial year CRUD (prefix /api/blocks/{block_id}/years)
    flats.py        # Flat CRUD (prefix /api/blocks/{block_id}/flats)
    leaseholders.py # Leaseholder CRUD (prefix /api/blocks/{block_id}/leaseholders)
    charges.py      # Budget, expenditure, income, invoice upload/parse, prior_closing
                    #   (prefix /api/blocks/{block_id}/years/{year_id})
    demands.py      # Demand letter PDF generation (prefix /api/blocks/{block_id}/years/{year_id})
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
| `building_name` | string? | Short name e.g. "Eagle Court" — used in demand letter addresses |
| `address` | string? | |
| `company_number` | string? | Companies House number |
| `url` | string? | Website URL |
| `sc_bank_account_name` | string? | SC trust account name |
| `sc_bank_sort_code` | string? | SC trust account sort code |
| `sc_bank_account_number` | string? | SC trust account number |
| `rf_bank_account_name` | string? | RF trust account name |
| `rf_bank_sort_code` | string? | RF trust account sort code |
| `rf_bank_account_number` | string? | RF trust account number |

> SC and RF funds are held in separate designated trust accounts (LTA 1987 s.42).

> `opening_arrears` is also stored on the block document (not in the Block Pydantic model) — see below.

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
| `sc_opening_balance` | float | SC opening balance brought forward (default 0) |
| `rf_opening_balance` | float | RF opening balance brought forward (default 0) |
| `sc_notes` | string? | |
| `rf_notes` | string? | |
| `billing_freq` | string | `"annual"` \| `"quarterly"` |
| `due_date` | string? | ISO date |
| `sc_categories` | string[] | Expenditure categories for SC |
| `rf_categories` | string[] | Expenditure categories for RF |

> Opening balances feed into reconciliation (surplus/closing balance) and the balance-over-time chart. If not set manually, the chart falls back to the prior year's computed closing balance via `GET /prior_closing`.

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
| `supplier` | string? | |
| `invoice_url` | string? | Signed GCS URL, generated on demand |

> When a PDF invoice is uploaded, `POST /expenditure/parse-invoice` uses pdfplumber + Claude Haiku to extract fields and auto-populate the form.

### Income
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID, set on create |
| `type` | string | `"leaseholder"` \| `"interest"` \| `"other"` |
| `fund` | string | `"sc"` \| `"rf"` |
| `flat_id` | string? | Required for `leaseholder` type |
| `amount` | float | Must be > 0 |
| `date` | string | ISO date — when cash was received |
| `charge_year` | string | Which financial year this income relates to |
| `description` | string? | |
| `reference` | string? | e.g. bank ref |

### Opening arrears _(stored as a map on the block document, outside the Block model)_

```
blocks/{block_id}.opening_arrears = {
  "_year": "2024-25",          # year slug — arrears only shown when viewing this year
  "{flat_id}": { "sc": 500.0, "rf": 200.0 },
  ...
}
```

> Represents pre-system debts carried over from a previous managing agent. Only shown in the charge schedule for the exact year set (`_year === current year`). In subsequent years, unpaid amounts appear as calculated arrears via the `/arrears` endpoint, which includes the opening arrears for the `_year` in its outstanding calculation.

## Firestore structure

```
blocks/{block_id}               # Block document — also holds opening_arrears map
  flats/{id}                    # Flat documents
  leaseholders/{id}             # Leaseholder documents
  years/{year_id}/              # Financial year documents (e.g. "2025-26")
    budget                      # Budget map (on year document, includes opening balances)
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
| GET/PUT | `/api/blocks/{block_id}/opening_arrears` | Get / save manual opening arrears |
| GET | `/api/blocks/{block_id}/arrears?exclude_year=` | Outstanding per flat per prior year (excludes current and future years); includes opening arrears in the year they were set |
| GET/POST | `/api/blocks/{block_id}/years/` | List / create financial years |
| PUT/DELETE | `/api/blocks/{block_id}/years/{year_id}` | Update / delete year |
| GET/POST | `/api/blocks/{block_id}/flats/` | List / create flats |
| PUT/DELETE | `/api/blocks/{block_id}/flats/{id}` | Update / delete flat |
| GET/POST | `/api/blocks/{block_id}/leaseholders/` | List / create leaseholders |
| PUT/DELETE | `/api/blocks/{block_id}/leaseholders/{id}` | Update / delete leaseholder |
| GET | `/api/blocks/{block_id}/years/{year_id}/prior_closing` | SC/RF closing balance of the year immediately before year_id |
| GET/PUT | `/api/blocks/{block_id}/years/{year_id}/budget` | Get / save budget (includes opening balances) |
| GET/POST | `/api/blocks/{block_id}/years/{year_id}/expenditure` | List / create expenditure |
| PUT/DELETE | `/api/blocks/{block_id}/years/{year_id}/expenditure/{id}` | Update / delete expenditure |
| POST | `/api/blocks/{block_id}/years/{year_id}/expenditure/parse-invoice` | Extract fields from PDF via Claude |
| POST | `/api/blocks/{block_id}/years/{year_id}/expenditure/{id}/invoice` | Upload invoice to GCS |
| GET | `/api/blocks/{block_id}/years/{year_id}/expenditure/{id}/invoice-url` | Get fresh signed URL |
| GET/POST | `/api/blocks/{block_id}/years/{year_id}/income` | List / create income |
| DELETE | `/api/blocks/{block_id}/years/{year_id}/income/{id}` | Delete income |
| GET | `/api/blocks/{block_id}/years/{year_id}/demands/{flat_id}` | Download demand letter PDF for one flat |
| GET | `/api/blocks/{block_id}/years/{year_id}/demands` | Download ZIP of demand letters for all flats |

## Key frontend conventions

- All state: `block`, `blocks`, `years`, `year`, `budget`, `flats`, `leaseholders`, `expenditure`, `payments`, `income`, `arrears`, `openingArrears`, `priorClosing`
- `year` is a year slug string e.g. `"2025-26"` (not a bare integer)
- `blockBase()` returns `/api/blocks/${block.id}` — use for flat/leaseholder/arrears routes
- `yearBase()` returns `${blockBase()}/years/${year}` — use for budget/expenditure/income routes
- `loadAll()` → `loadBlock(blockId)` → `loadBuilding()` + `loadYear()`
- `loadBuilding()` fetches flats, leaseholders, calculated arrears, and opening arrears
- `loadYear()` fetches budget, expenditure, payments, income, and prior_closing
- `changeYear(y)` calls `loadYear()` + `reloadArrears()` — flats/leaseholders are not reloaded
- `reloadArrears()` refreshes both `arrears` and `openingArrears` (called on year change)
- `changeBlock(blockId)` resets all state and calls `loadBlock()`
- Each page has a `render*()` function called from `showPage()`
- `sortFlats(arr)` sorts flats by numeric name — apply to all flat lists
- `activeLH(flatId)` returns the current active leaseholder for a flat (not expired, most recent effective date)
- `effSC(p)` / `effRF(p)` are module-level helpers — return `'paid'` automatically when the fund budget is £0
- `fmt(n)` formats £ values; `fmtK(n)` abbreviates to £12.3k
- Charts use Chart.js 4 + chartjs-adapter-date-fns (loaded via CDN)
- `derivePayments()` recomputes the `payments` dict from income records (leaseholder type)

## Charge schedule — arrears logic

The charge schedule shows SC and RF arrears b/f per flat, split by fund:

- **SC/RF arrears b/f** = sum of `sc_outstanding`/`rf_outstanding` from the `/arrears` endpoint
  + opening arrears for the current year (if `openingArrears._year === year`)
- **SC/RF outstanding** = (owed − paid for current year) + arrears b/f

The `/arrears` endpoint returns outstanding per flat per prior year. For a year that equals `opening_arrears._year`, it adds the manual opening arrears to the owed amount so the pre-system debt carries forward correctly into subsequent years.

Opening arrears are only shown as a manual line item in the **exact year** they were set (`_year === current year`). In later years they surface through the calculated outstanding returned by `/arrears`.

## Balance chart / reconciliation — opening balance

Both the balance-over-time chart and reconciliation use an effective opening balance:

```
effectiveOB = budget.sc_opening_balance  (if manually set)
           || priorClosing.sc            (auto: prior year closing balance)
```

`priorClosing` is fetched from `GET /prior_closing` on every year load. This means the balance chart automatically carries forward from the previous year's closing position without manual entry, unless overridden in the budget form.

## Demand letters

`GET /demands/{flat_id}` and `GET /demands` (ZIP) generate PDF demand letters using fpdf2.

- Layout: block name + date header, leaseholder address, bordered charge table (SC/RF owed with no share column), BACS payment details per fund, statutory information (LTA 1985 s.47/48 landlord address, s.42 trust account statement)
- Page 2: full 12-point prescribed statutory summary (Service Charges (Summary of Rights and Obligations) (England) Regulations 2007) — legally required; leaseholders can withhold payment if absent
- BACS reference format: `SC F3 WIL` (fund code + flat number + first 3 letters of surname)
- Uses built-in Helvetica font (Latin-1 only) — avoid non-Latin-1 characters (e.g. em dash → hyphen)

## Fund terminology

- **SC** — Service charge fund (recurring annual costs: insurance, maintenance, etc.)
- **RF** — Reserve fund (long-term savings for major works)
- Each flat has an independent `sc_share` and `rf_share` (% of total)
- Eagle Court currently has no SC budget — only RF contributions (due to s.20 qualifying works). RF contributions are still variable service charges under LTA 1985 s.18.

## Deployment

Push to `main` — Cloud Build triggers automatically via `cloudbuild.yaml`.
Secrets (`GCS_BUCKET_NAME`, `ANTHROPIC_API_KEY`) are pulled from Secret Manager at deploy time.
