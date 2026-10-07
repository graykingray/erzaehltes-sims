"""Generate a small set of narrator samples from the multi-speaker German MLS Piper voice."""

from pathlib import Path
import wave

from piper import PiperVoice, SynthesisConfig

MODEL = Path("voices/de_DE-mls-medium.onnx")
OUT = Path("data/voice_samples")
TEXT = "Lotta und Helena sind schon wach. Jasper sucht noch seine Schuhe."
SPEAKERS = [0, 1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 75, 100, 150, 200, 235]


def main():
    if not MODEL.exists():
        raise SystemExit(f"Stimme fehlt: {MODEL}")

    OUT.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(str(MODEL))

    for speaker_id in SPEAKERS:
        target = OUT / f"mls-{speaker_id:03d}.wav"
        print(f"Erzeuge {target}")
        with wave.open(str(target), "wb") as wav_file:
            voice.synthesize_wav(
                TEXT,
                wav_file,
                syn_config=SynthesisConfig(speaker_id=speaker_id, length_scale=0.78),
            )

    print(f"\nFertig: {OUT}/")


if __name__ == "__main__":
    main()
