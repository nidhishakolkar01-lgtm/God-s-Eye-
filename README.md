# PROJECT TRINETRA-C2: Autonomous Border Surveillance Platform
**AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure**  
**Smart India Hackathon (SIH) 2026 | Problem Statement ID: 26187 | Ministry of Home Affairs (MHA)**

---

## 🎯 Executive Summary & Mission
Project **TRINETRA-C2** transforms existing, low-cost border CCTV infrastructure into an autonomous edge-intelligence sentry system. Designed for the **Ministry of Home Affairs (MHA)** and border guarding forces (**BSF / ITBP / SSB**), TRINETRA-C2 solves three critical field challenges:
1. **Dynamic CCTV / RTSP Stream Ingestion**: Connect any existing IP camera, RTSP network stream, or USB optical sensor on-the-fly without restarting services.
2. **False Alarm Reduction Rate (FARR > 94%)**: Eliminates 90%+ false alarms caused by wildlife (camels, dogs, cattle, birds), windblown foliage, dust storms, and headlight glares using dual-tier taxonomy and 15-frame spatiotemporal persistence.
3. **Multi-Channel Instant Incident Alerting**: Dispatches high-resolution breach snapshots, MGRS grid coordinates, and threat levels to field commanders via Telegram Bot API and central C2 Webhooks.
4. **Court-Admissible Legal Forensics**: Automated Section 65B(4) Indian Evidence Act compliance with SHA-256 cryptographic hashing and digital warrant certificate generation.

---

## 🚀 1-Click Cloud & Docker Deployment

TRINETRA-C2 is fully containerized and pre-configured for 1-click cloud deployment. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for complete step-by-step guides.

### Option A: 1-Click Deploy on Render.com (Recommended for SIH)
1. Push repository to GitHub.
2. In [Render.com](https://render.com), click **New +** &rarr; **Blueprint** and select your repository.
3. Render automatically provisions the container using `render.yaml` and gives you a permanent HTTPS link.

### Option B: Local / On-Premise Docker Compose
```bash
docker compose up --build -d
```
Access the dashboard at **`http://localhost:8080`**.

### Option C: Google Cloud Run (Serverless)
```bash
# On Linux/macOS:
./deploy_cloud.sh
# On Windows PowerShell:
.\deploy_cloud.ps1
```

---

## 💻 Localhost Quick Start Guide (Direct Python)

### 1. Prerequisites & Environment
Ensure you are using the local virtual environment:
```powershell
cd "C:\Users\nidhi\Downloads\Gods Eye"
.\.venv\Scripts\python.exe server.py
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser.

### 2. Connect Physical RTSP CCTV Feeds or Webcams
Click **`[+ CCTV / RTSP]`** in the dashboard top bar, or launch via CLI:
```powershell
# USB Webcam:
.\.venv\Scripts\python.exe main.py --source 0

# Network RTSP CCTV Camera:
.\.venv\Scripts\python.exe main.py --source "rtsp://username:password@192.168.1.100:554/stream1"
```

---

## ⌨️ Interactive Tactical Hotkeys

| Key | Action | Description |
| :---: | :--- | :--- |
| **`1`** | **Sector 1** | Border Perimeter Wall & Fence Incursion (intruders scaling barrier). |
| **`2`** | **Sector 2** | Thermal RVSS Night Vision (infrared drop-zone incursion). |
| **`3`** | **Sector 3** | Forward Security Checkpost (elevated mast camera & barricades). |
| **`4`** | **Sector 4** | Live USB Webcam / Optical Sensor. |
| **`X`** | **2x2 Matrix** | Toggles 4-camera composite sentry grid. |
| **`C`** | **CLAHE Night** | Hardware Contrast Limited Adaptive Histogram Equalization (+34% contrast). |
| **`Z`** | **Tripwire Zone** | Toggles polygon wireframe. Left-click to add points; Right-click to seal. |
| **`M`** | **Mute Klaxon** | Toggles audio siren alerts and visual-only sentry mode. |
| **`S`** | **Sec-65B Ledger** | Manually commits forensic snapshot with SHA-256 hash in legal evidence ledger. |
| **`T`** | **Theater Mode** | Expands video player to full viewport width. |

---

## 📁 System Architecture

```
├── Dockerfile                  # Production Debian-based container (PyTorch CPU + OpenCV)
├── docker-compose.yml          # Container orchestration with persistent volumes
├── render.yaml                 # Render.com 1-click cloud blueprint
├── railway.json                # Railway.app 1-click cloud configuration
├── fly.toml                    # Fly.io cloud deployment manifest
├── deploy_cloud.sh             # Automated Linux cloud build & deploy script
├── deploy_cloud.ps1            # Automated Windows PowerShell deploy script
├── DEPLOYMENT.md               # Comprehensive 1-click cloud hosting documentation
├── requirements-docker.txt     # Linux-optimized container dependencies
├── server.py                   # High-performance FastAPI C2 backend & REST endpoints
├── core/
│   ├── alert_dispatcher.py     # Non-blocking Telegram Bot API & Webhook dispatch
│   ├── tripwire.py             # Jordan curve raycasting & FARR false alarm filter
│   ├── camera_manager.py       # Dynamic RTSP ingestion & USB hardware scanner
│   ├── detector.py             # YOLOv8 neural perception & multi-spectral CLAHE
│   ├── evidence_logger.py      # Section 65B Indian Evidence Act SHA-256 ledger
│   ├── anpr_engine.py          # PyTorch OCR vehicle license plate recognizer
│   ├── face_engine.py          # YuNet + SFace biometric vector embedding matcher
│   ├── reid_engine.py          # MobileNetV3 multi-camera appearance re-identification
│   └── interdiction_engine.py  # Kinematic vector intercept & QRT dispatch ticketing
├── static/                     # CIBMS defense web dashboard (HTML5/CSS3/ES6)
└── evidence/                   # Section 65B cryptographic evidence ledger & snapshots
```
