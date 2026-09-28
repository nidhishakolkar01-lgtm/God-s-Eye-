// ===================================================================
// TRINETRA // GOD'S EYE DEFENSE COMMAND JAVASCRIPT
// Real-Time Face Recognition, Multi-Spectral Sentry & Zero-Lag Streams
// ===================================================================

let map;
let sectorMarkers = {};
let activeSectorId = 1;
let audioContext = null;
let lastBreachCount = 0;
let autoHandoffActive = true;
let currentSensorMode = "NORMAL";

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initControls();
    startPolling();
    initClocks();
    fetchEnrolledFaces();
    fetchGlobalCameras();
});

// 1. Defense Clocks (IST / UTC)
function initClocks() {
    function updateClock() {
        const now = new Date();
        const istStr = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';
        const elIst = document.getElementById('clock-ist');
        if (elIst) elIst.innerText = istStr;
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// 2. Geospatial Map (Leaflet.js + CartoDB Dark)
function initMap() {
    map = L.map('tactical-map', {
        zoomControl: false,
        attributionControl: false
    }).setView([31.604, 74.572], 6);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 10,
        subdomains: 'abcd'
    }).addTo(map);

    fetch('/api/sectors')
        .then(res => res.json())
        .then(sectors => renderSectors(sectors));
}

function renderSectors(sectors) {
    const listContainer = document.getElementById('sector-list');
    if (!listContainer) return;
    listContainer.innerHTML = '';

    sectors.forEach(s => {
        const isSelected = s.id === activeSectorId;
        const markerColor = isSelected ? '#00f0ff' : '#00ff77';

        if (!sectorMarkers[s.id]) {
            const icon = L.divIcon({
                className: 'custom-radar-blip',
                html: `<div style="width: 12px; height: 12px; border-radius: 50%; background: ${markerColor}; border: 2px solid #fff; box-shadow: 0 0 8px ${markerColor}; cursor: pointer;"></div>`,
                iconSize: [12, 12]
            });

            const marker = L.marker([s.lat, s.lng], { icon: icon }).addTo(map);
            marker.on('click', () => switchSector(s.id));
            sectorMarkers[s.id] = marker;
        }

        const card = document.createElement('div');
        card.className = `sector-card ${isSelected ? 'active' : ''}`;
        card.onclick = () => switchSector(s.id);
        card.innerHTML = `
            <div class="sector-card-top">
                <span class="sector-name">${s.name}</span>
                <span style="color: ${s.stsi > 70 ? 'var(--c-red)' : 'var(--c-cyan)'}; font-size: 10px; font-weight: 800;">
                    STSI: ${s.stsi}
                </span>
            </div>
            <div class="sector-meta">
                <span>${s.type}</span>
                <span style="color: ${s.status.includes('BREACH') ? 'var(--c-red)' : 'var(--text-muted)'}">${s.status}</span>
            </div>
        `;
        listContainer.appendChild(card);
    });
}

// 3. Sensor & God's Eye Controls
function setSensorMode(mode) {
    currentSensorMode = mode;
    fetch('/api/control/set_sensor_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        ['normal', 'nvg', 'ironbow', 'whot'].forEach(m => {
            const btn = document.getElementById(`btn-mode-${m}`);
            if (btn) btn.classList.remove('active');
        });
        const key = mode.toLowerCase().replace('flir_', '').replace('_p43', '');
        const activeBtn = document.getElementById(`btn-mode-${key}`) || document.getElementById(`btn-mode-normal`);
        if (activeBtn) activeBtn.classList.add('active');
    });
}

function toggleScopeMask() {
    fetch('/api/control/toggle_scope', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            const btn = document.getElementById('btn-mode-scope');
            if (btn) {
                if (data.scope_mask) btn.classList.add('active');
                else btn.classList.remove('active');
            }
        });
}

function resetStreamSensors() {
    fetch('/api/control/reset_sensors', { method: 'POST' })
        .then(res => res.json())
        .then(() => {
            currentSensorMode = "NORMAL";
            syncSensorUI("NORMAL", false, false);
        });
}

function syncSensorUI(sensorMode, scopeMaskOn, claheOn) {
    const modes = ['normal', 'nvg', 'ironbow', 'whot'];
    modes.forEach(m => {
        const btn = document.getElementById(`btn-mode-${m}`);
        if (btn) btn.classList.remove('active');
    });
    const key = (sensorMode || 'NORMAL').toLowerCase().replace('flir_', '').replace('_p43', '');
    const activeBtn = document.getElementById(`btn-mode-${key}`) || document.getElementById(`btn-mode-normal`);
    if (activeBtn) activeBtn.classList.add('active');

    const scopeBtn = document.getElementById('btn-mode-scope');
    if (scopeBtn) {
        if (scopeMaskOn) scopeBtn.classList.add('active');
        else scopeBtn.classList.remove('active');
    }

    const claheBtn = document.getElementById('btn-clahe');
    if (claheBtn) {
        claheBtn.innerText = claheOn ? '[C] CLAHE ON' : '[C] CLAHE BOOST';
    }
}

function toggleGodsEye() {
    fetch('/api/control/toggle_godseye', { method: 'POST' })
        .then(res => res.json())
        .then(data => syncGodsEyeUI(data.gods_eye_mode));
}

function syncGodsEyeUI(isGodsEye) {
    const btn = document.getElementById('btn-godseye');
    if (btn) {
        if (isGodsEye) {
            btn.classList.add('active');
            btn.innerText = "[G] GOD'S EYE: ON";
        } else {
            btn.classList.remove('active');
            btn.innerText = "[G] GOD'S EYE: OFF";
        }
    }
}

function toggleTheaterMode() {
    const grid = document.getElementById('main-grid');
    if (grid) {
        grid.classList.toggle('theater-mode');
        const isTheater = grid.classList.contains('theater-mode');
        const btn = document.getElementById('btn-theater');
        if (btn) btn.innerText = isTheater ? '[T] EXIT THEATER' : '[T] THEATER MODE';
        const deckBtn = document.getElementById('btn-theater-deck');
        if (deckBtn) deckBtn.innerText = isTheater ? '[T] NORMAL' : '[T] THEATER';
    }
}

function toggleHudBoxes() {
    fetch('/api/control/toggle_hud_overlays', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            const btn = document.getElementById('btn-hud-toggle');
            if (btn) btn.innerText = data.show_aux_hud ? '[H] HUD BOXES: ON' : '[H] HUD BOXES: OFF';
            const headBtn = document.getElementById('btn-toggle-hud');
            if (headBtn) headBtn.innerText = data.show_aux_hud ? '[H] HUD: ON' : '[H] HUD: OFF';
        });
}

function toggleZone() {
    fetch('/api/control/toggle_zone', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            const btnZone = document.getElementById('btn-zone-toggle');
            if (btnZone) btnZone.innerText = data.zone_visible ? '[Z] ZONE: ON' : '[Z] ZONE: OFF';
            console.log('[C2] Zone overlay visibility:', data.zone_visible);
        });
}

function toggleAutoHandoff() {
    fetch('/api/control/toggle_auto_handoff', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            const btnHandoff = document.getElementById('btn-handoff-toggle');
            if (btnHandoff) {
                btnHandoff.innerText = data.auto_handoff ? '[A] HANDOFF: ON' : '[A] HANDOFF: OFF';
                if (data.auto_handoff) btnHandoff.classList.add('active');
                else btnHandoff.classList.remove('active');
            }
            console.log('[C2] Auto-handoff set to:', data.auto_handoff);
        });
}

// 4. Camera & CCTV Stream Switching
function openCctvModal() { document.getElementById('modal-cctv').style.display = 'flex'; }
function closeCctvModal() { document.getElementById('modal-cctv').style.display = 'none'; }
function setCctvInput(val) { document.getElementById('input-cctv-url').value = val; }
function connectWebcam(idx = 0) { switchCustomSource(idx.toString()); }

function submitCctvSource() {
    const src = document.getElementById('input-cctv-url').value.trim();
    if (!src) return;
    switchCustomSource(src);
    closeCctvModal();
}

function switchCustomSource(src) {
    fetch('/api/control/switch_source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: src })
    })
    .then(res => res.json())
    .then(data => {
        console.log('[C2] Video source switched to:', data.source);
    });
}

function highlightSectorButton(sectorId) {
    for (let i = 1; i <= 5; i++) {
        const btn = document.getElementById(`btn-sector-${i}`);
        if (btn) {
            if (i === sectorId) btn.classList.add('highlight-btn');
            else btn.classList.remove('highlight-btn');
        }
    }
}

function switchSector(sectorId) {
    if (activeSectorId === sectorId) return;

    activeSectorId = sectorId;
    highlightSectorButton(sectorId);

    // Immediately hide incursion alert banner to prevent ghost alerts across sectors
    const bannerEl = document.getElementById('breach-banner');
    if (bannerEl) bannerEl.style.display = 'none';

    fetch('/api/control/switch_sector', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sector: sectorId })
    })
    .then(res => res.json())
    .then(data => {
        refreshSectors();
        fetch('/api/sectors')
            .then(res => res.json())
            .then(sectors => {
                const target = sectors.find(s => s.id === sectorId);
                if (target && map) {
                    map.flyTo([target.lat, target.lng], 7, { duration: 1.2 });
                }
            });
    });
}

function refreshSectors() {
    fetch('/api/sectors')
        .then(res => res.json())
        .then(sectors => renderSectors(sectors));
}

// 5. Face Recognition Enrollment (PySource Integration)
function openEnrollModal() { document.getElementById('modal-enroll').style.display = 'flex'; }
function closeEnrollModal() { 
    document.getElementById('modal-enroll').style.display = 'none'; 
    document.getElementById('enroll-status').innerText = '';
}

function enrollCurrentFrame() {
    const name = document.getElementById('input-enroll-name').value.trim();
    if (!name) {
        alert('Please enter a name for the person.');
        return;
    }
    const statusEl = document.getElementById('enroll-status');
    statusEl.innerText = 'Analyzing camera frame for face...';
    
    fetch('/api/faces/enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            statusEl.innerText = `Enrolled '${data.name}' into God's Eye Grid!`;
            fetchEnrolledFaces();
        } else {
            statusEl.innerText = `Enrollment failed: ${data.message}`;
        }
    })
    .catch(err => {
        statusEl.innerText = `Network Error: ${err}`;
    });
}

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const name = document.getElementById('input-enroll-name').value.trim() || file.name.split('.')[0];
    const reader = new FileReader();
    reader.onload = function(evt) {
        const b64 = evt.target.result;
        const statusEl = document.getElementById('enroll-status');
        statusEl.innerText = `Uploading and enrolling '${name}'...`;
        
        fetch('/api/faces/enroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, image_b64: b64 })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                statusEl.innerText = `Successfully enrolled '${data.name}'!`;
                fetchEnrolledFaces();
            } else {
                statusEl.innerText = `Error: ${data.message}`;
            }
        });
    };
    reader.readAsDataURL(file);
}

function fetchEnrolledFaces() {
    fetch('/api/faces/list')
        .then(res => res.json())
        .then(data => {
            const pillsContainer = document.getElementById('enrolled-pills');
            if (pillsContainer) {
                pillsContainer.innerHTML = '';
                (data.identities || []).forEach(name => {
                    const pill = document.createElement('span');
                    pill.className = 'face-pill';
                    pill.innerHTML = `&#128100; ${name}`;
                    pillsContainer.appendChild(pill);
                });
            }
            const enrolledCount = document.getElementById('telem-enrolled');
            if (enrolledCount) enrolledCount.innerText = data.count || 0;
        });
}

