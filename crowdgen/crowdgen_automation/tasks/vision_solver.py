"""Multimodal vision solver for Project Origami/Oberon captioning."""

import base64

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from crowdgen_automation.config import Settings
from crowdgen_automation.tasks import caption_cache, key_pool
from crowdgen_automation.tasks.caption_sanitizer import _clean_json, _sanitize

__all__ = ["_clean_json", "_sanitize", "generate_captions"]

SYSTEM_PROMPT = ('Expert Project Origami Batch 4 captioner. If unusable image (blurry/dark/damaged), return {"unusable_quality": true, "detailed_caption": "", "short_caption": "", "camera_angle": ""}. If dense text doc, blueprint, diagram, technical drawing, or document image, return {"is_dense": true, "detailed_caption": "", "short_caption": "", "camera_angle": ""}. Else JSON: "detailed_caption" (1-3 sentences, >=26 words, independent description adding details), "short_caption" (1 standalone sentence, 6-25 words), "camera_angle" (12-30 word sentence or ""). ENGLISH ONLY. RULES: 1. Start with main subject (NO "A photograph of", "An image of"). 2. Strict factual accuracy (reconstruction accuracy): describe ONLY what is directly visible, NO hallucinating objects/text/materials. 3. Numbers: count items as words ("two dogs"); printed numbers/dates in quotes ("1918") or words. 4. NO HEDGING: appears, seems, likely, probably, possibly, perhaps, may/might/could be, suggests, looks like. 5. NO OPINION: mostly, X or Y, ornate, beautiful, elegant, striking, decorative, intricate, peaceful, charming. 6. NO "illegible"/"unreadable" - use "faint". 7. NO age/role guessing. 8. NO motion in still image. 9. NEVER copy short caption verbatim into detailed caption.')

def _call_model(url: str, key: str, model: str, img: str, err: str | None, is_gemini: bool = False) -> dict[str, str]:
    p = f"{SYSTEM_PROMPT if is_gemini else ''}Describe image per Project Origami rules.{f' CRITICAL: Previous failed with error: {err}.' if err else ''}"
    if is_gemini:
        b64 = img.split(",", 1)[1] if "," in img else base64.b64encode(requests.get(img, timeout=20).content).decode()
        (r := requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}", json={"contents": [{"parts": [{"text": p}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}], "generationConfig": {"response_mime_type": "application/json"}}, timeout=45)).raise_for_status()
        return _clean_json(r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}"))
    b = {"model": model, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": [{"type": "text", "text": p}, {"type": "image_url", "image_url": {"url": img}}]}]}
    (r := requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=b, timeout=45)).raise_for_status()
    return _clean_json(r.json()["choices"][0]["message"]["content"])

@retry(retry=retry_if_exception_type(requests.RequestException), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def generate_captions(img_ref: str, cfg: Settings, error_feedback: str | None = None) -> dict[str, str]:
    if not error_feedback and (cached := caption_cache.get_cached_caption(img_ref)):
        return cached
    if gk := cfg.gemini_api_key:
        for m in (cfg.gemini_model, "gemini-3-flash-preview", "gemini-3.5-flash"):
            try:
                res = _call_model("", gk, m, img_ref, error_feedback, is_gemini=True)
                caption_cache.save_cached_caption(img_ref, res)
                return res
            except requests.RequestException:
                continue
        if not cfg.openrouter_api_key and not key_pool.load_keys():
            raise RuntimeError("Gemini models failed and no OpenRouter keys configured.")
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
    raise RuntimeError("Vision models exhausted. Please verify Gemini or OpenRouter API keys.")
