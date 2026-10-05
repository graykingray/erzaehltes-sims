import json
import os
import urllib.error
import urllib.request

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

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


def speak(text: str) -> None:
    if pyttsx3 is None:
        return

    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass


def ask_ollama(prompt: str) -> dict:
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

    return json.loads(result["response"])


def next_scene() -> str:
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

    data = ask_ollama(prompt)
    world.clear()
    world.update(data["world"])
    return data["story"]


def main() -> None:
    print("Erzähltes Sims")
    print(f"Modell: {OLLAMA_MODEL}")
    print("Enter = nächste Szene | q = Ende")

    while True:
        command = input("\n> ").strip().lower()
        if command == "q":
            break

        story = next_scene()
        print("\n" + story)
        speak(story)


if __name__ == "__main__":
    main()
