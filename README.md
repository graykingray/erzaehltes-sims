# Erzähltes Sims

Ein kleines Python-Experiment: Figuren leben in einer einfachen Welt, treffen mit Hilfe einer **lokalen KI über Ollama** Entscheidungen, und die Simulation wird als fortlaufende Geschichte erzählt und mit **Piper TTS** vorgelesen.

Es wird kein OpenAI-API-Key benötigt. Ollama und Piper laufen lokal.

## V0

- zwei Figuren
- drei Orte
- Hunger, Energie und Stimmung
- kurze Szenen mit wörtlicher Rede
- Enter = nächste Szene
- lokale Sprachausgabe mit Piper
- **eigene Stimme für Erzähler, Mia und Leo**
- Weltzustand bleibt in Python
- Mock- und Debug-Modus zum Testen ohne Ollama

## Sofort testen – ohne Ollama

```bash
python main.py --mock
```

Mit Debug-Ausgabe:

```bash
python main.py --mock --debug
```

Ohne Sprachausgabe:

```bash
python main.py --mock --debug --no-speech
```

## Python-Umgebung

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Piper-Stimme herunterladen

Für den ersten Test reicht eine einzige deutsche Stimme:

```bash
mkdir -p voices
python -m piper.download_voices --data-dir voices de_DE-thorsten-medium
```

Danach sollten dort mindestens diese Dateien liegen:

```text
voices/de_DE-thorsten-medium.onnx
voices/de_DE-thorsten-medium.onnx.json
```

Standardmäßig verwenden Erzähler, Mia und Leo zunächst alle diese Stimme.

## Unterschiedliche Stimmen für die Figuren

Die Stimmen können getrennt über Umgebungsvariablen gesetzt werden:

```bash
PIPER_NARRATOR_VOICE="voices/erzaehler.onnx" \
PIPER_MIA_VOICE="voices/mia.onnx" \
PIPER_LEO_VOICE="voices/leo.onnx" \
python main.py --mock
```

Die Dateinamen sind nur Beispiele. Verwende dort tatsächlich heruntergeladene Piper-`.onnx`-Modelle.

Verfügbare Piper-Stimmen anzeigen:

```bash
python -m piper.download_voices
```

Das Programm erkennt wörtliche Rede im Format

```text
Mia: „Hallo!“
Leo: „Kommst du mit?“
```

und spricht sie mit der jeweiligen Figurenstimme. Alles andere übernimmt die Erzählerstimme.

Geladene Stimmen bleiben während des Programmlaufs im Speicher, damit sie nicht bei jedem Satz neu geladen werden.

## Audio unter Arch Linux

Zum Abspielen der von Piper erzeugten WAV-Dateien verwendet das Projekt `aplay`:

```bash
sudo pacman -S alsa-utils
```

## Ollama

Modell laden:

```bash
ollama pull qwen2.5:3b
```

Dann:

```bash
python main.py
```

Mit Debug-Ausgabe:

```bash
python main.py --debug
```

Ein anderes Ollama-Modell:

```bash
OLLAMA_MODEL="qwen2.5:7b" python main.py
```

## Idee

V0 ist absichtlich klein. Wenn sie Spaß macht, können später Erinnerungen, Beziehungen, Gegenstände und weitere Figuren dazukommen.
