import argparse
import copy
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import wave

from piper import PiperVoice


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
PIPER_VOICE = os.getenv("PIPER_VOICE", "voices/de_DE-thorsten-medium.onnx")
PIPER_NARRATOR_VOICE = os.getenv("PIPER_NARRATOR_VOICE", PIPER_VOICE)
PIPER_MIA_VOICE = os.getenv("PIPER_MIA_VOICE", PIPER_VOICE)
PIPER_LEO_VOICE = os.getenv("PIPER_LEO_VOICE", PIPER_VOICE)

VOICE_FILES = {
    "Erzähler": PIPER_NARRATOR_VOICE,
    "Mia": PIPER_MIA_VOICE,
    "Leo": PIPER_LEO_VOICE,
}

world = {
    "time": "08:00",
    "places": ["Küche", "Wohnzimmer", "Garten"],
    "characters": {
        "Mia": {
            "place": "Küche",
            "hunger": 65,
            "energy": 80,
            "mood": "gut",
            "personality": "neugierig, frech, hilfsbereit",
        },
        "Leo": {
            "place": "Wohnzimmer",
            "hunger": 35,
            "energy": 55,
            "mood": "müde",
            "personality": "ruhig, lustig, etwas stur",
        },
    },
}

mock_step = 0
piper_voices = {}


def load_piper_voice(voice_file: str):
    if voice_file in piper_voices:
        return piper_voices[voice_file]

    if not os.path.exists(voice_file):
        print(f"[TTS] Piper-Stimme nicht gefunden: {voice_file}")
        return None

    try:
        voice = PiperVoice.load(voice_file)
        piper_voices[voice_file] = voice
        return voice
    except Exception as exc:
        print(f"[TTS] Piper konnte {voice_file} nicht laden: {exc}")
        return None


def speak_part(speaker: str, text: str) -> None:
    text = text.strip()
    if not text:
        return

    voice_file = VOICE_FILES.get(speaker, PIPER_NARRATOR_VOICE)
    voice = load_piper_voice(voice_file)
    if voice is None:
        return

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            with wave.open(tmp.name, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)

            subprocess.run(["aplay", "-q", tmp.name], check=False)
    except FileNotFoundError:
        print("[TTS] 'aplay' wurde nicht gefunden. Unter Arch: sudo pacman -S alsa-utils")
    except Exception as exc:
        print(f"[TTS] Sprachausgabe fehlgeschlagen: {exc}")


def split_story_by_speaker(text: str):
    names = "|".join(re.escape(name) for name in world["characters"])
    pattern = re.compile(rf'\b({names}):\s*[„"](.+?)[“"]')

    position = 0
    parts = []

    for match in pattern.finditer(text):
        narrator = text[position:match.start()].strip()
        if narrator:
            parts.append(("Erzähler", narrator))

        parts.append((match.group(1), match.group(2).strip()))
        position = match.end()

    narrator = text[position:].strip()
    if narrator:
        parts.append(("Erzähler", narrator))

    return parts


def speak(text: str, debug: bool = False) -> None:
    for speaker, part in split_story_by_speaker(text):
        if debug:
            print(f"[TTS DEBUG] {speaker} -> {VOICE_FILES.get(speaker, PIPER_NARRATOR_VOICE)}")
            print(f"[TTS DEBUG] Text: {part}")
        speak_part(speaker, part)


def ask_ollama(prompt: str, debug: bool = False) -> dict:
    if debug:
        print("\n[DEBUG] Ollama-Aufruf")
        print(f"[DEBUG] Modell: {OLLAMA_MODEL}")
        print("[DEBUG] Prompt:")
        print(prompt)

    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Ollama ist nicht erreichbar. Läuft Ollama und ist das Modell installiert?"
        ) from exc

    if debug:
        print("[DEBUG] Ollama-Antwort erhalten")

    return json.loads(result["response"])


