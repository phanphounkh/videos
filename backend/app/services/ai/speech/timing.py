"""Speech timing estimation and caption segmentation.

WHY this module exists even though we have a TTS provider: captions need per-
segment timings. Real word-level timings come from forced alignment (Phase: STT),
but we must still produce usable captions when the provider gives us only an
audio file and a total duration. This module distributes a known duration across
segments proportionally to their length.

When the TTS provider reports speech marks, `captions_from_marks` builds
captions from those instead, so they follow the real voice.

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
# Short-form video captions are big and few words at a time: a short line is
# read at a glance and keeps pace with the voice.
TARGET_SEGMENT_CHARS_LATIN = 26
TARGET_SEGMENT_CHARS_KHMER = 22
MAX_CAPTION_WORDS_LATIN = 4
# A pause at least this long in the speech always starts a new caption.
CAPTION_BREAK_PAUSE_SECONDS = 0.35

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


def align_marks(
    narration: str, marks: list[tuple[str, float, float]]
) -> list[tuple[str, float, float]]:
    """Maps provider speech marks back onto the narration as it was written.

    Providers report the spoken text without punctuation ("cola" for "cola?")
    or quotes, but captions should show what the writer typed. Each mark is
    found in the narration from where the previous one ended, then widened to
    the surrounding non-space characters. A mark that cannot be found is used
    as reported, so nothing is ever dropped.
    """
    tokens: list[tuple[str, float, float]] = []
    cursor = 0
    for text, start, end in marks:
        index = narration.find(text, cursor)
        if index < 0:
            tokens.append((text, start, end))
            continue
        begin = index
        while begin > cursor and not narration[begin - 1].isspace():
            begin -= 1
        finish = index + len(text)
        while finish < len(narration) and not narration[finish].isspace():
            finish += 1
        tokens.append((narration[begin:finish], start, end))
        cursor = finish
    return tokens


def captions_from_marks(
    tokens: list[tuple[str, float, float]], total_duration: float, *, language: str = "en"
) -> list[tuple[str, float, float]]:
    """Builds caption segments timed to real speech marks.

    `tokens` come from `align_marks`: words for English, space-separated
    phrases for Khmer. Latin words are grouped into short lines that break on
    pauses and sentence ends. A long Khmer phrase is packed into cluster-safe
    lines and its time is shared between them by length. Each caption stays up
    until the next one starts, and the last one until the scene ends.
    """
    if not tokens:
        return []

    joined = "".join(text for text, _, _ in tokens)
    khmer = is_khmer(joined) or language.lower().startswith("km")
    pieces: list[tuple[str, float, float]] = []

    if khmer:
        for text, start, end in tokens:
            lines = (
                [text]
                if len(text) <= TARGET_SEGMENT_CHARS_KHMER
                else _split_long(text, TARGET_SEGMENT_CHARS_KHMER, True)
            )
            weight_sum = sum(len(line) for line in lines) or 1
            cursor = start
            for line in lines:
                span = (end - start) * len(line) / weight_sum
                pieces.append((line, cursor, cursor + span))
                cursor += span
    else:
        group: list[tuple[str, float, float]] = []
        for index, token in enumerate(tokens):
            group.append(token)
            text = " ".join(t for t, _, _ in group)
            nxt = tokens[index + 1] if index + 1 < len(tokens) else None
            if (
                nxt is None
                or len(group) >= MAX_CAPTION_WORDS_LATIN
                or len(f"{text} {nxt[0]}") > TARGET_SEGMENT_CHARS_LATIN
                or nxt[1] - token[2] >= CAPTION_BREAK_PAUSE_SECONDS
                or token[0][-1:] in ".!?,;:"
            ):
                pieces.append((text, group[0][1], group[-1][2]))
                group = []

    captions: list[tuple[str, float, float]] = []
    for index, (text, start, _end) in enumerate(pieces):
        start = min(max(0.0, start), total_duration)
        following = pieces[index + 1][1] if index + 1 < len(pieces) else total_duration
        end = min(max(following, start + 0.05), total_duration)
        if end > start:
            captions.append((text, round(start, 3), round(end, 3)))
    return captions


# Longest Khmer unit handed to an aligner; longer phrases are split on cluster
# boundaries so every unit gets its own timestamp.
ALIGN_UNIT_CHARS_KHMER = 24


def speech_units(text: str, *, language: str = "en") -> list[str]:
    """Splits narration into the units a speech aligner timestamps.

    Words for space-separated languages. For Khmer, the space-separated phrases
    (as written), with long ones packed into cluster-safe pieces - never a raw
    character slice. Joining the units with single spaces gives back the text
    up to whitespace, which is what lets `align_marks` map them home.
    """
    stripped = text.strip()
    if not stripped:
        return []
    khmer = is_khmer(stripped) or language.lower().startswith("km")
    units: list[str] = []
    for chunk in stripped.split():
        if khmer and len(chunk) > ALIGN_UNIT_CHARS_KHMER:
            units.extend(_split_long(chunk, ALIGN_UNIT_CHARS_KHMER, True))
        else:
            units.append(chunk)
    return [unit for unit in units if unit]


# A gap in the voice at least this long counts as a pause between phrases.
MIN_PAUSE_SECONDS = 0.15
# How far a phrase boundary may move to reach a real pause.
SNAP_WINDOW_SECONDS = 0.45
# A snap may not leave a phrase shorter than this.
MIN_MARK_SECONDS = 0.12


def find_pauses(envelope: list[int], fps: int, *, threshold: int = 10) -> list[tuple[float, float]]:
    """(start, end) of every quiet stretch in a loudness envelope, in seconds."""
    pauses: list[tuple[float, float]] = []
    index = 0
    while index < len(envelope):
        if envelope[index] >= threshold:
            index += 1
            continue
        end = index
        while end < len(envelope) and envelope[end] < threshold:
            end += 1
        if (end - index) / fps >= MIN_PAUSE_SECONDS:
            pauses.append((index / fps, end / fps))
        index = end
    return pauses


def snap_to_pauses(
    marks: list[tuple[str, float, float]], pauses: list[tuple[float, float]]
) -> list[tuple[str, float, float]]:
    """Moves phrase boundaries onto the real pauses in the audio.

    WHY: an aligner reliably knows WHICH phrase is spoken where, but its
    timestamps can be off by a few hundred milliseconds, so a subtitle appears
    before its words are heard. The audio knows exactly where the voice stops
    and starts.

    Each pause is matched to the nearest boundary within SNAP_WINDOW_SECONDS:
    the gap between two phrases (the earlier one then ends where the pause
    starts, the later one starts where it ends), the start of the first phrase
    (leading silence) or the end of the last. A snap that would squeeze a
    phrase below MIN_MARK_SECONDS is skipped on its own; the others still apply.
    """
    count = len(marks)
    if count == 0 or not pauses:
        return marks
    starts = [start for _, start, _ in marks]
    ends = [end for _, _, end in marks]
    used: set[int] = set()

    for pause_start, pause_end in pauses:
        best: tuple[float, int] | None = None
        # Silence at the very start of the audio can only precede phrase 1.
        leading = pause_start <= 0.01
        for k in [0] if leading else range(count + 1):
            if k in used:
                continue
            if k == 0:
                if not leading:
                    continue
                distance = abs(starts[0] - pause_end)
            elif k == count:
                distance = abs(ends[-1] - pause_start)
            else:
                gap = (ends[k - 1] + starts[k]) / 2
                inside = pause_start <= gap <= pause_end
                distance = 0.0 if inside else min(abs(gap - pause_start), abs(gap - pause_end))
            if distance <= SNAP_WINDOW_SECONDS and (best is None or distance < best[0]):
                best = (distance, k)
        if best is None:
            continue

        k = best[1]
        new_ends, new_starts = list(ends), list(starts)
        if k > 0:
            new_ends[k - 1] = pause_start
        if k < count:
            new_starts[k] = pause_end
        touched = {k - 1, k} & set(range(count))
        if all(new_ends[i] - new_starts[i] >= MIN_MARK_SECONDS for i in touched):
            starts, ends = new_starts, new_ends
            used.add(k)

    return [
        (text, round(s, 3), round(e, 3))
        for (text, _, _), s, e in zip(marks, starts, ends, strict=True)
    ]


def marks_from_pauses(
    units: list[str], pauses: list[tuple[float, float]], duration: float, *, language: str = "en"
) -> list[tuple[str, float, float]]:
    """Times speech units from the audio alone, when no aligner is available.

    The units are laid out over the parts of the audio where the voice is
    actually heard (pauses skipped), in proportion to their spoken length, and
    the boundaries are then snapped onto the real pauses. Free, local and
    deterministic - much closer than spreading text over the whole clip,
    because sentence breaks land where the speaker really pauses.
    """
    if not units or duration <= 0:
        return []
    regions: list[tuple[float, float]] = []
    cursor = 0.0
    for pause_start, pause_end in sorted(pauses):
        if pause_start > cursor:
            regions.append((cursor, min(pause_start, duration)))
        cursor = max(cursor, pause_end)
    if cursor < duration:
        regions.append((cursor, duration))
    regions = [(s, e) for s, e in regions if e > s]
    speech = sum(e - s for s, e in regions)
    if speech <= 0:
        return []

    def at(offset: float, *, ending: bool) -> float:
        """Real time of a point `offset` seconds into the speech-only timeline."""
        for start, end in regions:
            length = end - start
            if offset < length or (ending and offset <= length + 1e-9):
                return start + offset
            offset -= length
        return regions[-1][1]

    weights = [estimate_duration(unit, language=language) for unit in units]
    scale = speech / (sum(weights) or 1.0)
    marks: list[tuple[str, float, float]] = []
    spent = 0.0
    for unit, weight in zip(units, weights, strict=True):
        span = weight * scale
        start, end = at(spent, ending=False), at(spent + span, ending=True)
        marks.append((unit, round(start, 3), round(max(end, start + 0.05), 3)))
        spent += span
    return snap_to_pauses(marks, pauses)
