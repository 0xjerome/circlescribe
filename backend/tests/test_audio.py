import io
import math
import struct
import unittest
import wave

from app.audio import UnsupportedAudioError, decode_wav_bytes


def wav_bytes(*, sample_rate: int = 48_000, seconds: float = 0.05, channels: int = 1) -> bytes:
    frame_count = int(sample_rate * seconds)
    samples = [int(12_000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(frame_count)]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for sample in samples:
            for _ in range(channels):
                frames.extend(struct.pack("<h", sample))
        wav.writeframes(bytes(frames))
    return payload.getvalue()


class AudioTests(unittest.TestCase):
    def test_browser_wav_is_resampled_to_whisper_rate(self):
        decoded = decode_wav_bytes(wav_bytes(sample_rate=48_000, seconds=0.10))

        self.assertEqual(decoded.sample_rate, 16_000)
        self.assertAlmostEqual(decoded.duration_seconds, 0.10, places=2)
        self.assertGreater(decoded.samples.size, 1_500)
        self.assertLess(decoded.samples.size, 1_700)

    def test_stereo_is_downmixed(self):
        decoded = decode_wav_bytes(wav_bytes(channels=2))
        self.assertEqual(decoded.samples.ndim, 1)
        self.assertEqual(decoded.sample_rate, 16_000)

    def test_non_wav_payload_is_rejected(self):
        with self.assertRaises(UnsupportedAudioError):
            decode_wav_bytes(b"not a wav file")


if __name__ == "__main__":
    unittest.main()