def mock_ollama(prompt: str, debug: bool = False) -> dict:
    global mock_step

    if debug:
        print("\n[DEBUG] Ollama-Aufruf wäre jetzt erfolgt")
        print(f"[DEBUG] Modell: {OLLAMA_MODEL}")
        print("[DEBUG] Prompt:")
        print(prompt)

    mock_scenes = [
        {
            "story": (
                "Mia schaut sich in der Küche um und entdeckt einen Apfel. "
                "Mia: „Den esse ich jetzt.“ "
                "Sie setzt sich an den Tisch und beginnt zu essen."
            ),
            "changes": {
                "Mia": {"hunger": 45, "place": "Küche", "mood": "gut"},
            },
            "time": "08:10",
        },
        {
            "story": (
                "Leo kommt langsam aus dem Wohnzimmer in die Küche. "
                "Leo: „Was machst du?“ "
                "Mia grinst. Mia: „Frühstück.“"
            ),
            "changes": {
                "Leo": {"place": "Küche", "energy": 50, "mood": "neugierig"},
            },
            "time": "08:15",
        },
        {
            "story": (
                "Mia steht auf und schaut durch die Gartentür. "
                "Mia: „Komm, wir gehen raus.“ "
                "Leo überlegt kurz und folgt ihr in den Garten."
            ),
            "changes": {
                "Mia": {"place": "Garten", "energy": 75},
                "Leo": {"place": "Garten", "energy": 45, "mood": "gut"},
            },
            "time": "08:25",
        },
    ]

    scene = mock_scenes[mock_step % len(mock_scenes)]
    mock_step += 1

    for name, changes in scene["changes"].items():
        world["characters"][name].update(changes)
    world["time"] = scene["time"]

    return {"story": scene["story"], "world": copy.deepcopy(world)}


def next_scene(mock: bool = False, debug: bool = False) -> str:
    prompt = f"""
Du leitest eine sehr kleine Sims-artige Simulation für Kinder.

Hier ist der aktuelle Weltzustand:
{json.dumps(world, ensure_ascii=False, indent=2)}

Erzeuge genau EINE kurze Szene.

Regeln:
- Die Figuren handeln selbstständig.
- Schreibe lebendig, aber kurz.
- Wörtliche Rede immer mit Namen, z. B. Mia: „Hallo!“
- Keine gefährlichen, gruseligen oder erwachsenen Inhalte.
- Verändere nur Dinge, die plausibel aus der Szene folgen.
- Hunger und Energie liegen immer zwischen 0 und 100.
- Gib den vollständigen neuen Weltzustand zurück.

Antworte ausschließlich als JSON:
{{
  "story": "Die erzählte Szene",
  "world": {{ ... kompletter aktualisierter Weltzustand ... }}
}}
"""

    if mock:
        data = mock_ollama(prompt, debug=debug)
    else:
        data = ask_ollama(prompt, debug=debug)

    world.clear()
    world.update(data["world"])

    if debug:
        print("[DEBUG] Neuer Weltzustand:")
        print(json.dumps(world, ensure_ascii=False, indent=2))

    return data["story"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Ohne Ollama mit festen Test-Szenen laufen.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Zeigt Ollama-Aufrufe, Prompt und Weltzustand.",
    )
    parser.add_argument(
        "--no-speech",
        action="store_true",
        help="Sprachausgabe deaktivieren.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("Erzähltes Sims")
    print(f"Modell: {OLLAMA_MODEL}")
    print("Piper-Stimmen:")
    for speaker, voice_file in VOICE_FILES.items():
        print(f"  {speaker}: {voice_file}")

    if args.mock:
        print("Modus: MOCK (kein Ollama nötig)")
    elif args.debug:
        print("Modus: Ollama + Debug")

    print("Enter = nächste Szene | q = Ende")

    while True:
        command = input("\n> ").strip().lower()
        if command == "q":
            break

        story = next_scene(mock=args.mock, debug=args.debug)
        print("\n" + story)

        if not args.no_speech:
            speak(story, debug=args.debug)


if __name__ == "__main__":
    main()
