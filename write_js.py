js = """// ===================================================================
// TRINETRA-C2 // TACTICAL DASHBOARD CLIENT LOGIC (WORLD MONITOR THEME)
// ===================================================================

let map;
let sectorMarkers = {};
let activeSectorId = 1;
let audioContext = null;
let lastBreachCount = 0;

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initControls();
    startPolling();
    initClocks();
});

// 1. Defense Clocks (IST / UTC)
function initClocks() {
    function updateClock() {
        const now = new Date();
        const utcStr = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        const istStr = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';
        document.getElementById('clock-utc').innerText = utcStr;
        document.getElementById('clock-ist').innerText = istStr;
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// 2. Tactical Geospatial Map (Leaflet.js + CartoDB Dark Tiles)
function initMap() {
    // Centered on North-Western Indian Frontier
    map = L.map('tactical-map', {
        zoomControl: false,
        attributionControl: false
    }).setView([30.5, 74.5], 5);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 10,
        subdomains: 'abcd'
    }).addTo(map);

    // Fetch and place sector markers
    fetch('/api/sectors')
        .then(res => res.json())
        .then(sectors => {
            renderSectors(sectors);
        });
}

function renderSectors(sectors) {
    const listContainer = document.getElementById('sector-list');
    listContainer.innerHTML = '';

    sectors.forEach(s => {
        // Create custom pulsating SVG marker
        const isSelected = s.id === activeSectorId;
        const markerColor = isSelected ? '#00f0ff' : '#10b981';
        
        const customIcon = L.divIcon({
            className: 'tactical-marker',
            html: `<div style="
                width: 14px; 
                height: 14px; 
                border-radius: 50%; 
                background: ${markerColor}; 
                box-shadow: 0 0 10px ${markerColor};
                border: 2px solid #000;
            "></div>`,
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });

        if (sectorMarkers[s.id]) {
            map.removeLayer(sectorMarkers[s.id]);
        }

        const marker = L.marker([s.lat, s.lng], { icon: customIcon }).addTo(map);
        marker.bindTooltip(`<b>${s.codename}</b><br>${s.location}<br>STSI: ${s.stsi}%`, {
            direction: 'top',
            className: 'tactical-tooltip'
        });
        marker.on('click', () => switchSector(s.id));
        sectorMarkers[s.id] = marker;

        // Add Sector Card to Sidebar
        const card = document.createElement('div');
        card.className = `sector-card ${isSelected ? 'active' : ''}`;
        card.id = `sector-card-${s.id}`;
        card.onclick = () => switchSector(s.id);
        
        const isHighRisk = s.stsi > 70;
        card.innerHTML = `
            <div class="sector-card-head">
                <span class="sector-name">${s.codename}</span>
                <span class="sector-stsi ${isHighRisk ? 'high' : ''}">STSI: ${s.stsi}%</span>
            </div>
            <div class="sector-desc">${s.location} // ${s.type}</div>
        `;
        listContainer.appendChild(card);
    });
}

// 3. Sector Switching
function switchSector(sectorId) {
    if (sectorId === activeSectorId) return;
    activeSectorId = sectorId;

    fetch('/api/control/switch_sector', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sector: sectorId })
    }).then(() => {
        // Re-center map smoothly
        fetch('/api/sectors')
            .then(res => res.json())
            .then(sectors => {
                const s = sectors.find(x => x.id === sectorId);
                if (s) {
                    map.flyTo([s.lat, s.lng], 6, { duration: 1.2 });
                }
                renderSectors(sectors);
            });

        // Refresh Stream Image to prevent browser socket stall
        const streamImg = document.getElementById('live-stream');
        streamImg.src = '/api/stream?t=' + Date.now();
    });
}

// 4. Tactical Controls Bar
function initControls() {
    document.getElementById('btn-clahe').onclick = () => {
        fetch('/api/control/toggle_clahe', { method: 'POST' });
    };
    document.getElementById('btn-mute').onclick = () => {
        fetch('/api/control/toggle_mute', { method: 'POST' });
    };
    document.getElementById('btn-reset-zone').onclick = () => {
        fetch('/api/control/reset_zone', { method: 'POST' });
    };
    document.getElementById('btn-evidence').onclick = () => {
        fetch('/api/control/capture_evidence', { method: 'POST' })
            .then(() => loadEvidence());
    };
}

// 5. Polling Telemetry & STSI Radar
function startPolling() {
    setInterval(() => {
        // Telemetry Update
        fetch('/api/telemetry')
            .then(res => res.json())
            .then(data => {
                document.getElementById('telem-fps').innerText = data.fps + ' FPS';
                document.getElementById('telem-latency').innerText = data.latency_ms + 'ms';
                document.getElementById('telem-tracked').innerText = data.tracked_count;
                document.getElementById('telem-sector').innerText = data.codename;
                document.getElementById('telem-status').innerText = data.status;

                // Breach Strobe Banner
                const banner = document.getElementById('breach-banner');
                const chip = document.getElementById('status-chip');
                if (data.is_breached) {
                    banner.style.display = 'block';
                    banner.innerText = `*** TACTICAL PERIMETER BREACH (${data.breach_count} TARGETS IN STERILE ZONE) ***`;
                    chip.className = 'metric-chip alert';
                    chip.innerHTML = `<span class="status-dot red"></span> INTRUSION DETECTED`;
                } else {
                    banner.style.display = 'none';
                    chip.className = 'metric-chip live';
                    chip.innerHTML = `<span class="status-dot"></span> SENTRY SECURE`;
                }

                // CLAHE and Mute button active states
                const btnClahe = document.getElementById('btn-clahe');
                if (data.clahe_enabled) btnClahe.classList.add('active');
                else btnClahe.classList.remove('active');

                const btnMute = document.getElementById('btn-mute');
                if (data.audio_muted) {
                    btnMute.innerText = '[M] AUDIO MUTED';
                    btnMute.classList.add('active');
                } else {
                    btnMute.innerText = '[M] MUTE AUDIO';
                    btnMute.classList.remove('active');
                }
            })
            .catch(() => {});

        // Sectors & STSI update
        fetch('/api/sectors')
            .then(res => res.json())
            .then(sectors => {
                renderSTSI(sectors);
            })
            .catch(() => {});
            
    }, 800);

    // Evidence Log Update (every 2.5s)
    setInterval(loadEvidence, 2500);
    loadEvidence();
}

// 6. STSI Threat Radar Rendering (Inspired by CII)
function renderSTSI(sectors) {
    const container = document.getElementById('stsi-bars');
    container.innerHTML = '';

    sectors.forEach(s => {
        let barClass = '';
        if (s.stsi >= 75) barClass = 'critical';
        else if (s.stsi >= 50) barClass = 'warning';

        const row = document.createElement('div');
        row.className = 'stsi-row';
        row.innerHTML = `
            <div class="stsi-labels">
                <span style="color: ${s.id === activeSectorId ? 'var(--c-cyan)' : 'var(--text-main)'}; font-weight: 700;">${s.codename}</span>
                <span style="font-weight: 800; color: ${barClass === 'critical' ? 'var(--c-red)' : 'var(--c-green)'}">${s.stsi}%</span>
            </div>
            <div class="stsi-bar-bg">
                <div class="stsi-bar-fill ${barClass}" style="width: ${s.stsi}%"></div>
            </div>
        `;
        container.appendChild(row);
    });
}

// 7. Cryptographic Section 65B Evidence Ledger
function loadEvidence() {
    fetch('/api/evidence')
        .then(res => res.json())
        .then(records => {
            const feed = document.getElementById('evidence-feed');
            if (records.length === 0) {
                feed.innerHTML = '<div style="font-size: 10px; color: var(--text-dim); text-align: center; margin-top: 30px;">NO INCIDENT RECORDS IN VAULT</div>';
                return;
            }

            feed.innerHTML = '';
            records.slice(0, 15).forEach(r => {
                const item = document.createElement('div');
                item.className = `evidence-item ${r.target_class !== 'MANUAL_OPERATOR_SWEEP' ? 'breach' : ''}`;
                
                const shortHash = r.sha256_hash ? r.sha256_hash.substring(0, 24) + '...' : 'SEC-65B SEALED';
                const timeStr = r.timestamp || 'RECENT';
                const imgSrc = r.relative_image_path ? '/' + r.relative_image_path : '';

                item.innerHTML = `
                    <div class="evidence-head">
                        <span>${r.target_class} // ID#${r.track_id}</span>
                        <span style="color: var(--text-muted); font-size: 9px;">${timeStr.split(' ')[1] || timeStr}</span>
                    </div>
                    <div class="evidence-meta">
                        <span>CONF: ${Math.round((r.confidence || 1.0) * 100)}%</span>
                        <span>ACT: SEC-65B COMMITTED</span>
                    </div>
                    <div class="evidence-hash" title="${r.sha256_hash}">
                        SHA-256: ${shortHash}
                    </div>
                `;
                feed.appendChild(item);
            });
        })
        .catch(() => {});
}
"""

with open("static/app.js", "w", encoding="utf-8") as f:
    f.write(js)
print("static/app.js written successfully!")
