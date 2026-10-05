# Erzähltes Sims

Ein kleines Python-Experiment: Figuren leben in einer einfachen Welt, treffen mit Hilfe einer **lokalen KI über Ollama** Entscheidungen, und die Simulation wird als fortlaufende Geschichte erzählt und vorgelesen.

Es wird kein OpenAI-API-Key benötigt und die KI läuft lokal auf dem eigenen Rechner.

## V0

- zwei Figuren
- drei Orte
- Hunger, Energie und Stimmung
- kurze Szenen mit wörtlicher Rede
- Enter = nächste Szene
- optionale Sprachausgabe
- Weltzustand bleibt in Python

## 1. Ollama installieren

Ollama installieren und anschließend ein kleines Modell laden:

```bash
ollama pull qwen2.5:3b
```

Zum Testen:

```bash
ollama run qwen2.5:3b
```

Wenn das funktioniert, kann der Chat mit `/bye` wieder beendet werden.

## 2. Erzähltes Sims starten

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Das Programm spricht Ollama lokal unter `http://localhost:11434` an.

Ein anderes installiertes Modell kann so verwendet werden:

```bash
OLLAMA_MODEL="qwen2.5:7b" python main.py
```

## Sprachausgabe

Die Sprachausgabe verwendet `pyttsx3`. Unter Linux wird dafür normalerweise eine lokale Speech-Engine wie eSpeak/eSpeak-NG benötigt.

Falls keine Sprach-Engine verfügbar ist, läuft die Geschichte trotzdem als Text weiter.

## Idee

V0 ist absichtlich klein. Erst wenn sie Spaß macht, kommen Erinnerungen, Beziehungen, Gegenstände, mehr Weltregeln oder verschiedene Stimmen dazu.
