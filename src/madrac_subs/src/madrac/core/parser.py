"""
Video filename parser — extracts structured metadata from filenames.

Gate: only meaningful when the user has consented to normalization
(``comunidad.normalizacion_habilitada``).  The parser itself is stateless
and always available.
"""

import re
from typing import Any, Dict, Optional, List, Tuple

PAT_SEASON_EP = re.compile(
    r"[.\-_[([ ]?[Ss](\d+)[Ee](\d+)(?:[Ee](\d+))?[.\-_\]) ]?"
)
PAT_EPISODE_SUELTO = re.compile(
    r"(?:Cap[íiÍÍ]tulo|Cap|Ep[.]?|[-\s]+)\s*(\d{1,3})(?!\d)", re.IGNORECASE
)
PAT_YEAR = re.compile(
    r"([.\-([\s])(19\d\d|20\d\d)([.\-)\]\s])"
)
PAT_RESOLUTION = re.compile(
    r"(2160[PpIi]|1080[PpIi]|720[PpIi]|480[PpIi]|360[PpIi])"
)
PAT_SOURCE = re.compile(
    r"(WEB[-.]?DL|WEB[-.]?Rip|BluRay|Blu[-.]?Ray|HDTV|DVDRip|DVD|BD[-]?Remux|BR[-]?Rip|HDRip)",
    re.IGNORECASE,
)
PAT_CODEC = re.compile(
    r"(x\.?264|h\.?264|x\.?265|h\.?265|HEVC|AVC|AV1|VP9)",
    re.IGNORECASE,
)
PAT_AUDIO = re.compile(
    r"(DDP\d*\.?\d*|DD\d*\.?\d*|DTS[-.]?HD|DTS|AAC|AC3|FLAC|MP3|Opus)",
    re.IGNORECASE,
)
PAT_RELEASE_GROUP = re.compile(
    r"^\[([A-Za-z0-9]{2,15})\]|\[([A-Za-z0-9]{2,15})\]$"
)


def _last_matches(text: str) -> Dict[str, re.Match]:
    result: Dict[str, re.Match] = {}
    pairs = [
        ("season_ep", PAT_SEASON_EP),
        ("resolution", PAT_RESOLUTION),
        ("source", PAT_SOURCE),
        ("codec", PAT_CODEC),
        ("audio", PAT_AUDIO),
        ("year", PAT_YEAR),
        ("release_group", PAT_RELEASE_GROUP),
        ("ep_suelto", PAT_EPISODE_SUELTO),
    ]
    for key, pat in pairs:
        ms = list(pat.finditer(text))
        if ms:
            result[key] = ms[-1]
    return result


def parse_video_filename(name: str) -> Dict[str, Any]:
    stem = re.sub(r"\.(mkv|mp4|avi|mov|webm|m4v|wmv|ts|mts|flv)$", "",
                  name.strip(), flags=re.IGNORECASE)

    matches = _last_matches(stem)

    # ── Extract values ────────────────────────────────────────
    season: Optional[int] = None
    episode: Optional[int] = None
    if "season_ep" in matches:
        m = matches["season_ep"]
        season = int(m.group(1))
        episode = int(m.group(2))
    elif "ep_suelto" in matches:
        episode = int(matches["ep_suelto"].group(1))
        season = 1

    year = None
    if "year" in matches:
        year = int(matches["year"].group(2))

    resolution = None
    if "resolution" in matches:
        resolution = matches["resolution"].group(0).lower()

    source = None
    if "source" in matches:
        source = matches["source"].group(0).lower().replace("-", "").replace(".", "")

    codec_v = None
    if "codec" in matches:
        codec_v = matches["codec"].group(0).lower().replace("x.", "x").replace("h.", "h")

    audio = None
    if "audio" in matches:
        audio = matches["audio"].group(0).lower()

    release_group = None
    if "release_group" in matches:
        m_rg = matches["release_group"]
        release_group = m_rg.group(1) or m_rg.group(2)

    has_episode = season is not None or episode is not None
    media_type = "episode" if has_episode else "movie"

    # ── Build title_clean: remove matched segments right-to-left ──
    title_clean = stem
    spans: List[Tuple[int, int]] = []
    for m in matches.values():
        spans.append((m.start(), m.end()))
    spans.sort(key=lambda x: -x[0])
    for start, end in spans:
        title_clean = title_clean[:start] + title_clean[end:]

    title_clean = re.sub(r"[._\s-]+", " ", title_clean).strip()
    # Clean up leftover brackets/parens
    title_clean = re.sub(r"\s*[\u005b\u005d()]\s*", " ", title_clean)
    title_clean = re.sub(r"\s+", " ", title_clean).strip()

    # ── Confidence (5 categories) ─────────────────────────────
    matched = 0
    if resolution:
        matched += 1
    if source:
        matched += 1
    if codec_v or audio:
        matched += 1
    if has_episode:
        matched += 1
    if year:
        matched += 1
    confidence = matched / 5.0

    if confidence < 0.5:
        return {
            "title_clean": name,
            "season": None,
            "episode": None,
            "year": None,
            "resolution": None,
            "source": None,
            "codec": None,
            "audio": None,
            "release_group": None,
            "type": "movie",
            "confidence": 0.0,
            "normalization_version": "parser_v1",
        }

    return {
        "title_clean": title_clean or name,
        "season": season,
        "episode": episode,
        "year": year,
        "resolution": resolution,
        "source": source,
        "codec": codec_v,
        "audio": audio,
        "release_group": release_group,
        "type": media_type,
        "confidence": round(confidence, 2),
        "normalization_version": "parser_v1",
    }
