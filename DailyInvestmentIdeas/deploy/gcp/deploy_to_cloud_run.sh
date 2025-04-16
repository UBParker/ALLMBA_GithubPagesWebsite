#!/bin/bash
# Deploy ALLMBA Daily Investment Ideas to Google Cloud Run

# Set variables
PROJECT_ID="alan-banking-assistant"
REGION="us-central1"
SERVICE_NAME="investment-ideas-api"
DATA_BUCKET="${PROJECT_ID}-investment-data"

# Ensure we're in the project root directory
cd "$(dirname "$0")/../.." || exit 1

echo "=== ALLMBA Daily Investment Ideas - Google Cloud Run Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"
echo ""

# 1. Check if user is logged in
echo "Checking gcloud authentication..."
gcloud auth print-identity-token &>/dev/null || gcloud auth login

# 2. Set the project
echo "Setting gcloud project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# 3. Enable required services
echo "Enabling required GCP services..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com storage.googleapis.com

# 4. Check if the Cloud Storage bucket exists, create if it doesn't
echo "Setting up Cloud Storage bucket for data..."
if gsutil ls -b "gs://${DATA_BUCKET}" &>/dev/null; then
    echo "Bucket gs://${DATA_BUCKET} already exists."
else
    echo "Creating bucket gs://${DATA_BUCKET}..."
    gsutil mb -l "$REGION" "gs://${DATA_BUCKET}"
fi

# 5. Build and deploy to Cloud Run
echo "Building and deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "STORAGE_BUCKET=${DATA_BUCKET}" \
    --memory 2Gi

# 6. Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
echo "Deployment complete!"
echo "Service URL: $SERVICE_URL"
echo "API URL: ${SERVICE_URL}/api"
echo ""

# 7. Set up the GitHub Pages integration
echo "To integrate with GitHub Pages:"
echo "1. Update the API_BASE_URL in github_pages_integration.js:"
echo "   const API_BASE_URL = '${SERVICE_URL}/api';"
echo ""
echo "2. Copy the integration files to your GitHub Pages repository:"
echo "   cp integration/investment_ideas_template.html /path/to/your/github/pages/repo/"
echo "   cp integration/github_pages_integration.js /path/to/your/github/pages/repo/js/"
echo ""

# 8. Set up a scheduler (optional)
if [[ "$1" == "--with-scheduler" ]]; then
    echo "Setting up Cloud Scheduler for daily data updates..."
    
    # Create a service account for the scheduler
    SA_NAME="investment-ideas-updater"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if service account exists
    if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
        echo "Service account $SA_EMAIL already exists."
    else
        echo "Creating service account $SA_EMAIL..."
        gcloud iam service-accounts create "$SA_NAME" \
            --display-name "Investment Ideas Updater"
    fi
    
    # Grant the service account permission to invoke the Cloud Run service
    echo "Granting permissions to service account..."
    gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/run.invoker" \
        --region "$REGION"
    
    # Enable Cloud Scheduler API
    echo "Enabling Cloud Scheduler API..."
    gcloud services enable cloudscheduler.googleapis.com
    
    # Create the scheduler job
    JOB_NAME="update-investment-ideas-daily"
    
    # Delete the job if it already exists
    gcloud scheduler jobs delete "$JOB_NAME" --quiet 2>/dev/null || true
    
    echo "Creating scheduler job $JOB_NAME..."
    gcloud scheduler jobs create http "$JOB_NAME" \
        --schedule="0 5 * * *" \
        --uri="${SERVICE_URL}/api/tasks/update" \
        --http-method=POST \
        --oidc-service-account-email="$SA_EMAIL" \
        --oidc-token-audience="${SERVICE_URL}" \
        --location="$REGION" \
        --description="Trigger daily update of investment ideas data"
    
    echo "Cloud Scheduler job created. Data will be updated daily at 5:00 AM UTC."
fi

echo "Deployment to Google Cloud Run completed successfully!"