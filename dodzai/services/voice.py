"""Voice interaction helpers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..utils.paths import app_media_dir

try:  # pragma: no cover - optional dependency
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import speech_recognition as sr
except Exception:  # pragma: no cover
    sr = None  # type: ignore


class VoiceInterface:
    """Best-effort speech synthesis and recognition wrappers."""

    def __init__(self) -> None:
        self._tts_engine = self._initialise_tts()
        self._recognizer = sr.Recognizer() if sr else None

    # ------------------------------------------------------------------
    def speak(self, text: str) -> None:
        if not text:
            return
        if self._tts_engine is None:  # pragma: no cover - environment without pyttsx3
            # No TTS engine available; write to a text file for external playback.
            media = app_media_dir()
            media.mkdir(parents=True, exist_ok=True)
            path = media / "tts-output.txt"
            path.write_text(text, encoding="utf-8")
            return
        try:  # pragma: no cover - interacts with OS audio stack
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
        except Exception:
            pass

    def synthesize_to_file(self, text: str, filename: Optional[str] = None) -> Optional[str]:
        if not text:
            return None
        media = app_media_dir()
        media.mkdir(parents=True, exist_ok=True)
        path = media / (filename or "tts-output.wav")
        if self._tts_engine is None:  # pragma: no cover - fallback path
            path.write_text(text, encoding="utf-8")
            return str(path)
        try:  # pragma: no cover - interacts with OS audio stack
            self._tts_engine.save_to_file(text, str(path))
            self._tts_engine.runAndWait()
            return str(path)
        except Exception:
            return None

    # ------------------------------------------------------------------
    def transcribe(self, audio_path: str) -> str:
        if sr is None or self._recognizer is None:  # pragma: no cover - fallback path
            return f"[transcription unavailable] {os.path.basename(audio_path)}"
        audio_file = Path(audio_path)
        if not audio_file.exists():
            return f"[file missing] {audio_path}"
        try:  # pragma: no cover - interacts with OS audio stack
            with sr.AudioFile(str(audio_file)) as source:
                audio = self._recognizer.record(source)
            return self._recognizer.recognize_google(audio)
        except Exception:
            return f"[transcription failed] {audio_file.name}"

    # ------------------------------------------------------------------
    def _initialise_tts(self):
        if pyttsx3 is None:
            return None
        try:  # pragma: no cover - optional dependency
            engine = pyttsx3.init()
            engine.setProperty("rate", 180)
            return engine
        except Exception:
            return None
