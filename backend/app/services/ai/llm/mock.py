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
from app.services.ai.speech.timing import estimate_duration

log = get_logger(__name__)

# Offline story beats. They are intentionally generic; production uses
# OpenRouter because only a real model can understand arbitrary story prompts.
EN_BEATS = [
    "Without warning, {topic} changed everything, and nobody nearby was ready for it.",
    "Only a few hours earlier, the day had seemed completely normal.",
    "Then one small decision created a problem that could no longer be ignored.",
    "Every attempt to fix it made the situation stranger and more urgent.",
    "Just when there seemed to be no way out, the hidden truth finally appeared.",
    "There was only one choice left, and it had to be made immediately.",
    "What happened next turned the whole story in an unexpected direction.",
    "The ending surprised everyone. What would you have done in that moment?",
]

# Khmer beats: real Khmer script, not transliteration, so the Khmer path
# (fonts, caption segmentation, UTF-8) is exercised from the very first phase.
KM_BEATS = [
    "ភ្លាមៗនោះ {topic} បានផ្លាស់ប្តូរគ្រប់យ៉ាង ហើយគ្មាននរណាម្នាក់បានត្រៀមខ្លួនទេ។",
    "ប៉ុន្មានម៉ោងមុន ថ្ងៃនោះនៅធម្មតា ហើយគ្មានអ្នកណាសង្ស័យអ្វីឡើយ។",
    "បន្ទាប់មក ការសម្រេចចិត្តតូចមួយបានបង្កបញ្ហាដែលមិនអាចមើលរំលងបាន។",
    "រាល់ការព្យាយាមដោះស្រាយ បែរជាធ្វើឱ្យស្ថានការណ៍កាន់តែចម្លែក និងបន្ទាន់។",
    "ពេលដែលគ្មានផ្លូវចេញ ការពិតដែលលាក់បាំងក៏បានបង្ហាញខ្លួន។",
    "នៅសល់តែជម្រើសមួយ ហើយត្រូវសម្រេចចិត្តភ្លាមៗ។",
    "អ្វីដែលកើតឡើងបន្ទាប់ បានបង្វែរសាច់រឿងទៅទិសដែលគ្មានអ្នកណានឹកស្មាន។",
    "ចុងបញ្ចប់បានធ្វើឱ្យគ្រប់គ្នាភ្ញាក់ផ្អើល។ បើជាអ្នក អ្នកនឹងធ្វើយ៉ាងម៉េច?",
]

VISUAL_BEATS = [
    "animated cold open at the most surprising moment of {topic}, dramatic close-up",
    "animated establishing shot before the trouble begins, warm Cambodian atmosphere",
    "animated character making a risky choice, expressive pose, dynamic camera",
    "animated escalating trouble, fast movement, strong emotional reaction",
    "animated twist reveal, dramatic lighting and surprised character expression",
    "animated decisive action at the point of no return, cinematic framing",
    "animated climax with energetic motion and high contrast lighting",
    "animated emotional or funny payoff, memorable final reaction shot",
]

ON_SCREEN_EN = ["Wait—what happened?", "Hours earlier", "The mistake", "It gets worse",
                "The hidden truth", "One last choice", "No turning back", "What would you do?"]
ON_SCREEN_KM = ["មានអ្វីកើតឡើង?", "ប៉ុន្មានម៉ោងមុន", "កំហុសមួយ", "កាន់តែធ្ងន់",
                "ការពិតលេចឡើង", "ជម្រើសចុងក្រោយ", "គ្មានផ្លូវថយ", "បើជាអ្នកវិញ?"]

# Extra teaching beats let the offline provider fill longer lessons with
# narration that matches the requested scene duration. Without these, a
# five-minute script still contained only eight short sentences and the TTS
# duration reconciliation collapsed the finished video to under a minute.
EN_DETAILS = [
    "The room went quiet as everyone tried to understand what they had just seen.",
    "A nervous glance revealed that someone knew more than they were willing to admit.",
    "Time was running out, and waiting any longer would make the consequences worse.",
    "For one brief moment, the obvious answer looked completely wrong.",
    "That detail changed the meaning of everything that had happened before.",
    "Even then, nobody could predict the choice that came next.",
    "The tension broke only when one character finally acted instead of hesitating.",
    "That decision carried the story directly toward its final surprise.",
]

