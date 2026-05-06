# ─────────────────────────────────────────────────────────────────────────────
#  tts.py  –  Local text-to-speech with serial playback queue
# ─────────────────────────────────────────────────────────────────────────────
#
#  Uses pyttsx3 (offline, cross-platform): SAPI5 on Windows.
#  The engine is reinitialised for every utterance — this avoids the SAPI5
#  state accumulation bug where only the first agent's voice plays and
#  subsequent runAndWait() calls silently fail.
# ─────────────────────────────────────────────────────────────────────────────

import queue
import threading

try:
    import pyttsx3
    _HAS_PYTTSX3 = True
except ImportError:
    pyttsx3 = None
    _HAS_PYTTSX3 = False


class TTSEngine:

    def __init__(self, enabled: bool = True):
        self._available = _HAS_PYTTSX3
        self.enabled    = bool(enabled and _HAS_PYTTSX3)

        self._queue    = queue.Queue()
        self._n_voices = 0
        self._worker: threading.Thread | None = None
        self._stop_evt = threading.Event()

        if self._available:
            self._detect_voices()
            self._start_worker()

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._available

    def speak(self, text: str, voice_idx: int = 0, rate: int = 180):
        """Queue a text for speech. Non-blocking. Silently dropped if disabled."""
        if not self.enabled or not text:
            return
        clean = text.strip()[:480]
        if clean:
            self._queue.put((clean, voice_idx, rate))

    def toggle(self) -> bool:
        """Flip enabled state. Drains queue when turning off. Returns new state."""
        if not self._available:
            return False
        self.enabled = not self.enabled
        if not self.enabled:
            self._drain()
        return self.enabled

    def shutdown(self):
        """Stop the worker thread cleanly (called on app exit)."""
        self._stop_evt.set()
        self._drain()
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass

    # ── Internal ──────────────────────────────────────────────────────────

    def _detect_voices(self):
        """Count available voices once at startup."""
        try:
            eng = pyttsx3.init()
            self._n_voices = len(list(eng.getProperty("voices") or []))
            eng.stop()
        except Exception:
            self._n_voices = 1

    def _drain(self):
        try:
            while True:
                self._queue.get_nowait()
                self._queue.task_done()
        except queue.Empty:
            pass

    def _start_worker(self):
        def run():
            while not self._stop_evt.is_set():
                try:
                    item = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if item is None:          # shutdown sentinel
                    self._queue.task_done()
                    break
                if not self.enabled:
                    self._queue.task_done()
                    continue

                text, voice_idx, rate = item
                try:
                    # Fresh engine per utterance — avoids SAPI5 state bugs
                    # where only the first agent speaks and the rest are silent.
                    eng = pyttsx3.init()
                    voices = list(eng.getProperty("voices") or [])
                    if voices:
                        eng.setProperty("voice",
                                        voices[voice_idx % len(voices)].id)
                    eng.setProperty("rate", int(rate))
                    eng.say(text)
                    eng.runAndWait()
                except Exception as e:
                    print(f"[TTS] speak error: {e}")
                finally:
                    self._queue.task_done()

        self._worker = threading.Thread(target=run, daemon=True,
                                        name="tts-worker")
        self._worker.start()
