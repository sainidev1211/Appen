"""Multimodal vision solver for Project Origami/Oberon captioning."""

import base64
import json
import re

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from crowdgen_automation.config import Settings
from crowdgen_automation.tasks import caption_cache, key_pool

SYSTEM_PROMPT = ('Expert Project Origami Batch 4 captioner. If unusable image (blurry/dark/damaged), return {"unusable_quality": true, "detailed_caption": "", "short_caption": "", "camera_angle": ""}. If dense text doc, blueprint, diagram, technical drawing, or document image, return {"is_dense": true, "detailed_caption": "", "short_caption": "", "camera_angle": ""}. Else JSON: "detailed_caption" (1-3 sentences, >=26 words, independent description adding details), "short_caption" (1 standalone sentence, 6-25 words), "camera_angle" (12-30 word sentence or ""). ENGLISH ONLY. RULES: 1. Start with main subject (NO "A photograph of", "An image of"). 2. Strict factual accuracy (reconstruction accuracy): describe ONLY what is directly visible, NO hallucinating objects/text/materials. 3. Numbers: count items as words ("two dogs"); printed numbers/dates in quotes ("1918") or words. 4. NO HEDGING: appears, seems, likely, probably, possibly, perhaps, may/might/could be, suggests, looks like. 5. NO OPINION: mostly, X or Y, ornate, beautiful, elegant, striking, decorative, intricate, peaceful, charming. 6. NO "illegible"/"unreadable" - use "faint". 7. NO age/role guessing. 8. NO motion in still image. 9. NEVER copy short caption verbatim into detailed caption.')
BANNED_WORDS = re.compile(r"\b(beautifully|beautiful|stunning|gorgeous|scenic|peaceful|charming|adorable|picturesque|delicate|vibrant|ornate|elegant|striking|decorative|intricate|playful|enjoying|beaming|wonderful|rustic)\s*", re.IGNORECASE)

def _sanitize(text: str) -> str:
    c = re.sub(r"\b(illegible|unreadable)\b", "faint", re.sub(r"^(?:(?:Detailed|Short)\s*Caption\s*:\s*|(?:A\s+photograph\s+of|An\s+image\s+of|This\s+image\s+shows)\s+)", "", text, flags=re.IGNORECASE), flags=re.IGNORECASE)
    c = re.sub(r"\ban\s+([b-df-hj-np-tv-z])", r"a \1", re.sub(r"\ba\s+([aeio])", r"an \1", re.sub(r"[ \t]+", " ", BANNED_WORDS.sub("", re.sub(r"\bmostly\s+|\b(kind|sort)\s+of\s*|\bcontrast\s+beautifully\s+with\b", lambda m: "contrast with" if "contrast" in m.group(0) else "", c, flags=re.IGNORECASE))).strip(), flags=re.IGNORECASE), flags=re.IGNORECASE)
    return (c[0].upper() + c[1:]) if c else ""

def _clean_json(text: str) -> dict[str, str]:
    c = re.sub(r"```(?:json)?\s*|\s*```", "", re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)).strip()
    d = json.loads(m.group(0) if (m := re.search(r"\{.*\}", c, re.DOTALL)) else c)
    if k := next((f for f in ("is_dense", "unusable_quality") if d.get(f) in (True, "true")), None):
        return {k: "true", "detailed_caption": "", "short_caption": "", "camera_angle": ""}
    res = {k: _sanitize(str(d.get(k, ""))) for k in ("detailed_caption", "short_caption", "camera_angle")}
    if (ang := res["camera_angle"]) and len(ang.split()) < 5 and (sh := res["short_caption"]):
        res["camera_angle"] = f"A {ang.lower().rstrip('.')} view showing {sh[0].lower() + sh[1:].rstrip('.')}."
    return res

def _call_model(url: str, key: str, model: str, img: str, err: str | None, is_gemini: bool = False) -> dict[str, str]:
    p = f"{SYSTEM_PROMPT if is_gemini else ''}Describe image per Project Origami rules.{f' CRITICAL: Validation rejected previous: {err}. Fix strictly.' if err else ''}"
    if is_gemini:
        b64 = img.split(",", 1)[1] if "," in img else base64.b64encode(requests.get(img, timeout=20).content).decode()
        (r := requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}", json={"contents": [{"parts": [{"text": p}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}], "generationConfig": {"response_mime_type": "application/json"}}, timeout=45)).raise_for_status()
        return _clean_json(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    b = {"model": model, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": [{"type": "text", "text": p}, {"type": "image_url", "image_url": {"url": img}}]}]}
    (r := requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=b, timeout=45)).raise_for_status()
    return _clean_json(r.json()["choices"][0]["message"]["content"])

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_captions(img_ref: str, cfg: Settings, error_feedback: str | None = None) -> dict[str, str]:
    if not error_feedback and (cached := caption_cache.get_cached_caption(img_ref)):
        return cached
    if gk := cfg.gemini_api_key:
        try:
            res = _call_model("", gk, cfg.gemini_model, img_ref, error_feedback, is_gemini=True)
            caption_cache.save_cached_caption(img_ref, res)
            return res
        except requests.RequestException:
            if not cfg.openrouter_api_key and not key_pool.load_keys():
                raise
    keys = key_pool.load_keys(extra_keys=[cfg.openrouter_api_key] if cfg.openrouter_api_key else None)
    while key := key_pool.get_active_key(keys):
        try:
            res = _call_model(f"{cfg.openrouter_base_url.rstrip('/')}/chat/completions", key, cfg.openrouter_vision_model, img_ref, error_feedback)
            caption_cache.save_cached_caption(img_ref, res)
            return res
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (401, 402, 403, 429, 500, 502, 503):
                key_pool.mark_key_exhausted(key)
            else:
                raise
    raise RuntimeError("OpenRouter keys exhausted and no Gemini API key configured.")
