import time
import threading

class TacticalAudioAlert:
    """
    Non-blocking, threaded tactical audio alert system.
    Synthesizes voice warnings and sounds perimeter sirens without dropping video FPS.
    """
    def __init__(self, cooldown=3.5):
        self.cooldown = cooldown
        self.last_alert_time = 0
        self.muted = True  # Default to MUTED so it does not speak in background without operator consent
        self.is_playing = False
        
        # Test if pyttsx3 or winsound is available
        self.tts_available = False
        try:
            import pyttsx3
            self.tts_available = True
        except Exception:
            pass

    def toggle_mute(self):
        self.muted = not self.muted
        state = "MUTED" if self.muted else "UNMUTED"
        print(f"[TRINETRA-C2] Audio Klaxon: {state}")
        return self.muted

    def trigger_breach_alert(self, intruder_count=1):
        """Triggers a spoken tactical warning if cooldown has elapsed."""
        if self.muted:
            return

        now = time.time()
        if now - self.last_alert_time < self.cooldown:
            return

        if self.is_playing:
            return

        self.last_alert_time = now
        threading.Thread(target=self._play_alert_worker, args=(intruder_count,), daemon=True).start()

    def _play_alert_worker(self, count):
        self.is_playing = True
        try:
            # First sound tactical short frequency beeps
            try:
                import winsound
                winsound.Beep(1800, 180)
                winsound.Beep(2400, 220)
            except Exception:
                pass

            # If TTS engine is available, speak tactical message
            if self.tts_available:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 175)
                    phrase = f"Warning. Perimeter breach detected. {count} incursion in sterile zone."
                    engine.say(phrase)
                    engine.runAndWait()
                except Exception:
                    pass
        finally:
            self.is_playing = False

    def trigger_vehicle_alert(self, plate: str, category: str = "STOLEN VEHICLE"):
        """Triggers an urgent voice warning for a stolen or watchlist vehicle."""
        if self.muted:
            return

        now = time.time()
        if now - self.last_alert_time < 3.0:
            return

        if self.is_playing:
            return

        self.last_alert_time = now
        threading.Thread(target=self._play_vehicle_alert_worker, args=(plate, category), daemon=True).start()

    def _play_vehicle_alert_worker(self, plate: str, category: str):
        self.is_playing = True
        try:
            try:
                import winsound
                winsound.Beep(2600, 150)
                winsound.Beep(2000, 150)
                winsound.Beep(2600, 250)
            except Exception:
                pass

            if self.tts_available:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 170)
                    spoken_plate = " ".join(list(plate.replace(" ", "")))
                    phrase = f"Tactical Warning. Watchlist vehicle intercepted. Category: {category}. License plate: {spoken_plate}."
                    engine.say(phrase)
                    engine.runAndWait()
                except Exception:
                    pass
        finally:
            self.is_playing = False

