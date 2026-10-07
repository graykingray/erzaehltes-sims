import json
import os
import re
import sqlite3
import uuid
import wave
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import main as game


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "scenes.sqlite3"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Erzähltes Sims")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

PHASE_VISUALS = [
    {"background":"elternbett","characters":[{"name":"Johanna","pose":"lying","position":"bed-left"},{"name":"Lotta","pose":"lying","position":"bed-right"}],"note":"Ray schläft in Lottas Zimmer"},
    {"background":"kueche_gesamt","characters":[{"name":"Johanna","pose":"standing","position":"left"},{"name":"Ray","pose":"standing","position":"right"}]},
    {"background":"jasper_zimmer","characters":[{"name":"Johanna","pose":"standing","position":"left"},{"name":"Jasper","pose":"lying","position":"bed-right"}],"note":"Lotta wird ebenfalls geweckt"},
]


def connect_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                phase_index INTEGER PRIMARY KEY,
                scene_json TEXT NOT NULL
            )
        """)


def load_cache():
    with connect_db() as db:
        rows = db.execute("SELECT phase_index, scene_json FROM scenes ORDER BY phase_index").fetchall()
    return [json.loads(scene_json) for _, scene_json in rows]


def save_scene(scene):
    with connect_db() as db:
        db.execute(
            """INSERT INTO scenes (phase_index, scene_json) VALUES (?, ?)
               ON CONFLICT(phase_index) DO UPDATE SET scene_json = excluded.scene_json""",
            (scene["index"], json.dumps(scene, ensure_ascii=False)),
        )


def split_structured_speech(story: str):
    names = ["Johanna", "Ray", "Lotta", "Jasper", "Helena"]
    names_re = "|".join(names)
    pattern = re.compile(
        rf'(?:(?P<prefix>{names_re})\s*:\s*)?'
        rf'„(?P<quote>[^“]+)“'
        rf'(?P<suffix>\s*,?\s*(?:sagte|fragte|rief|meinte|antwortete|murmelte)\s+'
        rf'(?P<suffix_name>{names_re}))?',
        re.IGNORECASE,
    )
    parts, cursor = [], 0
    for match in pattern.finditer(story):
        before = story[cursor:match.start()].strip()
        if before:
            parts.append({"speaker": "Erzähler", "text": before})
        speaker = match.group("prefix") or match.group("suffix_name") or "Erzähler"
        parts.append({"speaker": speaker, "text": match.group("quote").strip()})
        cursor = match.end()
    after = story[cursor:].strip()
    if after:
        parts.append({"speaker": "Erzähler", "text": after})
    return parts or [{"speaker": "Erzähler", "text": story.strip()}]


def create_audio(story: str):
    result = []
    for part in split_structured_speech(story):
        speaker, text = part["speaker"], part["text"]
        voice_file = game.VOICE_FILES.get(speaker, game.PIPER_NARRATOR_VOICE)
        voice = game.load_piper_voice(voice_file)
        if voice is None:
            continue
        filename = f"{uuid.uuid4().hex}.wav"
        path = AUDIO_DIR / filename
        with wave.open(str(path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        result.append({"speaker": speaker, "text": text, "audio": f"/audio/{filename}"})
    return result


init_db()
scene_cache = load_cache()
current_scene = -1

# Rebuild old cached speech once with the improved speaker detection.
for cached_scene in scene_cache:
    if cached_scene.get("speech_format") != 2:
        cached_scene["speech"] = create_audio(cached_scene["story"])
        cached_scene["speech_format"] = 2
        save_scene(cached_scene)

if scene_cache:
    game.phase_index = len(scene_cache)
    game.story_history[:] = [scene["story"] for scene in scene_cache]


def generate_scene(phase_index: int):
    story = game.next_scene(mock=os.getenv("SIMS_MOCK") == "1")
    visual = PHASE_VISUALS[min(phase_index, len(PHASE_VISUALS) - 1)]
    return {
        "index": phase_index,
        "time": game.world["time"],
        "story": story,
        **visual,
        "speech": create_audio(story),
        "speech_format": 2,
    }


@app.post("/api/next-scene")
def next_scene():
    global current_scene
    target = current_scene + 1
    if target < len(scene_cache):
        current_scene = target
        return scene_cache[current_scene]
    if game.phase_index >= len(game.MORNING_PHASES):
        raise HTTPException(409, "Der Morgen ist bereits zu Ende.")
    scene = generate_scene(game.phase_index)
    scene_cache.append(scene)
    save_scene(scene)
    current_scene = len(scene_cache) - 1
    return scene


@app.post("/api/previous-scene")
def previous_scene():
    global current_scene
    if current_scene <= 0:
        raise HTTPException(409, "Das ist bereits die erste Szene.")
    current_scene -= 1
    return scene_cache[current_scene]


@app.post("/api/replay-scene")
def replay_scene():
    if current_scene < 0:
        raise HTTPException(409, "Noch keine Szene vorhanden.")
    return scene_cache[current_scene]


@app.post("/api/regenerate-scene")
def regenerate_scene():
    global current_scene
    if current_scene < 0:
        raise HTTPException(409, "Noch keine Szene vorhanden.")
    if current_scene != len(scene_cache) - 1:
        raise HTTPException(409, "Nur die zuletzt erzeugte Szene kann neu erzählt werden.")
    phase = scene_cache[current_scene]["index"]
    game.phase_index = phase
    if len(game.story_history) > phase:
        del game.story_history[phase:]
    scene = generate_scene(phase)
    scene_cache[current_scene] = scene
    save_scene(scene)
    return scene


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
