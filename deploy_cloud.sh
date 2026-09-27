#!/bin/bash
# ======================================================================
# PROJECT TRINETRA-C2 // AUTOMATED CLOUD DEPLOYMENT SCRIPT
# AI Border Surveillance Video Analytics (SIH PS 26187 // MHA CIBMS)
# ======================================================================

set -e

IMAGE_NAME="trinetra-c2"
CONTAINER_NAME="trinetra-c2-sentry"
PORT="${PORT:-8080}"

echo "======================================================================"
echo " TRINETRA-C2: 1-CLICK CLOUD DEPLOYMENT & DOCKER BUILD AUTOMATION"
echo "======================================================================"

echo ""
echo "Select Deployment Target:"
echo " 1) Build and Run Docker Locally / On-Premise"
echo " 2) Deploy to Google Cloud Run (Serverless)"
echo " 3) Build and Tag for Docker Hub / AWS ECR / Private Registry"
echo " 4) Run via Docker Compose with Persistent Volumes"
echo ""
read -p "Enter choice [1-4]: " CHOICE

case "$CHOICE" in
  1)
    echo "[+] Building Docker Image: $IMAGE_NAME..."
    docker build -t $IMAGE_NAME .
    
    echo "[+] Stopping existing container if running..."
    docker rm -f $CONTAINER_NAME 2>/dev/null || true
    
    echo "[+] Running container on port $PORT..."
    docker run -d \
      --name $CONTAINER_NAME \
      -p $PORT:8080 \
      -v "$(pwd)/evidence:/app/evidence" \
      -v "$(pwd)/known_faces:/app/known_faces" \
      $IMAGE_NAME
    
    echo ""
    echo "======================================================================"
    echo " SUCCESS: TRINETRA-C2 is running at http://localhost:$PORT"
    echo " View logs with: docker logs -f $CONTAINER_NAME"
    echo "======================================================================"
    ;;

  2)
    read -p "Enter Google Cloud Project ID: " GCP_PROJECT
    read -p "Enter GCP Region (default: asia-south1): " GCP_REGION
    GCP_REGION=${GCP_REGION:-asia-south1}
    
    echo "[+] Deploying directly to Google Cloud Run..."
    gcloud run deploy trinetra-c2 \
      --source . \
      --platform managed \
      --region $GCP_REGION \
      --project $GCP_PROJECT \
      --allow-unauthenticated \
      --memory 2Gi \
      --cpu 2 \
      --port 8080
    ;;

  3)
    read -p "Enter Registry Image Name (e.g. docker.io/username/trinetra-c2:latest): " REG_IMAGE
    echo "[+] Building and tagging image: $REG_IMAGE..."
    docker build -t $REG_IMAGE .
    echo "[+] Pushing to registry..."
    docker push $REG_IMAGE
    echo "SUCCESS: Image pushed to $REG_IMAGE"
    ;;

  4)
    echo "[+] Launching TRINETRA-C2 via Docker Compose..."
    docker compose up --build -d
    echo ""
    echo "SUCCESS: Stack launched. Check status with: docker compose ps"
    ;;

  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac
