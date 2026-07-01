"""Validate the Geneva Matthew+Mark subtext (mirror of the DR-MM validation)."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from palimpsest.project import Project

WS = Path(".scratch/validation-mm")
child = Project.load(next(WS.glob("1599-geneva-bible-*-chapter-in-book-*")))
parent = Project.load(next(WS.glob("1599-geneva-bible-*-anna-s-archive")))
ref = child.reference_text()
pref = parent.reference_text()
print("=== Geneva-MM child ===")
print("id:", child.metadata.id)
print("chars:", len(ref), "words:", child.metadata.word_count)
print("HEAD:", repr(ref[:110]))
print("TAIL:", repr(ref[-110:]))

recs = [json.loads(l) for l in (child.path / "tracks" / "verses.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
by_book = Counter(r["b"] for r in recs)
print("\n--- verses.jsonl ---  total:", len(recs), "by book:", dict(by_book))
for book in ["Matthew", "Mark"]:
    chs = sorted({r["c"] for r in recs if r["b"] == book})
    print(f"  {book}: {len(chs)} chapters (min {chs[0]} max {chs[-1]})")
print("  first:", recs[0]["b"], recs[0]["c"], ":", recs[0]["v"], " | last:", recs[-1]["b"], recs[-1]["c"], ":", recs[-1]["v"])

atext, _ = child.analyzable_text(sep="")
i = atext.find("The book of the generation of Jesus Christ")
print("\n--- analyzable ---  chars:", len(atext), " masked_delta:", len(ref) - len(atext))
print("  Mt1:1 ctx:", repr(atext[max(0, i - 18):i + 60]))

print("\n--- LEAKAGE (all should be 'absent') ---")
for name, phrase in {
    "arg 'That Jesus is that Messiah'": "That Jesus is that Messiah",
    "arg 'The wise men, who are the firstfruits'": "The wise men, who are the firstfruits",
    "xref 'Luke 3:23'": "Luke 3:23",
    "xref 'Gen. 21:2'": "Gen. 21:2",
    "Genesis 'In the beginning God created'": "In the beginning God created",
    "Luke 'Forasmuch as many'": "Forasmuch as many",
    "John 'In the beginning was that Word'": "In the beginning was that Word",
}.items():
    inchild = phrase in ref
    inparent = phrase in pref
    tag = "PRESENT (LEAK!)" if inchild else f"absent (parent has it: {inparent})"
    print(f"  {name:46s}: {tag}")

print("\n--- PRESENCE (all should be FOUND) ---")
for name, phrase in {
    "Mt1:1": "The book of the generation of Jesus Christ",
    "Mt27 Barabbas": "Whether of the twain will ye that I let loose",
    "Mt28 risen": "He is not here, but is risen",
    "Mk1:1": "The beginning of the Gospel of Jesus Christ",
    "Mk16:20 end": "preached everywhere",
}.items():
    j = ref.find(phrase)
    print(f"  {name:16s}: {'FOUND @' + str(j) if j >= 0 else 'MISSING!'}")

# chapter sections in child layout
from palimpsest.layout import load_layout
cfg = load_layout(child.path)
types = Counter(s.type for s in cfg.sections)
print("\n--- child layout section types ---", dict(types))
