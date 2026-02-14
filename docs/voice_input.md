# Voice Input - Implementation Documentation

## Overview

Voice input continuously listens to the microphone, detects when the user speaks (VAD), transcribes the speech (STT), and feeds the text into the existing CLI loop as if the user had typed it. Keyboard input still works alongside voice.

## Architecture

```
Microphone (sounddevice) → raw PCM frames
    → VAD (Silero) detects speech start/end
    → accumulates frames into complete utterance
    → STT (Voxtral/Whisper) transcribes to text
    → text placed in queue
    → main loop picks up text as user input
```

All of this runs in a **background daemon thread** via `VoiceManager`. The main loop polls a `queue.Queue` for transcribed text.

## Files Created

### `src/voice/audio_io.py` — MicStream

```python
class MicStream:
    """Captures audio from default microphone via sounddevice."""

    def __init__(self, sample_rate=16000, frame_duration_ms=30):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)  # 480 samples at 16kHz/30ms
        self._queue = queue.Queue()

    def start(self):
        import sounddevice as sd
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_size,
            callback=self._callback,  # puts bytes into queue
        )
        self._stream.start()

    def read_frame(self, timeout=1.0) -> bytes | None:
        """Returns one frame of raw PCM int16 bytes, or None on timeout."""

    def stop(self):
        """Stops and closes the stream."""
```

Key details:
- 16kHz mono int16 — standard for speech processing
- 30ms frames (480 samples) — matches Silero VAD's expected input size
- `sounddevice.InputStream` runs its own callback thread, pushes frames into a `queue.Queue`
- `read_frame()` is called by the VoiceManager loop

### `src/voice/vad.py` — Voice Activity Detection (Silero)

```python
class VoiceActivityDetector:
    """Detects speech start/end using Silero VAD model."""

    def __init__(self, threshold=0.5, min_speech_ms=250, min_silence_ms=500, sample_rate=16000):
        import torch
        self._model, _ = torch.hub.load("snakers4/silero-vad", "silero_vad", trust_repo=True)
        # Converts min_speech_ms/min_silence_ms to sample counts

    def process_frame(self, frame_bytes: bytes) -> tuple[bool, bytes | None]:
        """Feed one audio frame. Returns (is_speaking, complete_utterance_or_None)."""
```

**How the state machine works:**

1. Each frame gets a speech probability from Silero (0.0-1.0)
2. If `prob >= threshold`: increment `speech_counter`, reset `silence_counter`
3. When `speech_counter >= min_speech_samples`: mark `is_speaking = True`, start buffering
4. While speaking: accumulate all frame bytes into `speech_buffer`
5. When silence frames accumulate past `min_silence_samples`: speech ended
6. Return the complete utterance bytes, reset state, call `model.reset_states()`

**Important**: Silero VAD is stateful (uses internal RNN state). Call `model.reset_states()` after each utterance.

Dependencies:
- `torch` (CPU version is fine: `pip install torch --index-url https://download.pytorch.org/whl/cpu`)
- Silero model downloaded from torch hub on first use (~2MB, cached at `~/.cache/torch/hub/`)

### `src/voice/stt.py` — Speech-to-Text Providers

```python
class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str: ...
```

**Three providers:**

| Provider | Class | Package | Notes |
|----------|-------|---------|-------|
| **Voxtral Mini** (recommended) | `VoxtralSTTProvider` | `mistralai` | Via Mistral API. Uses existing `MISTRAL_API_KEY`. Wraps raw PCM in WAV before sending. `client.audio.transcriptions.complete(model="voxtral-mini-latest", file={...})`. Beats Whisper large-v3 accuracy. |
| **Whisper Local** | `WhisperLocalSTTProvider` | `openai-whisper` | Loads model on init (`whisper.load_model("base")`). Converts int16→float32, calls `model.transcribe()`. Heavy (~1GB for base model). |
| **OpenAI Whisper API** | `OpenAIWhisperSTTProvider` | `openai` | Cloud API. Wraps PCM in WAV, sends via `client.audio.transcriptions.create(model="whisper-1", file=buf)`. |

**Factory:**
```python
def create_stt(config: dict) -> STTProvider:
    # config keys: provider ("voxtral"|"whisper_local"|"openai"), model_size ("base"), model ("voxtral-mini-latest")
```

**Audio format note**: All providers receive raw PCM int16 mono bytes. Voxtral and OpenAI APIs need WAV format, so the providers wrap the bytes in a WAV header using Python's `wave` module before sending.

### `src/voice/manager.py` — VoiceManager Orchestrator

```python
class VoiceManager:
    """Orchestrates mic → VAD → STT in a background thread."""

    def __init__(self, config: dict):
        voice_cfg = config.get("voice", {})
        self.mic = MicStream(sample_rate=..., frame_duration_ms=...)
        self.vad = VoiceActivityDetector(threshold=..., min_speech_ms=..., min_silence_ms=...)
        self.stt = create_stt(voice_cfg.get("stt", {}))
        self.tts = create_tts(voice_cfg.get("tts", {}))
        configure_speak(self.tts, self.audio_player)  # Wire up speak tool
        self.text_queue = queue.Queue()

    def start(self):
        """Start mic + background processing thread."""
        self.mic.start()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        """Background: read frames → VAD → STT → put text in queue."""
        while self._running:
            frame = self.mic.read_frame(timeout=0.5)
            if frame is None: continue
            is_speaking, utterance = self.vad.process_frame(frame)
            if utterance is not None:
                text = self.stt.transcribe(utterance, self.mic.sample_rate)
                if text and text.strip():
                    print(f"\n[Voice] Heard: {text}")
                    self.text_queue.put(text.strip())

    def get_text(self, timeout=0.1) -> str | None:
        """Non-blocking check for transcribed text. Called by main loop."""

    def stop(self):
        """Stop mic, reset VAD, disconnect speak tool."""
```

