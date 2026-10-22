"""Provider interfaces and their shared result types.

Every external AI capability is expressed as a small ABC here. Application
services depend on these abstractions only, so:
  - a provider can be swapped through configuration (mock -> OpenRouter),
  - tests can inject a fake without touching the network or spending money,
  - Khmer-specific providers can be added per language later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.schemas.generation import GeneratedScript


@dataclass(slots=True)
class ScriptRequest:
    prompt: str
    duration: int
    language: str
    style: str
    tone: str | None = None
    audience: str | None = None
    purpose: str = "story"
    # Whether an animated host appears; without one the narration is a voice-over.
    presenter: bool = True


@dataclass(slots=True)
class ImageResult:
    data: bytes
    mime_type: str
    width: int
    height: int
    provider: str
    # True when the bytes are a locally drawn placeholder, not a real generation.
    is_placeholder: bool = False


@dataclass(slots=True)
class WordMark:
    """When one spoken unit (an English word, a Khmer phrase) is heard, in seconds."""

    text: str
    start: float
    end: float


@dataclass(slots=True)
class AudioResult:
    data: bytes
    mime_type: str
    duration: float
    provider: str
    voice: str
    is_placeholder: bool = False
    # Speech marks reported by the provider. Empty when it gives none, in which
    # case captions fall back to estimated timings.
    marks: list[WordMark] = field(default_factory=list)


@dataclass(slots=True)
class TranscriptSegment:
    text: str
    start: float
    end: float


@dataclass(slots=True)
class TranscriptResult:
    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str = "en"
    provider: str = "unknown"


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate_script(self, request: ScriptRequest) -> GeneratedScript:
        """Return a VALIDATED script. Implementations must not return raw text."""


class ImageProvider(ABC):
    name: str

    @abstractmethod
    async def generate_image(
        self, prompt: str, width: int, height: int, *, style: str | None = None
    ) -> ImageResult: ...


class TTSProvider(ABC):
    name: str

    @abstractmethod
    async def generate(
        self, text: str, language: str, voice: str, *, style: str | None = None
    ) -> AudioResult:
        """`style` is an optional delivery direction ("whispering, tense").
        Providers that cannot act on it ignore it."""

    @abstractmethod
    def supports_language(self, language: str) -> bool: ...


class STTProvider(ABC):
    name: str

    @abstractmethod
    async def transcribe(self, audio: bytes, language: str) -> TranscriptResult: ...


class VideoProvider(ABC):
    """Text-to-video / image-to-video. Intentionally unimplemented for the MVP."""

    name: str

    @abstractmethod
    async def generate_clip(
        self, prompt: str, duration: float, width: int, height: int
    ) -> bytes: ...