// 6. Tactical Action Controls & Shortcuts
function initControls() {
    const btnClahe = document.getElementById('btn-clahe');
    if (btnClahe) {
        btnClahe.onclick = () => {
            fetch('/api/control/toggle_clahe', { method: 'POST' });
        };
    }

    const btnMute = document.getElementById('btn-mute');
    if (btnMute) {
        btnMute.onclick = () => {
            fetch('/api/control/toggle_mute', { method: 'POST' })
                .then(res => res.json())
                .then(d => {
                    btnMute.innerText = d.muted ? '[M] UNMUTE' : '[M] MUTE';
                });
        };
    }

    const btnEvidence = document.getElementById('btn-evidence');
    if (btnEvidence) {
        btnEvidence.onclick = () => {
            fetch('/api/control/capture_evidence', { method: 'POST' })
                .then(res => res.json())
                .then(() => fetchEvidence());
        };
    }

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') return; // Do not trigger when typing in input
        if (e.key === '1') switchSector(1);
        if (e.key === '2') switchSector(2);
        if (e.key === '3') switchSector(3);
        if (e.key === '4') switchSector(4);
        if (e.key === '5') switchSector(5);
        if (e.key === '0') connectWebcam(0);
        if (e.key.toLowerCase() === 't') toggleTheaterMode();
        if (e.key.toLowerCase() === 'h') toggleHudBoxes();
        if (e.key.toLowerCase() === 'g') toggleGodsEye();
        if (e.key.toLowerCase() === 'z') toggleZone();
        if (e.key.toLowerCase() === 'a') toggleAutoHandoff();
        if (e.key.toLowerCase() === 'c' && btnClahe) btnClahe.click();
        if (e.key.toLowerCase() === 's' && btnEvidence) btnEvidence.click();
        if (e.key.toLowerCase() === 'm' && btnMute) btnMute.click();
        if (e.key.toLowerCase() === 'k') toggleScopeMask();
        if (e.key.toLowerCase() === 'r') resetStreamSensors();
        if (e.key.toLowerCase() === 'p') openWatchlistModal();
        if (e.key.toLowerCase() === 'x') toggleMultiview();
        if (e.key.toLowerCase() === 'u') toggleAutoTrack();
        if (e.key === 'ArrowLeft') { e.preventDefault(); jogTurret(-5, 0); }
        if (e.key === 'ArrowRight') { e.preventDefault(); jogTurret(5, 0); }
        if (e.key === 'ArrowUp') { e.preventDefault(); jogTurret(0, 5); }
        if (e.key === 'ArrowDown') { e.preventDefault(); jogTurret(0, -5); }
    });
}

// 7. Real-Time Telemetry & STSI Polling
function startPolling() {
    setInterval(() => {
        fetch('/api/telemetry')
            .then(res => res.json())
            .then(data => updateTelemetry(data))
            .catch(() => {});
    }, 350);

    setInterval(fetchEvidence, 2500);
    setInterval(fetchAnprLogs, 1500);
    setInterval(fetchSatellites, 2000);
    setInterval(fetchReidData, 2000);
    setInterval(refreshSectors, 4000);
    fetchWatchlist();
    fetchSatellites();
    fetchReidData();
}

function updateTelemetry(t) {
    document.getElementById('telem-fps').innerText = t.fps.toFixed(1);
    document.getElementById('telem-lat').innerText = `${Math.round(t.latency_ms)}ms`;
    document.getElementById('telem-faces').innerText = t.faces_detected !== undefined ? t.faces_detected : 0;
    if (t.enrolled_faces_count !== undefined) {
        document.getElementById('telem-enrolled').innerText = t.enrolled_faces_count;
    }
    const elPlates = document.getElementById('telem-plates');
    if (elPlates && t.anpr_scans_count !== undefined) elPlates.innerText = t.anpr_scans_count;
    const elWatchlist = document.getElementById('telem-watchlist');
    if (elWatchlist && t.anpr_watchlist_count !== undefined) elWatchlist.innerText = t.anpr_watchlist_count;

    const elReidChip = document.getElementById('telem-reid-chip');
    if (elReidChip && t.reid_entities_count !== undefined) elReidChip.innerText = `${t.reid_entities_count} G-IDS`;

    syncSensorUI(t.sensor_mode, t.scope_mask, t.clahe_enabled);
    if (t.gods_eye_mode !== undefined) syncGodsEyeUI(t.gods_eye_mode);
    const btnZone = document.getElementById('btn-zone-toggle');
    if (btnZone && t.zone_visible !== undefined) {
        btnZone.innerText = t.zone_visible ? '[Z] ZONE: ON' : '[Z] ZONE: OFF';
    }
    const btnHandoff = document.getElementById('btn-handoff-toggle');
    if (btnHandoff && t.auto_handoff !== undefined) {
        btnHandoff.innerText = t.auto_handoff ? '[A] HANDOFF: ON' : '[A] HANDOFF: OFF';
        if (t.auto_handoff) btnHandoff.classList.add('active');
        else btnHandoff.classList.remove('active');
    }
    if (t.multiview_mode !== undefined) syncMultiviewUI(t.multiview_mode);
    if (t.hardware) updateHardwareUI(t.hardware);

    const elGlobalChip = document.getElementById('telem-globalcams-chip');
    if (elGlobalChip && t.global_cams_count !== undefined) {
        elGlobalChip.innerText = `${t.global_cams_count} LIVE`;
    }

    const elFarrChip = document.getElementById('telem-farr-chip');
    if (elFarrChip && t.farr) {
        elFarrChip.innerText = `${t.farr.farr_percentage}%`;
    }

    const elAlertChip = document.getElementById('telem-alert-chip');
    if (elAlertChip && t.alerts_config) {
        elAlertChip.innerText = t.alerts_config.telegram_enabled ? 'TG: ON' : 'STANDBY';
        elAlertChip.style.color = t.alerts_config.telegram_enabled ? 'var(--c-green)' : 'var(--c-cyan)';
    }

    if (t.farr && document.getElementById('modal-farr') && document.getElementById('modal-farr').style.display !== 'none') {
        updateFarrUI(t.farr);
    }

    const elQrtChip = document.getElementById('telem-qrt-chip');
    const chipQrtBox = document.getElementById('qrt-telem-chip');
    if (elQrtChip) {
        if (t.interdiction) {
            elQrtChip.innerText = `INTERCEPT (${Math.round(t.interdiction.countdown_seconds)}s)`;
            elQrtChip.style.color = 'var(--c-red)';
            if (chipQrtBox) chipQrtBox.style.borderColor = 'var(--c-red)';
            updateInterdictionQuickBanner(t.interdiction);
        } else {
            elQrtChip.innerText = 'READY';
            elQrtChip.style.color = 'var(--c-green)';
            if (chipQrtBox) chipQrtBox.style.borderColor = 'rgba(0, 255, 119, 0.3)';
        }
    }

    const statusEl = document.getElementById('telem-status');
    const chipEl = document.getElementById('status-chip');
    const bannerEl = document.getElementById('breach-banner');

    if (t.is_breached) {
        statusEl.innerText = `CRITICAL INCURSION (${t.breach_count})`;
        statusEl.style.color = 'var(--c-red)';
        chipEl.style.borderColor = 'var(--c-red)';
        bannerEl.style.display = 'block';

        if (!t.audio_muted && t.breach_count > lastBreachCount) {
            playTacticalChirp();
        }
    } else {
        statusEl.innerText = 'SENTRY SECURE';
        statusEl.style.color = 'var(--c-green)';
        chipEl.style.borderColor = 'rgba(0, 255, 119, 0.3)';
        bannerEl.style.display = 'none';
    }

    // Autonomous Handoff Alert Banner
    if (t.latest_handoff && t.latest_handoff.timestamp) {
        if (!window._lastHandoffTs || window._lastHandoffTs !== t.latest_handoff.timestamp) {
            window._lastHandoffTs = t.latest_handoff.timestamp;
            const handoffEl = document.getElementById('handoff-banner');
            if (handoffEl) {
                handoffEl.innerText = `*** AUTONOMOUS HANDOFF: SECTOR-0${t.latest_handoff.from_sector} -> SECTOR-0${t.latest_handoff.to_sector} (${t.latest_handoff.reason}) ***`;
                handoffEl.style.display = 'block';
                setTimeout(() => { handoffEl.style.display = 'none'; }, 4500);
            }
            if (t.sector_id && t.sector_id !== activeSectorId) {
                activeSectorId = t.sector_id;
                highlightSectorButton(t.sector_id);
                refreshSectors();
            }
        }
    }

    if (t.sector_id && t.sector_id !== activeSectorId) {
        activeSectorId = t.sector_id;
        highlightSectorButton(t.sector_id);
        refreshSectors();
    }

    lastBreachCount = t.breach_count;
    renderSTSI(t.stsi);
}

function renderSTSI(activeStsi) {
    const container = document.getElementById('stsi-bars');
    if (!container) return;
    container.innerHTML = `
        <div class="stsi-item">
            <div class="stsi-header">
                <span style="color: var(--text-main)">ACTIVE SECTOR THREAT INDEX</span>
                <strong style="color: ${activeStsi > 75 ? 'var(--c-red)' : activeStsi > 50 ? 'var(--c-amber)' : 'var(--c-green)'}">
                    ${activeStsi} / 100
                </strong>
            </div>
            <div class="stsi-track">
                <div class="stsi-fill" style="width: ${activeStsi}%; background: ${activeStsi > 75 ? 'var(--c-red)' : activeStsi > 50 ? 'var(--c-amber)' : 'var(--c-cyan)'}"></div>
            </div>
        </div>
    `;
}

// 8. Cryptographic Evidence Vault
let _lastEvidenceHash = '';
function fetchEvidence() {
    fetch('/api/evidence')
        .then(res => res.json())
        .then(records => {
            const feed = document.getElementById('evidence-feed');
            if (!feed || !records) return;
            const newHash = records.map(r => r.incident_uuid).join(',');
            if (newHash === _lastEvidenceHash) return; // Skip if no new records
            _lastEvidenceHash = newHash;
            feed.innerHTML = '';

            records.forEach(r => {
                const card = document.createElement('div');
                card.className = 'evidence-card';
                card.innerHTML = `
                    <img class="evidence-thumb" src="/evidence/${r.forensic_integrity.image_file}" alt="Capture" />
                    <div class="evidence-details">
                        <span class="evidence-id">${r.incident_uuid}</span>
                        <div style="color: var(--text-main); font-size: 9px;">
                            ${r.target_telemetry.class} | MGRS: ${r.mgrs_grid || '43R FN'}
                        </div>
                        <div class="evidence-hash">SHA: ${r.forensic_integrity.sha256_hash.substring(0, 16)}...</div>
                        <a class="btn-cert" href="/api/evidence/certificate/${r.incident_uuid}" target="_blank">
                            [SEC 65B CERTIFICATE]
                        </a>
                    </div>
                `;
                feed.appendChild(card);
            });
        });
}

function playTacticalChirp() {
    try {
        if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, audioContext.currentTime);
        osc.frequency.exponentialRampToValueAtTime(440, audioContext.currentTime + 0.25);
        gain.gain.setValueAtTime(0.2, audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.25);
        osc.connect(gain);
        gain.connect(audioContext.destination);
        osc.start();
        osc.stop(audioContext.currentTime + 0.26);
    } catch(e) {}
}

// 9. ANPR (Automatic Number Plate Recognition) & Suspect Watchlist
function openWatchlistModal() {
    document.getElementById('modal-watchlist').style.display = 'flex';
    fetchWatchlist();
}

function closeWatchlistModal() {
    document.getElementById('modal-watchlist').style.display = 'none';
    const st = document.getElementById('watchlist-add-status');
    if (st) st.innerText = '';
}

