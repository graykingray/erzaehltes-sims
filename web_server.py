import json
import os
import re
import sqlite3
import uuid
import wave
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import main as game

ROOT = Path(__file__).parent
DATA_DIR, AUDIO_DIR = ROOT / "data", ROOT / "data" / "audio"
DB_PATH = DATA_DIR / "scenes.sqlite3"
DATA_DIR.mkdir(exist_ok=True); AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Erzähltes Sims")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="web-static")

PHASE_VISUALS = [
 {"background":"elternbett","base":[("Johanna","lying","bed-left"),("Lotta","lying","bed-right")],"note":"Ray schläft in Lottas Zimmer"},
 {"background":"kueche_gesamt","base":[("Johanna","standing","left"),("Ray","standing","right")]},
 {"background":"jasper_zimmer","base":[("Johanna","standing","left"),("Jasper","lying","bed-right")],"note":"Lotta wird ebenfalls geweckt"},
 {"background":"bad","base":[("Jasper","standing","left"),("Lotta","standing","right")]},
 {"background":"kueche_wandregal","base":[("Helena","standing","left"),("Johanna","standing","right")]},
 {"background":"kueche_gesamt","base":[("Johanna","standing","far-left"),("Ray","standing","left"),("Lotta","standing","right"),("Jasper","standing","far-right")]},
 {"background":"kueche_gesamt","base":[("Johanna","standing","far-left"),("Ray","standing","left"),("Lotta","standing","right"),("Jasper","standing","far-right")]},
]

POSITIONS = ["far-left", "left", "right", "far-right"]

def scene_characters(index, speech):
    visual = PHASE_VISUALS[index]
    chars = [{"name": n, "pose": p, "position": pos} for n,p,pos in visual["base"]]
    visible = {c["name"] for c in chars}
    speakers = [p["speaker"] for p in speech if p["speaker"] != "Erzähler"]
    for speaker in speakers:
        if speaker not in visible:
            chars.append({"name":speaker,"pose":"standing","position":POSITIONS[len(chars) % len(POSITIONS)]})
            visible.add(speaker)
    return chars


def connect_db(): return sqlite3.connect(DB_PATH)
def init_db():
    with connect_db() as db:
        db.execute("CREATE TABLE IF NOT EXISTS scenes (phase_index INTEGER PRIMARY KEY, scene_json TEXT NOT NULL)")
def load_cache():
    with connect_db() as db:
        rows=db.execute("SELECT phase_index,scene_json FROM scenes ORDER BY phase_index").fetchall()
    return [json.loads(x) for _,x in rows]
def save_scene(scene):
    with connect_db() as db:
        db.execute("""INSERT INTO scenes(phase_index,scene_json) VALUES(?,?)
          ON CONFLICT(phase_index) DO UPDATE SET scene_json=excluded.scene_json""",
          (scene["index"],json.dumps(scene,ensure_ascii=False)))

def split_structured_speech(story):
    names=["Johanna","Ray","Lotta","Jasper","Helena"]; nr="|".join(names)
    pattern=re.compile(rf'(?:(?P<prefix>{nr})\s*:\s*)?„(?P<quote>[^“]+)“(?P<suffix>\s*,?\s*(?:sagte|fragte|rief|meinte|antwortete|murmelte)\s+(?P<suffix_name>{nr}))?',re.I)
    parts=[]; cursor=0
    for m in pattern.finditer(story):
        before=story[cursor:m.start()].strip()
        if before: parts.append({"speaker":"Erzähler","text":before})
        parts.append({"speaker":m.group("prefix") or m.group("suffix_name") or "Erzähler","text":m.group("quote").strip()})
        cursor=m.end()
    after=story[cursor:].strip()
    if after: parts.append({"speaker":"Erzähler","text":after})
    return parts or [{"speaker":"Erzähler","text":story.strip()}]

def create_audio(story, parts=None):
    result=[]
    for part in (parts or split_structured_speech(story)):
        speaker,text=part["speaker"],part["text"]
        spoken_text=game.tts_text(text)
        voice=game.load_piper_voice(game.VOICE_FILES.get(speaker,game.PIPER_NARRATOR_VOICE))
        if voice is None: continue
        filename=f"{uuid.uuid4().hex}.wav"
        with wave.open(str(AUDIO_DIR/filename),"wb") as wav_file: voice.synthesize_wav(spoken_text,wav_file,syn_config=game.SynthesisConfig(length_scale=game.PIPER_LENGTH_SCALE))
        result.append({"speaker":speaker,"text":text,"audio":f"/audio/{filename}"})
    return result

init_db(); scene_cache=load_cache()
for scene in scene_cache:
    if scene.get("speech_format") != 4:
        scene["speech"]=create_audio(scene["story"])
        scene["speech_format"]=4
        if scene["index"] < len(PHASE_VISUALS):
            visual=PHASE_VISUALS[scene["index"]]
            scene["background"]=visual["background"]
            scene["characters"]=scene_characters(scene["index"],scene["speech"])
            scene["note"]=visual.get("note")
        save_scene(scene)
if scene_cache:
    game.phase_index=len(scene_cache)
    game.story_history[:]=[s["story"] for s in scene_cache]

def generate_scene(index):
    result=game.next_scene(mock=os.getenv("SIMS_MOCK")=="1")
    if isinstance(result, dict):
        story=result["story"]
        parts=result.get("parts")
    else:
        story=result
        parts=None
    visual=PHASE_VISUALS[index]
    speech=create_audio(story,parts)
    return {"index":index,"number":index+1,"time":game.world["time"],"story":story,
            "background":visual["background"],"characters":scene_characters(index,speech),
            "note":visual.get("note"),"speech":speech,"speech_format":4}

@app.get("/api/scenes/{number}")
def get_scene(number:int):
    index=number-1
    if index < 0: raise HTTPException(404,"Diese Szene gibt es nicht.")
    if index < len(scene_cache): return scene_cache[index]
    if index != len(scene_cache): raise HTTPException(404,"Diese Szene wurde noch nicht erzeugt.")
    if game.phase_index >= len(game.MORNING_PHASES): raise HTTPException(409,"Der Morgen ist bereits zu Ende.")
    scene=generate_scene(index); scene_cache.append(scene); save_scene(scene); return scene

@app.post("/api/scenes/{number}/regenerate")
def regenerate(number: int):
    index = number - 1
    if index < 0 or index >= len(scene_cache):
        raise HTTPException(404, "Diese Szene gibt es nicht.")

    # Later scenes depend on this story version, so discard them.
    with connect_db() as db:
        db.execute("DELETE FROM scenes WHERE phase_index > ?", (index,))
    del scene_cache[index + 1:]

    game.phase_index = index
    if len(game.story_history) > index:
        del game.story_history[index:]

    scene = generate_scene(index)
    scene_cache[index] = scene
    save_scene(scene)
    return scene

@app.get("/")
def root(): return FileResponse(ROOT/"web"/"index.html")
@app.get("/scene/{number}")
def scene_page(number:int): return FileResponse(ROOT/"web"/"index.html")
