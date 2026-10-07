"""Speech timing estimation and caption segmentation.

WHY this module exists even though we have a TTS provider: captions need per-
segment timings. Real word-level timings come from forced alignment (Phase: STT),
but we must still produce usable captions when the provider gives us only an
audio file and a total duration. This module distributes a known duration across
segments proportionally to their length.

KHMER IS THE REASON THIS IS NOT TRIVIAL:
Khmer does not put spaces between words - a whole clause is one "word" to
`str.split()`. Splitting Khmer on whitespace produces one enormous caption, and
counting "words" to estimate duration gives a wildly wrong answer. So:

  - duration is estimated from CHARACTER count for Khmer, word count for
    space-separated languages;
  - segmentation breaks Khmer text on punctuation (។ ៕ , ?) and then on a
    character budget, never on spaces.
"""

import re
import unicodedata

# Khmer Unicode block.
KHMER_RANGE = ("\u1780", "\u17ff")

# COENG (U+17D2) is an invisible "stack the next consonant under this one" mark,
# so a cluster never ends immediately after it.
KHMER_COENG = "\u17d2"

# Rough speaking rates, deliberately conservative.
WORDS_PER_MINUTE = 150.0
KHMER_CHARS_PER_SECOND = 11.0

MIN_SEGMENT_SECONDS = 0.6
TARGET_SEGMENT_CHARS_LATIN = 42
TARGET_SEGMENT_CHARS_KHMER = 28

_KHMER_SENTENCE_END = re.compile(r"(?<=[។៕?!])\s*")
_LATIN_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_KHMER_SOFT_BREAK = re.compile(r"(?<=[,;:៖។])\s*")


def is_khmer(text: str) -> bool:
    """True when the text contains any Khmer codepoint."""
    return any(KHMER_RANGE[0] <= ch <= KHMER_RANGE[1] for ch in text)


def estimate_duration(text: str, *, language: str = "en") -> float:
    """Seconds needed to speak `text`. Never returns 0 for non-empty input."""
    stripped = text.strip()
    if not stripped:
        return MIN_SEGMENT_SECONDS

    if is_khmer(stripped) or language.lower().startswith("km"):
        # Count Khmer letters only; spaces and Latin punctuation do not take time.
        khmer_chars = sum(1 for ch in stripped if KHMER_RANGE[0] <= ch <= KHMER_RANGE[1])
        seconds = max(khmer_chars, 1) / KHMER_CHARS_PER_SECOND
    else:
        words = len([w for w in re.split(r"\s+", stripped) if w])
        seconds = (words / WORDS_PER_MINUTE) * 60.0

    return round(max(seconds, MIN_SEGMENT_SECONDS), 2)


def split_into_segments(text: str, *, language: str = "en") -> list[str]:
    """Splits narration into caption-sized pieces without breaking words."""
    stripped = text.strip()
    if not stripped:
        return []

    khmer = is_khmer(stripped) or language.lower().startswith("km")
    budget = TARGET_SEGMENT_CHARS_KHMER if khmer else TARGET_SEGMENT_CHARS_LATIN

    sentences = [
        s for s in (_KHMER_SENTENCE_END if khmer else _LATIN_SENTENCE_END).split(stripped) if s
    ]

    segments: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) <= budget:
            segments.append(sentence)
            continue
        segments.extend(_split_long(sentence, budget, khmer))
    return [s for s in segments if s]


def khmer_clusters(text: str) -> list[str]:
    """Splits Khmer text into orthographic clusters (base + dependent signs).

    WHY: Khmer vowels and diacritics are COMBINING characters, and COENG stacks a
    consonant under the previous one. Slicing Khmer by raw character index can
    therefore start a line with a dangling vowel sign (e.g. "ាទី"), which is
    simply wrong Khmer. Clusters are the smallest unit a line may break on.
    """
    clusters: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        cluster = char
        index += 1
        # Attach everything that cannot stand on its own.
        while index < len(text):
            nxt = text[index]
            if nxt == KHMER_COENG:
                # COENG plus the consonant it subscripts belong to this cluster.
                cluster += nxt
                index += 1
                if index < len(text):
                    cluster += text[index]
                    index += 1
                continue
            if unicodedata.combining(nxt) or unicodedata.category(nxt) in {"Mn", "Mc"}:
                cluster += nxt
                index += 1
                continue
            break
        clusters.append(cluster)
    return clusters


def _pack_khmer(chunk: str, budget: int) -> list[str]:
    """Packs Khmer clusters into lines no longer than `budget` characters."""
    out: list[str] = []
    current = ""
    for cluster in khmer_clusters(chunk):
        if current and len(current) + len(cluster) > budget:
            out.append(current.strip())
            current = cluster.lstrip()
        else:
            current += cluster
    if current.strip():
        out.append(current.strip())
    return out


def _split_long(sentence: str, budget: int, khmer: bool) -> list[str]:
    if khmer:
        # Prefer punctuation boundaries, then pack clusters up to the budget -
        # never slice by raw character index.
        chunks = [c.strip() for c in _KHMER_SOFT_BREAK.split(sentence) if c.strip()]
        out: list[str] = []
        for chunk in chunks:
            if len(chunk) <= budget:
                out.append(chunk)
            else:
                out.extend(_pack_khmer(chunk, budget))
        return out

    # Space-separated languages: pack whole words up to the budget.
    out, current = [], ""
    for word in sentence.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > budget and current:
            out.append(current)
            current = word
        else:
            current = candidate
    if current:
        out.append(current)
    return out


def distribute_timings(
    segments: list[str], total_duration: float, *, language: str = "en"
) -> list[tuple[str, float, float]]:
    """Spreads `total_duration` over `segments`, weighted by spoken length.

    Returns (text, start, end) with times relative to the start of the scene, and
    guarantees the last segment ends exactly at `total_duration` so audio and
    captions cannot drift apart.
    """
    if not segments:
        return []

    weights = [estimate_duration(segment, language=language) for segment in segments]
    weight_sum = sum(weights) or 1.0

    timings: list[tuple[str, float, float]] = []
    cursor = 0.0
    for index, (segment, weight) in enumerate(zip(segments, weights, strict=True)):
        span = total_duration * (weight / weight_sum)
        start = cursor
        end = total_duration if index == len(segments) - 1 else min(cursor + span, total_duration)
        timings.append((segment, round(start, 3), round(end, 3)))
        cursor = end
    return timings
