# 🎄 Die 24 Türen von Frosthaven — Advents-RPG Discord-Bot

Ein Discord-Bot für ein gemeinsames Weihnachts-Fantasy-RPG im Advent: Jeden Tag öffnet sich eine Tür mit einem Story-Kapitel (morgens) und einem Abenteuer (nachmittags) — Kampf, Rätsel oder Gruppenentscheidung.

## Features

- **Tür 1 — Charaktererschaffung**: 5 Rassen (Mensch, Elf, Zwerg, Wichtel, Schneewesen) und 4 Klassen (Krieger, Magier, Waldläufer, Kleriker) mit individuellen Werten und Spezialfähigkeit
- **Morgens (~9 Uhr)**: Story-Abschnitt des Tages, jeder entscheidet individuell per Buttons → persönliche Folgen + Loot
- **Nachmittags (~15 Uhr)**: rotierend
  - ⚔️ **Gruppenkampf** gegen einen Boss (Angriff / Fähigkeit / Block, 5 Aktionen pro Held)
  - 🧩 **Rätsel** (Bonus für die schnellste richtige Antwort)
  - 🗳️ **Gruppenentscheidung** (Mehrheit entscheidet, Ergebnis am nächsten Morgen)
- **XP & Level**: Level erhöhen maximale LP und Werte (`/profil`, `/bestenliste`)
- **Inventar & Tauschen**: `/inventar`, `/ausruesten`, `/benutzen`, `/tauschen`
- **Fair für jede Gruppengröße**: Boss-HP skaliert automatisch mit der Zahl der Helden (Solo ≈ 35 %, 3 Spieler = 100 %, große Gruppen bis 250 %). Kämpfe bleiben über Tage bestehen — jeden Morgen füllt der Bot LP und Aktionen auf. **Das Happy End ist also garantiert erreichbar**, egal wie groß die Gruppe ist.
- **Story frei editierbar**: Ein Kapitel pro Datei in `data/story/` — siehe [STORY-SCHREIBEN.md](STORY-SCHREIBEN.md)

## Einrichtung

### 1. Discord-Bot erstellen

1. Öffne das [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → Name vergeben (z. B. „Frosthaven“).
2. Links auf **Bot** → **Reset Token** → Token kopieren (nicht weitergeben!).
3. Auf derselben Seite unter **Privileged Gateway Intents** aktivieren:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
4. Links auf **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Bot-Permissions: `Send Messages`, `Embed Links`, `Read Message History`, `Use External Emojis`
5. Die generierte URL öffnen und den Bot auf deinen Server einladen.

### 2. Bot starten

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # Windows: copy .env.example .env
# .env öffnen und DISCORD_TOKEN eintragen

python bot.py
```

Beim ersten Start synchronisiert der Bot seine Slash-Commands (kann 1–2 Minuten dauern, bis sie überall erscheinen).

### 3. Im Server einrichten

```
/kanal #adventsrpg     → setzt den Story-Kanal (nur Server-Admins)
/charakter             → eigenen Helden erschaffen (Tür 1)
/kalender              → persönlicher Kalender-Überblick
/heute                 → was wartet heute?
```

Ab dem 1. Dezember postet der Bot dann automatisch: **9 Uhr** Geschichte + Entscheidungsbuttons, **15 Uhr** Kampf/Rätsel/Gruppenabenteuer.

## Alle Befehle

| Befehl | Beschreibung |
|---|---|
| `/kanal #kanal` | Story-Kanal festlegen (Admin) |
| `/charakter` | Helden erschaffen (Rasse + Klasse) |
| `/profil [mitglied]` | Profil mit Werten, LP, Ausrüstung |
| `/bestenliste` | Top 10 der Helden |
| `/kalender` | Dein Tür-für-Tür-Status |
| `/heute` | Heutige Tür nachholen |
| `/inventar` | Rucksack anzeigen |
| `/ausruesten <item>` | Waffe/Rüstung anlegen |
| `/benutzen <item>` | Verbrauchsgegenstand nutzen (Heilung) |
| `/tauschen @user <angebot> <gefragt>` | Tauschangebot senden |

## Projektstruktur

```
bot.py                  Startpunkt
database.py             SQLite-Layer (Spieler, Inventar, Entscheidungen …)
game_data.py            Rassen, Klassen, Items, Kampfformeln
utils.py                Hilfsfunktionen (Story-Laden, Stat-Berechnung)
cogs/
  calendar.py           Tür-Freischaltung & tägliche Posts (/kanal, /kalender, /heute)
  character.py          Charaktererschaffung, /profil, /bestenliste
  story.py              Morgenposts + Entscheidungsbuttons
  afternoon.py          Kämpfe, Rätsel, Gruppenabstimmungen
  inventory.py          Inventar, Ausrüsten, Tauschen
data/story/door_XX.json Ein Kapitel pro Tür (editierbar!)
tools/make_story_drafts.py  Erzeugt Entwürfe für Türen 2–24
```

## Tipps

- **Testen vor dem 1. Dezember?** Ändere kurz die Systemzeit des Rechners — oder poste testweise manuell, indem du in `cogs/calendar.py` im Scheduler `local.hour >= 9` temporär auf `>= 0` setzt.
- **Bot-Neustart während eines Kampfes**: Die Boss-HP wird im Speicher gehalten und startet nach einem Neustart neu — Spieler-Fortschritt (XP, Loot) geht durch die Datenbank nie verloren. Aktionen und LP der Helden werden jeden Morgen ohnehin aufgefrischt.
- **Story mitgestalten**: Siehe [STORY-SCHREIBEN.md](STORY-SCHREIBEN.md) — du kannst die Kapitel direkt in den JSON-Dateien schreiben oder mir Text liefern, den ich einarbeite.
