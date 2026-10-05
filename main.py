import argparse
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
PIPER_JOHANNA_VOICE = os.getenv("PIPER_JOHANNA_VOICE", PIPER_VOICE)
PIPER_RAY_VOICE = os.getenv("PIPER_RAY_VOICE", PIPER_VOICE)
PIPER_LOTTA_VOICE = os.getenv("PIPER_LOTTA_VOICE", PIPER_VOICE)
PIPER_JASPER_VOICE = os.getenv("PIPER_JASPER_VOICE", PIPER_VOICE)
PIPER_HELENA_VOICE = os.getenv("PIPER_HELENA_VOICE", PIPER_VOICE)

VOICE_FILES = {
    "Erzähler": PIPER_NARRATOR_VOICE,
    "Johanna": PIPER_JOHANNA_VOICE,
    "Ray": PIPER_RAY_VOICE,
    "Lotta": PIPER_LOTTA_VOICE,
    "Jasper": PIPER_JASPER_VOICE,
    "Helena": PIPER_HELENA_VOICE,
}

world = {
    "family": "Weidauer",
    "time": "06:00",
    "goal": "Alle kommen möglichst liebevoll und halbwegs pünktlich durch den Morgen.",
    "morning_schedule": [
        "06:00 Wecker klingelt; Johanna drückt ihn meist noch ein paar Mal weiter.",
        "06:30 Eltern sollten aufstehen und Vesper machen.",
        "06:45 Lotta und Jasper werden zum ersten Mal geweckt.",
        "07:00 Spätestens aufstehen, Zähne putzen und etwas essen.",
        "07:20 Angepeilte Losgehzeit; diese Uhrzeit ist sichtbar markiert und wird oft erwähnt.",
        "07:30 Tatsächliches Losgehen."
    ],
    "places": [
        "Elternbett im Wohnzimmer",
        "Küche",
        "Bad",
        "Lottas Zimmer",
        "Jaspers Zimmer",
        "Helenas Zimmer",
        "Flur"
    ],
    "characters": {
        "Johanna": {
            "role": "Mama",
            "place": "Elternbett im Wohnzimmer",
            "state": "noch müde, aber verantwortlich",
            "personality": "liebevoll, organisiert, morgens die Einsatzleitung; wird genervt, wenn niemand aufstehen will",
            "morning_facts": "macht Vesper, weckt liebevoll, hilft beim Anziehen und hält den Zeitplan zusammen"
        },
        "Ray": {
            "role": "Papa",
            "place": "Lottas Zimmer",
            "state": "schläft",
            "personality": "gibt sein Bestes aufzustehen, stellt aber keinen Wecker und vertraut darauf, dass das Dao alles richten wird",
            "morning_facts": "landet nachts gelegentlich in Lottas Zimmer, wenn Lotta ins Elternbett im Wohnzimmer gewandert ist"
        },
        "Lotta": {
            "role": "Kind, Klasse 4",
            "place": "Elternbett im Wohnzimmer",
            "state": "schläft",
            "personality": "sehr lustig, macht gern Gags und übertreibt sie gegenüber Jasper manchmal",
            "morning_facts": "wacht nachts oft auf und kommt ins Wohnzimmer; kann morgens mit Quatsch für zusätzliche Dynamik sorgen"
        },
        "Jasper": {
            "role": "Kind, Klasse 1",
            "place": "Jaspers Zimmer",
            "state": "schläft",
            "personality": "noch nicht an den frühen Schulrhythmus gewöhnt, braucht Hilfe beim Anziehen",
            "morning_facts": "ist genervt, wenn Ray ihn weckt und wünscht sich dann Mama; ganz am Ende fällt ihm oft ein, dass er noch etwas essen will"
        },
        "Helena": {
            "role": "Kind, Klasse 9",
            "place": "Helenas Zimmer",
            "state": "schläft",
            "personality": "ordentlich, hilfsbereit, selbstständig",
            "morning_facts": "muss später los als die anderen und bleibt deshalb gern so lange wie möglich in ihrem Zimmer"
        }
    }
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


def _ollama_request(prompt: str) -> dict:
    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.7,
                "num_predict": 220,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Ollama ist nicht erreichbar. Läuft Ollama und ist das Modell installiert?"
        ) from exc


