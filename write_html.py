html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TRINETRA-C2 // Tactical Border Surveillance Command & Control</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>

  <!-- 1. TOP COMMAND TELEMETRY RIBBON -->
  <header class="header-bar">
    <div class="brand-section">
      <div class="brand-badge">T3</div>
      <div>
        <div class="brand-title">TRINETRA-C2 // DEFENSE COMMAND & CONTROL</div>
        <div class="brand-subtitle">MINISTRY OF HOME AFFAIRS (MHA) | SIH PS 26187 | AUTONOMOUS BORDER AI</div>
      </div>
    </div>

    <div class="telemetry-group">
      <div class="metric-chip live" id="status-chip">
        <span class="status-dot"></span> <span id="telem-status">SENTRY SECURE</span>
      </div>
      <div class="metric-chip">
        <span style="color: var(--text-muted)">ACTIVE SECTOR:</span>
        <strong id="telem-sector" style="color: var(--c-cyan)">TRINETRA-PUNJAB-04</strong>
      </div>
      <div class="metric-chip">
        <span style="color: var(--text-muted)">FPS:</span>
        <strong id="telem-fps" style="color: #fff">30.0 FPS</strong>
      </div>
      <div class="metric-chip">
        <span style="color: var(--text-muted)">LATENCY:</span>
        <strong id="telem-latency" style="color: #fff">11.2ms</strong>
      </div>
      <div class="metric-chip">
        <span style="color: var(--text-muted)">TRACKED:</span>
        <strong id="telem-tracked" style="color: var(--c-green)">0</strong>
      </div>
      <div class="metric-chip" style="font-size: 10px; color: var(--text-muted)">
        <span id="clock-ist">--:--:-- IST</span> | <span id="clock-utc">--:--:-- UTC</span>
      </div>
    </div>
  </header>

  <!-- 2. MAIN TACTICAL GRID -->
  <main class="c2-grid">

    <!-- COLUMN 1: GEOSPATIAL MAP & SECTORS -->
    <section class="panel">
      <div class="panel-header">
        <span>GEOSPATIAL FRONTIER RADAR</span>
        <span style="color: var(--text-muted); font-size: 10px;">DECK.GL // LEAFLET</span>
      </div>
      <div id="tactical-map"></div>
      
      <div class="panel-header" style="border-top: 1px solid var(--border-subtle);">
        <span>SENTRY SECTOR NETWORK</span>
        <span style="color: var(--c-green); font-size: 10px;">4 ONLINE</span>
      </div>
      <div class="panel-body">
        <div class="sector-list" id="sector-list"></div>
      </div>
    </section>

    <!-- COLUMN 2: LIVE EDGE VIDEO & CONTROLS -->
    <section class="panel" style="grid-column: 2;">
      <div class="panel-header">
        <span>LIVE EDGE VIDEO PERCEPTION STREAM</span>
        <span style="color: var(--c-cyan); font-size: 10px;">YOLOV8n + BYTETRACK + JORDAN CURVE</span>
      </div>

      <div class="video-wrapper">
        <img id="live-stream" src="/api/stream" alt="Tactical Sentry Stream" />
        <div class="incursion-alert-banner" id="breach-banner">
          *** TACTICAL PERIMETER BREACH DETECTED ***
        </div>
      </div>

      <!-- TACTICAL ACTION DECK -->
      <div class="control-bar">
        <button class="btn-tactical" onclick="switchSector(1)">[1] SEC-01 FENCE</button>
        <button class="btn-tactical" onclick="switchSector(2)">[2] SEC-02 NIGHT FLIR</button>
        <button class="btn-tactical" onclick="switchSector(3)">[3] SEC-03 CHECKPOST</button>
        <button class="btn-tactical" onclick="switchSector(4)">[4] SEC-04 LIVE CAM</button>
        <button class="btn-tactical" id="btn-clahe">[C] CLAHE NIGHT BOOST</button>
        <button class="btn-tactical" id="btn-reset-zone">[Z] RESET STERILE ZONE</button>
        <button class="btn-tactical" id="btn-mute">[M] MUTE AUDIO</button>
        <button class="btn-tactical alert-btn" id="btn-evidence">[S] SEC-65B EVIDENCE</button>
      </div>
    </section>

    <!-- COLUMN 3: STSI RADAR & EVIDENCE VAULT -->
    <section class="panel" style="grid-column: 3;">
      <div class="panel-header">
        <span>SECTOR THREAT SEVERITY INDEX (STSI)</span>
        <span style="color: var(--text-muted); font-size: 10px;">WORLD MONITOR CII COMPOSITE</span>
      </div>
      <div style="padding: 10px;">
        <div class="stsi-panel" id="stsi-bars"></div>
      </div>

      <div class="panel-header" style="border-top: 1px solid var(--border-subtle);">
        <span>CRYPTOGRAPHIC EVIDENCE VAULT</span>
        <span style="color: var(--c-cyan); font-size: 10px;">SEC 65B TAMPER-PROOF</span>
      </div>
      <div class="panel-body">
        <div class="evidence-feed" id="evidence-feed"></div>
      </div>
    </section>

  </main>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="/static/app.js"></script>
</body>
</html>
"""

with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("static/index.html written successfully!")