function fetchWatchlist() {
    fetch('/api/anpr/watchlist')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('watchlist-rows');
            if (!tbody) return;
            tbody.innerHTML = '';
            const wl = data.watchlist || {};
            const countEl = document.getElementById('telem-watchlist');
            if (countEl) countEl.innerText = Object.keys(wl).length;

            Object.values(wl).forEach(item => {
                const tr = document.createElement('tr');
                const isAlert = item.category && (item.category.includes('STOLEN') || item.category.includes('TRAFFICKING') || item.category.includes('UNAUTHORIZED'));
                const badgeColor = isAlert ? 'var(--c-red)' : (item.category && item.category.includes('AUTHORIZED') ? 'var(--c-green)' : 'var(--c-cyan)');
                tr.innerHTML = `
                    <td style="font-weight: 800; color: #fff; letter-spacing: 0.5px;">${item.plate}</td>
                    <td style="color: ${badgeColor}; font-weight: 700;">${item.category}</td>
                    <td style="color: var(--text-main);">${item.vehicle_model || 'UNKNOWN'}</td>
                    <td style="color: var(--text-muted);">${item.risk}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(() => {});
}

function submitWatchlistEntry() {
    const plate = document.getElementById('input-plate-num').value.trim();
    if (!plate) {
        alert('Please enter a license plate number (e.g. JK 02 B 1892)');
        return;
    }
    const vmodel = document.getElementById('input-plate-model').value.trim() || 'SUSPECT VEHICLE';
    const cat = document.getElementById('input-plate-cat').value;
    const risk = document.getElementById('input-plate-risk').value;
    const msg = document.getElementById('input-plate-msg').value.trim() || `Watchlist interdiction for ${plate}`;

    const stEl = document.getElementById('watchlist-add-status');
    stEl.innerText = 'Enrolling plate into border interdiction database...';

    fetch('/api/anpr/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            plate: plate,
            category: cat,
            risk: risk,
            vehicle_model: vmodel,
            alert_msg: msg
        })
    })
    .then(res => res.json())
    .then(d => {
        if (d.status === 'success') {
            stEl.innerText = `Enrolled '${plate}' into active watchlist!`;
            document.getElementById('input-plate-num').value = '';
            document.getElementById('input-plate-model').value = '';
            document.getElementById('input-plate-msg').value = '';
            fetchWatchlist();
        } else {
            stEl.innerText = 'Enrollment failed.';
        }
    })
    .catch(err => {
        stEl.innerText = `Network error: ${err}`;
    });
}

let _lastAnprHash = '';
function fetchAnprLogs() {
    fetch('/api/anpr/logs')
        .then(res => res.json())
        .then(data => {
            const feed = document.getElementById('anpr-feed');
            if (!feed) return;
            const logs = data.logs || [];
            if (logs.length === 0) {
                if (_lastAnprHash !== 'empty') {
                    _lastAnprHash = 'empty';
                    feed.innerHTML = '<div style="color: var(--text-dim); font-size: 10px; text-align: center; padding: 10px;">Awaiting vehicle scans...</div>';
                }
                return;
            }

            const currentHash = logs.slice(0, 15).map(l => `${l.plate}-${l.time_str}`).join('|');
            if (currentHash === _lastAnprHash) return; // Skip DOM rebuild if no new scans
            _lastAnprHash = currentHash;

            feed.innerHTML = '';
            logs.slice(0, 15).forEach(scan => {
                const card = document.createElement('div');
                const isThreat = scan.is_alert;
                const isAuth = scan.category && scan.category.includes('AUTHORIZED');
                card.className = `anpr-card ${isThreat ? 'threat' : (isAuth ? 'authorized' : '')}`;

                const pillColor = isThreat ? 'var(--c-red)' : (isAuth ? 'var(--c-green)' : 'var(--c-cyan)');

                card.innerHTML = `
                    <div class="anpr-card-top">
                        <span class="anpr-plate-badge">${scan.plate}</span>
                        <span class="anpr-status-pill" style="color: ${pillColor};">
                            ${isThreat ? '!! WATCHLIST ALERT !!' : (isAuth ? 'AUTHORIZED PATROL' : 'CLEAR')}
                        </span>
                    </div>
                    <div class="anpr-card-sub">
                        <span>${scan.vehicle_type || 'VEHICLE'} // ${scan.vehicle_model || scan.category}</span>
                        <span>${scan.time_str || ''} (${Math.round(scan.confidence || 0)}%)</span>
                    </div>
                `;
                feed.appendChild(card);
            });
        })
        .catch(() => {});
}

// ===================================================================
// 8. 3D DIGITAL TWIN & REAL-TIME ORBITAL SATELLITE TRACKING (SGP4)
// ===================================================================
let currentMapView = '2D';
let cesiumFullViewer = null;
let cesiumMiniViewer = null;
let satellitesData = [];
let satellitePassesData = [];

let satelliteMarkers2D = {};
let satelliteFootprints2D = {};
let satelliteTracks2D = {};
let satelliteEntitiesFull = {};
let satelliteTracksFull = {};
let satelliteEntitiesMini = {};

function fetchSatellites() {
    Promise.all([
        fetch('/api/satellites').then(r => r.json()),
        fetch('/api/satellites/passes').then(r => r.json())
    ])
    .then(([sats, passes]) => {
        satellitesData = sats || [];
        satellitePassesData = passes || [];
        updateSatellitesUI();
        updateSatellites2DMap();
        if (cesiumFullViewer) updateSatellitesCesium(cesiumFullViewer, satelliteEntitiesFull, satelliteTracksFull);
        if (cesiumMiniViewer) updateSatellitesCesium(cesiumMiniViewer, satelliteEntitiesMini, null);
    })
    .catch(err => console.warn('[SAT-C2] Error fetching satellite telemetry:', err));
}

function updateSatellitesUI() {
    // 1. Update Header Chip
    const satChip = document.getElementById('telem-satellite-chip');
    if (satChip && satellitesData.length > 0) {
        const primary = satellitesData.find(s => s.id === 'CARTOSAT-3') || satellitesData[0];
        satChip.innerText = `${primary.name.replace('ISRO ', '')} (${Math.round(primary.alt_km)}km)`;
    }

    // 2. Update Right Panel Drawer
    const feed = document.getElementById('satellites-feed');
    if (feed && satellitesData.length > 0) {
        feed.innerHTML = '';
        satellitesData.forEach(sat => {
            const item = document.createElement('div');
            item.className = 'sat-feed-item';
            item.onclick = () => {
                openFullGlobeModal();
                setTimeout(() => flyToSatellite(sat.id), 400);
            };

            // Find overflight info
            const pInfo = satellitePassesData.find(p => p.satellite_id === sat.id && p.sector_id === activeSectorId);
            const isOverflight = pInfo && pInfo.in_recon_swath;
            const statusCol = isOverflight ? 'var(--c-red)' : (sat.country === 'INDIA' ? 'var(--c-cyan)' : 'var(--text-muted)');
            const statusLabel = isOverflight ? '!! OVERFLIGHT ACTIVE !!' : (pInfo ? `${Math.round(pInfo.distance_km)}km to Sector` : 'ORBITING');

            item.innerHTML = `
                <div>
                    <div class="sat-feed-name" style="color: ${sat.color}">🛰️ ${sat.name}</div>
                    <div class="sat-feed-meta">${sat.payload.substring(0, 32)}...</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 9px; font-weight: 800; color: ${statusCol};">${statusLabel}</div>
                    <div style="font-size: 8px; color: var(--text-dim);">${sat.alt_km}km | ${sat.velocity_km_s}km/s</div>
                </div>
            `;
            feed.appendChild(item);
        });
    }

    // 3. Update Modal List
    const modalList = document.getElementById('sat-modal-list');
    if (modalList && satellitesData.length > 0) {
        modalList.innerHTML = '';
        satellitesData.forEach(sat => {
            const card = document.createElement('div');
            card.className = 'sat-card-modal';
            
            const pInfo = satellitePassesData.find(p => p.satellite_id === sat.id && p.sector_id === activeSectorId);
            const isLock = pInfo && pInfo.in_recon_swath;
            if (isLock) card.classList.add('active-lock');

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 800; font-size: 12px; color: ${sat.color}">🛰️ ${sat.name} (${sat.agency})</span>
                    <span style="font-size: 9px; font-weight: 800; color: ${isLock ? 'var(--c-red)' : 'var(--c-green)'};">
                        ${isLock ? '!! SECTOR RECON LOCK !!' : 'ORBITAL EPHEMERIS VERIFIED'}
                    </span>
                </div>
                <div style="font-size: 11px; color: var(--text-main); margin: 2px 0;">${sat.payload}</div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; font-size: 10px; color: var(--text-muted); background: rgba(0,0,0,0.3); padding: 6px; border-radius: 3px;">
                    <div>ALTITUDE: <strong style="color: #fff;">${sat.alt_km} km</strong></div>
                    <div>VELOCITY: <strong style="color: var(--c-green);">${sat.velocity_km_s} km/s</strong></div>
                    <div>SUB-POINT: <strong style="color: var(--c-cyan);">${sat.lat}°, ${sat.lng}°</strong></div>
                    <div>SWATH RADIUS: <strong style="color: var(--c-yellow);">${sat.footprint_radius_km} km</strong></div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span style="font-size: 9px; color: var(--text-dim);">NORAD ID: ${sat.norad_id} | SGP4 UTC: ${sat.timestamp_utc.substring(11, 19)}</span>
                    <button class="btn-mini" onclick="closeSatelliteModal(); openFullGlobeModal(); setTimeout(() => flyToSatellite('${sat.id}'), 400);">[3D TRACK ORBIT]</button>
                </div>
            `;
            modalList.appendChild(card);
        });
    }
}

function updateSatellites2DMap() {
    if (!map || currentMapView !== '2D') return;

    satellitesData.forEach(sat => {
        const id = sat.id;
        const pos = [sat.lat, sat.lng];

        // 1. Marker with SVG satellite icon
        if (!satelliteMarkers2D[id]) {
            const icon = L.divIcon({
                className: 'custom-sat-icon',
                html: `
                    <div style="display: flex; flex-direction: column; align-items: center; pointer-events: auto; cursor: pointer;">
                        <div style="font-size: 16px; filter: drop-shadow(0 0 5px ${sat.color});">🛰️</div>
                        <div style="font-size: 8px; font-weight: 800; background: rgba(0,0,0,0.8); padding: 1px 4px; border: 1px solid ${sat.color}; border-radius: 2px; color: ${sat.color}; white-space: nowrap;">
                            ${sat.id}
                        </div>
                    </div>
                `,
                iconSize: [60, 30],
                iconAnchor: [30, 15]
            });
            const m = L.marker(pos, { icon: icon, zIndexOffset: 1000 }).addTo(map);
            m.on('click', () => {
                openFullGlobeModal();
                setTimeout(() => flyToSatellite(sat.id), 400);
            });
            satelliteMarkers2D[id] = m;
        } else {
            satelliteMarkers2D[id].setLatLng(pos);
        }

        // 2. Sensor footprint ground circle
        if (!satelliteFootprints2D[id]) {
            const circle = L.circle(pos, {
                radius: sat.footprint_radius_km * 1000,
                color: sat.color,
                weight: 1,
                dashArray: '2, 4',
                fillColor: sat.color,
                fillOpacity: 0.08
            }).addTo(map);
            satelliteFootprints2D[id] = circle;
        } else {
            satelliteFootprints2D[id].setLatLng(pos);
            satelliteFootprints2D[id].setRadius(sat.footprint_radius_km * 1000);
        }

        // 3. Ground track path
        if (sat.ground_track && sat.ground_track.length > 0) {
            const latlngs = sat.ground_track.map(pt => [pt.lat, pt.lng]);
            if (!satelliteTracks2D[id]) {
                const track = L.polyline(latlngs, {
                    color: sat.color,
                    weight: 1,
                    opacity: 0.35,
                    dashArray: '4, 6'
                }).addTo(map);
                satelliteTracks2D[id] = track;
            } else {
                satelliteTracks2D[id].setLatLngs(latlngs);
            }
        }
    });
}

