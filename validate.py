"""Checks the built flashcard files. Standard library only: python3 validate.py [path/to/sauna_glossary.csv]

- sauna-words.apkg is a zip with collection.anki2 and media, the SQLite database opens,
  it holds one note per glossary term and two cards per note, with the fixed deck and
  model ids, and every note's fields match the glossary row
- quizlet.txt has one line per term, exactly one tab per line, no empty sides
- flashcards.csv has the same rows as the glossary

(c) 2026 DIVELUX Inc. MIT License. https://diveluxsaunahat.com
"""
import csv
import html
import json
import os
import sqlite3
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_deck as B  # noqa: E402  (does not import genanki at module level)

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


def main(argv):
    rows = B.load(B.find_source(argv))
    n = len(rows)
    check(n == 145, "expected 145 glossary terms, got %d" % n)

    # --- Anki package
    apkg = os.path.join(HERE, "sauna-words.apkg")
    with zipfile.ZipFile(apkg) as z:
        names = set(z.namelist())
        check({"collection.anki2", "media"} <= names, "apkg members: %s" % sorted(names))
        check(json.loads(z.read("media").decode("utf-8")) == {}, "media map should be empty")
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "collection.anki2")
            with open(db_path, "wb") as f:
                f.write(z.read("collection.anki2"))
            db = sqlite3.connect(db_path)
            try:
                check(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "sqlite integrity_check failed")
                notes = db.execute("SELECT id, guid, mid, flds, tags FROM notes").fetchall()
                cards = db.execute("SELECT nid, did, ord FROM cards").fetchall()
                models, decks = db.execute("SELECT models, decks FROM col").fetchone()
            finally:
                db.close()
    models, decks = json.loads(models), json.loads(decks)
    check(str(B.MODEL_ID) in models, "model id %d missing" % B.MODEL_ID)
    check(str(B.DECK_ID) in decks and decks[str(B.DECK_ID)]["name"] == B.DECK_NAME, "deck id/name missing")
    if str(B.DECK_ID) in decks:
        check("CC BY 4.0" in decks[str(B.DECK_ID)]["desc"], "deck description lacks the CC BY 4.0 credit")
    if str(B.MODEL_ID) in models:
        m = models[str(B.MODEL_ID)]
        check([f["name"] for f in m["flds"]] == B.FIELDS, "model fields differ")
        check(len(m["tmpls"]) == 2, "expected 2 card templates")
    check(len(notes) == n, "notes: %d, terms: %d" % (len(notes), n))
    check(len(cards) == 2 * n, "cards: %d, expected %d" % (len(cards), 2 * n))
    check(all(c[1] == B.DECK_ID for c in cards), "a card is outside the deck")
    check(sorted(c[2] for c in cards) == sorted([0, 1] * n), "each note needs card 0 and card 1")
    check(len({x[1] for x in notes}) == n, "note GUIDs are not unique")
    by_term = {}
    for _, _, mid, flds, tags in notes:
        check(mid == B.MODEL_ID, "note with a foreign model")
        f = [html.unescape(x) for x in flds.split("\x1f")]
        check(len(f) == len(B.FIELDS), "field count")
        by_term[(f[2], f[0])] = (f, tags)
    for r in rows:
        got = by_term.get((r["language"], r["term"]))
        check(got is not None, "missing note for %s (%s)" % (r["term"], r["language"]))
        if got:
            f, tags = got
            check(f[1] == r["transliteration"] and f[3] == r["meaning_en"] and f[4] == r["category"]
                  and f[5] == r["tradition"] and f[6] == r["notes"], "fields differ for %s" % r["term"])
            check(f[7] == B.ATTRIBUTION, "attribution field for %s" % r["term"])
            check("lang::" + B.tag(r["language"]) in tags.split(), "language tag for %s" % r["term"])

    # --- Quizlet text
    with open(os.path.join(HERE, "quizlet.txt"), encoding="utf-8") as f:
        lines = f.read().split("\n")
    check(lines[-1] == "", "quizlet.txt should end with a newline")
    lines = lines[:-1]
    check(len(lines) == n, "quizlet.txt lines: %d" % len(lines))
    for ln, r in zip(lines, rows):
        parts = ln.split("\t")
        check(len(parts) == 2 and all(p.strip() for p in parts), "bad Quizlet line: %r" % ln)
        check(parts[0] == B.quizlet_term(r) and parts[1] == B.quizlet_definition(r), "Quizlet line differs: %r" % ln)
    check(len({ln.split("\t")[0] for ln in lines}) == n, "duplicate Quizlet terms")

    # --- Plain CSV
    with open(os.path.join(HERE, "flashcards.csv"), encoding="utf-8", newline="") as f:
        out = list(csv.DictReader(f))
    check(len(out) == n, "flashcards.csv rows: %d" % len(out))
    for o, r in zip(out, rows):
        check(o["term"] == r["term"] and o["meaning_en"] == r["meaning_en"] and o["language"] == r["language"],
              "flashcards.csv differs at %s" % r["term"])

    print("%d terms, %d notes, %d cards, %d Quizlet lines, %d CSV rows" % (n, len(notes), len(cards), len(lines), len(out)))
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems[:40]))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
