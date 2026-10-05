# Erzähltes Sims – Familie Weidauer

Ein kleines Familienexperiment mit Python, Ollama und Piper: Eine lokale KI erzählt einen ganz normalen Schulmorgen der Familie Weidauer als fortlaufende, leicht überdrehte Familien-Sitcom.

Die Figuren handeln auf Basis ihrer Eigenschaften, der Morgen schreitet von 06:00 bis ungefähr 07:30 Uhr voran und wörtliche Rede wird mit unterschiedlichen Piper-Stimmen vorgelesen.

## Die Figuren

- **Johanna** – hält morgens den Laden zusammen, macht Vesper, weckt liebevoll und wird verständlicherweise nervös, wenn niemand aufstehen will.
- **Ray** – gibt sein Bestes aufzustehen, stellt keinen Wecker und vertraut dem Dao sowie gelegentlich Johanna.
- **Lotta** – Klasse 4, sehr lustig, manchmal mit etwas zu langem Atem bei Gags gegenüber Jasper.
- **Jasper** – Klasse 1, noch nicht ganz mit dem frühen Rhythmus versöhnt, braucht morgens Hilfe und entdeckt gern kurz vor dem Losgehen noch Hunger.
- **Helena** – Klasse 9, ordentlich, hilfsbereit und selbstständig; weil sie später losmuss, bleibt sie morgens gern noch etwas länger in ihrem Zimmer.

## Der Morgen

Die KI orientiert sich an diesen festen Punkten:

- 06:00 – Wecker klingelt, Schlummern
- 06:30 – Eltern aufstehen, Vesper machen
- 06:45 – Lotta und Jasper erstmals wecken
- 07:00 – spätestens aufstehen, Zähne putzen, essen
- 07:20 – angepeilte Losgehzeit, sichtbar auf der Uhr markiert
- 07:30 – tatsächliches Losgehen

## Ohne Ollama testen

```bash
python main.py --mock
```

Der Mock-Modus erzählt bereits einen beispielhaften Weidauer-Morgen.

Mit Debug-Ausgabe:

```bash
python main.py --mock --debug
```

## Mit Ollama

```bash
ollama pull qwen2.5:3b
python main.py
```

Die KI bekommt bei jeder Szene den aktuellen Familienzustand und die Morgenregeln und schreibt die Geschichte ein Stück weiter.

## Piper-Stimmen

Die Sprachausgabe erkennt Dialoge wie:

```text
Johanna: „Aufstehen.“
Jasper: „Mama soll mich wecken.“
Ray: „Das Dao hat keinen Wecker.“
```

und ordnet jedem Namen eine Stimme zu.

Konfigurierbare Variablen:

```bash
PIPER_NARRATOR_VOICE="voices/de_DE-thorsten-medium.onnx" \
PIPER_JOHANNA_VOICE="voices/johanna.onnx" \
PIPER_RAY_VOICE="voices/ray.onnx" \
PIPER_LOTTA_VOICE="voices/lotta.onnx" \
PIPER_JASPER_VOICE="voices/jasper.onnx" \
PIPER_HELENA_VOICE="voices/helena.onnx" \
python main.py
```

Wenn keine eigenen Modelle angegeben sind, verwenden zunächst alle die Standardstimme.

## Ziel

Nicht perfekte Simulation, sondern möglichst schnell etwas, bei dem die Familie beim Zuhören sagt: **„Ja. Genau so ist es morgens bei uns.“**
