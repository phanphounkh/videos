"""Mock LLM provider - MOCK, not a real model.

It builds a deterministic, schema-valid script from the prompt by splitting the
requested duration into scenes. It exists so the whole pipeline (scenes ->
images -> voice -> captions -> render) can be developed, tested and demoed with
no API key and no cost.

It does NOT understand the prompt. Narration is templated around the prompt
text. Switch to the real provider with LLM_PROVIDER=openrouter.
"""

import re

from app.core.logging import get_logger
from app.schemas.generation import GeneratedScene, GeneratedScript
from app.services.ai.base import LLMProvider, ScriptRequest

log = get_logger(__name__)

# Narration templates per scene role. {topic} is the user's prompt, trimmed.
EN_BEATS = [
    "Let's talk about {topic}. Here is what you need to know, in plain language.",
    "First, the basics. {topic} is easier to understand than it first appears.",
    "Here is how it actually works, step by step, with a simple example.",
    "This matters because it already shapes the tools you use every day.",
    "A common misunderstanding is worth clearing up before we go further.",
    "Let's look at one concrete case so the idea becomes memorable.",
    "Put together, these pieces give you the full picture.",
    "That is {topic} in a nutshell. Thanks for watching.",
]

# Khmer beats: real Khmer script, not transliteration, so the Khmer path
# (fonts, caption segmentation, UTF-8) is exercised from the very first phase.
KM_BEATS = [
    "មកនិយាយអំពី {topic}។ នេះជាចំណុចសំខាន់ដែលអ្នកគួរដឹង។",
    "ជាដំបូង យើងមកមើលមូលដ្ឋានគ្រឹះ ដែលងាយស្រួលយល់ជាងការគិត។",
    "នេះជារបៀបដែលវាដំណើរការ ជាជំហានៗ ជាមួយឧទាហរណ៍ងាយៗ។",
    "វាមានសារៈសំខាន់ ព្រោះវាប៉ះពាល់ដល់ជីវិតប្រចាំថ្ងៃរបស់យើង។",
    "មានការយល់ច្រឡំមួយ ដែលយើងគួរបញ្ជាក់ឱ្យបានច្បាស់។",
    "មកមើលករណីជាក់ស្តែងមួយ ដើម្បីងាយចងចាំ។",
    "ពេលដាក់បញ្ចូលគ្នា ចំណុចទាំងនេះបង្ហាញរូបភាពពេញលេញ។",
    "នេះជាសេចក្តីសង្ខេបអំពី {topic}។ អរគុណសម្រាប់ការមើល។",
]

VISUAL_BEATS = [
    "wide establishing shot illustrating {topic}, soft cinematic lighting, clean background",
    "flat vector infographic explaining the fundamentals of {topic}, minimal palette",
    "close-up of a step-by-step diagram about {topic}, shallow depth of field",
    "person using modern technology related to {topic}, warm natural light",
    "split comparison illustration contrasting two ideas about {topic}",
    "single concrete real-world example of {topic}, documentary photography style",
    "abstract geometric composition summarising {topic}, cool tones",
    "calm closing shot with plenty of negative space, related to {topic}",
]

ON_SCREEN_EN = ["What is it?", "The basics", "How it works", "Why it matters",
                "A common myth", "An example", "The big picture", "Thanks for watching"]
ON_SCREEN_KM = ["តើវាជាអ្វី?", "មូលដ្ឋានគ្រឹះ", "របៀបដំណើរការ", "ហេតុអ្វីសំខាន់",
                "ការយល់ច្រឡំ", "ឧទាហរណ៍", "រូបភាពរួម", "អរគុណ"]


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def generate_script(self, request: ScriptRequest) -> GeneratedScript:
        topic = self._topic(request.prompt)
        is_khmer = request.language.lower().startswith("km")
        beats = KM_BEATS if is_khmer else EN_BEATS
        titles = ON_SCREEN_KM if is_khmer else ON_SCREEN_EN

        # Image models are trained on English text, so a visual prompt must stay
        # ASCII. A Khmer (or any non-Latin) topic cannot be pasted into it, so
        # fall back to a neutral English subject for the imagery.
        visual_topic = topic if topic.isascii() else f"{request.style} subject matter"

        scene_count = max(3, min(len(beats), round(request.duration / 7)))
        per_scene = round(request.duration / scene_count, 2)

        scenes = [
            GeneratedScene(
                scene_number=index + 1,
                narration=beats[index % len(beats)].format(topic=topic),
                visual_prompt=VISUAL_BEATS[index % len(VISUAL_BEATS)].format(topic=visual_topic),
                on_screen_text=titles[index % len(titles)],
                duration=per_scene,
                transition="fade",
            )
            for index in range(scene_count)
        ]

        title = topic if is_khmer else f"{topic.title()} Explained"
        script = GeneratedScript(
            title=title[:300],
            description=f"A {request.style} video about {topic}.",
            language=request.language,
            estimated_duration=round(per_scene * scene_count, 2),
            scenes=scenes,
        )
        log.info(
            "script_generated",
            provider=self.name,
            is_mock=True,
            scenes=len(scenes),
            language=request.language,
        )
        return script

    @staticmethod
    def _topic(prompt: str) -> str:
        """Strips instruction boilerplate so the topic reads naturally."""
        cleaned = re.sub(
            r"(?i)\b(create|make|generate|produce)\b|"
            r"\b\d+[- ]?(second|sec|minute|min)s?\b|"
            r"\b(a|an|the|video|about|explaining|explain|for|beginners?)\b",
            " ",
            prompt,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-")
        return cleaned or prompt.strip()[:80]