function switchMapView(view) {
    currentMapView = view;
    const btn2d = document.getElementById('btn-map-2d');
    const btn3d = document.getElementById('btn-map-3d');
    const map2d = document.getElementById('tactical-map');
    const globeMini = document.getElementById('cesium-globe-mini');

    if (view === '2D') {
        if (btn2d) btn2d.classList.add('active');
        if (btn3d) btn3d.classList.remove('active');
        if (map2d) map2d.style.display = 'block';
        if (globeMini) globeMini.style.display = 'none';
        if (map) map.invalidateSize();
    } else {
        if (btn2d) btn2d.classList.remove('active');
        if (btn3d) btn3d.classList.add('active');
        if (map2d) map2d.style.display = 'none';
        if (globeMini) globeMini.style.display = 'block';
        initCesiumMini();
    }
}

function setupGlobeLayers(viewer, mode = 'SATELLITE') {
    if (!viewer || !viewer.imageryLayers) return;
    viewer.imageryLayers.removeAll();

    if (mode === 'DARK') {
        const darkProvider = new Cesium.UrlTemplateImageryProvider({
            url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            subdomains: ['a', 'b', 'c', 'd']
        });
        viewer.imageryLayers.addImageryProvider(darkProvider);
    } else if (mode === 'OSM') {
        const osmProvider = new Cesium.UrlTemplateImageryProvider({
            url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
        });
        viewer.imageryLayers.addImageryProvider(osmProvider);
    } else {
        // 1. High-Resolution True Satellite Imagery
        const satProvider = new Cesium.UrlTemplateImageryProvider({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            maximumLevel: 19
        });
        viewer.imageryLayers.addImageryProvider(satProvider);

        // 2. High-Visibility Illuminated Road Networks, Highways & Transportation
        const roadProvider = new Cesium.UrlTemplateImageryProvider({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
            maximumLevel: 19
        });
        const roadLayer = viewer.imageryLayers.addImageryProvider(roadProvider);
        if (roadLayer) roadLayer.alpha = 0.90;

        // 3. World Boundaries, National Frontiers, and City Infrastructure
        const borderProvider = new Cesium.UrlTemplateImageryProvider({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            maximumLevel: 19
        });
        const borderLayer = viewer.imageryLayers.addImageryProvider(borderProvider);
        if (borderLayer) borderLayer.alpha = 0.95;
    }
}

let currentGlobeBasemap = 'SATELLITE';

function setGlobeBasemap(mode) {
    currentGlobeBasemap = mode;
    [cesiumFullViewer, cesiumMiniViewer].forEach(v => {
        if (v) setupGlobeLayers(v, mode);
    });
}

function initCesiumMini() {
    if (cesiumMiniViewer) {
        cesiumMiniViewer.resize();
        return;
    }
    if (typeof Cesium === 'undefined') {
        console.warn('[CESIUM] Cesium library not ready.');
        return;
    }

    try {
        if (Cesium.Ion) Cesium.Ion.defaultAccessToken = null;

        cesiumMiniViewer = new Cesium.Viewer('cesium-globe-mini', {
            animation: false,
            baseLayerPicker: false,
            baseLayer: false,
            terrainProvider: new Cesium.EllipsoidTerrainProvider(),
            fullscreenButton: false,
            geocoder: false,
            homeButton: false,
            infoBox: false,
            sceneModePicker: false,
            selectionIndicator: false,
            timeline: false,
            navigationHelpButton: false,
            navigationInstructionsInitiallyVisible: false
        });

        // Silence any Cesium modal error panels
        if (cesiumMiniViewer.cesiumWidget) {
            cesiumMiniViewer.cesiumWidget.showErrorPanel = function(title, message) {
                console.warn('[CESIUM MINI WARNING SUPPRESSED]', title, message);
            };
        }

        cesiumMiniViewer.scene.globe.enableLighting = false;
        cesiumMiniViewer.scene.backgroundColor = Cesium.Color.BLACK;

        setupGlobeLayers(cesiumMiniViewer, 'SATELLITE');

        // Fly to India Frontier
        cesiumMiniViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(74.572, 31.604, 3800000),
            duration: 1.5
        });

        // Add Sectors & Beacons
        addSectorEntitiesToCesium(cesiumMiniViewer);
        plotGlobalCamerasOnCesium(cesiumMiniViewer);
    } catch (e) {
        console.error('[CESIUM] Mini viewer init failed:', e);
    }
}

function openFullGlobeModal() {
    const modal = document.getElementById('modal-globe');
    if (modal) modal.style.display = 'flex';
    initCesiumFull();
}

function closeFullGlobeModal() {
    const modal = document.getElementById('modal-globe');
    if (modal) modal.style.display = 'none';
    closeGlobeCctvIntercept();
}

function initCesiumFull() {
    if (cesiumFullViewer) {
        cesiumFullViewer.resize();
        return;
    }
    if (typeof Cesium === 'undefined') {
        console.warn('[CESIUM] Cesium library not ready.');
        return;
    }

    try {
        if (Cesium.Ion) Cesium.Ion.defaultAccessToken = null;

        cesiumFullViewer = new Cesium.Viewer('cesium-globe-full', {
            animation: false,
            baseLayerPicker: false,
            baseLayer: false,
            terrainProvider: new Cesium.EllipsoidTerrainProvider(),
            fullscreenButton: false,
            geocoder: false,
            homeButton: false,
            infoBox: false,
            sceneModePicker: false,
            selectionIndicator: false,
            timeline: false,
            navigationHelpButton: false,
            navigationInstructionsInitiallyVisible: false
        });

        // Silence any Cesium modal error panels
        if (cesiumFullViewer.cesiumWidget) {
            cesiumFullViewer.cesiumWidget.showErrorPanel = function(title, message) {
                console.warn('[CESIUM FULL WARNING SUPPRESSED]', title, message);
            };
        }

        cesiumFullViewer.scene.globe.enableLighting = true;
        cesiumFullViewer.scene.backgroundColor = Cesium.Color.BLACK;

        setupGlobeLayers(cesiumFullViewer, 'SATELLITE');

        // Default perspective over Northern Defense Frontier
        cesiumFullViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(74.572, 31.604, 5500000),
            duration: 2.0
        });

        addSectorEntitiesToCesium(cesiumFullViewer);
        plotGlobalCamerasOnCesium(cesiumFullViewer);
        updateSatellitesCesium(cesiumFullViewer, satelliteEntitiesFull, satelliteTracksFull);

        // Click handler on satellites and CCTV camera beacon entities
        const handler = new Cesium.ScreenSpaceEventHandler(cesiumFullViewer.scene.canvas);
        handler.setInputAction((click) => {
            const picked = cesiumFullViewer.scene.pick(click.position);
            if (Cesium.defined(picked) && picked.id && picked.id.properties) {
                const satId = picked.id.properties.satelliteId ? picked.id.properties.satelliteId.getValue() : null;
                if (satId) {
                    flyToSatellite(satId);
                    return;
                }
                const camData = picked.id.properties.cameraData ? picked.id.properties.cameraData.getValue() : null;
                if (camData) {
                    cesiumFullViewer.camera.flyTo({
                        destination: Cesium.Cartesian3.fromDegrees(camData.lng, camData.lat, 18000),
                        duration: 1.8
                    });
                    openGlobeCctvIntercept(camData);
                    return;
                }
            }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    } catch (e) {
        console.error('[CESIUM] Full viewer init failed:', e);
    }
}

function addSectorEntitiesToCesium(viewer) {
    const sectors = [
        { id: 1, name: "SECTOR-01 PUNJAB WALL", lat: 31.604, lng: 74.572, color: Cesium.Color.fromCssColorString('#00ff77') },
        { id: 2, name: "SECTOR-02 THAR NIGHT SENTRY", lat: 27.023, lng: 70.912, color: Cesium.Color.fromCssColorString('#ffaa00') },
        { id: 3, name: "SECTOR-03 HIGHWAY ANPR CORRIDOR", lat: 32.610, lng: 74.720, color: Cesium.Color.fromCssColorString('#00f0ff') },
        { id: 4, name: "SECTOR-04 CHECKPOST SENTINEL", lat: 32.726, lng: 74.857, color: Cesium.Color.fromCssColorString('#ff3344') }
    ];

    sectors.forEach(s => {
        // Vertical 120km Skyward Light Beam
        viewer.entities.add({
            name: `BEAM-${s.id}`,
            polyline: {
                positions: [
                    Cesium.Cartesian3.fromDegrees(s.lng, s.lat, 0),
                    Cesium.Cartesian3.fromDegrees(s.lng, s.lat, 120000)
                ],
                width: 2.5,
                material: s.color.withAlpha(0.70)
            }
        });

        // Terrestrial Beacon Point
        viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(s.lng, s.lat, 500),
            point: {
                pixelSize: 10,
                color: s.color,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
                scaleByDistance: new Cesium.NearFarScalar(1.5e2, 2.0, 8.0e6, 0.8),
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            },
            label: {
                text: s.name,
                font: '11px monospace',
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12),
                fillColor: s.color,
                scaleByDistance: new Cesium.NearFarScalar(1.5e2, 1.2, 5.0e6, 0.6),
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            }
        });
    });
}

function updateSatellitesCesium(viewer, entityStore, trackStore) {
    if (!viewer) return;

    satellitesData.forEach(sat => {
        const id = sat.id;
        const color = Cesium.Color.fromCssColorString(sat.color || '#00f0ff');
        const pos = Cesium.Cartesian3.fromDegrees(sat.lng, sat.lat, sat.alt_km * 1000);

        if (!entityStore[id]) {
            const ent = viewer.entities.add({
                name: sat.name,
                properties: { satelliteId: sat.id },
                position: pos,
                point: {
                    pixelSize: 9,
                    color: color,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 1
                },
                label: {
                    text: `🛰️ ${sat.name} [${Math.round(sat.alt_km)}km]`,
                    font: '10px monospace',
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 2,
                    fillColor: color,
                    pixelOffset: new Cesium.Cartesian2(0, -12)
                }
            });
            entityStore[id] = ent;
        } else {
            entityStore[id].position = pos;
        }

        // 3D Orbital Trajectory
        if (trackStore && sat.ground_track && sat.ground_track.length > 0) {
            const positions = sat.ground_track.map(pt => Cesium.Cartesian3.fromDegrees(pt.lng, pt.lat, pt.alt * 1000));
            if (!trackStore[id]) {
                const track = viewer.entities.add({
                    polyline: {
                        positions: positions,
                        width: 1.5,
                        material: color.withAlpha(0.5)
                    }
                });
                trackStore[id] = track;
            } else {
                trackStore[id].polyline.positions = positions;
            }
        }
    });
}

function flyToLocation(lat, lng, name) {
    if (!cesiumFullViewer) return;
    cesiumFullViewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lng, lat, 250000),
        duration: 1.8
    });
    const cardName = document.getElementById('globe-sat-name');
    if (cardName) cardName.innerText = `GROUND SENTRY // ${name}`;
    const cardPayload = document.getElementById('globe-sat-payload');
    if (cardPayload) cardPayload.innerText = `Terrestrial Border Defense Post (Lat: ${lat}°, Lng: ${lng}°)`;
}

function flyToSatellite(satId) {
    const sat = satellitesData.find(s => s.id === satId);
    if (!sat) return;

    if (cesiumFullViewer) {
        cesiumFullViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(sat.lng, sat.lat, (sat.alt_km + 450) * 1000),
            duration: 2.0
        });
    }

    // Update Globe HUD Card
    const nameEl = document.getElementById('globe-sat-name');
    if (nameEl) nameEl.innerText = `${sat.name} // ${sat.sensor_type}`;
    const payloadEl = document.getElementById('globe-sat-payload');
    if (payloadEl) payloadEl.innerText = `${sat.payload} (${sat.agency})`;
    const altEl = document.getElementById('globe-sat-alt');
    if (altEl) altEl.innerText = `${sat.alt_km} km`;
    const velEl = document.getElementById('globe-sat-vel');
    if (velEl) velEl.innerText = `${sat.velocity_km_s} km/s`;
    const subEl = document.getElementById('globe-sat-sub');
    if (subEl) subEl.innerText = `${sat.lat}°, ${sat.lng}°`;
    const fpEl = document.getElementById('globe-sat-fp');
    if (fpEl) fpEl.innerText = `${sat.footprint_radius_km} km`;
}

