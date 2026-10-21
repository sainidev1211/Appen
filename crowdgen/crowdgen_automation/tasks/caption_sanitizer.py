"""Sanitization and JSON parsing for caption model outputs."""

import json
import re

BANNED = re.compile(r"\b(beautifully|beautiful|stunning|gorgeous|scenic|peaceful|charming|adorable|picturesque|delicate|vibrant|ornate|elegant|striking|decorative|intricate|playful|enjoying|beaming|wonderful|rustic)\s*", re.IGNORECASE)

def _sanitize(text: str) -> str:
    c = re.sub(r"\b(illegible|unreadable)\b", "faint", re.sub(r"^(?:(?:Detailed|Short)\s*Caption\s*:\s*|(?:A\s+photograph\s+of|An\s+image\s+of|This\s+image\s+shows)\s+)", "", text, flags=re.IGNORECASE), flags=re.IGNORECASE)
    c = re.sub(r"\ban\s+([b-df-hj-np-tv-z])", r"a \1", re.sub(r"\ba\s+([aeio])", r"an \1", re.sub(r"[ \t]+", " ", BANNED.sub("", re.sub(r"\bmostly\s+|\b(kind|sort)\s+of\s*|\bcontrast\s+beautifully\s+with\b", lambda m: "contrast with" if "contrast" in m.group(0) else "", c, flags=re.IGNORECASE))).strip(), flags=re.IGNORECASE), flags=re.IGNORECASE)
    return (c[0].upper() + c[1:]) if c else ""

def _clean_json(text: str) -> dict[str, str]:
    c = re.sub(r"```(?:json)?\s*|\s*```", "", re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)).strip()
    d = json.loads(m.group(0) if (m := re.search(r"\{.*\}", c, re.DOTALL)) else c) if "{" in c else {}
    if k := next((f for f in ("is_dense", "unusable_quality") if d.get(f) in (True, "true")), None):
        return {k: "true", "detailed_caption": "", "short_caption": "", "camera_angle": ""}
    res = {k: _sanitize(str(d.get(k, ""))) for k in ("detailed_caption", "short_caption", "camera_angle")}
    if (ang := res["camera_angle"]) and len(ang.split()) < 5 and (sh := res["short_caption"]):
        res["camera_angle"] = f"A {ang.lower().rstrip('.')} view showing {sh[0].lower() + sh[1:].rstrip('.')}."
    return res
