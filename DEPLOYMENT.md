# 🚀 Project TRINETRA-C2: 1-Click Cloud Deployment Guide
**Autonomous AI Video Analytics Platform for Border Surveillance**  
**Smart India Hackathon (SIH) 2026 | Problem Statement ID: 26187 | Ministry of Home Affairs (MHA)**

---

## 📋 Overview of Deployment Options

TRINETRA-C2 is fully containerized using **Docker** and pre-configured for **1-click cloud deployment** across all major hosting platforms.

| Cloud Platform | Cost / Tier | Best For | 1-Click Configuration |
| :--- | :--- | :--- | :--- |
| **Render.com** | Free / Standard ($7/mo) | **SIH Submission Live URL** | `render.yaml` Blueprint |
| **Railway.app** | $5 free trial | Quick GitHub CI/CD Deploy | `railway.json` |
| **Hugging Face Spaces** | **100% Free (16GB RAM CPU)** | Free 24/7 Academic / SIH Host | Docker Space |
| **Google Cloud Run** | Free tier (2M req/mo) | Scalable Defense Serverless | `deploy_cloud.sh` |
| **AWS Lightsail / EC2** | $3.50/mo | Dedicated VPS with Static IP | `docker-compose.yml` |
| **Local / On-Premise** | Free | Offline Sentry Outpost Edge | `docker compose up -d` |

---

## 🌐 Option 1: 1-Click Deploy on Render.com (Recommended for SIH)

Render allows you to deploy directly from your GitHub repository using the included `render.yaml` blueprint.

### Steps:
1. Push this project to your GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "feat: Project TRINETRA-C2 Cloud Deployment"
   git remote add origin https://github.com/your-username/trinetra-c2.git
   git push -u origin main
   ```
2. Go to **[Render.com](https://render.com/)** and sign in.
3. Click **New +** &rarr; **Blueprint**.
4. Connect your `trinetra-c2` GitHub repository.
5. Render will automatically read `render.yaml`, build the Docker container, and provide you with a permanent HTTPS link:
   ```
   https://trinetra-c2-border-sentry.onrender.com
   ```
6. **Submit this permanent URL to the SIH portal!**

---

## 🚂 Option 2: 1-Click Deploy on Railway.app

1. Sign in to **[Railway.app](https://railway.app/)**.
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select your `trinetra-c2` repository.
4. Railway will automatically detect the `Dockerfile` and `railway.json` and start building.
5. Under **Settings** &rarr; **Networking**, click **Generate Domain** to get your public HTTPS URL.

---

## 🤗 Option 3: Deploy Free on Hugging Face Spaces (16GB RAM Free)

Hugging Face Spaces provides free 16 GB RAM Docker environments that never sleep:

1. Go to **[huggingface.co/spaces](https://huggingface.co/spaces)** &rarr; **Create new Space**.
2. Choose:
   * **Space SDK:** `Docker`
   * **Docker template:** `Blank`
   * **Hardware:** `CPU Basic (2 vCPU, 16GB RAM) - Free`
3. Clone the space repository locally or push your files directly:
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/trinetra-c2
   git push space main
   ```
4. Hugging Face builds the Docker container and opens the live interactive dashboard directly inside your browser!

---

## ☁️ Option 4: Deploy to Google Cloud Run (Serverless)

If you have the Google Cloud SDK (`gcloud`) installed:

### Linux / macOS:
```bash
./deploy_cloud.sh
# Select Option 2 (Deploy to Google Cloud Run)
```

### Windows PowerShell:
```powershell
.\deploy_cloud.ps1
# Select Option 2
```

Or run the single command:
```bash
gcloud run deploy trinetra-c2 \
  --source . \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8080
```

---

## 🐳 Option 5: Local & On-Premises Docker Deployment

To run the container locally on any Linux, macOS, or Windows machine with Docker installed:

### Using Docker Compose (Recommended):
```bash
docker compose up --build -d
```
* Dashboard will be live at: **`http://localhost:8080`**
* Evidence ledger and snapshots are automatically persisted in `./evidence`.
* Check container status:
  ```bash
  docker compose ps
  docker compose logs -f
  ```

### Using Standard Docker CLI:
```bash
# 1. Build the image
docker build -t trinetra-c2 .

# 2. Run container with persistent volume mounts
docker run -d \
  --name trinetra-c2-sentry \
  -p 8080:8080 \
  -v $(pwd)/evidence:/app/evidence \
  -v $(pwd)/known_faces:/app/known_faces \
  trinetra-c2
```

---

## 🛡️ Container Health Check & Diagnostics

The container includes a built-in health check polling the C2 telemetry API every 30 seconds:

```bash
# Inspect container health
docker inspect --format='{{json .State.Health}}' trinetra-c2-sentry
```

**Healthcheck Endpoint:**  
`GET /api/telemetry` &rarr; Returns HTTP `200 OK` with live FPS, FARR noise suppression %, and MGRS coordinates.
