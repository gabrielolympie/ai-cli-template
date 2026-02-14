"""Audio playback via sounddevice."""

import threading


class AudioPlayer:
    """Plays audio through the default speaker, non-blocking."""

    def play_audio(self, audio_bytes: bytes, sample_rate: int = 22050):
        """Play raw PCM int16 bytes in a background thread."""
        thread = threading.Thread(
            target=self._play, args=(audio_bytes, sample_rate), daemon=True
        )
        thread.start()

    def _play(self, audio_bytes: bytes, sample_rate: int):
        import sounddevice as sd
        import numpy as np

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_np.astype(np.float32) / 32768.0
        sd.play(audio_float, samplerate=sample_rate)
        sd.wait()

    def play_numpy(self, audio_array, sample_rate: int = 22050):
        """Play a numpy array directly (for providers that return numpy)."""
        thread = threading.Thread(
            target=self._play_numpy, args=(audio_array, sample_rate), daemon=True
        )
        thread.start()

    def _play_numpy(self, audio_array, sample_rate: int):
        import sounddevice as sd
        import numpy as np

        audio_float = audio_array.astype(np.float32)
        max_val = np.abs(audio_float).max()
        if max_val > 1.0:
            audio_float = audio_float / max_val
        sd.play(audio_float, samplerate=sample_rate)
        sd.wait()