function openSatelliteModal() {
    const modal = document.getElementById('modal-satellites');
    if (modal) modal.style.display = 'flex';
    fetchSatellites();
}

function closeSatelliteModal() {
    const modal = document.getElementById('modal-satellites');
    if (modal) modal.style.display = 'none';
}

// ===================================================================
// 12. Multi-Camera 2x2 Matrix & Cross-Camera ReID Engine
// ===================================================================
let isMultiviewMode = false;
let reidEntitiesData = [];
let reidTransitsData = [];

function toggleMultiview() {
    fetch('/api/control/toggle_multiview', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            isMultiviewMode = !!data.multiview_mode;
            syncMultiviewUI(isMultiviewMode);
        })
        .catch(err => console.error('Error toggling multiview:', err));
}

function syncMultiviewUI(active) {
    isMultiviewMode = !!active;
    const btns = [
        document.getElementById('btn-toggle-multiview'),
        document.getElementById('btn-deck-multiview'),
        document.getElementById('btn-left-multiview')
    ];
    btns.forEach(btn => {
        if (btn) {
            if (active) {
                btn.classList.add('active-matrix');
                btn.style.color = 'var(--c-cyan)';
            } else {
                btn.classList.remove('active-matrix');
                btn.style.color = '';
            }
        }
    });
}

function fetchReidData() {
    Promise.all([
        fetch('/api/reid/entities').then(r => r.json()),
        fetch('/api/reid/transits').then(r => r.json())
    ])
    .then(([entRes, trnRes]) => {
        reidEntitiesData = entRes.entities || [];
        reidTransitsData = trnRes.transits || [];
        renderReidDrawer();
        renderReidModal();
    })
    .catch(() => {});
}

function renderReidDrawer() {
    const feed = document.getElementById('reid-feed');
    const badge = document.getElementById('reid-status-badge');
    const chip = document.getElementById('telem-reid-chip');

    if (badge) badge.innerText = `${reidEntitiesData.length} ENTITIES`;
    if (chip) chip.innerText = `${reidEntitiesData.length} G-IDS`;
    if (!feed) return;

    if (reidEntitiesData.length === 0) {
        feed.innerHTML = '<div style="color: var(--text-dim); font-size: 10px; text-align: center; padding: 8px;">Awaiting person sightings...</div>';
        return;
    }

    feed.innerHTML = '';
    reidEntitiesData.slice(0, 5).forEach(e => {
        const item = document.createElement('div');
        const transit = e.latest_transit || e.last_transit;
        const inTransit = !!transit;
        const camId = e.current_camera_id || e.last_camera || 1;
        item.className = `reid-feed-item ${inTransit ? 'in-transit' : ''}`;
        item.onclick = openReidModal;

        const faceTag = e.face_name ? `<span class="reid-badge face">${e.face_name}</span>` : '';
        const transitTag = inTransit ? `<span class="reid-badge transit">TRANSIT ${transit.elapsed_sec}s</span>` : '';

        item.innerHTML = `
            <div style="flex: 1;">
                <div class="reid-feed-title">
                    <span>${e.global_id}</span>
                    ${faceTag}
                    ${transitTag}
                </div>
                <div class="reid-feed-meta">Cam #${camId} | Sightings: ${e.sighting_count} | ${Math.round(e.last_seen_sec_ago || 0)}s ago</div>
            </div>
            <div style="display: flex; gap: 4px; align-items: center;">
                <button class="btn-mini highlight-btn" onclick="event.stopPropagation(); lockCameraOnEntity(${camId})" title="Lock Primary Sentry on Cam #${camId}">[LOCK]</button>
                <button class="btn-mini" onclick="event.stopPropagation(); traceRouteOnGlobe('${e.global_id}')" title="Trace 3D route trajectory on Cesium Earth">[TRACE]</button>
                <button class="btn-mini alert-btn" onclick="event.stopPropagation(); dispatchQRTForEntity('${e.global_id}')" title="Dispatch QRT Interdiction vector against target">[QRT]</button>
            </div>
        `;
        feed.appendChild(item);
    });
}

function renderReidModal() {
    const entCont = document.getElementById('reid-modal-entities');
    const trnCont = document.getElementById('reid-modal-transits');

    if (entCont) {
        if (reidEntitiesData.length === 0) {
            entCont.innerHTML = '<div style="color: var(--text-dim); font-size: 10px; text-align: center; padding: 20px;">No global entities currently registered. Point camera at person to initialize 576D appearance features.</div>';
        } else {
            entCont.innerHTML = '';
            reidEntitiesData.forEach(e => {
                const card = document.createElement('div');
                const transit = e.latest_transit || e.last_transit;
                const camId = e.current_camera_id || e.last_camera || 1;
                const secName = e.current_sector_name || e.last_sector_name || `Cam #${camId}`;
                card.className = `reid-card-modal ${transit ? 'in-transit' : ''}`;
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 800; color: var(--c-cyan);">${e.global_id}</span>
                        <span style="font-size: 10px; color: ${e.face_name ? 'var(--c-green)' : 'var(--text-muted)'}; font-weight: 700;">
                            ${e.face_name ? `&#128100; ${e.face_name}` : 'UNIDENTIFIED SUBJECT'}
                        </span>
                    </div>
                    <div style="font-size: 10px; color: var(--text-muted); display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 4px;">
                        <div>LAST SIGHTED: <strong style="color: #fff">Cam #${camId} (${secName})</strong></div>
                        <div>SIGHTING COUNT: <strong style="color: var(--c-cyan)">${e.sighting_count}</strong></div>
                        <div>FIRST SEEN: <strong style="color: #fff">${e.first_seen_str || '--'}</strong></div>
                        <div>LAST SEEN: <strong style="color: var(--c-yellow)">${Math.round(e.last_seen_sec_ago || 0)}s ago</strong></div>
                    </div>
                    ${transit ? `
                        <div style="margin-top: 5px; padding: 4px 8px; background: rgba(245,158,11,0.15); border-left: 2px solid var(--c-amber); font-size: 10px; color: var(--c-amber);">
                            TRANSIT EVENT: Cam #${transit.from_camera} &rarr; Cam #${transit.to_camera} (transit time: ${transit.elapsed_sec}s)
                        </div>
                    ` : ''}
                    <div style="margin-top: 8px; display: flex; gap: 6px;">
                        <button class="btn-mini highlight-btn" onclick="lockCameraOnEntity(${camId})" title="Switch Primary Sentry to Cam #${camId}">[LOCK CAMERA #${camId}]</button>
                        <button class="btn-mini" onclick="traceRouteOnGlobe('${e.global_id}')" title="Trace 3D route trajectory across sectors on Cesium globe">[TRACE ROUTE ON GLOBE]</button>
                        <button class="btn-mini alert-btn" onclick="dispatchQRTForEntity('${e.global_id}')" title="Dispatch QRT intercept against target">[DISPATCH QRT]</button>
                    </div>
                `;
                entCont.appendChild(card);
            });
        }
    }

    if (trnCont) {
        if (reidTransitsData.length === 0) {
            trnCont.innerHTML = '<div style="color: var(--text-dim); font-size: 10px; text-align: center; padding: 20px;">No inter-camera movement detected yet. Switch streams or walk between camera angles.</div>';
        } else {
            trnCont.innerHTML = '';
            reidTransitsData.slice(0, 15).forEach(t => {
                const item = document.createElement('div');
                item.className = 'transit-event-card';
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color: var(--c-amber)">${t.global_id} INTER-CAMERA TRANSIT</strong>
                        <span style="color: var(--text-muted); font-size: 9px;">${t.timestamp || 'RECENT'}</span>
                    </div>
                    <div style="margin-top: 3px; color: #fff;">
                        Route: <strong>Cam #${t.from_camera} &rarr; Cam #${t.to_camera}</strong>
                    </div>
                    <div style="color: var(--c-cyan); font-size: 9px; margin-top: 2px;">
                        Transit Elapsed: <strong>${t.elapsed_sec}s</strong> | Identity: ${t.face_name || 'UNKNOWN'}
                    </div>
                `;
                trnCont.appendChild(item);
            });
        }
    }
}

function openReidModal() {
    const m = document.getElementById('modal-reid');
    if (m) m.style.display = 'flex';
    fetchReidData();
}

function closeReidModal() {
    const m = document.getElementById('modal-reid');
    if (m) m.style.display = 'none';
}

// ===================================================================
// 13. Hardware Gateway & Pan-Tilt Turret Controller
// ===================================================================
let hardwareData = null;

function jogTurret(dPan, dTilt) {
    fetch('/api/hardware/turret/jog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pan_delta: dPan, tilt_delta: dTilt })
    })
    .then(r => r.json())
    .catch(() => {});
}

function centerTurret() {
    fetch('/api/hardware/turret/center', { method: 'POST' })
        .then(r => r.json())
        .catch(() => {});
}

function toggleAutoTrack() {
    fetch('/api/hardware/turret/toggle_autotrack', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            const btn = document.getElementById('btn-toggle-autotrack');
            if (btn) {
                if (d.auto_track) {
                    btn.classList.add('active');
                    btn.innerText = '[TRACK: ON]';
                } else {
                    btn.classList.remove('active');
                    btn.innerText = '[TRACK: OFF]';
                }
            }
        })
        .catch(() => {});
}

function toggleIRCut() {
    fetch('/api/hardware/ircut/toggle', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            if (d.ircut) {
                const el = document.getElementById('gimbal-ircut-mode');
                if (el) el.innerText = d.ircut.filter_engaged ? 'IR-CUT: DAY OPTICAL' : 'IR-CUT: NIGHT PASS';
            }
        })
        .catch(() => {});
}

