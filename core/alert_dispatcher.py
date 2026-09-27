import os
import cv2
import json
import time
import queue
import threading
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

class AlertDispatcher:
    """
    Project TRINETRA-C2 // Multi-Channel Incident Alert Dispatcher
    Dispatches real-time breach incidents, MGRS coordinates, Section 65B forensic hashes,
    and photo evidence to field commanders via Telegram Bot API and HTTP Webhooks.
    """
    def __init__(self, config_path: str = "alert_config.json"):
        self.config_path = config_path
        self.queue = queue.Queue(maxsize=100)
        self.running = True
        self.lock = threading.Lock()
        
        # Default config
        self.config = {
            "telegram_enabled": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "webhook_enabled": False,
            "webhook_url": "",
            "cooldown_seconds": 10.0,
            "last_dispatched": 0.0,
            "total_alerts_sent": 0
        }
        self._load_config()
        
        # Start background worker thread
        self.worker_thread = threading.Thread(target=self._dispatch_worker, daemon=True)
        self.worker_thread.start()

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception as e:
                print(f"[ALERT-DISPATCHER] Failed to read {self.config_path}: {e}")

    def save_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            self.config.update(new_config)
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2)
                print(f"[ALERT-DISPATCHER] Config saved successfully.")
            except Exception as e:
                print(f"[ALERT-DISPATCHER] Failed to save {self.config_path}: {e}")
            return self.get_config()

    def get_config(self) -> Dict[str, Any]:
        with self.lock:
            cfg = dict(self.config)
            if cfg.get("telegram_bot_token"):
                token = cfg["telegram_bot_token"]
                if len(token) > 8:
                    cfg["telegram_bot_token_masked"] = token[:4] + "..." + token[-4:]
                else:
                    cfg["telegram_bot_token_masked"] = "***"
            else:
                cfg["telegram_bot_token_masked"] = "NOT CONFIGURED"
            return cfg

    def trigger_alert(self, incident_data: Dict[str, Any], frame_bgr: Optional[Any] = None) -> bool:
        """Enqueues an alert for asynchronous non-blocking dispatch."""
        now = time.time()
        cooldown = self.config.get("cooldown_seconds", 10.0)
        
        with self.lock:
            if now - self.config.get("last_dispatched", 0.0) < cooldown:
                return False  # Suppress rapid duplicate alerts within cooldown
            self.config["last_dispatched"] = now
            self.config["total_alerts_sent"] += 1

        try:
            img_bytes = None
            if frame_bgr is not None:
                ret, buf = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    img_bytes = buf.tobytes()

            self.queue.put_nowait({
                "data": incident_data,
                "image_bytes": img_bytes,
                "timestamp": now
            })
            return True
        except queue.Full:
            print("[ALERT-DISPATCHER] Warning: Alert queue is full, dropping alert.")
            return False

    def _dispatch_worker(self):
        """Background thread handling HTTP requests to external services."""
        while self.running:
            try:
                item = self.queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                incident = item["data"]
                img_bytes = item.get("image_bytes")
                
                # 1. Telegram Bot API
                if self.config.get("telegram_enabled") and self.config.get("telegram_bot_token") and self.config.get("telegram_chat_id"):
                    self._send_telegram_alert(incident, img_bytes)
                
                # 2. HTTP Webhook
                if self.config.get("webhook_enabled") and self.config.get("webhook_url"):
                    self._send_webhook_alert(incident)
                    
            except Exception as e:
                print(f"[ALERT-DISPATCHER] Dispatch worker error: {e}")
            finally:
                self.queue.task_done()

    def _send_telegram_alert(self, incident: Dict[str, Any], img_bytes: Optional[bytes]):
        token = self.config["telegram_bot_token"]
        chat_id = self.config["telegram_chat_id"]
        
        sector_name = incident.get("sector_name", "UNKNOWN SECTOR")
        mgrs = incident.get("mgrs", "UNKNOWN MGRS")
        threat_level = incident.get("threat_level", "CRITICAL INCURSION")
        sec65b_hash = incident.get("sec65b_hash", "N/A")
        ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(incident.get("timestamp", time.time())))
        
        caption = (
            f"🚨 *TRINETRA-C2 BORDER SECURITY ALERT*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *Sector:* `{sector_name}`\n"
            f"🗺️ *MGRS Grid:* `{mgrs}`\n"
            f"⚠️ *Threat Level:* *{threat_level}*\n"
            f"🕒 *Time:* `{ts}`\n"
            f"🔒 *Section 65B Hash:* `{sec65b_hash[:16]}...`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *Immediate QRT Interdiction Recommended*"
        )
        
        if img_bytes:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            boundary = f"----WebKitFormBoundary{int(time.time() * 1000)}"
            body = bytearray()
            
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode('utf-8'))
            
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode('utf-8'))
            
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\nMarkdown\r\n'.encode('utf-8'))
            
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="photo"; filename="breach_evidence.jpg"\r\n'.encode('utf-8'))
            body.extend(b'Content-Type: image/jpeg\r\n\r\n')
            body.extend(img_bytes)
            body.extend(b'\r\n')
            
            body.extend(f"--{boundary}--\r\n".encode('utf-8'))
            
            req = urllib.request.Request(url, data=bytes(body))
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        print(f"[ALERT-DISPATCHER] Telegram photo alert sent successfully to {chat_id}")
            except Exception as e:
                print(f"[ALERT-DISPATCHER] Telegram photo send failed: {e}")
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "Markdown"
            }
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        print(f"[ALERT-DISPATCHER] Telegram text alert sent successfully to {chat_id}")
            except Exception as e:
                print(f"[ALERT-DISPATCHER] Telegram message send failed: {e}")

    def _send_webhook_alert(self, incident: Dict[str, Any]):
        webhook_url = self.config["webhook_url"]
        payload = {
            "source": "TRINETRA-C2",
            "protocol": "CIBMS-MHA-V1",
            "incident": incident,
            "timestamp": time.time()
        }
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=req_data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[ALERT-DISPATCHER] Webhook delivered with status {resp.status}")
        except Exception as e:
            print(f"[ALERT-DISPATCHER] Webhook delivery failed: {e}")

    def test_alert(self) -> Dict[str, Any]:
        """Dispatches a mock test alert to verify Telegram / Webhook connectivity."""
        test_incident = {
            "sector_name": "TEST // AMRITSAR OUTPOST 04",
            "mgrs": "43R EQ 5940 9662",
            "threat_level": "OPERATIONAL TEST VERIFICATION",
            "sec65b_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "timestamp": time.time()
        }
        success = self.trigger_alert(test_incident, None)
        return {
            "status": "queued" if success else "cooldown_or_error",
            "message": "Test alert enqueued for immediate dispatch to configured channels."
        }
