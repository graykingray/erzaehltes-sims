import os
import tempfile
import uuid
import wave
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import main as game


ROOT = Path(__file__).parent
AUDIO_DIR = Path(tempfile.gettempdir()) / "erzaehltes-sims-audio"
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Erzähltes Sims")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
PHASE_VISUALS = [
    {
        "background": "elternbett",
        "characters": [
            {"name": "Johanna", "pose": "lying", "position": "bed-left"},
            {"name": "Lotta", "pose": "lying", "position": "bed-right"},
        ],
        "note": "Ray schläft in Lottas Zimmer",
    },
    {
        "background": "kueche_gesamt",
        "characters": [
            {"name": "Johanna", "pose": "standing", "position": "left"},
            {"name": "Ray", "pose": "standing", "position": "right"},
        ],
    },
    {
        "background": "jasper_zimmer",
        "characters": [
            {"name": "Johanna", "pose": "standing", "position": "left"},
            {"name": "Jasper", "pose": "lying", "position": "bed-right"},
        ],
        "note": "Lotta wird ebenfalls geweckt",
    },
]


def create_audio(story: str):
    result = []
    for speaker, text in game.split_story_by_speaker(story):
        voice_file = game.VOICE_FILES.get(speaker, game.PIPER_NARRATOR_VOICE)
        voice = game.load_piper_voice(voice_file)
        if voice is None:
            continue

        filename = f"{uuid.uuid4().hex}.wav"
        path = AUDIO_DIR / filename
        with wave.open(str(path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        result.append({
            "speaker": speaker,
            "text": text,
            "audio": f"/audio/{filename}",
        })
    return result


@app.post("/api/next-scene")
def next_scene():
    phase_before = game.phase_index
    story = game.next_scene(mock=os.getenv("SIMS_MOCK") == "1")
    visual = PHASE_VISUALS[min(phase_before, len(PHASE_VISUALS) - 1)]

    return {
        "time": game.world["time"],
        "story": story,
        **visual,
        "speech": create_audio(story),
    }


# Catch-all static web app must be mounted last, otherwise it intercepts /api POST requests.
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
