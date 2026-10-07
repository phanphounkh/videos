"""Caption segmentation and timing, including the Khmer rules.

The Khmer tests exist because Khmer has no spaces between words: anything that
splits on whitespace or counts "words" produces nonsense for Khmer.
"""

import unicodedata

from app.services.ai.speech.timing import (
    distribute_timings,
    estimate_duration,
    is_khmer,
    khmer_clusters,
    split_into_segments,
)

KHMER = "ការរៀនម៉ាស៊ីនអនុញ្ញាតឱ្យកុំព្យូទ័ររៀនពីទិន្នន័យ។ វាមានប្រយោជន៍ច្រើន។"
ENGLISH = "Machine learning lets computers learn from data. It is useful in many fields."


def test_is_khmer_detects_the_script() -> None:
    assert is_khmer(KHMER)
    assert not is_khmer(ENGLISH)


def test_duration_scales_with_length() -> None:
    assert estimate_duration("one two three") < estimate_duration(ENGLISH)
    assert estimate_duration("", language="en") > 0


def test_khmer_duration_uses_characters_not_words() -> None:
    # Khmer is one whitespace-"word", so a word-based estimate would be absurdly
    # short. Character-based estimation must give a sane multi-second duration.
    assert estimate_duration(KHMER, language="km") > 3


def test_english_segments_never_split_a_word() -> None:
    segments = split_into_segments(ENGLISH)
    assert segments
    for segment in segments:
        assert segment.strip() == segment
    rejoined = " ".join(segments).replace("  ", " ")
    for word in ENGLISH.replace(".", "").split():
        assert word in rejoined


def test_khmer_segments_are_bounded_and_non_empty() -> None:
    segments = split_into_segments(KHMER, language="km")
    assert len(segments) >= 2
    assert all(segment for segment in segments)
    assert all(len(segment) <= 40 for segment in segments)


def test_timings_cover_the_whole_duration_without_gaps() -> None:
    segments = split_into_segments(ENGLISH)
    timings = distribute_timings(segments, 10.0)

    assert timings[0][1] == 0.0
    assert timings[-1][2] == 10.0
    for (_, _, end), (_, next_start, _) in zip(timings, timings[1:], strict=False):
        assert abs(end - next_start) < 1e-6  # contiguous, no overlap, no gap


def test_timings_are_monotonic() -> None:
    timings = distribute_timings(split_into_segments(KHMER, language="km"), 7.5, language="km")
    for text, start, end in timings:
        assert end > start
        assert text


def test_empty_narration_produces_no_captions() -> None:
    assert split_into_segments("   ") == []
    assert distribute_timings([], 5.0) == []


def test_khmer_clusters_keep_dependent_signs_attached() -> None:
    # "ការ" is ក + ា + រ : the vowel sign must stay with its base consonant.
    clusters = khmer_clusters("ការ")
    assert clusters == ["កា", "រ"]
    # Nothing is lost or duplicated.
    assert "".join(khmer_clusters(KHMER)) == KHMER


def test_khmer_clusters_keep_coeng_stacks_together() -> None:
    # ស + COENG + ត  -> one stacked cluster, never split in the middle.
    stacked = "ស\u17d2ត"
    assert khmer_clusters(stacked) == [stacked]


def test_khmer_segments_never_start_with_a_combining_mark() -> None:
    """A caption starting with a dangling vowel sign is broken Khmer."""
    long_khmer = (
        "ការរៀនម៉ាស៊ីនអនុញ្ញាតឱ្យកុំព្យូទ័ររៀនពីទិន្នន័យដោយគ្មានការសរសេរកូដជាក់លាក់"
        "ហើយវាកំពុងផ្លាស់ប្តូរពិភពលោកយ៉ាងឆាប់រហ័ស"
    )
    for segment in split_into_segments(long_khmer, language="km"):
        first = segment[0]
        assert not unicodedata.combining(first)
        assert unicodedata.category(first) not in {"Mn", "Mc"}
        assert first != "\u17d2"
