import json
import os

from openai import OpenAI

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


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


def next_scene(client: OpenAI) -> str:
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
- Gib am Ende den neuen Zustand als JSON zurück.

Antworte ausschließlich in diesem JSON-Format:
{{
  "story": "Die erzählte Szene",
  "world": {{ ... kompletter aktualisierter Weltzustand ... }}
}}
"""

    response = client.responses.create(
        model="gpt-5.6-mini",
        input=prompt,
    )

    data = json.loads(response.output_text)
    world.clear()
    world.update(data["world"])
    return data["story"]


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Bitte OPENAI_API_KEY setzen.")

    client = OpenAI()

    print("Erzähltes Sims")
    print("Enter = nächste Szene | q = Ende")

    while True:
        command = input("\n> ").strip().lower()
        if command == "q":
            break

        story = next_scene(client)
        print("\n" + story)
        speak(story)


if __name__ == "__main__":
    main()
