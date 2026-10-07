import argparse
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import wave

from piper import PiperVoice


AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")
OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
PIPER_VOICE = os.getenv("PIPER_VOICE", "voices/de_DE-thorsten-medium.onnx")
PIPER_NARRATOR_VOICE = os.getenv(
    "PIPER_NARRATOR_VOICE", "voices/de_DE-thorsten-medium.onnx"
)
PIPER_JOHANNA_VOICE = os.getenv(
    "PIPER_JOHANNA_VOICE", "voices/de_DE-kerstin-low.onnx"
)
PIPER_RAY_VOICE = os.getenv(
    "PIPER_RAY_VOICE", "voices/de_DE-thorsten_emotional-medium.onnx"
)
PIPER_LOTTA_VOICE = os.getenv(
    "PIPER_LOTTA_VOICE", "voices/de_DE-ramona-low.onnx"
)
PIPER_JASPER_VOICE = os.getenv(
    "PIPER_JASPER_VOICE", "voices/de_DE-karlsson-low.onnx"
)
PIPER_HELENA_VOICE = os.getenv(
    "PIPER_HELENA_VOICE", "voices/de_DE-eva_k-x_low.onnx"
)

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
            "personality": "gibt sein Bestes aufzustehen, stellt aber keinen Wecker; ist morgens gelassen und vertraut darauf, dass sich die Dinge irgendwie fügen",
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


MORNING_PHASES = [
    {
        "time": "06:05",
        "actors": ["Johanna", "Lotta", "Ray"],
        "task": "Der Wecker klingelt zum ersten Mal. Johanna drückt auf Schlummern. Lotta liegt quer im Elternbett im Wohnzimmer. Ray schläft in Lottas Zimmer.",
        "facts": "Johanna ist noch liebevoll verschlafen. Ray wacht nicht von selbst auf. Niemand steht schon auf."
    },
    {
        "time": "06:30",
        "actors": ["Johanna", "Ray"],
        "task": "Jetzt sollten Johanna und Ray aufstehen und in der Küche Vesper für die Kinder machen.",
        "facts": "Johanna kommt eher in Gang. Ray braucht einen kleinen Schubs und bleibt dabei auffallend gelassen. Das Wort Dao soll in dieser Szene nicht vorkommen."
    },
    {
        "time": "06:45",
        "actors": ["Johanna", "Lotta", "Jasper"],
        "task": "Johanna weckt Lotta und Jasper zum ersten Mal liebevoll.",
        "facts": "Lotta reagiert gern mit einem Witz. Jasper ist sehr müde und möchte am liebsten von Mama geweckt werden."
    },
    {
        "time": "07:00",
        "actors": ["Johanna", "Lotta", "Jasper", "Ray"],
        "task": "Jetzt müssen Lotta und Jasper wirklich aufstehen, Zähne putzen, sich anziehen und etwas essen.",
        "facts": "Jasper braucht Hilfe beim Anziehen. Lotta macht gern Quatsch. Johanna wird langsam ungeduldig, bleibt aber liebevoll. Ray hilft, wo er kann."
    },
    {
        "time": "07:10",
        "actors": ["Helena", "Johanna"],
        "task": "Helena taucht kurz auf. Sie ist ordentlich, schon recht selbstständig und hilft bei einer Kleinigkeit, bevor sie wieder in ihr Zimmer verschwindet.",
        "facts": "Helena muss später los als die anderen und hat deshalb keinen Grund zur Hektik."
    },
    {
        "time": "07:20",
        "actors": ["Johanna", "Ray", "Lotta", "Jasper"],
        "task": "Die markierte 07:20 auf der Uhr ist erreicht. Eigentlich sollten jetzt alle losgehen, aber natürlich fehlt noch irgendetwas.",
        "facts": "Johanna verweist auf die deutlich markierte Uhrzeit. Der Humor entsteht daraus, dass diese Markierung seit langem bekannt ist und trotzdem niemand wirklich fertig ist."
    },
    {
        "time": "07:30",
        "actors": ["Johanna", "Ray", "Lotta", "Jasper"],
        "task": "Jetzt gehen Johanna, Ray, Lotta und Jasper tatsächlich gemeinsam aus dem Haus. Unmittelbar vorher fällt Jasper ein, dass er noch etwas essen möchte.",
        "facts": "Johanna findet eine pragmatische Lösung für Jaspers Hunger. Helena bleibt zurück, weil sie später losmuss. Die Szene MUSS damit enden, dass Johanna, Ray, Lotta und Jasper die Wohnung verlassen und die Haustür hinter ihnen zufällt."
    },
]
phase_index = 0
story_history = []

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


def tts_text(text: str) -> str:
    # Piper/phonemizer tends to lengthen the "o" in Lotta. A doubled
    # consonant is not always interpreted as German vowel shortening, so
    # use a pronunciation-only spelling. The visible story stays unchanged.
    return re.sub(r"\\bLotta\\b", "Lotta", text)


