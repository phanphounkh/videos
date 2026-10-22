"""Caption segmentation and timing, including the Khmer rules.

The Khmer tests exist because Khmer has no spaces between words: anything that
splits on whitespace or counts "words" produces nonsense for Khmer.
"""

import unicodedata

from app.services.ai.speech.timing import (
    align_marks,
    captions_from_marks,
    distribute_timings,
    estimate_duration,
    find_pauses,
    is_khmer,
    khmer_clusters,
    marks_from_pauses,
    snap_to_pauses,
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
        "ការរៀនម៉ាស៊ីនអនុញ្ញាតឱ្យកុំព្យូទ័ររៀនពីទិន្នន័យដោយគ្មានការសរសេរកូដជាក់លាក់ហើយវាកំពុងផ្លាស់ប្តូរពិភពលោកយ៉ាងឆាប់រហ័ស"
    )
    for segment in split_into_segments(long_khmer, language="km"):
        first = segment[0]
        assert not unicodedata.combining(first)
        assert unicodedata.category(first) not in {"Mn", "Mc"}
        assert first != "\u17d2"


def test_align_marks_restores_the_written_punctuation() -> None:
    narration = '"Do you like cola?" he asked.'
    marks = [
        ("Do", 0.1, 0.25),
        ("you", 0.26, 0.36),
        ("like", 0.37, 0.6),
        ("cola", 0.62, 1.07),
        ("he", 1.9, 2.1),
        ("asked", 2.1, 2.4),
    ]
    tokens = align_marks(narration, marks)
    assert [t for t, _, _ in tokens] == ['"Do', "you", "like", 'cola?"', "he", "asked."]
    assert tokens[3][1:] == (0.62, 1.07)


def test_align_marks_keeps_unmatched_marks() -> None:
    assert align_marks("hello", [("hello", 0.0, 0.3), ("ghost", 0.3, 0.5)])[1][0] == "ghost"


def test_latin_captions_follow_speech_and_break_on_pauses() -> None:
    tokens = [
        ("Do", 0.1, 0.25),
        ("you", 0.26, 0.36),
        ("like", 0.37, 0.6),
        ("cola?", 0.62, 1.07),
        ("he", 1.9, 2.1),
        ("asked.", 2.1, 2.4),
    ]
    captions = captions_from_marks(tokens, 3.0)
    assert [c[0] for c in captions] == ["Do you like cola?", "he asked."]
    # Starts at the first spoken word, holds until the next line, ends with the scene.
    assert captions[0][1:] == (0.1, 1.9)
    assert captions[-1][2] == 3.0


def test_latin_captions_are_short() -> None:
    words = "one two three four five six seven eight nine".split()
    tokens = [(w, i * 0.3, i * 0.3 + 0.25) for i, w in enumerate(words)]
    for text, _, _ in captions_from_marks(tokens, 3.0):
        assert len(text.split()) <= 4


def test_long_khmer_phrase_is_split_within_its_spoken_time() -> None:
    phrase = "តើអ្នកចូលចិត្តកូរ៉ូឡាដែរឬទេ?ការរៀនម៉ាស៊ីនអនុញ្ញាត"
    marks = [(phrase, 0.125, 3.0), ("គាត់បានសួរ។", 3.2, 4.0)]
    captions = captions_from_marks(marks, 4.5, language="km")
    assert len(captions) >= 3
    assert "".join(c[0] for c in captions[:-1]) == phrase
    assert captions[0][1] == 0.125
    assert captions[-2][2] == 3.2  # held until the next phrase is spoken
    for text, start, end in captions:
        assert end > start
        assert not unicodedata.combining(text[0])


def test_no_marks_no_captions() -> None:
    assert captions_from_marks([], 5.0) == []


def test_pauses_are_found_in_a_loudness_envelope() -> None:
    envelope = [0] * 9 + [80] * 30 + [0] * 12 + [70] * 30 + [3, 0]
    assert find_pauses(envelope, 30) == [(0.0, 0.3), (1.3, 1.7)]


def test_boundaries_snap_to_real_pauses() -> None:
    # Measured on real Gemini output: the aligner started phrases up to 0.34 s early.
    marks = [("អូ!", 0.08, 0.48), ("តើអ្នកដឹងទេ?", 0.53, 1.25), ("នៅថ្ងៃ", 1.63, 2.6)]
    pauses = [(0.0, 0.27), (0.53, 0.87), (1.4, 1.73)]
    assert snap_to_pauses(marks, pauses) == [
        ("អូ!", 0.27, 0.53),
        ("តើអ្នកដឹងទេ?", 0.87, 1.4),
        ("នៅថ្ងៃ", 1.73, 2.6),
    ]


def test_far_pauses_are_ignored_and_order_is_preserved() -> None:
    marks = [("a", 0.0, 1.0), ("b", 1.0, 2.0)]
    assert snap_to_pauses(marks, [(5.0, 5.5)]) == marks
    # A snap that would squeeze a phrase to nothing is skipped.
    assert snap_to_pauses([("a", 0.0, 0.1), ("b", 0.1, 0.2)], [(0.0, 0.3)]) == [
        ("a", 0.0, 0.1),
        ("b", 0.1, 0.2),
    ]


def test_one_bad_snap_does_not_cancel_the_others() -> None:
    # The second pause would squeeze "b" to 0.05 s, so only that snap is skipped.
    marks = [("a", 0.1, 0.9), ("b", 1.0, 1.3), ("c", 1.3, 2.0)]
    snapped = snap_to_pauses(marks, [(0.0, 0.3), (1.05, 1.6)])
    assert snapped[0] == ("a", 0.3, 0.9)
    assert snapped[1:] == marks[1:]


def test_leading_silence_only_moves_the_first_phrase() -> None:
    # Real case: the aligner put "អូ!" at 0.00 inside the opening silence.
    snapped = snap_to_pauses([("អូ!", 0.0, 0.5), ("តើ", 0.6, 0.9)], [(0.0, 0.27)])
    assert snapped == [("អូ!", 0.27, 0.5), ("តើ", 0.6, 0.9)]


def test_marks_from_pauses_skip_the_silences() -> None:
    # Two phrases of equal length around a pause: each gets one speech region.
    units = ["ក្មេងប្រុសម្នាក់", "ទៅផ្ទះលោកយាយ"]
    marks = marks_from_pauses(units, [(0.0, 0.3), (1.3, 1.8)], 2.8, language="km")
    assert [m[0] for m in marks] == units
    assert marks[0][1] == 0.3 and marks[0][2] == 1.3
    assert marks[1][1] == 1.8 and abs(marks[1][2] - 2.8) < 0.15


def test_marks_from_pauses_without_speech_is_empty() -> None:
    assert marks_from_pauses(["a"], [(0.0, 2.0)], 2.0) == []
    assert marks_from_pauses([], [], 2.0) == []
