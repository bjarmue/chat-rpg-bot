# ✍️ Story schreiben — Anleitung

Die ganze Geschichte lebt in `data/story/` — **eine JSON-Datei pro Tür** (`door_01.json` bis `door_24.json`). Du kannst sie mit jedem Texteditor bearbeiten. Tür 1 ist fertig ausgeschrieben, Türen 2–24 sind Entwürfe mit Gliederung (alles mit `✍️ TODO` markiert, braucht dich).

## Aufbau einer Tür

```json
{
  "door": 3,
  "title": "Der Titel des Kapitels",
  "morning": {
    "text": "Der morgendliche Story-Abschnitt (2–4 Absätze). \n\n Erzeugt neue Zeilen.",
    "choices": [
      {
        "key": "a",
        "label": "Kurzlabel für den Button (max. ~80 Zeichen)",
        "emoji": "🔥",
        "text": "Was dem Spieler nach seiner Wahl passiert (privat, nur für ihn)",
        "xp": 20,
        "loot": ["heiltrank"]
      }
    ]
  },
  "afternoon": { "type": "..." }
}
```

Regeln:

- `key` muss innerhalb der Liste eindeutig sein — **nachträglich nicht ändern**, sonst werden alte Entscheidungen nicht mehr erkannt.
- `label` = Button-Text, `emoji` optional.
- `text` = private Auflösung für den Spieler.
- `xp` = Belohnung, `loot` = Liste von Item-**Keys** (siehe unten).

## Nachmittags-Abenteuer (drei Typen)

### ⚔️ Kampf

```json
"afternoon": {
  "type": "fight",
  "name": "Name des Gegners",
  "intro": "2–3 Sätze Dramatik vor dem Kampf.",
  "hp": 120, "atk": 9, "def": 2,
  "loot": ["zinnpanzer"],
  "xp": 45
}
```

Alle, die mitkämpfen, bekommen Loot + XP. Richtwerte: Tür 4–8 `hp 90–110`, Tür 10–16 `hp 110–140`, Tür 19–24 `hp 150–180`.

### 🧩 Rätsel

```json
"afternoon": {
  "type": "riddle",
  "question": "Szene + das Rätsel selbst.",
  "answer": "offizielle antwort (kleingeschrieben)",
  "alternatives": ["alternative schreibweise"],
  "xp": 40,
  "loot": ["heiltrank"],
  "flavor": "Satz bei richtiger Antwort."
}
```

Antworten werden groß-/kleinschreibungsunempfindlich exakt geprüft — deshalb mehrere `alternatives` angeben (z. B. mit und ohne Artikel).

### 🗳️ Gruppenentscheidung

```json
"afternoon": {
  "type": "interaction",
  "title": "Kurzer Titel",
  "question": "Die Situation, vor der die Gruppe steht.",
  "options": [
    { "key": "wald", "label": "Durch den Wald", "emoji": "🌲", "loot": ["plaetzchen"] }
  ],
  "outcomes": {
    "wald": "Was die Mehrheitsentscheidung bedeutet (wird am nächsten Morgen verkündet)."
  },
  "loot": ["plaetzchen"]
}
```

Alle Abstimmenden bekommen den Loot der gewählten Option.

## Item-Keys (aus `game_data.py`)

| Key | Item | Typ |
|---|---|---|
| `holzschwert` | Holzschwert (+2 Angriff) | Waffe |
| `lebkuchenklinge` | Lebkuchenklinge (+4 Angriff) | Waffe |
| `eiszapfenlanze` | Eiszapfenlanze (+6 Angriff) | Waffe |
| `sternenschwert` | Sternenschwert (+9 Angriff) | Waffe (legendär) |
| `wollmantel` | Wollmantel (+2 Schutz) | Rüstung |
| `zinnpanzer` | Zinnpanzer (+4 Schutz) | Rüstung |
| `polarfuchspelz` | Polarfuchspelz (+6 Schutz) | Rüstung |
| `glanzruestung` | Glanzrüstung (+9 Schutz) | Rüstung (legendär) |
| `plaetzchen` | Zimtplätzchen (+15 LP) | Verbrauch |
| `heiltrank` | Glühweintrank (+30 LP) | Verbrauch |
| `goldglocke` | Goldene Glocke | Trophäe |
| `kristallkugel` | Kristallkugel | Trophäe |
| `sternsplitter` | Sternsplitter | Trophäe (legendär) |

Neue Items? In `game_data.py` unter `ITEMS` ergänzen (Key, Name, Emoji, Typ, Werte, Beschreibung) — danach Bot neu starten.

## Grobe Kapitel-Gliederung (Entwurf)

1. **Die Nacht, in der der Stern erlosch** — Charaktererschaffung, Aufbruch
2. Der Flüsterwald · 3. Glühwürmchenlichtung (Rätsel) · 4. Der Bär mit dem Zimtgeruch (Kampf)
5. Die Lebkuchenhexe · 6. Das Eistormrätsel (Rätsel) · 7. Lawinenalarm (Kampf)
8. Die Bergschenke · 9. Brücke der gefrorenen Träume (Rätsel) · 10. Schneewolf-Rudel (Kampf)
11. Dorf der Schneewesen · 12. Der stille See (Rätsel) · 13. Der gestohlene Schlitten
14. Werkstatt im Schnee (Kampf) · 15. Lied der Nordlichter (Rätsel) · 16. Der Frostgolem (Kampf)
17. Über das Eismeer · 18. Fischerdörfer (Rätsel) · 19. Der Schneesturm (Kampf)
20. Die Eisburg des Zweifels · 21. Die Palastwachen (Kampf) · 22. Der Thronsaal (Rätsel)
23. Der Stern in der Eiskrone · 24. Heimkehr mit dem Stern (Finalkampf + Fest)

Die Gliederung ist nur ein Vorschlag — ändere Titel, Reihenfolge und Typen beliebig. Wichtig ist nur: **Tür 1 = Charaktererschaffung** (kein `choices`-Feld nötig), und die JSON-Dateien müssen gültig bleiben (z. B. auf [jsonlint.com](https://jsonlint.com) prüfen).

## Workflow-Vorschlag

1. Du schreibst (oder diktierst mir im Chat) einen Kapitel-Abschnitt + die Entscheidungsmöglichkeiten.
2. Datei speichern → Bot neu starten (`Strg+C`, dann `python bot.py`) — Story-Änderungen werden beim nächsten Post übernommen.
3. Am besten schreibst du 2–3 Kapitel im Voraus, dann kann nichts klemmen.
