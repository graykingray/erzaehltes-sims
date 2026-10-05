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
- Weltzustand bleibt in Python
- Mock- und Debug-Modus zum Testen ohne Ollama

## Sofort testen – ohne Ollama

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

Piper braucht ein Sprachmodell. Für Deutsch verwenden wir zunächst `de_DE-thorsten-medium`.

```bash
mkdir -p voices
python -m piper.download_voices --data-dir voices de_DE-thorsten-medium
```

Danach sollten dort mindestens diese Dateien liegen:

```text
voices/de_DE-thorsten-medium.onnx
voices/de_DE-thorsten-medium.onnx.json
```

Das Programm lädt die Stimme beim ersten Vorlesen und behält sie anschließend im Speicher.

Eine andere Stimme kann über eine Umgebungsvariable gewählt werden:

```bash
PIPER_VOICE="voices/meine-stimme.onnx" python main.py --mock
```

Die Liste verfügbarer Stimmen erhältst du mit:

```bash
python -m piper.download_voices
```

Piper bietet auch deutsche Stimmen; `de_DE-thorsten-medium` ist ein guter neutraler Start. Die Voice-Dateien bestehen aus einer `.onnx`-Datei plus passender `.onnx.json`-Datei.

## Audio unter Arch Linux

Zum Abspielen der von Piper erzeugten WAV-Datei verwendet das Projekt `aplay`:

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

V0 ist absichtlich klein. Wenn sie Spaß macht, können später Erinnerungen, Beziehungen, Gegenstände und vor allem unterschiedliche Piper-Stimmen für Erzähler, Mia und Leo dazukommen.
