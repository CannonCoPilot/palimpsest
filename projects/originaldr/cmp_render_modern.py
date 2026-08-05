"""Verify basis-db render_modern reproduces gen_dr_original's clean_scripture(Madueke) per verse."""
import sqlite3, sys
from pathlib import Path
ME = Path("core/tests/fixtures/gold/mask_engine").resolve()
sys.path.insert(0, str(ME))
import gen_dr_original as gen

mad_books, mad_order = gen.parse_madueke()
sab_order = gen.OT + gen.NT
slug_to_disp = dict(zip(sab_order, mad_order)) if len(mad_order) == len(sab_order) else {}
print(f"madueke books={len(mad_order)} sab_order={len(sab_order)} aligned={bool(slug_to_disp)}")

db = "projects/originaldr/reconstruction/basis-db.sqlite"
con = sqlite3.connect(db)
rows = con.execute("SELECT id, render_modern FROM elements WHERE type='scripture-verse'").fetchall()

total=match=mismatch=absent_mad=tobias=0
samples=[]
for sid, rm in rows:
    _, slug, ch, v = sid.split("/")
    if slug == "tobias":   # gen drops spurious ch0 + renumbers; skip auto-compare
        tobias += 1; continue
    disp = slug_to_disp.get(slug)
    mtext = (mad_books.get(disp, {}).get(int(ch), {}) or {}).get(int(v)) if disp else None
    if mtext is None:
        absent_mad += 1; continue      # Madueke absent -> gen uses Sabates fallback; not a render_modern==madueke case
    cs = gen.clean_scripture(mtext)
    total += 1
    if cs == rm:
        match += 1
    else:
        mismatch += 1
        if len(samples) < 8:
            samples.append((sid, repr(cs[:90]), repr((rm or "")[:90])))

print(f"compared(madueke-present, non-tobias)={total}  match={match}  mismatch={mismatch}")
print(f"tobias(skipped)={tobias}  madueke-absent(skipped)={absent_mad}  db_total={len(rows)}")
for s in samples:
    print("  MISMATCH", s[0]); print("    gen :", s[1]); print("    base:", s[2])