def speak_part(speaker: str, text: str) -> None:
    text = tts_text(text.strip())
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


def _loading_indicator(stop_event: threading.Event) -> None:
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    started = time.monotonic()
    index = 0

    while not stop_event.wait(0.1):
        elapsed = time.monotonic() - started
        print(
            f"\r{frames[index % len(frames)]} KI schreibt Szene … {elapsed:4.1f}s",
            end="",
            flush=True,
        )
        index += 1

    elapsed = time.monotonic() - started
    print(f"\r✓ KI-Szene fertig ({elapsed:.1f}s)          ")


def _ollama_request(prompt: str) -> str:
    # /no_think ist zusätzlich zu think=False gesetzt. Damit funktioniert
    # Qwen3 auch mit Ollama-Versionen, die den API-Schalter nicht sauber
    # in das Qwen-Chat-Template übernehmen.
    user_prompt = prompt.rstrip() + "\n\n/no_think"

    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Du bist Autor einer deutschen Familienkomödie. "
                        "Antworte ausschließlich auf Deutsch. "
                        "Gib nur die fertige Szene aus, niemals Analyse, Planung "
                        "oder Erklärungen. /no_think"
                    ),
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 220,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    stop_event = threading.Event()
    loader = threading.Thread(
        target=_loading_indicator,
        args=(stop_event,),
        daemon=True,
    )
    loader.start()

    try:
        with urllib.request.urlopen(request) as response:
            result = json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Ollama ist nicht erreichbar. Läuft Ollama und ist das Modell installiert?"
        ) from exc
    finally:
        stop_event.set()
        loader.join()

    message = result.get("message", {})
    content = message.get("content", "").strip()

    # Manche ältere Kombinationen aus Ollama/Qwen können Thinking trotzdem
    # als <think>-Block ausgeben. Diesen zeigen wir nicht als Spieltext.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    return content


def _openai_request(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY fehlt. Beispiel: export OPENAI_API_KEY='sk-...'"
        )

    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "instructions": (
                "Du bist Autor einer warmherzigen deutschen Familienkomödie. "
                "Antworte ausschließlich auf Deutsch und gib nur die fertige Szene aus."
            ),
            "input": prompt,
            "reasoning": {
                "effort": "none",
            },
            "max_output_tokens": 300,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    stop_event = threading.Event()
    loader = threading.Thread(
        target=_loading_indicator,
        args=(stop_event,),
        daemon=True,
    )
    loader.start()

    try:
        with urllib.request.urlopen(request) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI API Fehler {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit("OpenAI API ist nicht erreichbar.") from exc
    finally:
        stop_event.set()
        loader.join()

    texts = []

    # Manche Responses enthalten den aggregierten Text direkt.
    if isinstance(result.get("output_text"), str):
        texts.append(result["output_text"])

    # Fallback: normale Output-Items durchsuchen.
    for item in result.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))

    story = "\n".join(text for text in texts if text).strip()

    if not story:
        status = result.get("status")
        incomplete = result.get("incomplete_details")
        output_types = [item.get("type") for item in result.get("output", [])]
        raise RuntimeError(
            "OpenAI lieferte keinen Text. "
            f"status={status!r}, incomplete_details={incomplete!r}, "
            f"output_types={output_types!r}"
        )

    return story


def ask_openai(prompt: str, debug: bool = False) -> str:
    if debug:
        print("\n[DEBUG] OpenAI-Aufruf")
        print(f"[DEBUG] Modell: {OPENAI_MODEL}")
        print("[DEBUG] Prompt:")
        print(prompt)

    story = _openai_request(prompt)

    if debug:
        print("[DEBUG] Rohantwort:")
        print(story)

    if len(story) < 30:
        raise RuntimeError(
            f"OpenAI hat keine brauchbare Szene geliefert. Rohantwort: {story!r}"
        )

    return story