def _valid_scene(data: dict) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("story"), str)
        and len(data["story"].strip()) > 20
        and isinstance(data.get("time"), str)
        and isinstance(data.get("changes", {}), dict)
    )


def ask_ollama(prompt: str, debug: bool = False) -> dict:
    if debug:
        print("\n[DEBUG] Ollama-Aufruf")
        print(f"[DEBUG] Modell: {OLLAMA_MODEL}")
        print("[DEBUG] Prompt:")
        print(prompt)

    result = _ollama_request(prompt)

    if debug:
        print("[DEBUG] Rohantwort:")
        print(result.get("response", ""))

    try:
        data = json.loads(result["response"])
    except (KeyError, json.JSONDecodeError):
        data = {}

    if _valid_scene(data):
        return data

    if debug:
        print("[DEBUG] Antwort unbrauchbar – ein Reparaturversuch folgt.")

    repair_prompt = f"""
Die vorige Antwort war unvollständig.

Erzeuge JETZT eine vollständige kurze Szene.
Mindestens 3 Sätze, maximal 120 Wörter.
Keine Erklärung.

Antworte NUR als JSON:
{{
  "story": "vollständige Szene mit mindestens 3 Sätzen",
  "time": "HH:MM",
  "changes": {{}}
}}

Kontext:
{prompt}
"""

    result = _ollama_request(repair_prompt)

    if debug:
        print("[DEBUG] Reparatur-Rohantwort:")
        print(result.get("response", ""))

    try:
        data = json.loads(result["response"])
    except (KeyError, json.JSONDecodeError):
        data = {}

    if not _valid_scene(data):
        raise RuntimeError(
            "Ollama hat auch beim zweiten Versuch keine vollständige Szene geliefert."
        )

    return data


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
                "Um sechs Uhr klingelt der Wecker. Johanna öffnet ein Auge, findet das Geräusch unverschämt optimistisch "
                "und drückt auf Schlummern. Johanna: „Noch einmal.“ "
                "Im Elternbett liegt Lotta quer wie ein besonders zufriedener Seestern. Ray schläft derweil in Lottas Zimmer weiter, "
                "weil das Dao offenbar beschlossen hat, dass dort heute sein Platz ist."
            ),
            "time": "06:05",
        },
        {
            "story": (
                "Um halb sieben ist aus dem philosophischen Problem des Aufstehens ein logistisches geworden. "
                "Johanna steht in der Küche und beginnt Vesper zu machen. Johanna: „Ray?“ "
                "Aus Lottas Zimmer kommt nach einigen Sekunden ein müdes: Ray: „Ich bin praktisch schon unterwegs.“ "
                "Der Erzähler stellt fest, dass diese Aussage mit dem tatsächlichen Zustand der Bettdecke nur lose verbunden ist."
            ),
            "time": "06:32",
        },
        {
            "story": (
                "Kurz vor sieben startet die erste Weckrunde. Johanna weckt Lotta und Jasper freundlich. "
                "Lotta: „Ich bin wach!“ sagt Lotta mit geschlossenen Augen. "
                "Jasper zieht die Decke höher. Jasper: „Mama soll mich wecken.“ "
                "Ray, der gerade in der Tür steht, nickt verständnisvoll. Ray: „Das ist ein sehr klarer Wunsch.“"
            ),
            "time": "06:47",
        },
        {
            "story": (
                "Um sieben Uhr erreicht der Morgen seine betriebliche Kernphase: Zähne, Kleidung, Frühstück. "
                "Lotta erfindet beim Anziehen einen Witz über Jaspers Socken und führt ihn deutlich länger aus, als der Stoff trägt. "
                "Johanna: „Lotta. Einmal war lustig.“ "
                "Helena erscheint ordentlich angezogen im Flur, hilft kurz beim Suchen einer Brotdose und verschwindet danach wieder in ihr Zimmer."
            ),
            "time": "07:05",
        },
        {
            "story": (
                "Die große Uhr zeigt auf die markierte 7:20. Johanna deutet darauf wie eine Fluglotsin auf eine Landebahn. "
                "Johanna: „Da. Sieben Uhr zwanzig. Das ist unsere Zeit.“ "
                "Niemand bestreitet die Existenz der Markierung. Ihre praktische Bedeutung bleibt dennoch Gegenstand familieninterner Forschung."
            ),
            "time": "07:21",
        },
        {
            "story": (
                "Um halb acht stehen tatsächlich fast alle im Flur. Schuhe sind an, Taschen sind da, die Tür ist offen. "
                "Jasper bleibt plötzlich stehen. Jasper: „Ich wollte noch was essen.“ "
                "Für einen Moment sagt niemand etwas. Dann reicht Johanna ihm mit der Ruhe einer erfahrenen Einsatzleiterin etwas für unterwegs. "
                "Die Familie Weidauer verlässt das Haus. Der Morgen gilt offiziell als erfolgreich."
            ),
            "time": "07:30",
        },
    ]
    scene = mock_scenes[mock_step % len(mock_scenes)]
    mock_step += 1

    return {
        "story": scene["story"],
        "time": scene["time"],
        "changes": {},
    }