KM_DETAILS = [
    "បន្ទប់ទាំងមូលស្ងាត់ជ្រងំ ខណៈគ្រប់គ្នាព្យាយាមយល់អ្វីដែលទើបបានឃើញ។",
    "ក្រសែភ្នែកភ័យៗមួយបានបង្ហាញថា មាននរណាម្នាក់ដឹងច្រើនជាងអ្វីដែលគេព្រមប្រាប់។",
    "ពេលវេលាកាន់តែខើច ហើយការរង់ចាំនឹងធ្វើឱ្យផលវិបាកកាន់តែធ្ងន់។",
    "មួយភ្លែតនោះ ចម្លើយដែលមើលទៅច្បាស់ បែរជាខុសទាំងស្រុង។",
    "ព័ត៌មានលម្អិតនោះ បានផ្លាស់ប្តូរអត្ថន័យនៃអ្វីគ្រប់យ៉ាងដែលកើតឡើងមុននេះ។",
    "ទោះយ៉ាងណា គ្មាននរណាម្នាក់អាចទាយជម្រើសដែលកើតឡើងបន្ទាប់បានទេ។",
    "ភាពតានតឹងបានធូរស្រាល ពេលតួអង្គម្នាក់ឈប់ស្ទាក់ស្ទើរ ហើយចាប់ផ្តើមធ្វើសកម្មភាព។",
    "ការសម្រេចចិត្តនោះ បាននាំសាច់រឿងឆ្ពោះទៅកាន់ការភ្ញាក់ផ្អើលចុងក្រោយ។",
]


def _paced_narration(base: str, topic: str, target_seconds: float, *, language: str) -> str:
    """Add useful teaching detail until speech approximately fills the scene."""
    details = KM_DETAILS if language.lower().startswith("km") else EN_DETAILS
    parts = [base]
    index = 0
    # Leave a small visual pause at the end of every scene. The cap is defensive
    # in case timing constants or templates are changed independently later.
    target = max(0.6, target_seconds - 0.5)
    while estimate_duration(" ".join(parts), language=language) < target and index < 40:
        parts.append(details[index % len(details)].format(topic=topic))
        index += 1
    return " ".join(parts)


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def generate_script(self, request: ScriptRequest) -> GeneratedScript:
        topic = self._topic(request.prompt)
        is_khmer = request.language.lower().startswith("km")
        beats = KM_BEATS if is_khmer else EN_BEATS
        titles = ON_SCREEN_KM if is_khmer else ON_SCREEN_EN
        # The offline provider cannot translate an English topic. Keep spoken
        # Khmer fully Khmer instead of making the Khmer voice read Latin words.
        narration_topic = "ប្រធានបទនេះ" if is_khmer and topic.isascii() else topic

        # Image models are trained on English text, so a visual prompt must stay
        # ASCII. A Khmer (or any non-Latin) topic cannot be pasted into it, so
        # fall back to a neutral English subject for the imagery.
        visual_topic = topic if topic.isascii() else f"{request.style} subject matter"

        scene_count = max(3, min(len(beats), round(request.duration / 7)))
        per_scene = round(request.duration / scene_count, 2)

        scenes = [
            GeneratedScene(
                scene_number=index + 1,
                narration=_paced_narration(
                    beats[index % len(beats)].format(topic=narration_topic),
                    narration_topic,
                    per_scene,
                    language=request.language,
                ),
                visual_prompt=VISUAL_BEATS[index % len(VISUAL_BEATS)].format(topic=visual_topic),
                on_screen_text=titles[index % len(titles)],
                duration=per_scene,
                transition="fade",
            )
            for index in range(scene_count)
        ]

        title = f"រឿងខ្លី៖ {narration_topic}" if is_khmer else topic.title()
        script = GeneratedScript(
            title=title[:300],
            description=f"A connected {request.style} entertainment story inspired by {topic}.",
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