The manager also initializes TTS and wires up the `speak` tool via `configure_speak()`, so both input and output are managed together.

### `src/voice/__init__.py`

```python
from src.voice.manager import VoiceManager
from src.voice.audio_io import AudioPlayer
from src.voice.tts import create_tts
from src.voice.stt import create_stt
```

## Config (`config.yaml`)

```yaml
voice:
  sample_rate: 16000          # Mic capture rate (Hz)

  vad:
    threshold: 0.5            # Speech probability threshold (0.0-1.0)
    min_speech_ms: 250        # Min speech duration to trigger capture
    min_silence_ms: 500       # Silence duration to end utterance

  stt:
    provider: "voxtral"       # "voxtral" | "whisper_local" | "openai"
    model_size: "base"        # For whisper_local only
```

## Integration in `mirascope_cli.py`

### `/voice` Command Handler

```python
if user_input.lower().strip() == "/voice":
    if not voice_active:
        try:
            from src.voice.manager import VoiceManager  # Lazy import
            voice_manager = VoiceManager(config)
            voice_manager.start()
            voice_active = True
        except ImportError as e:
            print(f"[Voice] Missing dependencies: {e}")
        except Exception as e:
            print(f"[Voice] Failed to start: {e}")
    else:
        voice_manager.stop()
        voice_manager = None
        voice_active = False
    continue
```

### Dual Input Loop (keyboard + voice)

When voice is active, the main loop must listen to both keyboard and mic simultaneously. Since `multiline_input()` blocks, we run it in a background thread:

```python
if voice_active and voice_manager:
    import threading, queue

    input_q = queue.Queue()

    def kb_input():
        try:
            text = multiline_input("> ")
            input_q.put(("kb", text))
        except (EOFError, KeyboardInterrupt):
            input_q.put(("kb_exit", ""))

    kb_thread = threading.Thread(target=kb_input, daemon=True)
    kb_thread.start()

    user_input = None
    while user_input is None:
        # Check voice queue (50ms poll)
        voice_text = voice_manager.get_text(timeout=0.05)
        if voice_text:
            user_input = voice_text
            break
        # Check keyboard queue (50ms poll)
        try:
            kind, text = input_q.get(timeout=0.05)
            if kind == "kb_exit":
                voice_manager.stop()
                return
            user_input = text
        except queue.Empty:
            pass
else:
    user_input = multiline_input("> ")  # Normal blocking input
```

Whichever fires first (voice or keyboard) becomes the user input. The other is discarded (keyboard thread is daemon, dies with main).

### Voice Context Injection

Before each LLM call when voice is active, inject a transient message:

```python
if voice_active:
    messages.append(llm.messages.user(
        "[System: Voice mode is active. The user may be speaking via microphone. "
        "Use the 'speak' tool to respond verbally when appropriate. Keep spoken "
        "responses concise and conversational (1-3 sentences). You can still use "
        "text output for code, file contents, etc. Speech plays in the background.]"
    ))
```

## Dependencies

```
sounddevice>=0.4.6     # Mic capture (requires libportaudio2)
numpy>=1.24            # Audio array conversion
torch                  # Silero VAD runtime (CPU version OK)
mistralai>=1.0         # Voxtral Mini STT (recommended)
# openai-whisper       # Alternative: local Whisper STT
# openai               # Alternative: OpenAI Whisper API
```

**System packages (WSL2):**
```bash
sudo apt-get install -y libportaudio2 portaudio19-dev libasound2-plugins pulseaudio-utils
```

## WSL2 Audio Setup

See [voice_output.md](voice_output.md) § "WSL2 Audio Issues Encountered" for the full list of fixes needed:
1. Install PortAudio + ALSA plugins
2. Fix conda libstdc++ conflict
3. Create `~/.asoundrc` for ALSA→PulseAudio routing
4. Set `PULSE_SERVER=unix:/mnt/wslg/PulseServer`

## Thread Model Summary

```
Main Thread          : CLI loop, polls voice_manager.text_queue + keyboard queue
                       Runs LLM streaming, handles tool calls

MicStream Thread     : sounddevice callback, pushes PCM frames to mic queue
                       (managed by sounddevice internally)

VoiceManager Thread  : Daemon. Reads mic frames → VAD → STT → text_queue
                       (src/voice/manager.py _loop)

AudioPlayer Thread(s): Daemon. One per speak() call, plays TTS audio via sd.play()
                       (src/voice/audio_io.py play_audio/play_numpy)

Keyboard Thread      : Daemon. Runs multiline_input() when voice active
                       (created in main loop, one per input cycle)
```

All inter-thread communication uses `queue.Queue` (thread-safe). No shared mutable state.