function updateHardwareUI(hw) {
    hardwareData = hw;
    const turret = hw.turret;
    const ircut = hw.ircut;
    const gw = hw.gateway;

    if (turret) {
        const chipTurret = document.getElementById('telem-turret-chip');
        if (chipTurret) chipTurret.innerText = `${Math.round(turret.pan)}° / ${Math.round(turret.tilt)}°`;

        const panVal = document.getElementById('gimbal-pan-val');
        if (panVal) panVal.innerText = `PAN: ${turret.pan.toFixed(1)}°`;

        const tiltVal = document.getElementById('gimbal-tilt-val');
        if (tiltVal) tiltVal.innerText = `TILT: ${turret.tilt.toFixed(1)}°`;

        const trackBadge = document.getElementById('gimbal-track-mode');
        if (trackBadge) {
            trackBadge.innerText = turret.auto_track ? 'AUTO-TRACK: ON' : 'MANUAL JOG';
            if (turret.auto_track) trackBadge.classList.add('active');
            else trackBadge.classList.remove('active');
        }

        const btnTrack = document.getElementById('btn-toggle-autotrack');
        if (btnTrack) {
            btnTrack.innerText = turret.auto_track ? '[TRACK: ON]' : '[TRACK: OFF]';
            if (turret.auto_track) btnTrack.classList.add('active');
            else btnTrack.classList.remove('active');
        }

        // Modal elements
        const hwPan = document.getElementById('hw-pan-val');
        if (hwPan) hwPan.innerText = `${turret.pan.toFixed(1)}° (Cmd: ${turret.target_pan.toFixed(1)}°)`;
        const hwTilt = document.getElementById('hw-tilt-val');
        if (hwTilt) hwTilt.innerText = `${turret.tilt.toFixed(1)}° (Cmd: ${turret.target_tilt.toFixed(1)}°)`;
        const hwAz = document.getElementById('hw-az-val');
        if (hwAz) hwAz.innerText = `${turret.azimuth_heading_deg > 0 ? '+' : ''}${turret.azimuth_heading_deg.toFixed(1)}°`;
        const hwEl = document.getElementById('hw-el-val');
        if (hwEl) hwEl.innerText = `${turret.elevation_deg > 0 ? '+' : ''}${turret.elevation_deg.toFixed(1)}°`;
        const hwTrack = document.getElementById('hw-track-val');
        if (hwTrack) hwTrack.innerText = turret.auto_track ? 'ACTIVE LOCK' : 'MANUAL';
    }

    if (ircut) {
        const chipIrcut = document.getElementById('telem-ircut-chip');
        if (chipIrcut) {
            chipIrcut.innerText = ircut.filter_engaged ? 'DAY' : 'NIGHT';
            chipIrcut.style.color = ircut.filter_engaged ? 'var(--c-green)' : 'var(--c-amber)';
        }

        const ircutBadge = document.getElementById('gimbal-ircut-mode');
        if (ircutBadge) {
            ircutBadge.innerText = ircut.filter_engaged ? 'IR-CUT: DAY OPTICAL' : 'IR-CUT: NIGHT PASS';
            ircutBadge.style.color = ircut.filter_engaged ? 'var(--c-green)' : 'var(--c-amber)';
        }

        const hwIrcut = document.getElementById('hw-ircut-val');
        if (hwIrcut) {
            hwIrcut.innerText = ircut.state_label;
            hwIrcut.style.color = ircut.filter_engaged ? 'var(--c-green)' : 'var(--c-amber)';
        }
    }

    if (gw) {
        const badge = document.getElementById('hw-mode-badge');
        if (badge) {
            badge.innerText = gw.mode;
            badge.style.borderColor = gw.is_connected ? 'var(--c-green)' : 'var(--c-cyan)';
            badge.style.color = gw.is_connected ? 'var(--c-green)' : 'var(--c-cyan)';
        }

        // Ultrasonic sensor telemetry
        if (gw.peripherals) {
            const usDist = document.getElementById('hw-us-dist');
            if (usDist && gw.peripherals.ultrasonic_distance_cm !== undefined) {
                usDist.innerText = `${gw.peripherals.ultrasonic_distance_cm.toFixed(1)} cm`;
            }
            const usAlert = document.getElementById('hw-us-alert');
            if (usAlert && gw.peripherals.pir_motion_detected !== undefined) {
                if (gw.peripherals.pir_motion_detected) {
                    usAlert.innerText = 'PROXIMITY BREACH (<50cm)';
                    usAlert.style.color = 'var(--c-red)';
                } else {
                    usAlert.innerText = 'SECURE';
                    usAlert.style.color = 'var(--c-green)';
                }
            }
        }

        // Available COM ports populate
        const portSelect = document.getElementById('select-serial-port');
        if (portSelect && gw.available_ports && gw.available_ports.length > 0) {
            const currentVal = portSelect.value;
            // Only update if options count changed
            if (portSelect.options.length !== gw.available_ports.length + 1) {
                portSelect.innerHTML = '<option value="">-- Detect Available Ports --</option>';
                gw.available_ports.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.port;
                    opt.innerText = `${p.port} (${p.desc || 'Serial Device'})`;
                    portSelect.appendChild(opt);
                });
                if (currentVal) portSelect.value = currentVal;
            }
        }
    }
}

function openHardwareModal() {
    const modal = document.getElementById('modal-hardware');
    if (modal) modal.style.display = 'flex';
}

function closeHardwareModal() {
    const modal = document.getElementById('modal-hardware');
    if (modal) modal.style.display = 'none';
    const status = document.getElementById('serial-connect-status');
    if (status) status.innerText = '';
}

function submitConnectSerial() {
    const port = document.getElementById('input-serial-port').value.trim();
    const status = document.getElementById('serial-connect-status');
    if (!port) {
        if (status) status.innerText = 'Please specify a serial port (e.g. COM3 or /dev/ttyUSB0).';
        return;
    }
    if (status) status.innerText = `Connecting to ${port}...`;
    fetch('/api/hardware/connect_serial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: port })
    })
    .then(r => r.json())
    .then(d => {
        if (d.connected) {
            if (status) {
                status.innerText = `Connected successfully to physical port ${port}!`;
                status.style.color = 'var(--c-green)';
            }
        } else {
            if (status) {
                status.innerText = `Port ${port} not open. System remains active on Virtual Loopback Bridge.`;
                status.style.color = 'var(--c-amber)';
            }
        }
    })
    .catch(err => {
        if (status) {
            status.innerText = `Serial link error: ${err}`;
            status.style.color = 'var(--c-red)';
        }
    });
}

// ===================================================================
// 12. GLOBAL CAMERA DIRECTORY & STRATEGIC FEEDS GATEWAY
// ===================================================================
let globalCamerasList = [];
let activeRegionFilter = 'ALL';
let globalCamMarkersLeaflet = {};
let globalCamEntitiesCesium = [];

function fetchGlobalCameras() {
    return fetch('/api/cameras/global/list')
        .then(res => res.json())
        .then(data => {
            globalCamerasList = data.cameras || [];
            const elChip = document.getElementById('telem-globalcams-chip');
            if (elChip) elChip.innerText = `${globalCamerasList.length} LIVE`;

            renderGlobalCamerasGrid();
            plotGlobalCamerasOnLeaflet();
            if (cesiumFullViewer) plotGlobalCamerasOnCesium(cesiumFullViewer);
            if (cesiumMiniViewer) plotGlobalCamerasOnCesium(cesiumMiniViewer);
            return globalCamerasList;
        })
        .catch(err => console.warn('[GLOBAL-CAMS] Error fetching cameras:', err));
}

function openGlobalCamsModal() {
    const modal = document.getElementById('modal-global-cams');
    if (modal) modal.style.display = 'flex';
    fetchGlobalCameras();
}

function closeGlobalCamsModal() {
    const modal = document.getElementById('modal-global-cams');
    if (modal) modal.style.display = 'none';
}

function toggleAddCustomCamForm() {
    const form = document.getElementById('custom-cam-form-container');
    const btn = document.getElementById('btn-toggle-add-cam');
    if (form) {
        const isHidden = form.style.display === 'none';
        form.style.display = isHidden ? 'block' : 'none';
        if (btn) btn.innerText = isHidden ? '[-] HIDE REGISTRATION FORM' : '[+] REGISTER CUSTOM RTSP / IP STREAM';
    }
}

function setRegionFilter(region) {
    activeRegionFilter = region;
    const pills = document.querySelectorAll('.filter-pills .filter-pill');
    pills.forEach(p => {
        if (p.getAttribute('data-region') === region) p.classList.add('active');
        else p.classList.remove('active');
    });
    renderGlobalCamerasGrid();
}

function filterGlobalCameras() {
    renderGlobalCamerasGrid();
}

function renderGlobalCamerasGrid() {
    const grid = document.getElementById('global-cams-grid');
    if (!grid) return;

    const searchTerm = (document.getElementById('global-cam-search')?.value || '').toLowerCase().trim();

    const filtered = globalCamerasList.filter(cam => {
        const matchesRegion = (activeRegionFilter === 'ALL') || (cam.region === activeRegionFilter);
        const matchesSearch = !searchTerm ||
            cam.name.toLowerCase().includes(searchTerm) ||
            cam.codename.toLowerCase().includes(searchTerm) ||
            (cam.location && cam.location.toLowerCase().includes(searchTerm)) ||
            (cam.country && cam.country.toLowerCase().includes(searchTerm)) ||
            cam.type.toLowerCase().includes(searchTerm);
        return matchesRegion && matchesSearch;
    });

    if (filtered.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; color: var(--text-dim); text-align: center; padding: 40px;">No camera sentries matching search filters.</div>';
        return;
    }

    grid.innerHTML = '';
    filtered.forEach(cam => {
        const card = document.createElement('div');
        card.className = 'global-cam-card';

        const regionLabel = (cam.region || 'FRONTIER').replace('_', ' ');

        card.innerHTML = `
            <div>
                <div class="cam-card-header">
                    <div>
                        <div class="cam-card-title">${cam.name}</div>
                        <div style="font-size: 9px; color: var(--c-cyan); font-family: var(--font-mono); margin-top: 1px;">
                            ${cam.codename} &bull; ${cam.location || cam.country}
                        </div>
                    </div>
                    <span class="cam-card-badge">${regionLabel}</span>
                </div>
                <div class="cam-card-meta" style="margin-top: 8px;">
                    <div>SENSOR: <span style="color: #fff;">${cam.type}</span></div>
                    <div>STATUS: <span style="color: var(--c-green);">${cam.status}</span></div>
                    <div>GPS: <span style="color: var(--c-cyan);">${cam.lat.toFixed(3)}°, ${cam.lng.toFixed(3)}°</span></div>
                    <div>MGRS: <span style="color: var(--c-yellow);">${cam.mgrs || 'GRID'}</span></div>
                </div>
            </div>
            <div class="cam-card-actions">
                <span style="font-size: 8px; color: var(--text-muted); margin-right: 4px;">ASSIGN:</span>
                <button class="btn-mini highlight-btn" onclick="assignGlobalCameraToSlot('${cam.id}', 1, true)" title="Set as Primary Sentry Stream & Slot 1">[PRI / S1]</button>
                <button class="btn-mini" onclick="assignGlobalCameraToSlot('${cam.id}', 2, false)" title="Assign to 2x2 Matrix Slot 2">[SLOT 2]</button>
                <button class="btn-mini" onclick="assignGlobalCameraToSlot('${cam.id}', 3, false)" title="Assign to 2x2 Matrix Slot 3">[SLOT 3]</button>
                <button class="btn-mini" onclick="assignGlobalCameraToSlot('${cam.id}', 4, false)" title="Assign to 2x2 Matrix Slot 4">[SLOT 4]</button>
                <button class="btn-mini" style="margin-left: auto; border-color: var(--c-cyan);" onclick="flyToLocation(${cam.lat}, ${cam.lng}, '${cam.name.replace(/'/g, "\\'")}')" title="Fly 3D Globe & Map to this Outpost">[FLY TO]</button>
            </div>
        `;
        grid.appendChild(card);
    });
}

function submitAddCustomCamera() {
    const name = document.getElementById('cust-cam-name')?.value.trim();
    const src = document.getElementById('cust-cam-src')?.value.trim();
    const lat = parseFloat(document.getElementById('cust-cam-lat')?.value) || 31.604;
    const lng = parseFloat(document.getElementById('cust-cam-lng')?.value) || 74.572;
    const ctype = document.getElementById('cust-cam-type')?.value.trim() || 'CUSTOM RTSP / IP STREAM';
    const loc = document.getElementById('cust-cam-loc')?.value.trim() || 'Operator Registered Sector';
    const stEl = document.getElementById('cust-cam-status');

    if (!name || !src) {
        if (stEl) {
            stEl.innerText = 'Please specify both a Camera Name and Stream URL/Source.';
            stEl.style.color = 'var(--c-red)';
        }
        return;
    }

    if (stEl) {
        stEl.innerText = 'Registering stream with Global C2 Gateway...';
        stEl.style.color = 'var(--c-cyan)';
    }

    fetch('/api/cameras/global/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            source: src,
            lat: lat,
            lng: lng,
            type: ctype,
            location: loc,
            region: 'CUSTOM'
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            if (stEl) {
                stEl.innerText = `Successfully registered ${name}!`;
                stEl.style.color = 'var(--c-green)';
            }
            document.getElementById('cust-cam-name').value = '';
            document.getElementById('cust-cam-src').value = '';
            fetchGlobalCameras();
        } else {
            if (stEl) {
                stEl.innerText = 'Failed to register camera.';
                stEl.style.color = 'var(--c-red)';
            }
        }
    })
    .catch(err => {
        if (stEl) {
            stEl.innerText = `Registration network error: ${err}`;
            stEl.style.color = 'var(--c-red)';
        }
    });
}

