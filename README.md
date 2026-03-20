# Block Management — Service Charges

A private property management tool for service charges and reserve fund tracking. Built with FastAPI + Firestore, deployed on Google Cloud Run.

---

## Architecture

- **Frontend**: Vanilla JS served as static files by FastAPI
- **Backend**: FastAPI (Python) on Cloud Run — serverless, scales to zero
- **Database**: Firestore — serverless NoSQL, generous free tier
- **File storage**: Cloud Storage (GCS) — invoices, contracts, PDFs
- **Auth**: Cloud IAP — Google login, no custom auth code needed

---

## GCP Setup (one-time)

### 1. Create a GCP project

```bash
gcloud projects create block-management-prod
gcloud config set project block-management-prod
```

### 2. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  iap.googleapis.com
```

### 3. Create Firestore database

In the GCP Console → Firestore → Create database → **Native mode** → Region: `europe-west2`.

### 4. Create GCS bucket for documents

```bash
gsutil mb -l europe-west2 gs://block-management-docs
```

### 5. Set up Cloud Build trigger

In GCP Console → Cloud Build → Triggers → Connect your GitHub repo → select `cloudbuild.yaml` as the config file. Set the trigger to fire on pushes to `main`.

Grant Cloud Build permission to deploy to Cloud Run:
```bash
PROJECT_NUMBER=$(gcloud projects describe block-management-prod --format='value(projectNumber)')
gcloud projects add-iam-policy-binding block-management-prod \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud iam service-accounts add-iam-policy-binding \
  ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 6. Configure Cloud IAP

After first deploy:

1. GCP Console → Security → Identity-Aware Proxy
2. Enable IAP for your Cloud Run service
3. Add your email (and any co-directors / property manager) as **IAP-secured Web App User**

That's your login system — anyone not on the list gets a 403.

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Authenticate with GCP (uses your personal credentials locally)
gcloud auth application-default login

# Copy and edit env file
cp .env.example .env
# Edit .env with your GCP_PROJECT_ID and GCS_BUCKET_NAME

# Run the server
uvicorn backend.main:app --reload --port 8080
```

Open http://localhost:8080

---

## Firestore Data Structure

```
years/
  {year}/                        # e.g. "2025"
    budget: { sc, rf, ... }
    leaseholders/
      {id}: { flat, name, email, sc_share, rf_share }
    expenditure/
      {id}: { date, fund, description, amount, invoice_gcs_path, ... }
    payments/
      {leaseholder_id}: { sc_status, rf_status }
```

---

## Deployment

Push to `main` — Cloud Build handles the rest automatically.

To deploy manually:
```bash
gcloud builds submit --config cloudbuild.yaml
```

---

## Estimated costs (light usage)

| Service | Cost |
|---|---|
| Cloud Run | ~£0 (scales to zero) |
| Firestore | ~£0 (free tier: 1GB, 50k reads/day) |
| Cloud Storage | ~£0 (pennies/month at this scale) |
| Cloud Build | ~£0 (120 free build-minutes/day) |
| **Total** | **~£0–2/month** |

The only cost that could creep up is if you store many large PDF invoices in GCS — but at £0.02/GB/month, 5GB of documents would cost £0.10/month.
