"""Tests for plate_gold: geometry, estimator, validation. Run: python3 -m pytest test_plate_gold.py -q"""
import json, copy
from PIL import Image, ImageDraw
import plate_gold as PG

def page(w=800, h=1100, tilt=0.0):
    im = Image.new("RGB", (w, h), (245, 240, 230)); d = ImageDraw.Draw(im)
    for y in range(120, 980, 22): d.rectangle([120, y, 680, y+9], fill=(20, 15, 10))
    return im.rotate(tilt, resample=3, expand=False, fillcolor=(245, 240, 230))

def test_estimator_recovers_known_tilt():
    for t in (-2.3, -0.7, 0.0, 1.1, 2.6):
        est = PG.estimate_skew(page(tilt=t))
        assert abs(est + t) <= 0.06, (t, est)       # levelling = rotate back by -t

def test_deskew_levels_page():
    im = page(tilt=1.4); lev = PG.deskew(im, PG.estimate_skew(im))
    assert abs(PG.estimate_skew(lev)) <= 0.06

def test_transform_box_follows_ink():
    w, h = 800, 1100
    im = Image.new("RGB", (w, h), (255, 255, 255)); ImageDraw.Draw(im).rectangle([150, 200, 250, 260], fill=(0, 0, 0))
    box = [150/w, 200/h, 250/w, 260/h]
    for d in (-3.0, 2.5):
        rot = PG.deskew(im, d); nb = PG.transform_box(box, w, h, d)
        g = rot.convert("L"); px = [(x, y) for y in range(h) for x in range(w) if g.getpixel((x, y)) < 128] if False else None
        # centroid of ink via bbox of dark pixels
        inv = g.point(lambda v: 255 - v); bb = inv.getbbox(); cx, cy = (bb[0]+bb[2])/2/w, (bb[1]+bb[3])/2/h
        assert nb[0] <= cx <= nb[2] and nb[1] <= cy <= nb[3], (d, nb, cx, cy)
        assert abs((nb[0]+nb[2])/2 - cx) < 0.004 and abs((nb[1]+nb[3])/2 - cy) < 0.004
    # round trip
    b2 = PG.transform_box(PG.transform_box(box, w, h, 2.0), w, h, -2.0)
    assert all(abs(a-b) < 0.002 for a, b in zip(box, b2))

def rec():
    return {"format": "plate-gold/1", "source": {"path": "x", "sha256": "y"}, "classes": PG.CLASSES,
            "classes_added": [], "leaves": {"NT-1582-B_0009": {"witness": "NT-1582-B", "leaf": 9, "agent": {},
             "review": {"verdict": "accept", "skew_deg": 0.8, "regions": [
                 {"box": [0.1, 0.1, 0.5, 0.5], "class": "MT", "origin": "agent", "agent_index": 0}]}}}}

def test_validate_ok_and_provisional_class():
    r = rec(); PG.validate(r, check_source=False)
    r["classes_added"].append({"code": "AC", "meaning": "acrostic marker"})
    r["leaves"]["NT-1582-B_0009"]["review"]["regions"][0]["class"] = "AC"
    PG.validate(r, check_source=False)

def test_validate_rejects():
    import pytest
    r = rec(); r["leaves"]["NT-1582-B_0009"]["review"]["skew_deg"] = 7
    with pytest.raises(PG.GoldError): PG.validate(r, check_source=False)
    r = rec(); r["classes_added"].append({"code": "MT", "meaning": "dup"})
    with pytest.raises(PG.GoldError): PG.validate(r, check_source=False)
    r = rec(); r["classes_added"].append({"code": "toolong", "meaning": "x"})
    with pytest.raises(PG.GoldError): PG.validate(r, check_source=False)
    r = rec(); r["leaves"]["NT-1582-B_0009"]["review"]["regions"][0]["class"] = "ZZ"
    with pytest.raises(PG.GoldError): PG.validate(r, check_source=False)
    r = rec(); r["leaves"]["NT-1582-B_0009"]["review"]["regions"][0]["class"] = "??"
    with pytest.raises(PG.GoldError): PG.validate(r, check_source=False)
