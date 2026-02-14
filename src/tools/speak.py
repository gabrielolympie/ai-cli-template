"""Speak tool: async text-to-speech for the agent."""

from mirascope import llm
import numpy as np

_tts_provider = None
_audio_player = None


def configure_speak(tts_provider, audio_player):
    """Wire up TTS + audio playback. Called when voice mode toggles on/off."""
    global _tts_provider, _audio_player
    _tts_provider = tts_provider
    _audio_player = audio_player


@llm.tool
def speak(text: str) -> str:
    """Speak text aloud to the user using text-to-speech.

    Use this tool when you want the user to HEAR your response.
    Good for:
    - Answering voice questions conversationally
    - Brief spoken confirmations ("Done!", "File created")
    - Reading back important short results

    Do NOT speak code blocks, file contents, or long technical text.
    Speech plays in the background - you can continue working immediately.
    Keep spoken text concise and natural (1-3 sentences max).

    Args:
        text: The text to speak aloud. Keep it conversational and concise.

    Returns:
        Confirmation that speech was queued.
    """
    if _tts_provider is None or _audio_player is None:
        return "Voice output is not active. Text was not spoken."

    try:
        audio_data, sample_rate = _tts_provider.synthesize(text)

        if isinstance(audio_data, np.ndarray):
            _audio_player.play_numpy(audio_data, sample_rate)
        else:
            _audio_player.play_audio(audio_data, sample_rate)

        preview = text[:80] + ("..." if len(text) > 80 else "")
        return f'Speaking: "{preview}"'
    except Exception as e:
        return f"TTS error: {e}"
