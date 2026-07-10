#!/bin/sh
# Optional GCP Cloud Run deployment (Fase 4)
# Requires: gcloud CLI authenticated, OPENAI_API_KEY in Secret Manager

set -e

PROJECT_ID="${GCP_PROJECT_ID:-your-project}"
REGION="${GCP_REGION:-us-central1}"

echo "Building and pushing images..."
docker tag pi1-app-api gcr.io/$PROJECT_ID/pi1-rag-api:latest
docker tag pi1-app-web gcr.io/$PROJECT_ID/pi1-rag-web:latest
docker push gcr.io/$PROJECT_ID/pi1-rag-api:latest
docker push gcr.io/$PROJECT_ID/pi1-rag-web:latest

echo "Deploying API to Cloud Run..."
gcloud run deploy pi1-rag-api \
  --image gcr.io/$PROJECT_ID/pi1-rag-api:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --memory 2Gi \
  --timeout 60

echo "Deploying Web to Cloud Run..."
gcloud run deploy pi1-rag-web \
  --image gcr.io/$PROJECT_ID/pi1-rag-web:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated

echo "Done. Update VITE_API_URL and redeploy web with API URL."