function assignGlobalCameraToSlot(camId, slotId, setPrimary) {
    fetch('/api/cameras/global/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            camera_id: camId,
            slot_id: slotId,
            set_primary: setPrimary
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            console.log(`[GLOBAL-CAMS] Slot #${slotId} assigned to ${camId}`);
            refreshSectors();
            if (setPrimary) activeSectorId = slotId;
            closeGlobalCamsModal();
        }
    })
    .catch(err => console.warn('[GLOBAL-CAMS] Assignment error:', err));
}

function flyToLocation(lat, lng, name) {
    if (cesiumFullViewer) {
        cesiumFullViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(lng, lat, 25000),
            duration: 2.0
        });
    }
    if (map) {
        map.flyTo([lat, lng], 10, { duration: 1.5 });
    }
    closeGlobalCamsModal();
}

function plotGlobalCamerasOnLeaflet() {
    if (!map || typeof L === 'undefined') return;

    globalCamerasList.forEach(cam => {
        if (!globalCamMarkersLeaflet[cam.id]) {
            const icon = L.divIcon({
                className: 'custom-cam-pin',
                html: `<div style="width: 14px; height: 14px; border-radius: 3px; background: #0c1822; border: 2px solid #00f0ff; display: flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 800; color: #00f0ff; box-shadow: 0 0 8px rgba(0,240,255,0.6); cursor: pointer;">🎥</div>`,
                iconSize: [16, 16]
            });

            const marker = L.marker([cam.lat, cam.lng], { icon: icon }).addTo(map);
            marker.bindPopup(`
                <div style="font-family: monospace; font-size: 11px; color: #fff; background: #0c1118; padding: 6px; border: 1px solid #00f0ff;">
                    <div style="font-weight: 800; color: #00f0ff;">${cam.name}</div>
                    <div style="font-size: 9px; color: #a0b0c0; margin-top: 2px;">${cam.type}</div>
                    <div style="font-size: 9px; color: #ffaa00; margin-top: 2px;">MGRS: ${cam.mgrs}</div>
                    <button style="margin-top: 6px; width: 100%; background: #00f0ff; color: #000; font-weight: 800; border: none; padding: 4px; cursor: pointer;" onclick="assignGlobalCameraToSlot('${cam.id}', 1, true)">SET AS PRIMARY SENTRY</button>
                </div>
            `);
            globalCamMarkersLeaflet[cam.id] = marker;
        }
    });
}

function plotGlobalCamerasOnCesium(viewer) {
    if (!viewer || typeof Cesium === 'undefined') return;

    globalCamerasList.forEach(cam => {
        const color = Cesium.Color.fromCssColorString('#00f0ff');

        // 1. Vertical 120km Skyward Light Beam (Visible from Orbit)
        viewer.entities.add({
            name: `BEAM-${cam.id}`,
            polyline: {
                positions: [
                    Cesium.Cartesian3.fromDegrees(cam.lng, cam.lat, 0),
                    Cesium.Cartesian3.fromDegrees(cam.lng, cam.lat, 120000)
                ],
                width: 2.5,
                material: color.withAlpha(0.65)
            }
        });

        // 2. High-Visibility Sentry Node with properties for click intercept
        viewer.entities.add({
            name: cam.name,
            properties: { cameraData: cam },
            position: Cesium.Cartesian3.fromDegrees(cam.lng, cam.lat, 1000),
            point: {
                pixelSize: 10,
                color: color,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
                scaleByDistance: new Cesium.NearFarScalar(1.5e2, 2.0, 8.0e6, 0.8),
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            },
            label: {
                text: `🎥 [CAM] ${cam.name}`,
                font: '11px monospace',
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12),
                fillColor: color,
                scaleByDistance: new Cesium.NearFarScalar(1.5e2, 1.2, 5.0e6, 0.6),
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            }
        });
    });
}

let activeInterceptCamera = null;

function openGlobeCctvIntercept(cam) {
    activeInterceptCamera = cam;
    const box = document.getElementById('globe-cctv-intercept');
    if (!box) return;
    document.getElementById('globe-cctv-title').innerText = `CCTV INTERCEPT // ${cam.codename}`;
    document.getElementById('globe-cctv-stream-img').src = `/api/cameras/stream/${cam.id}?t=${Date.now()}`;
    document.getElementById('globe-cctv-mgrs-tag').innerText = `MGRS: ${cam.mgrs || 'GRID'}`;
    document.getElementById('globe-cctv-type').innerText = cam.type || 'OPTICAL 4K';
    document.getElementById('globe-cctv-loc').innerText = `${cam.name} (${cam.lat.toFixed(3)}°, ${cam.lng.toFixed(3)}°)`;
    box.style.display = 'block';
}

function closeGlobeCctvIntercept() {
    const box = document.getElementById('globe-cctv-intercept');
    if (box) box.style.display = 'none';
    const img = document.getElementById('globe-cctv-stream-img');
    if (img) img.src = '';
    activeInterceptCamera = null;
}

function assignActiveInterceptToSlot(slotId, setPrimary) {
    if (!activeInterceptCamera) return;
    assignGlobalCameraToSlot(activeInterceptCamera.id, slotId, setPrimary);
}

function lockCameraOnEntity(camId) {
    switchSector(camId);
    showTacticalToast(`SENTRY LOCKED ON CAMERA #${camId}`);
}

let activeRoutePolyline = null;

function traceRouteOnGlobe(globalId) {
    openFullGlobeModal();
    if (!cesiumFullViewer) return;

    const entity = reidEntitiesData.find(e => e.global_id === globalId);
    if (!entity) {
        showTacticalToast(`ENTITY ${globalId} DATA LOCATING...`);
        return;
    }

    if (activeRoutePolyline) {
        cesiumFullViewer.entities.remove(activeRoutePolyline);
        activeRoutePolyline = null;
    }

    const camIds = new Set();
    if (entity.current_camera_id) camIds.add(entity.current_camera_id);
    if (entity.last_camera) camIds.add(entity.last_camera);
    reidTransitsData.filter(t => t.global_id === globalId).forEach(t => {
        camIds.add(t.from_camera);
        camIds.add(t.to_camera);
    });

    const sectorsLookup = {
        1: { lat: 31.604, lng: 74.572 },
        2: { lat: 27.023, lng: 70.912 },
        3: { lat: 32.610, lng: 74.720 },
        4: { lat: 32.726, lng: 74.857 }
    };

    const pts = [];
    Array.from(camIds).forEach(cid => {
        const sec = sectorsLookup[cid] || sectorsLookup[1];
        pts.push(Cesium.Cartesian3.fromDegrees(sec.lng, sec.lat, 25000));
    });

    if (pts.length >= 2) {
        activeRoutePolyline = cesiumFullViewer.entities.add({
            name: `ROUTE-TRACE-${globalId}`,
            polyline: {
                positions: pts,
                width: 4.0,
                material: new Cesium.PolylineGlowMaterialProperty({
                    glowPower: 0.35,
                    color: Cesium.Color.fromCssColorString('#ff2244')
                })
            }
        });
        cesiumFullViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(sectorsLookup[1].lng, sectorsLookup[1].lat, 1200000),
            duration: 2.0
        });
        showTacticalToast(`TRACING REID TRAJECTORY FOR ${globalId} ACROSS ${camIds.size} SECTORS`);
    } else {
        const sec = sectorsLookup[entity.current_camera_id || 1];
        cesiumFullViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(sec.lng, sec.lat, 250000),
            duration: 1.8
        });
        showTacticalToast(`TARGET ${globalId} PINPOINTED AT SECTOR-0${entity.current_camera_id || 1}`);
    }
}

function dispatchQRTForEntity(globalId) {
    openInterdictionModal();
    const targetIntel = document.getElementById('int-target-intel');
    if (targetIntel) targetIntel.innerText = `${globalId} // PERSON (INTERCEPT VECTOR)`;
    showTacticalToast(`QRT INTERDICTION QUEUED FOR ${globalId}`);
}

function showTacticalToast(msg) {
    let toast = document.getElementById('tactical-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'tactical-toast';
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.background = 'rgba(8, 14, 20, 0.95)';
        toast.style.border = '1px solid var(--c-cyan)';
        toast.style.color = 'var(--c-cyan)';
        toast.style.padding = '8px 16px';
        toast.style.fontFamily = 'var(--font-mono)';
        toast.style.fontSize = '11px';
        toast.style.fontWeight = '800';
        toast.style.boxShadow = '0 0 15px rgba(0,240,255,0.4)';
        toast.style.borderRadius = '3px';
        toast.style.zIndex = '9999';
        toast.style.transition = 'opacity 0.3s ease';
        document.body.appendChild(toast);
    }
    toast.innerText = msg;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 3500);
}

// ===================================================================
// 13. AUTONOMOUS QRT INTERDICTION DISPATCH & HANDOFF ENGINE
// ===================================================================
let interdictionOrdersList = [];

function openInterdictionModal() {
    const modal = document.getElementById('modal-interdiction');
    if (modal) modal.style.display = 'flex';
    fetchInterdictionStatus();
    fetchInterdictionOrders();
}

function closeInterdictionModal() {
    const modal = document.getElementById('modal-interdiction');
    if (modal) modal.style.display = 'none';
}

function fetchInterdictionStatus() {
    fetch('/api/interdiction/status')
        .then(r => r.json())
        .then(d => {
            if (d.active_intercept) {
                updateInterdictionUI(d.active_intercept);
            }
        })
        .catch(err => console.warn('[INTERDICTION] Error:', err));
}

function updateInterdictionUI(intState) {
    const elTargetIntel = document.getElementById('int-target-intel');
    if (elTargetIntel) {
        elTargetIntel.innerText = `${intState.target_id} // ${intState.target_class} (${intState.vector.heading_deg}° @ ${intState.vector.speed_kmh} km/h)`;
    }

    const elTargetLoc = document.getElementById('int-target-loc');
    if (elTargetLoc) {
        elTargetLoc.innerText = `ORIGIN MGRS: ${intState.current_mgrs}`;
    }

    const elPredMgrs = document.getElementById('int-predicted-mgrs');
    if (elPredMgrs) {
        elPredMgrs.innerText = intState.vector.intercept_mgrs;
    }

    const elPredLatLng = document.getElementById('int-predicted-latlng');
    if (elPredLatLng) {
        elPredLatLng.innerText = `${intState.vector.intercept_lat.toFixed(4)}° N, ${intState.vector.intercept_lng.toFixed(4)}° E`;
    }

    const elAssigned = document.getElementById('int-assigned-unit');
    if (elAssigned) {
        elAssigned.innerText = `${intState.assigned_qrt.callsign} (${intState.assigned_qrt.unit_name})`;
    }

    const elSpecs = document.getElementById('int-unit-specs');
    if (elSpecs) {
        elSpecs.innerText = `${intState.assigned_qrt.vehicle} | ${intState.assigned_qrt.distance_to_intercept_km} km (ETA: ${Math.round(intState.assigned_qrt.eta_seconds)}s)`;
    }

    const badge = document.getElementById('interdiction-threat-badge');
    if (badge) {
        badge.innerText = intState.threat_level;
    }
}

function updateInterdictionQuickBanner(intState) {
    const btnQrt = document.getElementById('btn-head-qrt');
    if (btnQrt) {
        btnQrt.classList.add('alert-btn');
        btnQrt.innerText = `[QRT] INTERCEPT: ${Math.round(intState.countdown_seconds)}s`;
    }
}

function dispatchQRTOrder() {
    fetch('/api/interdiction/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operator_callsign: "C2-COMMANDER" })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const ord = data.order;
            alert(`[INTERDICTION DISPATCH TRANSMITTED]\n\nORDER UUID: ${ord.order_uuid}\nASSIGNED UNIT: ${ord.assigned_unit.callsign}\nINTERCEPT MGRS: ${ord.intercept_coordinates.mgrs}\nTIME TO INTERCEPT: ${ord.target.breach_eta_sec}s\nSEC 65B HASH SEAL: ${ord.sec65b_hash.substring(0, 16)}...`);
            fetchInterdictionOrders();
        }
    })
    .catch(err => alert(`Dispatch Error: ${err}`));
}