def ask_ollama(prompt: str, debug: bool = False) -> str:
    if debug:
        print("\n[DEBUG] Ollama-Aufruf")
        print(f"[DEBUG] Modell: {OLLAMA_MODEL}")
        print("[DEBUG] Prompt:")
        print(prompt)

    story = _ollama_request(prompt)

    if debug:
        print("[DEBUG] Rohantwort:")
        print(story)

    if len(story) < 30:
        raise RuntimeError(
            f"Ollama hat keine brauchbare Szene geliefert. Rohantwort: {story!r}"
        )

    english_markers = [" the ", " and ", " is ", " are ", " with ", " morning ", " says "]
    lowered = f" {story.lower()} "
    if sum(marker in lowered for marker in english_markers) >= 2:
        retry_prompt = (
            "Schreibe dieselbe Art Szene, aber AUSSCHLIESSLICH AUF DEUTSCH. "
            "Kein Englisch. Natürliches deutsches Familiengespräch.\n\n" + prompt
        )
        story = _ollama_request(retry_prompt)

    return story


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
    global phase_index

    if phase_index >= len(MORNING_PHASES):
        return (
            "Der Morgen ist geschafft. Johanna, Ray, Lotta und Jasper sind aus dem Haus. "
            "Helena hat noch etwas Zeit, bevor sie selbst losmuss."
        )

    phase = MORNING_PHASES[phase_index]
    world["time"] = phase["time"]

    active_characters = "\n".join(
        f"- {name}: {world['characters'][name]['personality']}"
        for name in phase["actors"]
    )

    previous = story_history[-1] if story_history else "Noch keine vorherige Szene."

    prompt = f"""
Schreibe die NÄCHSTE kurze Szene aus dem Morgen der Familie Weidauer.

Bisherige letzte Szene:
{previous}

Neue Uhrzeit: {phase["time"]}

Nur diese Personen dürfen aktiv handeln oder sprechen:
{active_characters}

Was in DIESER neuen Szene passieren MUSS:
{phase["task"]}

Zusätzliche Fakten:
{phase["facts"]}

Regeln:
- Schreibe ausschließlich auf Deutsch.
- Schreibe eine NEUE Szene. Wiederhole keine Dialoge, Gags oder Handlungen aus der vorherigen Szene.
- 3 bis 5 kurze Sätze.
- Liebevoller, trockener Familienhumor.
- Erfinde keine Handlung außerhalb der beschriebenen Situation.
- Niemand spricht über sich selbst in der dritten Person.
- Niemand nennt sich selbst beim eigenen Namen.
- Kinder sprechen kindgerecht, Erwachsene normal.
- Maximal zwei kurze direkte Reden.
- Antworte als JSON-Objekt mit genau zwei Feldern: "story" und "parts".
- "story" enthält die natürlich lesbare fertige Szene mit wörtlicher Rede.
- "parts" ist eine Liste in Vorlesereihenfolge. Jeder Eintrag hat genau "speaker" und "text".
- "speaker" ist ausschließlich einer von: Erzähler, Johanna, Ray, Lotta, Jasper, Helena.
- Erzähler-Text und direkte Rede müssen in getrennten parts stehen. Bei direkter Rede MUSS speaker die tatsächlich sprechende Person sein.
- Beispiel: {"story":"Johanna öffnet die Tür. „Guten Morgen“, sagt sie.","parts":[{"speaker":"Erzähler","text":"Johanna öffnet die Tür."},{"speaker":"Johanna","text":"Guten Morgen."}]}

- Das Wort „Dao“ NICHT verwenden. Rays Gelassenheit darf nur indirekt spürbar sein.
- Keine Überschrift, keine Uhrzeit, keine Erklärung.
- Schreibe nur die fertige Szene.
"""

    if mock:
        data = mock_ollama(prompt, debug=debug)
        story = data["story"]
    elif AI_PROVIDER == "openai":
        story = ask_openai(prompt, debug=debug)
    elif AI_PROVIDER == "ollama":
        story = ask_ollama(prompt, debug=debug)
    else:
        raise SystemExit(
            f"Unbekannter AI_PROVIDER: {AI_PROVIDER!r}. Erlaubt: ollama, openai"
        )

    parts = None
    if not mock:
        raw = story.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", raw, flags=re.IGNORECASE)
        try:
            structured = json.loads(raw)
            if isinstance(structured, dict) and isinstance(structured.get("story"), str):
                story = structured["story"].strip()
                candidate_parts = structured.get("parts")
                if isinstance(candidate_parts, list):
                    valid_speakers = {"Erzähler", *world["characters"].keys()}
                    parts = [
                        {"speaker": p["speaker"], "text": p["text"].strip()}
                        for p in candidate_parts
                        if isinstance(p, dict)
                        and p.get("speaker") in valid_speakers
                        and isinstance(p.get("text"), str)
                        and p["text"].strip()
                    ]
        except json.JSONDecodeError:
            pass

    story_history.append(story)
    phase_index += 1

    if debug:
        print(f"[DEBUG] Phase {phase_index}/{len(MORNING_PHASES)}")
        print(f"[DEBUG] Zeit: {world['time']}")
        print(f"[DEBUG] Aktive Figuren: {', '.join(phase['actors'])}")

    return story


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
    print(f"KI-Provider: {AI_PROVIDER}")
    if AI_PROVIDER == "openai":
        print(f"Modell: {OPENAI_MODEL}")
    else:
        print(f"Modell: {OLLAMA_MODEL}")
    print("Piper-Stimmen:")
    for speaker, voice_file in VOICE_FILES.items():
        print(f"  {speaker}: {voice_file}")

    if args.mock:
        print("Modus: MOCK (kein Ollama nötig)")
    elif args.debug:
        print(f"Modus: {AI_PROVIDER} + Debug")

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
