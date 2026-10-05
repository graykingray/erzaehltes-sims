# Erzähltes Sims – Familie Weidauer

Eine lokale, erzählte Familien-Simulation mit Python, Ollama und Piper.

## Ablauf

Jeder Druck auf Enter erzeugt die **nächste** Phase desselben Morgens:

1. 06:05 – Wecker und Schlummern
2. 06:30 – Johanna und Ray machen Vesper
3. 06:45 – Lotta und Jasper werden geweckt
4. 07:00 – Aufstehen, Zähne, Anziehen, Frühstück
5. 07:10 – Helena taucht kurz auf und hilft
6. 07:20 – die markierte Losgehzeit ist erreicht
7. 07:30 – Johanna, Ray, Lotta und Jasper verlassen gemeinsam das Haus

Die vorige Szene wird der KI jeweils als Kontext mitgegeben, damit sie nicht einfach dieselben Dialoge wiederholt.

Rays Gelassenheit gehört zu seiner Figur, aber **„Dao“ ist kein Running Gag** und wird im Szenentext aktuell bewusst nicht verwendet.

## Standard-Stimmen

Wenn die empfohlenen Stimmen im Ordner `voices/` liegen, werden sie automatisch verwendet:

- Erzähler: `de_DE-thorsten-medium`
- Johanna: `de_DE-kerstin-low`
- Ray: `de_DE-thorsten_emotional-medium`
- Lotta: `de_DE-ramona-low`
- Jasper: `de_DE-karlsson-low`
- Helena: `de_DE-eva_k-x_low`

Start:

```bash
python main.py
```

Beim Start zeigt das Programm die tatsächlich verwendeten Voice-Dateien an.

Eigene Stimmen können weiterhin per Umgebungsvariable überschrieben werden, z. B.:

```bash
PIPER_RAY_VOICE="voices/andere-stimme.onnx" python main.py
```

## Modell

Standard ist:

```text
qwen3:4b-instruct
```

Falls nötig:

```bash
ollama pull qwen3:4b-instruct
```

Debug-Modus:

```bash
python main.py --debug
```

Mock-Modus ohne Ollama:

```bash
python main.py --mock
```
