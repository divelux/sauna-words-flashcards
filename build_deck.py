"""Builds the Sauna Words flashcards from the Sauna Glossary.

    pip install genanki          # only needed for the .apkg
    python3 build_deck.py [path/to/sauna_glossary.csv]

Writes:
  sauna-words.apkg    Anki deck: 145 notes, 2 cards each (word -> meaning, meaning -> word)
  quizlet.txt         Quizlet import text: term <TAB> definition, one card per line
  flashcards.csv      Plain CSV with a header, for spreadsheets and other flashcard apps

The source CSV defaults to ../sauna-glossary/sauna_glossary.csv and then to
./sauna_glossary.csv. Data: Sauna Glossary by DIVELUX, CC BY 4.0,
https://doi.org/10.5281/zenodo.24387549

(c) 2026 DIVELUX Inc. Code MIT. https://diveluxsaunahat.com
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Fixed once, never change: Anki uses them to update an installed deck instead of duplicating it.
MODEL_ID = 1850128719
DECK_ID = 1805267710
DECK_NAME = "Sauna Words (DIVELUX)"
ATTRIBUTION = "Sauna Glossary by DIVELUX, CC BY 4.0. diveluxsaunahat.com"
SOURCE_URL = "https://doi.org/10.5281/zenodo.24387549"

DECK_DESCRIPTION = (
    "145 sauna, banya and hammam words in 25 languages, from the open Sauna Glossary. "
    "Each word has two cards: word to meaning, and meaning to word.<br><br>"
    "Data: <a href=\"%s\">Sauna Glossary</a> by DIVELUX, CC BY 4.0. "
    "Deck made by <a href=\"https://diveluxsaunahat.com\">DIVELUX</a>, makers of handmade wool sauna hats. "
    "More free sauna tools: <a href=\"https://diveluxsaunahat.com/pages/sauna-tools\">diveluxsaunahat.com/pages/sauna-tools</a>"
) % SOURCE_URL

FIELDS = ["Term", "Transliteration", "Language", "Meaning", "Category", "Tradition", "Notes", "Source"]

CSS = """.card { font-family: Inter, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; font-size: 20px;
  line-height: 1.45; color: #1c110b; background: #f6f3ee; text-align: center; padding: 12px; }
.nightMode.card, .night_mode .card { color: #f6f3ee; background: #1c110b; }
.term { font-size: 36px; font-weight: 700; line-height: 1.15; }
.translit { font-size: 20px; color: #66564b; margin-top: 6px; }
.nightMode .translit, .night_mode .translit { color: #c9bcae; }
.lang { font-size: 15px; letter-spacing: .04em; text-transform: uppercase; color: #7a4e2d; margin-bottom: 12px; }
.meaning { font-size: 22px; max-width: 32em; margin: 0 auto; }
.meta { font-size: 15px; color: #66564b; margin-top: 14px; }
.notes { font-size: 15px; font-style: italic; margin-top: 8px; max-width: 34em; margin-left: auto; margin-right: auto; }
.src { font-size: 11px; color: #8a7b70; margin-top: 22px; }
hr#answer { border: 0; border-top: 1px solid #d9cfc1; margin: 18px 0; }
"""

WORD_FRONT = """<div class="lang">{{Language}}</div>
<div class="term">{{Term}}</div>
{{#Transliteration}}<div class="translit">{{Transliteration}}</div>{{/Transliteration}}"""

BACK_DETAILS = """<div class="meaning">{{Meaning}}</div>
<div class="meta">{{Category}} · {{Tradition}}</div>
{{#Notes}}<div class="notes">{{Notes}}</div>{{/Notes}}
<div class="src">{{Source}}</div>"""

MEANING_FRONT = """<div class="lang">{{Language}} word for</div>
<div class="meaning">{{Meaning}}</div>
<div class="meta">{{Category}} · {{Tradition}}</div>"""

TEMPLATES = [
    {"name": "Word to meaning", "qfmt": WORD_FRONT,
     "afmt": "{{FrontSide}}<hr id=\"answer\">" + BACK_DETAILS},
    {"name": "Meaning to word", "qfmt": MEANING_FRONT,
     "afmt": "{{FrontSide}}<hr id=\"answer\"><div class=\"term\">{{Term}}</div>"
             "{{#Transliteration}}<div class=\"translit\">{{Transliteration}}</div>{{/Transliteration}}"
             "{{#Notes}}<div class=\"notes\">{{Notes}}</div>{{/Notes}}<div class=\"src\">{{Source}}</div>"},
]


def find_source(argv):
    if len(argv) > 1:
        return argv[1]
    for p in (os.path.join(HERE, "..", "sauna-glossary", "sauna_glossary.csv"), os.path.join(HERE, "sauna_glossary.csv")):
        if os.path.exists(p):
            return p
    sys.exit("sauna_glossary.csv not found. Pass its path as the first argument.")


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if v and ("\t" in v or "\n" in v):
                sys.exit("Tab or line break inside %r of %r: the Quizlet file would break." % (k, r["term"]))
    return rows


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tag(s):
    return s.strip().lower().replace(" ", "_")


def quizlet_term(r):
    t = r["term"]
    if r["transliteration"]:
        t += " (" + r["transliteration"] + ")"
    return t


def quizlet_definition(r):
    return "%s [%s; %s]" % (r["meaning_en"], r["language"], r["tradition"])


def write_quizlet(rows, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(quizlet_term(r) + "\t" + quizlet_definition(r) + "\n")


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["front", "back", "term", "transliteration", "language", "language_code",
                    "meaning_en", "category", "tradition", "notes", "source"])
        for r in rows:
            w.writerow([quizlet_term(r), quizlet_definition(r), r["term"], r["transliteration"], r["language"],
                        r["language_code"], r["meaning_en"], r["category"], r["tradition"], r["notes"], ATTRIBUTION])


def write_apkg(rows, path):
    import genanki  # imported here so the text files can be built without it

    model = genanki.Model(MODEL_ID, "Sauna Words (DIVELUX)", fields=[{"name": n} for n in FIELDS],
                          templates=TEMPLATES, css=CSS)
    deck = genanki.Deck(DECK_ID, DECK_NAME, description=DECK_DESCRIPTION)
    for r in rows:
        note = genanki.Note(
            model=model,
            fields=[esc(r["term"]), esc(r["transliteration"]), esc(r["language"]), esc(r["meaning_en"]),
                    esc(r["category"]), esc(r["tradition"]), esc(r["notes"]), esc(ATTRIBUTION)],
            tags=["sauna_words", "lang::" + tag(r["language"]), "category::" + tag(r["category"])],
            guid=genanki.guid_for("sauna-glossary", r["language_code"], r["term"]),
        )
        deck.add_note(note)
    genanki.Package(deck).write_to_file(path)
    return len(deck.notes)


def main(argv):
    src = find_source(argv)
    rows = load(src)
    write_quizlet(rows, os.path.join(HERE, "quizlet.txt"))
    write_csv(rows, os.path.join(HERE, "flashcards.csv"))
    n = write_apkg(rows, os.path.join(HERE, "sauna-words.apkg"))
    print("%d terms -> quizlet.txt, flashcards.csv, sauna-words.apkg (%d notes, %d cards)" % (len(rows), n, 2 * n))


if __name__ == "__main__":
    main(sys.argv)
