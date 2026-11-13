import json
import os

STORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "story")

OUTLINE = {
    2: ("Der Flüsterwald", "Der Weg führt in den Winterwald, wo die Bäume flüstern und die Wege sich verschieben.", "interaction"),
    3: ("Die Glühwürmchenlichtung", "Auf einer Lichtung tanzen seltsame Lichter — und ein Schatten huscht zwischen den Stämmen.", "riddle"),
    4: ("Der Bär mit dem Zimtgeruch", "Ein gewaltiger Winterbär blockiert den Weg — doch etwas an ihm ist ungewohnt.", "fight"),
    5: ("Die Hütte der Lebkuchenhexe", "Ein Duft von Lebkuchen lockt zu einer Hütte aus Keksen und Zucker.", "interaction"),
    6: ("Das Eisrätselfelsen-Tor", "Ein steinernes Tor versperrt den Pass — nur wer sein Rätsel löst, darf hindurch.", "riddle"),
    7: ("Lawinenalarm", "Ein Grollen über dem Frostgebirge: Schnee kommt ins Rutschen!", "fight"),
    8: ("Die Bergschenke „Zum Polaren Hirsch“", "Eine warme Schenke mitten im Schnee — Reisende, Gerüchte und ein verdächtiger Fremder.", "interaction"),
    9: ("Die Brücke der Gefrorenen Träume", "Eine Brücke aus Eis trägt nur, wer ehrlich ist.", "riddle"),
    10: ("Der Schneewolf-Rudel", "Hungrige Augen leuchten zwischen den Schneeverwehungen.", "fight"),
    11: ("Das Dorf der Schneewesen", "Ein Dorf aus lebendigen Schneemännern bittet um Hilfe.", "interaction"),
    12: ("Der halbe Weg", "In der Mitte der Reise liegt ein stiller See — Zeit für Erinnerungen und ein Rätsel des Sees.", "riddle"),
    13: ("Der gestohlene Schlitten", "Der Schlitten des Weihnachtsmanns! Aber wo ist der Weihnachtsmann?", "interaction"),
    14: ("Die Werkstatt im Schnee", "Eine verlassene Wichtelwerkstatt — Maschinen laufen noch, Werkler fehlen.", "fight"),
    15: ("Das Lied der Nordlichter", "Die Nordlichter singen ein Lied — wer es versteht, findet den Weg.", "riddle"),
    16: ("Der Frostgolem", "Aus Eis und alter Magie geformt: Der Wächter des Eismeeres.", "fight"),
    17: ("Über das Eismeer", "Die Gruppe muss das zugefrorene Meer überqueren — wie, das entscheidet die Gruppe.", "interaction"),
    18: ("Die Fischerdörfer des Eismeeres", "Robbenfischer erzählen vom Frostkönig und seinem Palast.", "riddle"),
    19: ("Der Schneesturm", "Ein Sturm wie aus tausend Messern — Schutz finden, bevor es zu spät ist.", "fight"),
    20: ("Die Eisburg des Zweifels", "Palastmauern zeigen jedem seine größte Sorge.", "interaction"),
    21: ("Die Wachen des Palasts", "Eiswachen blockieren das Tor des Frostkönigs.", "fight"),
    22: ("Der Thronsaal", "Der Frostkönig wartet — doch vielleicht ist mehr an seiner Geschichte, als man dachte.", "riddle"),
    23: ("Der Stern in der Eiskrone", "Der Weihnachtsstern schimmert in einer Krone aus ewigem Eis.", "interaction"),
    24: ("Heimkehr mit dem Stern", "Der Rückweg — und das große Weihnachtsfest von Frosthaven.", "fight"),
}

PLACEHOLDER = (
    "✍️ TODO-STORY: Hier deine Geschichte ausformulieren (2–4 Absätze). "
    "Premise dieser Tür: {premise}"
)

CHOICE_SEEDS = [
    {"key": "a", "label": "Mutig direkt angehen", "emoji": "🔥", "xp": 20, "loot": ["plaetzchen"]},
    {"key": "b", "label": "Umsichtig beobachten", "emoji": "👀", "xp": 20, "loot": ["wollmantel"]},
    {"key": "c", "label": "Klug umgehen", "emoji": "🧠", "xp": 20, "loot": ["holzschwert"]},
]

FIGHT_SEEDS = [
    (4, "Winterbär", 90, 7, 1, ["polarfuchspelz"], 40),
    (7, "Lawinengeist", 100, 8, 1, ["heiltrank"], 40),
    (10, "Schneewolf-Alpha", 110, 9, 2, ["eiszapfenlanze"], 45),
    (14, "Außer Kontrolle geratene Werkzeugmaschine", 120, 9, 2, ["zinnpanzer"], 45),
    (16, "Frostgolem", 140, 11, 3, ["glanzruestung"], 50),
    (19, "Sturmdämon", 150, 12, 3, ["heiltrank", "kristallkugel"], 55),
    (21, "Eiswachen-Kapitän", 160, 13, 3, ["sternenschwert"], 60),
    (24, "Schatten des Frostkönigs", 180, 14, 4, ["sternsplitter"], 80),
]

RIDDLE_SEEDS = {
    3: ("Ich bin nicht weiß, obwohl ich im Schnee lebe, und nicht warm, obwohl ich im Ofen schlafe. Was bin ich?", "eine kohle"),
    6: ("Je mehr du von mir nimmst, desto größer werde ich. Was bin ich?", "ein loch"),
    9: ("Ich habe einen Mund, aber nie Hunger, und ich laufe, obwohl ich nie müde werde. Was bin ich?", "ein fluss"),
    12: ("Ich komme einmal im Jahr, habe aber 365 Tage. Was bin ich?", "weihnachten"),
    15: ("Ich male Bänder in den Nachthimmel, doch Pinsel habe ich nie berührt. Was bin ich?", "nordlicht"),
    18: ("Ich habe Städte, aber keine Häuser, Wälder, aber keine Bäume, und Wasser, aber keinen Fisch. Was bin ich?", "eine karte"),
    22: ("Ich bin kälter als Eis und dennoch brenne ich. Was bin ich?", "hass"),
}

