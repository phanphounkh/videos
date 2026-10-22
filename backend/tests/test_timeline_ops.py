"""Cutting a window out of a scene (split / trim arithmetic)."""

import pytest

from app.core.exceptions import ValidationError
from app.services.timeline_ops import cut_window

CAPTIONS = [("one two", 0.0, 2.0), ("three four", 2.0, 4.0), ("five six", 4.0, 6.0)]
SPEECH = {
    "narration": "one two three four five six",
    "words": [["one two", 0.0, 2.0], ["three four", 2.0, 4.0], ["five six", 4.0, 6.0]],
    "mouth": list(range(60)),  # 10 samples per second at fps=10
    "fps": 10,
}


def _cut(a: float, b: float, **extra):
    base = {
        "duration": 6.0,
        "narration": "one two three four five six",
        "captions": CAPTIONS,
        "settings": {"speech": SPEECH, "mood": "hook"},
    }
    return cut_window(**{**base, **extra}, a=a, b=b)


def test_first_half_keeps_the_early_captions_and_the_start_offsets() -> None:
    cut = _cut(0, 3)
    assert cut.duration == 3
    assert [c[0] for c in cut.captions] == ["one two", "three four"] or [
        c[0] for c in cut.captions
    ] == ["one two"]
    assert "audio_start" not in cut.settings  # started at 0: nothing to skip


def test_second_half_shifts_captions_and_advances_audio_and_clip_start() -> None:
    cut = _cut(4, 6)
    assert cut.duration == 2
    assert cut.captions == [("five six", 0.0, 2.0)]
    assert cut.narration == "five six"
    assert cut.settings["audio_start"] == 4
    assert cut.settings["trim_start"] == 4


def test_every_caption_lands_on_exactly_one_side_of_a_split() -> None:
    for at in (1.0, 2.0, 2.9, 3.0, 3.1, 5.0):
        left, right = _cut(0, at), _cut(at, 6.0)
        texts = [c[0] for c in left.captions] + [c[0] for c in right.captions]
        assert sorted(texts) == sorted(c[0] for c in CAPTIONS), at


def test_speech_marks_and_mouth_are_cut_in_step_with_captions() -> None:
    cut = _cut(2, 6)
    speech = cut.settings["speech"]
    assert speech["words"] == [["three four", 0.0, 2.0], ["five six", 2.0, 4.0]]
    assert speech["mouth"] == list(range(20, 60))
    assert speech["narration"] == cut.narration  # still trusted by the caption builder
    assert cut.settings["mood"] == "hook"  # generator keys pass through


def test_a_window_with_no_speech_drops_the_speech_data() -> None:
    cut = _cut(0, 6, captions=[], narration="", settings={"speech": SPEECH})
    assert cut.narration == ""
    # whole scene: nothing to cut, speech untouched
    assert "speech" in cut.settings
    empty = _cut(0, 1, captions=[("late", 3.0, 4.0)], narration="late")
    assert "speech" not in empty.settings


def test_whole_scene_is_returned_unchanged() -> None:
    cut = _cut(0, 6)
    assert cut.narration == "one two three four five six"
    assert cut.settings["speech"] == SPEECH
    assert cut.captions == CAPTIONS


def test_layers_are_clipped_shifted_and_dropped() -> None:
    layers = [
        {"id": "a", "start": 0.0, "end": 1.0},  # entirely before the window
        {"id": "b", "start": 1.0, "end": 5.0},  # straddles the start
        {"id": "c", "start": 3.0, "end": 4.0},  # inside
        {"id": "d", "start": 5.5, "end": 6.0},  # after the window
    ]
    cut = _cut(2, 4.5, settings={"layers": layers})
    assert [(layer["id"], layer["start"], layer["end"]) for layer in cut.settings["layers"]] == [
        ("b", 0.0, 2.5),
        ("c", 1.0, 2.0),
    ]


def test_repeated_cuts_accumulate_the_offsets() -> None:
    first = _cut(1, 6)
    second = cut_window(
        duration=first.duration, narration=first.narration, captions=first.captions,
        settings=first.settings, a=2, b=first.duration,
    )
    assert second.settings["audio_start"] == 3


@pytest.mark.parametrize(("a", "b"), [(-1, 3), (0, 7), (3, 3.1), (5.95, 6)])
def test_invalid_windows_are_rejected(a: float, b: float) -> None:
    with pytest.raises(ValidationError):
        _cut(a, b)