function fetchInterdictionOrders() {
    fetch('/api/interdiction/orders')
        .then(r => r.json())
        .then(data => {
            interdictionOrdersList = data.orders || [];
            const tbody = document.getElementById('interdiction-orders-tbody');
            if (!tbody) return;

            if (interdictionOrdersList.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 15px;">No active dispatch orders issued yet</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            interdictionOrdersList.forEach(ord => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.06)';
                tr.innerHTML = `
                    <td style="font-weight: 800; color: #fff; padding: 6px 8px;">${ord.order_uuid}</td>
                    <td style="color: var(--text-muted); font-size: 10px; padding: 6px 8px;">${ord.timestamp_ist}</td>
                    <td style="color: var(--c-yellow); font-weight: 700; padding: 6px 8px;">${ord.target.id} (${ord.target.classification})</td>
                    <td style="color: var(--c-green); font-weight: 700; padding: 6px 8px;">${ord.assigned_unit.callsign} (${ord.assigned_unit.distance_km}km)</td>
                    <td style="color: var(--c-cyan); padding: 6px 8px;">${ord.intercept_coordinates.mgrs}</td>
                    <td style="color: #00ff77; font-family: monospace; font-size: 9px; padding: 6px 8px;">${ord.sec65b_hash.substring(0, 14)}...</td>
                    <td style="padding: 6px 8px;">
                        <button class="btn-mini highlight-btn" onclick="window.open('/api/interdiction/ticket/${ord.order_uuid}', '_blank')">[VIEW WARRANT]</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.warn('[INTERDICTION] Error fetching orders:', err));
}

// ===================================================================
// DYNAMIC CCTV & RTSP STREAM MANAGER HANDLERS
// ===================================================================
function openCctvManagerModal() {
    document.getElementById('modal-cctv-manager').style.display = 'flex';
    fetchCctvManagerList();
}

function closeCctvManagerModal() {
    document.getElementById('modal-cctv-manager').style.display = 'none';
    const st = document.getElementById('mgr-cam-status');
    if (st) st.innerText = '';
}

function fillCctvPreset(src) {
    document.getElementById('mgr-cam-src').value = src;
}

function fetchCctvManagerList() {
    fetch('/api/cameras/list')
        .then(r => r.json())
        .then(cams => {
            const tbody = document.getElementById('cctv-manager-tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            cams.forEach(c => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.06)';
                const isPrimary = c.is_active;
                const statusColor = c.is_streaming ? 'var(--c-green)' : (isPrimary ? 'var(--c-cyan)' : 'var(--text-muted)');
                const statusLabel = c.is_streaming ? 'LIVE STREAMING' : (isPrimary ? 'ACTIVE PRIMARY' : 'STANDBY');
                
                tr.innerHTML = `
                    <td style="font-weight: 800; color: var(--c-cyan); padding: 6px 8px;">#${c.id}</td>
                    <td style="color: #fff; font-weight: 700; padding: 6px 8px;">
                        ${c.name}
                        <div style="font-size: 9px; color: var(--text-dim);">${c.codename}</div>
                    </td>
                    <td style="color: var(--text-muted); font-size: 10px; padding: 6px 8px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <span style="background: rgba(0,240,255,0.1); padding: 1px 4px; border-radius: 2px; color: var(--c-cyan);">${c.protocol || 'RTSP'}</span>
                        ${c.source}
                    </td>
                    <td style="color: var(--text-main); padding: 6px 8px;">${c.resolution || '854x480'}</td>
                    <td style="color: var(--c-green); font-weight: 700; padding: 6px 8px;">${c.fps ? c.fps.toFixed(1) : '30.0'}</td>
                    <td style="color: ${statusColor}; font-weight: 700; padding: 6px 8px;">${statusLabel}</td>
                    <td style="text-align: right; padding: 6px 8px; display: flex; gap: 4px; justify-content: flex-end;">
                        <button class="btn-mini ${isPrimary ? 'highlight-btn' : ''}" onclick="switchSector(${c.id})">${isPrimary ? '[ACTIVE]' : '[SWITCH PRIMARY]'}</button>
                        ${c.id > 4 ? `<button class="btn-mini" style="border-color: var(--c-red); color: var(--c-red);" onclick="deleteCustomCamera(${c.id})">[DELETE]</button>` : ''}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.warn('[CCTV-MGR] Error fetching cameras:', err));
}

function submitOnboardCamera() {
    const name = document.getElementById('mgr-cam-name').value.trim();
    const src = document.getElementById('mgr-cam-src').value.trim();
    const type = document.getElementById('mgr-cam-type').value;
    const mgrs = document.getElementById('mgr-cam-mgrs').value.trim();
    const statusEl = document.getElementById('mgr-cam-status');

    if (!name || !src) {
        if (statusEl) {
            statusEl.innerText = 'Error: Camera Name and Stream Source are required.';
            statusEl.style.color = 'var(--c-red)';
        }
        return;
    }

    if (statusEl) {
        statusEl.innerText = 'Connecting & testing camera feed...';
        statusEl.style.color = 'var(--c-cyan)';
    }

    fetch('/api/cameras/add_custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            source: src,
            cam_type: type,
            mgrs: mgrs || '43R EQ 5940 9662'
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            if (statusEl) {
                statusEl.innerText = `Successfully provisioned ${data.camera.name} (Node #${data.camera.id})!`;
                statusEl.style.color = 'var(--c-green)';
            }
            document.getElementById('mgr-cam-name').value = '';
            document.getElementById('mgr-cam-src').value = '';
            fetchCctvManagerList();
            refreshSectors();
        } else {
            if (statusEl) {
                statusEl.innerText = `Error: ${data.message}`;
                statusEl.style.color = 'var(--c-red)';
            }
        }
    })
    .catch(err => {
        if (statusEl) {
            statusEl.innerText = `Connection Failed: ${err}`;
            statusEl.style.color = 'var(--c-red)';
        }
    });
}

function deleteCustomCamera(camId) {
    if (!confirm(`Are you sure you want to remove Camera Node #${camId}?`)) return;
    fetch(`/api/cameras/delete/${camId}`, { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            fetchCctvManagerList();
            refreshSectors();
        });
}

function scanLocalVideoDevices() {
    const listEl = document.getElementById('local-devices-list');
    if (listEl) listEl.innerHTML = '<span style="color: var(--c-cyan)">Probing local video capture buses...</span>';

    fetch('/api/cameras/scan_devices')
        .then(r => r.json())
        .then(data => {
            if (!listEl) return;
            if (!data.devices || data.devices.length === 0) {
                listEl.innerHTML = '<span style="color: var(--text-muted)">No active physical USB webcams found on local bus. Use simulated video streams or RTSP IP cameras.</span>';
                return;
            }

            let html = '<div style="display: flex; gap: 8px; flex-wrap: wrap;">';
            data.devices.forEach(d => {
                html += `
                    <div style="background: rgba(0,255,119,0.08); border: 1px solid var(--c-green); padding: 6px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px;">
                        <div>
                            <strong style="color: var(--c-green); font-size: 11px;">DEVICE #${d.index}</strong>
                            <div style="color: var(--text-muted); font-size: 9px;">${d.resolution} | ${d.type}</div>
                        </div>
                        <button class="btn-mini highlight-btn" onclick="fillCctvPreset('${d.index}')">[SELECT DEVICE #${d.index}]</button>
                    </div>
                `;
            });
            html += '</div>';
            listEl.innerHTML = html;
        })
        .catch(err => {
            if (listEl) listEl.innerHTML = `<span style="color: var(--c-red)">Probe failed: ${err}</span>`;
        });
}

// ===================================================================
// FALSE ALARM REDUCTION RATE (FARR) HANDLERS
// ===================================================================
function openFarrModal() {
    document.getElementById('modal-farr').style.display = 'flex';
}

function closeFarrModal() {
    document.getElementById('modal-farr').style.display = 'none';
}

function updateFarrUI(farr) {
    const elPct = document.getElementById('farr-stat-percentage');
    if (elPct) elPct.innerText = `${farr.farr_percentage}%`;

    const elFauna = document.getElementById('farr-stat-fauna');
    if (elFauna) elFauna.innerText = farr.suppressed_fauna_count || 0;

    const elGlitches = document.getElementById('farr-stat-glitches');
    if (elGlitches) elGlitches.innerText = farr.transient_glitches_filtered || 0;

    const elBreaches = document.getElementById('farr-stat-breaches');
    if (elBreaches) elBreaches.innerText = farr.verified_incursions || 0;
}

// ===================================================================
// MULTI-CHANNEL ALERT DISPATCH (TELEGRAM & WEBHOOK) HANDLERS
// ===================================================================
function openAlertsModal() {
    document.getElementById('modal-alerts').style.display = 'flex';
    fetchAlertsConfig();
}

function closeAlertsModal() {
    document.getElementById('modal-alerts').style.display = 'none';
    const st = document.getElementById('alerts-config-status');
    if (st) st.innerText = '';
}

function fetchAlertsConfig() {
    fetch('/api/alerts/config')
        .then(r => r.json())
        .then(cfg => {
            const chkFg = document.getElementById('cfg-tg-enabled');
            if (chkFg) chkFg.checked = !!cfg.telegram_enabled;

            const inChat = document.getElementById('cfg-tg-chat');
            if (inChat) inChat.value = cfg.telegram_chat_id || '';

            const chkWh = document.getElementById('cfg-webhook-enabled');
            if (chkWh) chkWh.checked = !!cfg.webhook_enabled;

            const inWhUrl = document.getElementById('cfg-webhook-url');
            if (inWhUrl) inWhUrl.value = cfg.webhook_url || '';

            const inCd = document.getElementById('cfg-cooldown');
            if (inCd) inCd.value = cfg.cooldown_seconds || 10;
        })
        .catch(err => console.warn('[ALERTS] Error fetching config:', err));
}

function saveAlertsConfig() {
    const tgEnabled = document.getElementById('cfg-tg-enabled').checked;
    const tgToken = document.getElementById('cfg-tg-token').value.trim();
    const tgChat = document.getElementById('cfg-tg-chat').value.trim();
    const whEnabled = document.getElementById('cfg-webhook-enabled').checked;
    const whUrl = document.getElementById('cfg-webhook-url').value.trim();
    const cd = parseFloat(document.getElementById('cfg-cooldown').value) || 10;
    const statusEl = document.getElementById('alerts-config-status');

    const payload = {
        telegram_enabled: tgEnabled,
        telegram_chat_id: tgChat,
        webhook_enabled: whEnabled,
        webhook_url: whUrl,
        cooldown_seconds: cd
    };
    if (tgToken) payload.telegram_bot_token = tgToken;

    fetch('/api/alerts/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (statusEl) {
            statusEl.innerText = 'Alert configuration saved successfully!';
            statusEl.style.color = 'var(--c-green)';
        }
        document.getElementById('cfg-tg-token').value = '';
    })
    .catch(err => {
        if (statusEl) {
            statusEl.innerText = `Save failed: ${err}`;
            statusEl.style.color = 'var(--c-red)';
        }
    });
}

function sendTestAlert() {
    const statusEl = document.getElementById('alerts-config-status');
    if (statusEl) {
        statusEl.innerText = 'Dispatching test alert to configured channels...';
        statusEl.style.color = 'var(--c-cyan)';
    }

    fetch('/api/alerts/test', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (statusEl) {
                statusEl.innerText = data.message || 'Test alert dispatched!';
                statusEl.style.color = 'var(--c-green)';
            }
        })
        .catch(err => {
            if (statusEl) {
                statusEl.innerText = `Test dispatch failed: ${err}`;
                statusEl.style.color = 'var(--c-red)';
            }
        });
}
