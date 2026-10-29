"""Generate concise Instagram captions via Gemini, with an offline fallback."""
from __future__ import annotations

import json
import re
import sys

from ..config import GEMINI_API_KEY
from .gemini import generate


CAPTION_PROMPT = """You write captions for short Instagram clips. You sound like a
real person posting a favourite moment — a friend in a group chat, not a
brand, not an AI. Sarcasm and playful roasting are encouraged.
{context_block}I'm cutting {n} clips from one longer video. The clips:
{clip_descriptions}

For EACH clip, write one caption:
- 1-2 short lines a friend would actually type. Dry humour beats hype.
- Use 0-2 emojis max in the WHOLE caption, never at the end of every line.
- Avoid obvious AI phrasing such as "delve", "unhinged", "game-changer",
  "you won't believe", "watch till the end", "POV:", or motivational slogans.
- End with 2-4 hashtags a real fan of this niche would use — one broad tag
  plus specific niche tags, no generic #content or #reels filler.
  {credit_line}

Respond with ONLY a JSON array, one object per clip:
[{{"caption": "..."}}, ...]
"""


_FALLBACK_CAPTIONS = [
    "clip {i} did not have to go this hard",
    "found this gem at {ts}. no notes.",
    "this part lives in my head rent free",
    "{i} minutes in and this happens. of course.",
]


def _fallback(clips: list[dict], uploader: str = "") -> list[dict]:
    credit = f"\n📹 {uploader}" if uploader else ""
    out = []
    for n, c in enumerate(clips):
        base = _FALLBACK_CAPTIONS[n % len(_FALLBACK_CAPTIONS)]
        caption = base.format(i=c["index"], ts=format_ts(c["start"])) \
            + credit + " #fyp #viral"
        out.append({"caption": caption})
    return out


def _context_block(context: dict | None) -> str:
    if not context:
        return ""
    lines: list[str] = []
    if context.get("title"):
        lines.append(f"Source video: \"{context['title']}\"")
    if context.get("uploader"):
        lines.append(f"Original creator: {context['uploader']}")
    if context.get("description"):
        desc = " ".join(str(context["description"]).split())[:600]
        lines.append(f"Source description: {desc}")
    if not lines:
        return ""
    return ("The clips come from this source video — match its topic and audience:\n"
            + "\n".join(lines) + "\n\n")


def _credit_line(uploader: str) -> str:
    """Per-prompt instruction to credit the original creator naturally."""
    if not uploader:
        return ""
    return (f'Always credit the original creator: end the caption with a short '
            f'natural tag like "📹 {uploader}" (or their handle if the '
            f'description shows one). Keep it casual, not a legal disclaimer.')


def generate_captions(clips: list[dict], video_name: str,
                      context: dict | None = None) -> list[dict]:
    """Return one ``{"caption": ...}`` dict per clip. Falls back on error."""
    # Keep the CLI/library import lightweight: google-genai is optional and
    # gemini.check_available() gives the authoritative dependency/key check.
    from . import gemini
    if not gemini._load_genai() or not GEMINI_API_KEY:
        print("[captions] Gemini not configured; using fallback captions.", file=sys.stderr)
        return _fallback(clips, uploader=(context or {}).get("uploader", ""))

    clip_descriptions = "\n".join(
        f"- Clip {c['index']}: {format_ts(c['start'])}-{format_ts(c['end'])} — {c.get('reason', '')}"
        for c in clips
    )
    prompt = CAPTION_PROMPT.format(
        n=len(clips), clip_descriptions=clip_descriptions,
        context_block=_context_block(context),
        credit_line=_credit_line((context or {}).get("uploader", "")))

    try:
        text = generate(prompt, temperature=0.9, max_output_tokens=1536)
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if not match:
            raise ValueError("no JSON array in response")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, list) or len(parsed) != len(clips):
            raise ValueError("caption count mismatch")
        results: list[dict] = []
        for item in parsed:
            if isinstance(item, dict):
                results.append({"caption": str(item.get("caption", "")).strip()})
            else:
                results.append({"caption": str(item).strip()})
        return results
    except Exception as exc:
        print(f"[captions] Gemini failed ({exc}); using fallback captions.", file=sys.stderr)
        return _fallback(clips, uploader=(context or {}).get("uploader", ""))


def format_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"

