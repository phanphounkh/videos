"""Synthesises the renderer's sound effects and background music.

    python3 scripts/make_audio.py        (from renderer/; standard library only)

WHY generated rather than downloaded: every sound here is made from sine waves,
noise and plucked strings by this script, so there is no licence to track and
anyone can regenerate or tweak them. Output is deterministic (fixed seed).

Writes public/studio/sfx/*.wav and public/studio/music/bed.wav. The music is
WAV, not MP3, on purpose: MP3 encoders pad the start and end with silence, which
is heard as a gap every time the loop restarts. To use a real track instead,
replace bed.wav with any loopable royalty-free WAV.
"""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 32_000
OUT = Path(__file__).resolve().parent.parent / "public" / "studio"
rng = random.Random(7)


def write_wav(path: Path, samples: list[float], peak: float = 0.9) -> None:
    top = max(1e-9, max(abs(s) for s in samples))
    scale = peak / top
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(b"".join(struct.pack("<h", int(s * scale * 32767)) for s in samples))


def lowpass(samples: list[float], cutoff: list[float] | float) -> list[float]:
    """One-pole low-pass; `cutoff` may vary per sample (Hz)."""
    out, state = [], 0.0
    for i, s in enumerate(samples):
        fc = cutoff[i] if isinstance(cutoff, list) else cutoff
        a = 1 - math.exp(-2 * math.pi * fc / RATE)
        state += a * (s - state)
        out.append(state)
    return out


def noise(n: int) -> list[float]:
    return [rng.uniform(-1, 1) for _ in range(n)]


# ---------------------------------------------------------------- effects
def whoosh() -> list[float]:
    n = int(0.5 * RATE)
    env = [math.sin(math.pi * (i / n)) ** 2 for i in range(n)]
    sweep = [300 + 5000 * math.sin(math.pi * i / n) ** 3 for i in range(n)]
    lp = lowpass(noise(n), sweep)
    hp = lowpass(lp, 250)
    return [(a - b) * e for a, b, e in zip(lp, hp, env, strict=True)]


def pop() -> list[float]:
    n = int(0.16 * RATE)
    out, phase = [], 0.0
    for i in range(n):
        t = i / RATE
        freq = 280 + 900 * math.exp(-t * 45)
        phase += 2 * math.pi * freq / RATE
        out.append(math.sin(phase) * math.exp(-t * 28))
    return out


def ding() -> list[float]:
    n = int(1.4 * RATE)
    partials = [(1.0, 1.0, 3.2), (2.76, 0.45, 5.0), (5.4, 0.22, 8.0), (2.0, 0.3, 4.0)]
    base = 1318.5  # E6
    return [
        sum(
            amp * math.sin(2 * math.pi * base * ratio * i / RATE) * math.exp(-decay * i / RATE)
            for ratio, amp, decay in partials
        )
        * min(1.0, i / 40)
        for i in range(n)
    ]


def impact() -> list[float]:
    n = int(0.7 * RATE)
    out, phase = [], 0.0
    hiss = lowpass(noise(n), 1800)
    for i in range(n):
        t = i / RATE
        freq = 38 + 95 * math.exp(-t * 14)
        phase += 2 * math.pi * freq / RATE
        out.append(math.tanh(1.8 * math.sin(phase)) * math.exp(-t * 5) + hiss[i] * math.exp(-t * 30) * 0.6)
    return out


# ------------------------------------------------------------------ music
BPM = 96
BEAT = 60 / BPM
# I - V - vi - IV in C, two bars each: 32 beats, 20 seconds, loops seamlessly.
CHORDS = [(48, [60, 64, 67]), (43, [59, 62, 67]), (45, [57, 60, 64]), (41, [57, 60, 65])]
LOOP_BEATS = 32


def midi(note: float) -> float:
    return 440 * 2 ** ((note - 69) / 12)


def add(buf: list[float], start: float, samples: list[float], gain: float) -> None:
    """Mixes in at `start` seconds, wrapping round so tails loop seamlessly."""
    offset = int(start * RATE)
    for i, s in enumerate(samples):
        buf[(offset + i) % len(buf)] += s * gain


