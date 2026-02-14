# Voice Output - Implementation Documentation

## Overview

Voice output lets the agent **choose** what to say aloud via an async `speak` tool. The agent continues working while audio plays in the background. Not everything gets spoken — only what the agent explicitly decides to vocalize.

## Architecture

```
Agent calls speak("Hello!") → TTS Provider → audio bytes → AudioPlayer (background thread) → speakers
```

### Key Design Decision: Tool, Not Auto-TTS

The agent produces code blocks, tool outputs, thoughts, and verbose text — none of which should be spoken. A `speak` tool gives the agent control over what to vocalize. The tool is fire-and-forget: it queues audio and returns immediately.

## Files Created

### `src/tools/speak.py` — The LLM Tool

```python
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
    Speech plays in the background - you can continue working immediately.
    Keep spoken text concise and natural (1-3 sentences max).
    Do NOT speak code blocks or file contents.
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
```

**How it integrates with `mirascope_cli.py`:**
- Added to `ALL_TOOLS` dict but gated: only included in `get_enabled_tools()` when `voice_active=True`
- No special handling in the agent loop (unlike `clarify` which pauses for input). The tool function itself handles everything.
- `configure_speak(tts, player)` is called when `/voice` toggles on; `configure_speak(None, None)` when off.

### `src/voice/tts.py` — TTS Provider Abstraction

```python
from abc import ABC, abstractmethod

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> tuple[bytes | None, int]:
        """Returns (audio_data, sample_rate)."""
        ...
```

**Three providers implemented:**

| Provider | Class | Package | How It Works |
|----------|-------|---------|-------------|
| **Kyutai Pocket TTS** (recommended) | `PocketTTSProvider` | `pocket-tts` | Local, CPU-only, 100M params. `TTSModel.load_model()` → `generate_audio(voice_state, text)` → numpy array. Returns numpy, not bytes. |
| **pyttsx3** (fallback) | `Pyttsx3TTSProvider` | `pyttsx3` | System TTS engine wrapper. Saves to temp WAV, reads back bytes. No model download. Low quality. |
| **OpenAI TTS** (cloud) | `OpenAITTSProvider` | `openai` | `client.audio.speech.create(model="tts-1", voice="alloy", response_format="pcm")`. Returns raw PCM at 24kHz. |

**Factory function:**
```python
def create_tts(config: dict) -> TTSProvider:
    # config keys: provider ("pocket_tts"|"pyttsx3"|"openai"), voice ("alba"|"alloy"|etc.)
```

### `src/voice/audio_io.py` — AudioPlayer

```python
class AudioPlayer:
    def play_audio(self, audio_bytes: bytes, sample_rate: int = 22050):
        """Play raw PCM int16 bytes in a background daemon thread."""
        # Converts to float32 numpy, calls sd.play() + sd.wait() in thread

    def play_numpy(self, audio_array, sample_rate: int = 22050):
        """Play numpy array directly (for PocketTTS which returns numpy)."""
        # Normalizes to [-1,1] if needed, plays in background thread
```

Both methods are non-blocking — they spawn daemon threads.

## Config (`config.yaml`)

```yaml
voice:
  tts:
    provider: "pocket_tts"    # "pocket_tts" | "pyttsx3" | "openai"
    voice: "alba"             # pocket_tts: alba | openai: alloy, nova, shimmer
```

## Integration in `mirascope_cli.py`

Changes needed in the main CLI:

1. **Import**: `from src.tools.speak import speak, configure_speak`
2. **Tool registration**: Add `"speak": speak` to `ALL_TOOLS` dict
3. **Gate on voice mode**: In `get_enabled_tools()`, skip `speak` unless `include_voice=True`
4. **On `/voice` toggle ON**: Create TTS provider + AudioPlayer, call `configure_speak(tts, player)`
5. **On `/voice` toggle OFF**: Call `configure_speak(None, None)`
6. **Before each LLM call (when voice active)**: Inject a transient user message telling the agent voice mode is on and to use `speak` for verbal responses

## Dependencies

```
sounddevice>=0.4.6     # Speaker output (requires libportaudio2 system package)
numpy>=1.24            # Audio array manipulation
pocket-tts>=0.1        # Kyutai Pocket TTS (recommended, local CPU)
# pyttsx3>=2.90        # Alternative: fallback local TTS
# openai>=1.0          # Alternative: cloud TTS
```

**System packages (WSL2):**
```bash
sudo apt-get install -y libportaudio2 portaudio19-dev libasound2-plugins pulseaudio-utils
```

## WSL2 Audio Issues Encountered

If you get a segfault when using `/voice` (PortAudio/ALSA crash), run the fix script:

```bash
./scripts/fix-wsl-audio.sh
```

Then reload your shell: `source ~/.bashrc`

This script fixes all common issues:

1. **PortAudio not found**: Installs `libportaudio2` and `portaudio19-dev`
2. **GLIBCXX version conflict**: Conda's `libstdc++.so.6` is too old. Fixes by symlinking system version
3. **No audio devices**: PortAudio uses ALSA but WSLg uses PulseAudio. Sets up bridge via `~/.asoundrc` and `PULSE_SERVER`

Manual fix steps (if script fails):
```bash
# Install packages
sudo apt-get install -y libportaudio2 portaudio19-dev libasound2-plugins pulseaudio-utils

# Fix conda libstdc++ conflict
ln -sf /usr/lib/x86_64-linux-gnu/libstdc++.so.6 $CONDA_PREFIX/lib/libstdc++.so.6

# Create ~/.asoundrc for ALSA → PulseAudio routing
cat > ~/.asoundrc << 'EOF'
pcm.default pulse
ctl.default pulse
pcm.pulse { type pulse }
ctl.pulse { type pulse }
EOF

# Set PULSE_SERVER for WSLg
echo 'export PULSE_SERVER=unix:/mnt/wslg/PulseServer' >> ~/.bashrc
source ~/.bashrc
```
