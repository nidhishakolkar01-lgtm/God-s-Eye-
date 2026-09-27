# ======================================================================
# PROJECT TRINETRA-C2 // WINDOWS POWERSHELL CLOUD DEPLOYMENT SCRIPT
# AI Border Surveillance Video Analytics (SIH PS 26187 // MHA CIBMS)
# ======================================================================

param(
    [string]$Port = "8080"
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " TRINETRA-C2: 1-CLICK CLOUD DEPLOYMENT & DOCKER BUILD AUTOMATION" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Select Deployment Target:"
Write-Host " 1) Build and Run Docker Locally / On-Premise"
Write-Host " 2) Deploy to Google Cloud Run (Serverless)"
Write-Host " 3) Run via Docker Compose with Persistent Volumes"
Write-Host " 4) Exit"
Write-Host ""

$choice = Read-Host "Enter choice [1-4]"

switch ($choice) {
    "1" {
        Write-Host "[+] Building Docker Image: trinetra-c2..." -ForegroundColor Green
        docker build -t trinetra-c2 .
        
        Write-Host "[+] Removing previous container if active..." -ForegroundColor Yellow
        docker rm -f trinetra-c2-sentry 2>$null

        Write-Host "[+] Running container on port $Port..." -ForegroundColor Green
        docker run -d `
            --name trinetra-c2-sentry `
            -p "${Port}:8080" `
            -v "${PWD}\evidence:/app/evidence" `
            -v "${PWD}\known_faces:/app/known_faces" `
            trinetra-c2

        Write-Host ""
        Write-Host "======================================================================" -ForegroundColor Cyan
        Write-Host " SUCCESS: TRINETRA-C2 is running at http://localhost:$Port" -ForegroundColor Green
        Write-Host " View live container logs with: docker logs -f trinetra-c2-sentry" -ForegroundColor White
        Write-Host "======================================================================" -ForegroundColor Cyan
    }
    "2" {
        $gcpProject = Read-Host "Enter Google Cloud Project ID"
        $gcpRegion = Read-Host "Enter GCP Region (default: asia-south1)"
        if ([string]::IsNullOrWhiteSpace($gcpRegion)) { $gcpRegion = "asia-south1" }

        Write-Host "[+] Deploying directly to Google Cloud Run..." -ForegroundColor Green
        gcloud run deploy trinetra-c2 `
            --source . `
            --platform managed `
            --region $gcpRegion `
            --project $gcpProject `
            --allow-unauthenticated `
            --memory 2Gi `
            --cpu 2 `
            --port 8080
    }
    "3" {
        Write-Host "[+] Launching TRINETRA-C2 via Docker Compose..." -ForegroundColor Green
        docker compose up --build -d
        Write-Host "SUCCESS: Stack launched. Check status with: docker compose ps" -ForegroundColor Cyan
    }
    Default {
        Write-Host "Exiting." -ForegroundColor Yellow
    }
}