def pluck(freq: float, seconds: float, brightness: float = 0.5) -> list[float]:
    """Karplus-Strong plucked string."""
    period = max(2, int(RATE / freq))
    ring = lowpass(noise(period), 1500 + 4000 * brightness)
    out = []
    for i in range(int(seconds * RATE)):
        j = i % period
        nxt = ring[(j + 1) % period]
        value = ring[j]
        ring[j] = 0.497 * (value + nxt)
        out.append(value)
    return out


def pad(freqs: list[float], seconds: float) -> list[float]:
    n = int(seconds * RATE)
    attack, release = 0.5 * RATE, 0.8 * RATE
    out = []
    for i in range(n):
        env = min(1.0, i / attack, (n - i) / release)
        t = i / RATE
        value = 0.0
        for f in freqs:
            for detune in (0.997, 1.003):
                ph = 2 * math.pi * f * detune * t
                value += math.sin(ph) + 0.25 * math.sin(2 * ph)
        out.append(value * env)
    return lowpass(out, 1400)


def bass(freq: float, seconds: float) -> list[float]:
    n = int(seconds * RATE)
    return [
        math.tanh(1.5 * math.sin(2 * math.pi * freq * i / RATE)) * min(1.0, i / 200) * math.exp(-2.2 * i / RATE)
        for i in range(n)
    ]


def kick() -> list[float]:
    n, out, phase = int(0.3 * RATE), [], 0.0
    for i in range(n):
        t = i / RATE
        phase += 2 * math.pi * (45 + 75 * math.exp(-t * 30)) / RATE
        out.append(math.sin(phase) * math.exp(-t * 11))
    return out


def snap() -> list[float]:
    n = int(0.18 * RATE)
    raw = noise(n)
    body = lowpass(raw, 3500)
    low = lowpass(body, 700)
    return [(b - lo) * math.exp(-i / RATE * 26) for i, (b, lo) in enumerate(zip(body, low, strict=True))]


def hat() -> list[float]:
    n = int(0.05 * RATE)
    raw = noise(n)
    low = lowpass(raw, 6000)
    return [(r - lo) * math.exp(-i / RATE * 90) for i, (r, lo) in enumerate(zip(raw, low, strict=True))]


def music() -> list[float]:
    buf = [0.0] * int(LOOP_BEATS * BEAT * RATE)
    k, s, h = kick(), snap(), hat()
    for index, (root, tones) in enumerate(CHORDS):
        bar = index * 8 * BEAT
        add(buf, bar, pad([midi(n) for n in tones], 8 * BEAT + 0.6), 0.05)
        for beat in range(8):
            t = bar + beat * BEAT
            if beat % 2 == 0:
                add(buf, t, bass(midi(root), BEAT * 1.6), 0.32)
            add(buf, t, k, 0.55 if beat % 2 == 0 else 0.0)
            if beat % 2 == 1:
                add(buf, t, s, 0.22)
            add(buf, t + BEAT / 2, h, 0.10)
            add(buf, t, h, 0.05)
        # Arpeggio: chord tones up an octave, eighth notes, gently varied.
        pattern = [0, 1, 2, 1, 0, 2, 1, 2]
        for step in range(16):
            note = tones[pattern[step % 8]] + 12 + (12 if step in (6, 14) else 0)
            add(buf, bar + step * BEAT / 2, pluck(midi(note), 0.9, 0.35 + 0.1 * (step % 3)), 0.30)
    # Soft bus compression so the bed sits evenly under the voice.
    return [math.tanh(1.3 * v) for v in buf]


def main() -> None:
    sfx = OUT / "sfx"
    write_wav(sfx / "whoosh.wav", whoosh(), 0.8)
    write_wav(sfx / "pop.wav", pop(), 0.8)
    write_wav(sfx / "ding.wav", ding(), 0.6)
    write_wav(sfx / "impact.wav", impact(), 0.9)

    write_wav(OUT / "music" / "bed.wav", music(), 0.85)
    for path in sorted(OUT.rglob("*.*")):
        print(f"{path.relative_to(OUT.parent)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