INTERACTION_SEEDS = {
    2: ("Am Waldrand spaltet sich der Pfad: Wie will die Gruppe vorgehen?", [
        ("pfeile", "Den Markierungen der Wichtel folgen", "🪧"),
        ("sterne", "Nach den Sternen navigieren", "⭐"),
        ("fuehrer", "Ein flüsterndem Baum um Führung bitten", "🌲"),
    ]),
    5: ("Die Lebkuchenhexe lädt zum Tee — aber man weiß ja nie. Wie verhält sich die Gruppe?", [
        ("essen", "Freundlich annehmen und probieren", "🍪"),
        ("ablehnen", "Höflich ablehnen und nach dem Weg fragen", "🚫"),
        ("tausch", "Einen Gegenstand als Gastgeschenk anbieten", "🎁"),
    ]),
    8: ("Der verdächtige Fremde in der Schenke erzählt vom Frostkönig. Was tut die Gruppe?", [
        ("zuhoeren", "Ihm aufmerksam zuhören", "👂"),
        ("fragen", "Ihn mit Fragen löchern", "❓"),
        ("spielen", "Ihn zu einem Würfelspiel herausfordern", "🎲"),
    ]),
    11: ("Die Schneewesen bitten um Hilfe gegen das Tauwetter. Was schlägt die Gruppe vor?", [
        ("schatten", "Ein Schatzdach aus Tannenzweigen bauen", "🌲"),
        ("eis", "Eisblöcke aus dem See heranschaffen", "🧊"),
        ("reise", "Den Schneewesen eine Reise in den Norden vorschlagen", "🧭"),
    ]),
    13: ("Der Schlitten ist da — aber die Rentiere sind verschwunden. Wie sucht die Gruppe?", [
        ("spuren", "Den Spuren im Schnee folgen", "🐾"),
        ("rufen", "Die Rentiere beim Namen rufen", "📣"),
        ("futter", "Lockfutter aus dem Schlitten auslegen", "🥕"),
    ]),
    17: ("Das Eismeer liegt still da. Wie überquert die Gruppe es?", [
        ("schlitten", "Mit dem reparierten Schlitten", "🛷"),
        ("fuesse", "Zu Fuß, langsam und vorsichtig", "🥾"),
        ("eissegel", "Mit einem improvisierten Eissegel", "⛵"),
    ]),
    20: ("Die Eisburg zeigt jedem seine größte Sorge. Wie geht die Gruppe damit um?", [
        ("zusammen", "Sich gegenseitig festhalten und weitergehen", "🤝"),
        ("augen", "Die Augen schließen und durchlaufen", "🙈"),
        ("antwort", "Jeder spricht seine Sorge laut aus", "🗣️"),
    ]),
    23: ("Die Eiskrone liegt vor euch. Wie nehmt ihr den Stern?", [
        ("heben", "Den Stern behutsam mit bloßen Händen heben", "🤲"),
        ("decke", "Eine Wolldecke um die Krone wickeln", "🧣"),
        ("beten", "Ein Winterlied singen, bevor ihr anfasst", "🎶"),
    ]),
}


def afternoon_block(door: int, kind: str) -> dict:
    if kind == "fight":
        for d, name, hp, atk, dfn, loot, xp in FIGHT_SEEDS:
            if d == door:
                return {
                    "type": "fight",
                    "name": name,
                    "intro": f"✍️ TODO: Kampf-Intro für {name} schreiben (2–3 Sätze).",
                    "hp": hp, "atk": atk, "def": dfn,
                    "loot": loot, "xp": xp,
                }
    if kind == "riddle":
        if door in RIDDLE_SEEDS:
            question, answer = RIDDLE_SEEDS[door]
            return {
                "type": "riddle",
                "question": f"✍️ TODO: Rätselszene ausformulieren. Rätsel: {question}",
                "answer": answer,
                "alternatives": [],
                "xp": 40,
                "loot": ["heiltrank"],
                "flavor": "Die Chronisten notieren deinen Scharfsinn.",
            }
    if kind == "interaction":
        if door in INTERACTION_SEEDS:
            question, options = INTERACTION_SEEDS[door]
            return {
                "type": "interaction",
                "title": "Die Gruppe berät",
                "question": f"✍️ TODO: Szene ausformulieren. {question}",
                "options": [
                    {"key": k, "label": label, "emoji": emoji, "loot": ["plaetzchen"]}
                    for k, label, emoji in options
                ],
                "outcomes": {k: "✍️ TODO: Ausgang beschreiben." for k, _l, _e in options},
                "loot": ["plaetzchen"],
            }
    return {
        "type": "riddle",
        "question": "✍️ TODO: Rätsel einfügen.",
        "answer": "todo",
        "alternatives": [],
        "xp": 40,
        "loot": [],
        "flavor": "",
    }


def main():
    for door, (title, premise, kind) in OUTLINE.items():
        path = os.path.join(STORY_DIR, f"door_{door:02d}.json")
        if os.path.exists(path):
            continue
        data = {
            "door": door,
            "title": title,
            "morning": {
                "text": PLACEHOLDER.format(premise=premise),
                "choices": [dict(c) for c in CHOICE_SEEDS],
            },
            "afternoon": afternoon_block(door, kind),
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
