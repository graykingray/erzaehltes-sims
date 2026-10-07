"""Generate narrator samples from the German single-speaker Piper voices already in the project."""

from pathlib import Path
import wave

from piper import PiperVoice, SynthesisConfig

OUT = Path("data/voice_samples")
TEXT = "Lotta und Helena sind schon wach. Jasper sucht noch seine Schuhe."
VOICES = {
    "thorsten": "voices/de_DE-thorsten-medium.onnx",
    "kerstin": "voices/de_DE-kerstin-low.onnx",
    "ramona": "voices/de_DE-ramona-low.onnx",
    "karlsson": "voices/de_DE-karlsson-low.onnx",
    "eva": "voices/de_DE-eva_k-x_low.onnx",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    for name, model in VOICES.items():
        model_path = Path(model)
        if not model_path.exists():
            print(f"Überspringe {name}: {model_path} fehlt")
            continue

        target = OUT / f"{name}.wav"
        print(f"Erzeuge {target}")
        voice = PiperVoice.load(str(model_path))
        with wave.open(str(target), "wb") as wav_file:
            voice.synthesize_wav(
                TEXT,
                wav_file,
                syn_config=SynthesisConfig(length_scale=1.0),
            )

    print(f"\nFertig: {OUT}/")


if __name__ == "__main__":
    main()
