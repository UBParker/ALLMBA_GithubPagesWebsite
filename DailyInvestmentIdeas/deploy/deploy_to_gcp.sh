#!/bin/bash

# Deploy script for ALLMBA Daily Investment Ideas to Google Cloud Platform

set -e

# Load environment variables from .env file
if [ -f "../.env" ]; then
  source ../.env
else
  echo "Error: .env file not found."
  exit 1
fi

# Verify required environment variables
if [ -z "$GCP_PROJECT_ID" ]; then
  echo "Error: GCP_PROJECT_ID not set in .env file."
  exit 1
fi

if [ -z "$GCP_REGION" ]; then
  echo "Error: GCP_REGION not set in .env file."
  exit 1
fi

# Set project and region
echo "Setting GCP project to $GCP_PROJECT_ID..."
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com

# Create Cloud Storage bucket for data storage
BUCKET_NAME="${GCP_PROJECT_ID}-investment-data"
echo "Creating Cloud Storage bucket $BUCKET_NAME..."
gcloud storage buckets create gs://$BUCKET_NAME --location=$GCP_REGION --uniform-bucket-level-access || true

# Create service account for data collection
SERVICE_ACCOUNT="investment-data-collector"
SA_EMAIL="${SERVICE_ACCOUNT}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

echo "Creating service account $SERVICE_ACCOUNT..."
gcloud iam service-accounts create $SERVICE_ACCOUNT \
  --display-name="Investment Data Collector" || true

# Grant permissions
echo "Granting permissions to service account..."
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/firestore.user"

# Set hardcoded API keys
ALPHA_VANTAGE_API_KEY="ZMUZQIRZWJKML99P"
FRED_API_KEY="fb670d7e87729f288ed7ffb40f986bb9"
NEWS_API_KEY="b8851f0d4dc5462bbdddebc446bbfe89"
FINNHUB_API_KEY="d000cm9r01qud9ql2jagd000cm9r01qud9ql2jb0"

# Build and deploy data collection function
echo "Deploying data collection Cloud Function..."
cd ..
gcloud functions deploy collect-investment-data \
  --gen2 \
  --runtime=python39 \
  --region=$GCP_REGION \
  --source=. \
  --entry-point=collect_data_handler \
  --trigger-http \
  --service-account=$SA_EMAIL \
  --memory=1024MB \
  --timeout=540s \
  --set-env-vars="BUCKET_NAME=${BUCKET_NAME},ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY},FRED_API_KEY=${FRED_API_KEY},NEWS_API_KEY=${NEWS_API_KEY},FINNHUB_API_KEY=${FINNHUB_API_KEY}"

# Build and deploy analysis function
echo "Deploying analysis Cloud Function..."
gcloud functions deploy analyze-investment-data \
  --gen2 \
  --runtime=python39 \
  --region=$GCP_REGION \
  --source=. \
  --entry-point=analyze_data_handler \
  --trigger-http \
  --service-account=$SA_EMAIL \
  --memory=1024MB \
  --timeout=540s \
  --set-env-vars="BUCKET_NAME=${BUCKET_NAME},ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY},FRED_API_KEY=${FRED_API_KEY},NEWS_API_KEY=${NEWS_API_KEY},FINNHUB_API_KEY=${FINNHUB_API_KEY}"

# Build and deploy API as Cloud Run service
echo "Deploying API to Cloud Run..."
gcloud run deploy investment-ideas-api \
  --source=. \
  --region=$GCP_REGION \
  --service-account=$SA_EMAIL \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --allow-unauthenticated \
  --set-env-vars="BUCKET_NAME=${BUCKET_NAME},ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY},FRED_API_KEY=${FRED_API_KEY},NEWS_API_KEY=${NEWS_API_KEY},FINNHUB_API_KEY=${FINNHUB_API_KEY}"

# Set up Cloud Scheduler jobs
echo "Setting up Cloud Scheduler jobs..."
# Create App Engine application if it doesn't exist (required for Cloud Scheduler)
gcloud app create --region=${GCP_REGION} || true

# Collection job - runs every day at 6 AM UTC
COLLECT_FUNCTION_URL=$(gcloud functions describe collect-investment-data --region=$GCP_REGION --format='value(url)')
gcloud scheduler jobs create http collect-investment-data-job \
  --schedule="0 6 * * *" \
  --uri="$COLLECT_FUNCTION_URL" \
  --http-method=POST \
  --time-zone="UTC" \
  --attempt-deadline=10m \
  --oidc-service-account-email=$SA_EMAIL || true

# Analysis job - runs every day at 7 AM UTC
ANALYZE_FUNCTION_URL=$(gcloud functions describe analyze-investment-data --region=$GCP_REGION --format='value(url)')
gcloud scheduler jobs create http analyze-investment-data-job \
  --schedule="0 7 * * *" \
  --uri="$ANALYZE_FUNCTION_URL" \
  --http-method=POST \
  --time-zone="UTC" \
  --attempt-deadline=10m \
  --oidc-service-account-email=$SA_EMAIL || true

# Get the deployed service URL
API_URL=$(gcloud run services describe investment-ideas-api --region=$GCP_REGION --format='value(status.url)')

echo "\nDeployment completed successfully!"
echo "API URL: $API_URL"
echo "\nUpdate the API_BASE_URL in integration/github_pages_integration.js with this URL."
