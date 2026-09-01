from __future__ import annotations

import tempfile
import wave
from pathlib import Path

from openai import OpenAI

from .config import API_KEY


class Voice:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.client = OpenAI(api_key=API_KEY) if API_KEY else None

    def record_and_transcribe(self, seconds: int = 6) -> str:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        import sounddevice as sd
        import numpy as np
        frames = sd.rec(int(seconds * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype="int16")
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = Path(f.name)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(np.dtype("int16").itemsize)
            wf.setframerate(self.sample_rate)
            wf.writeframes(frames.tobytes())
        try:
            with path.open("rb") as audio:
                result = self.client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio,
                    language="uk",
                )
            return result.text
        finally:
            path.unlink(missing_ok=True)

    def speak(self, text: str) -> None:
        # Local Windows TTS. It avoids sending the assistant's response back to the API.
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except Exception:
            pass
