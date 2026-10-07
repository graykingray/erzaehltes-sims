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
 {"background":"elternbett","characters":[{"name":"Johanna","pose":"lying","position":"bed-left"},{"name":"Lotta","pose":"lying","position":"bed-right"}],"note":"Ray schläft in Lottas Zimmer"},
 {"background":"kueche_gesamt","characters":[{"name":"Johanna","pose":"standing","position":"left"},{"name":"Ray","pose":"standing","position":"right"}]},
 {"background":"jasper_zimmer","characters":[{"name":"Johanna","pose":"standing","position":"left"},{"name":"Jasper","pose":"lying","position":"bed-right"}],"note":"Lotta wird ebenfalls geweckt"},
]

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

def create_audio(story):
    result=[]
    for part in split_structured_speech(story):
        speaker,text=part["speaker"],part["text"]
        voice=game.load_piper_voice(game.VOICE_FILES.get(speaker,game.PIPER_NARRATOR_VOICE))
        if voice is None: continue
        filename=f"{uuid.uuid4().hex}.wav"
        with wave.open(str(AUDIO_DIR/filename),"wb") as wav_file: voice.synthesize_wav(text,wav_file)
        result.append({"speaker":speaker,"text":text,"audio":f"/audio/{filename}"})
    return result

init_db(); scene_cache=load_cache()
for scene in scene_cache:
    if scene.get("speech_format") != 2:
        scene["speech"]=create_audio(scene["story"]); scene["speech_format"]=2; save_scene(scene)
if scene_cache:
    game.phase_index=len(scene_cache)
    game.story_history[:]=[s["story"] for s in scene_cache]

def generate_scene(index):
    story=game.next_scene(mock=os.getenv("SIMS_MOCK")=="1")
    visual=PHASE_VISUALS[min(index,len(PHASE_VISUALS)-1)]
    return {"index":index,"number":index+1,"time":game.world["time"],"story":story,**visual,
            "speech":create_audio(story),"speech_format":2}

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
