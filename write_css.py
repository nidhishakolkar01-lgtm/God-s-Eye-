css = """/* ===================================================================
   TRINETRA-C2 // DEFENSE TACTICAL C2 STYLESHEET (WORLD MONITOR INSPIRED)
   =================================================================== */

:root {
  --bg-core: #070a09;
  --bg-panel: #0d1411;
  --bg-panel-header: #131c18;
  --border-subtle: #1c2b24;
  --border-active: #00f0ff;
  --border-alert: #ff2a4b;
  
  --text-main: #e2e8f0;
  --text-muted: #829a90;
  --text-dim: #4d6359;
  
  --c-cyan: #00f0ff;
  --c-green: #00ff77;
  --c-amber: #f59e0b;
  --c-red: #ff2a4b;
  --c-blue: #3b82f6;

  --font-mono: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: var(--bg-core);
  color: var(--text-main);
  font-family: var(--font-mono);
  overflow-x: hidden;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 1. TOP COMMAND TELEMETRY BAR */
.header-bar {
  height: 52px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  z-index: 1000;
}

.brand-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  border: 1px solid var(--c-cyan);
  background: rgba(0, 240, 255, 0.1);
  color: var(--c-cyan);
  font-weight: 800;
  font-size: 14px;
}

.brand-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #ffffff;
}

.brand-subtitle {
  font-size: 11px;
  color: var(--text-muted);
}

.telemetry-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  font-size: 11px;
}

.metric-chip.live {
  border-color: rgba(0, 255, 119, 0.3);
  background: rgba(0, 255, 119, 0.08);
  color: var(--c-green);
}

.metric-chip.alert {
  border-color: rgba(255, 42, 75, 0.6);
  background: rgba(255, 42, 75, 0.15);
  color: var(--c-red);
  animation: pulse-red 1.2s infinite;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c-green);
  box-shadow: 0 0 6px var(--c-green);
}

.status-dot.red {
  background: var(--c-red);
  box-shadow: 0 0 8px var(--c-red);
}

/* 2. MAIN TACTICAL GRID */
.c2-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr 380px;
  gap: 6px;
  padding: 6px;
  height: calc(100vh - 52px);
  overflow: hidden;
}

.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.panel-header {
  height: 36px;
  background: var(--bg-panel-header);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--c-cyan);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 3. COLUMN 1: GEOSPATIAL MAP & SECTORS */
#tactical-map {
  height: 260px;
  width: 100%;
  border: 1px solid var(--border-subtle);
  background: #050807;
  flex-shrink: 0;
}

.sector-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  flex: 1;
}

.sector-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-subtle);
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sector-card:hover {
  background: rgba(0, 240, 255, 0.05);
  border-color: var(--c-cyan);
}

.sector-card.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--c-cyan);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.15);
}

.sector-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.sector-name {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}

.sector-stsi {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(0, 255, 119, 0.1);
  color: var(--c-green);
}

.sector-stsi.high {
  background: rgba(255, 42, 75, 0.2);
  color: var(--c-red);
}

.sector-desc {
  font-size: 10px;
  color: var(--text-muted);
  line-height: 1.3;
}

/* 4. COLUMN 2: VIDEO SENTRY & CONTROLS */
.video-wrapper {
  position: relative;
  flex: 1;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

#live-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.incursion-alert-banner {
  position: absolute;
  top: 12px;
  left: 5%;
  right: 5%;
  background: rgba(255, 42, 75, 0.9);
  color: #ffffff;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 800;
  text-align: center;
  letter-spacing: 0.8px;
  border-radius: 4px;
  box-shadow: 0 0 20px rgba(255, 42, 75, 0.8);
  display: none;
  animation: strobe-alert 0.8s infinite alternate;
}

.control-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background: var(--bg-panel-header);
  border-top: 1px solid var(--border-subtle);
}

.btn-tactical {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-tactical:hover {
  background: rgba(0, 240, 255, 0.15);
  border-color: var(--c-cyan);
  color: var(--c-cyan);
}

.btn-tactical.active {
  background: var(--c-cyan);
  color: #000;
}

.btn-tactical.alert-btn {
  border-color: rgba(255, 42, 75, 0.4);
}

.btn-tactical.alert-btn:hover {
  background: var(--c-red);
  color: #fff;
}

/* 5. COLUMN 3: STSI RADAR & EVIDENCE VAULT */
.stsi-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.stsi-row {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.stsi-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
}

.stsi-bar-bg {
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.stsi-bar-fill {
  height: 100%;
  background: var(--c-green);
  transition: width 0.4s ease;
}

.stsi-bar-fill.warning {
  background: var(--c-amber);
}

.stsi-bar-fill.critical {
  background: var(--c-red);
}

.evidence-feed {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.evidence-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--c-cyan);
  padding: 6px 8px;
  border-radius: 3px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.evidence-item.breach {
  border-left-color: var(--c-red);
}

.evidence-head {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  font-weight: 700;
  color: #ffffff;
}

.evidence-meta {
  font-size: 9px;
  color: var(--text-muted);
  display: flex;
  gap: 8px;
}

.evidence-hash {
  font-size: 9px;
  color: var(--c-cyan);
  background: rgba(0, 240, 255, 0.08);
  padding: 2px 4px;
  border-radius: 2px;
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ANIMATIONS */
@keyframes pulse-red {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes strobe-alert {
  0% { transform: scale(0.98); opacity: 0.85; }
  100% { transform: scale(1.0); opacity: 1; }
}

/* SCROLLBARS */
::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}
::-webkit-scrollbar-track {
  background: var(--bg-core);
}
::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--text-dim);
}
"""

with open("static/styles.css", "w", encoding="utf-8") as f:
    f.write(css)
print("static/styles.css written successfully!")
