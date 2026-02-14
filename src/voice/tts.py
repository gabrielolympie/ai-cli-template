"""TTS provider abstraction: synthesize text to audio."""

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> tuple:
        """Returns (audio_data, sample_rate). audio_data is bytes or numpy array."""
        ...


class PocketTTSProvider(TTSProvider):
    """Kyutai Pocket TTS - local, CPU-only, 100M params.

    Requires: pip install pocket-tts
    """

    def __init__(self, voice: str = "alba"):
        from pocket_tts import TTSModel

        self._model = TTSModel.load_model()
        self._voice_state = self._model.get_state_for_audio_prompt(voice)
        self._sample_rate = self._model.sample_rate

    def synthesize(self, text: str) -> tuple:
        audio = self._model.generate_audio(self._voice_state, text)
        return audio.numpy(), self._sample_rate


class Pyttsx3TTSProvider(TTSProvider):
    """Fallback local TTS using pyttsx3 (no model downloads).

    Requires: pip install pyttsx3
    """

    def __init__(self):
        import pyttsx3

        self._engine = pyttsx3.init()

    def synthesize(self, text: str) -> tuple[bytes, int]:
        import tempfile
        import wave
        import os

        tmp = tempfile.mktemp(suffix=".wav")
        try:
            self._engine.save_to_file(text, tmp)
            self._engine.runAndWait()
            with wave.open(tmp, "rb") as wf:
                sr = wf.getframerate()
                data = wf.readframes(wf.getnframes())
            return data, sr
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS API.

    Requires: pip install openai + OPENAI_API_KEY env var
    """

    def __init__(self, voice: str = "alloy", model: str = "tts-1"):
        import openai

        self._client = openai.OpenAI()
        self._voice = voice
        self._model = model

    def synthesize(self, text: str) -> tuple[bytes, int]:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="pcm",
        )
        return response.content, 24000


def create_tts(config: dict) -> TTSProvider:
    """Factory: build a TTS provider from voice config."""
    provider = config.get("provider", "pocket_tts")
    voice = config.get("voice", "alba")

    if provider == "pocket_tts":
        return PocketTTSProvider(voice=voice)
    elif provider == "pyttsx3":
        return Pyttsx3TTSProvider()
    elif provider == "openai":
        return OpenAITTSProvider(voice=voice, model=config.get("model", "tts-1"))
    else:
        raise ValueError(f"Unknown TTS provider: {provider}. Available: pocket_tts, pyttsx3, openai")
