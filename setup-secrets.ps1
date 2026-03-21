# setup-secrets.ps1
# One-time setup: stores secrets in GCP Secret Manager for lahiff-management.
# Run from the repo root with: .\setup-secrets.ps1

$PROJECT = "lahiff-management"

gcloud config set project $PROJECT
$PROJECT_NUMBER = gcloud projects describe $PROJECT --format='value(projectNumber)'

Write-Host "`nEnabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Prompt for secret values — nothing is hardcoded or written to disk
$GCS_BUCKET = Read-Host "GCS bucket name"
$ANTHROPIC_KEY = Read-Host "Anthropic API key"

Write-Host "`nCreating secrets..."
[System.Text.Encoding]::UTF8.GetBytes($GCS_BUCKET) | gcloud secrets create GCS_BUCKET_NAME --data-file=-
[System.Text.Encoding]::UTF8.GetBytes($ANTHROPIC_KEY) | gcloud secrets create ANTHROPIC_API_KEY --data-file=-

Write-Host "`nGranting Cloud Run service account access..."
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding GCS_BUCKET_NAME `
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding ANTHROPIC_API_KEY `
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"

Write-Host "`nGranting Cloud Build access..."
gcloud projects add-iam-policy-binding $PROJECT `
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

Write-Host "`nDone. Push to main to deploy with secrets injected automatically."
