# Erzähltes Sims

Ein kleines Python-Experiment: Figuren leben in einer einfachen Welt, treffen mit Hilfe einer KI Entscheidungen, und die Simulation wird als fortlaufende Geschichte erzählt und vorgelesen.

## V0

- zwei Figuren
- drei Orte
- Hunger, Energie und Stimmung
- kurze Szenen mit wörtlicher Rede
- Enter = nächste Szene
- optionale Sprachausgabe
- Weltzustand bleibt in Python

## Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
python main.py
```

Wenn keine lokale Sprach-Engine verfügbar ist, läuft die Geschichte einfach ohne Vorlesen weiter.

## Idee

V0 ist absichtlich klein. Erst wenn sie Spaß macht, kommen Erinnerungen, Beziehungen, Gegenstände, mehr Weltregeln oder verschiedene Stimmen dazu.
