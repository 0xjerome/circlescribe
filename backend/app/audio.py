from __future__ import annotations

import io
import os
import wave
from dataclasses import dataclass

import numpy as np

TARGET_SAMPLE_RATE = 16_000
DEFAULT_LOCAL_MODEL = "mlx-community/whisper-tiny"


class LocalTranscriptionUnavailable(RuntimeError):
    """Raised when the optional local MLX Whisper adapter is unavailable."""


class UnsupportedAudioError(ValueError):
    """Raised when the local demo receives an unsupported WAV payload."""


@dataclass(frozen=True)
class DecodedAudio:
    samples: np.ndarray
    sample_rate: int
    duration_seconds: float


def _resample_linear(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or samples.size == 0:
        return samples.astype(np.float32, copy=False)

    output_length = max(1, int(round(samples.size * target_rate / source_rate)))
    source_positions = np.linspace(0.0, 1.0, num=samples.size, endpoint=False)
    target_positions = np.linspace(0.0, 1.0, num=output_length, endpoint=False)
    return np.interp(target_positions, source_positions, samples).astype(np.float32)


def decode_wav_bytes(data: bytes, *, target_rate: int = TARGET_SAMPLE_RATE) -> DecodedAudio:
    """Decode uncompressed PCM WAV bytes to mono float32 audio.

    The browser recorder intentionally emits 16-bit PCM WAV so this local path
    can avoid requiring ffmpeg on the user's Mac. Production audio ingestion is
    handled by Amazon Transcribe once AWS access is restored.
    """

    if not data:
        raise UnsupportedAudioError("Audio file is empty.")

    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
    except (wave.Error, EOFError) as exc:
        raise UnsupportedAudioError("Local transcription currently accepts PCM WAV audio only.") from exc

    if channels not in {1, 2}:
        raise UnsupportedAudioError("Only mono or stereo WAV files are supported locally.")
    if sample_width != 2:
        raise UnsupportedAudioError("Local WAV input must use 16-bit PCM samples.")
    if sample_rate <= 0:
        raise UnsupportedAudioError("WAV sample rate is invalid.")

    pcm = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels == 2:
        if pcm.size % 2:
            pcm = pcm[:-1]
        pcm = pcm.reshape(-1, 2).mean(axis=1)

    duration = pcm.size / sample_rate if sample_rate else 0.0
    resampled = _resample_linear(pcm, sample_rate, target_rate)
    return DecodedAudio(samples=resampled, sample_rate=target_rate, duration_seconds=duration)


def transcribe_wav_bytes(data: bytes, *, model: str | None = None) -> tuple[str, str, float]:
    """Transcribe browser-recorded WAV audio using optional MLX Whisper.

    Returns (transcript, model_name, duration_seconds). Import is lazy so the
    main application and test suite do not require MLX Whisper unless the local
    microphone transcription feature is explicitly used.
    """

    decoded = decode_wav_bytes(data)
    model_name = model or os.getenv("CIRCLESCRIBE_LOCAL_WHISPER_MODEL", DEFAULT_LOCAL_MODEL)

    try:
        import mlx_whisper  # type: ignore
    except ImportError as exc:
        raise LocalTranscriptionUnavailable(
            "Local microphone transcription is optional. Install it with "
            "`uv pip install -e '.[audio]'` on Apple Silicon, then restart the API."
        ) from exc

    result = mlx_whisper.transcribe(
        decoded.samples,
        path_or_hf_repo=model_name,
        language="en",
        condition_on_previous_text=True,
        initial_prompt=(
            "Community savings group meeting transcript. Preserve spoken speaker labels "
            "when present, using Chair:, Amina:, John:, Mary:, or Sarah:."
        ),
    )
    transcript = str(result.get("text", "")).strip()
    if not transcript:
        raise LocalTranscriptionUnavailable("The local transcriber returned an empty transcript.")

    return transcript, model_name, decoded.duration_seconds