def compact_world_context() -> dict:
    return {
        "time": world["time"],
        "characters": {
            name: {
                "place": data["place"],
                "state": data["state"],
            }
            for name, data in world["characters"].items()
        },
    }


def apply_scene_update(data: dict) -> None:
    world["time"] = data.get("time", world["time"])

    for name, changes in data.get("changes", {}).items():
        if name in world["characters"]:
            world["characters"][name].update(changes)


def next_scene(mock: bool = False, debug: bool = False) -> str:
    context = compact_world_context()

    prompt = f"""
Du erzählst eine kurze humoristische Szene aus einem Schulmorgen der Familie Weidauer.

AKTUELL:
{json.dumps(context, ensure_ascii=False)}

FIGUREN:
Johanna: Mama, liebevoll und organisiert, morgens Einsatzleitung; macht Vesper, weckt und hilft beim Anziehen.
Ray: Papa, bemüht sich aufzustehen, stellt keinen Wecker und vertraut gern dem Dao.
Lotta: Klasse 4, sehr lustig, übertreibt Gags gegenüber Jasper manchmal.
Jasper: Klasse 1, morgens müde, braucht Hilfe beim Anziehen, will lieber von Mama geweckt werden; kurz vor Schluss oft noch hungrig.
Helena: Klasse 9, ordentlich, hilfsbereit, selbstständig; muss später los und bleibt gern länger im Zimmer.

ZEITPLAN:
06:00 Wecker und Schlummern.
06:30 Eltern aufstehen und Vesper machen.
06:45 Lotta und Jasper erstmals wecken.
07:00 Aufstehen, Zähne, Essen.
07:20 angepeilte Losgehzeit, sichtbar auf der Uhr markiert.
07:30 tatsächliches Losgehen.

REGELN:
- Erzeuge genau EINE kurze Szene, maximal etwa 120 Wörter.
- Humorvoll, warmherzig, alltagsnah, niemanden bloßstellen.
- Zeit muss vorwärts laufen und höchstens 07:30 sein.
- Wörtliche Rede immer: Name: „Satz“
- Gib nur Änderungen zurück, nicht den ganzen Weltzustand.
- Änderungen dürfen nur place und state enthalten.

Antworte ausschließlich als JSON:
{{
  "story": "Szene",
  "time": "HH:MM",
  "changes": {{
    "Name": {{"place": "...", "state": "..."}}
  }}
}}
"""

    if mock:
        data = mock_ollama(prompt, debug=debug)
    else:
        data = ask_ollama(prompt, debug=debug)

    apply_scene_update(data)

    if debug:
        print("[DEBUG] Änderungen:")
        print(json.dumps(data.get("changes", {}), ensure_ascii=False, indent=2))
        print("[DEBUG] Zeit:", world["time"])

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
