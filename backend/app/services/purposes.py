"""Video purposes: the templates that make one engine serve many kinds of video.

A purpose decides how the script is written (the prompt guide), what the video
looks like (presenter on or off, closing call to action) and sensible defaults
for the create form (aspect ratio, length, style, tone). Everything the frontend
shows about purposes comes from `PURPOSES` through GET /api/purposes, so adding
a purpose is one entry here and nothing else.
"""

from dataclasses import dataclass

from app.models.enums import AspectRatio, VideoPurpose, VideoStyle


@dataclass(frozen=True, slots=True)
class PurposeTemplate:
    key: VideoPurpose
    label: str
    description: str
    # Defaults offered by the create form; the user can change all of them.
    aspect_ratio: AspectRatio
    duration: int
    style: VideoStyle
    tone: str
    audience: str
    # Whether the animated host is on screen by default.
    presenter: bool
    # Closing call to action. None keeps the classic "Follow" button.
    cta_text: str | None
    # Seconds per scene the script should aim for.
    scene_seconds: int
    example_prompt: str
    # Purpose-specific writing instructions appended to the shared system prompt.
    guide: str


PURPOSES: dict[VideoPurpose, PurposeTemplate] = {
    VideoPurpose.STORY: PurposeTemplate(
        key=VideoPurpose.STORY,
        label="Story",
        description="A connected story with a hook, twist and payoff, told by a host.",
        aspect_ratio=AspectRatio.PORTRAIT,
        duration=60,
        style=VideoStyle.STORYTELLING,
        tone="funny, emotional, and fast-paced",
        audience="social media viewers",
        presenter=True,
        cta_text=None,
        scene_seconds=10,
        example_prompt="A funny short story about a young man who thinks his cat can talk.",
        guide="""Purpose: entertaining story for TikTok, Facebook Reels and YouTube Shorts.
Turn the user's exact idea into one complete, emotionally engaging story, not a
lesson, explainer or list.
- Follow the prompt faithfully: keep its subject, characters, setting, genre and
  requested events. Build ONE continuous story; every scene causes the next.
- Arc across the timeline: hook, character desire and setup, rising complications,
  a meaningful twist, climax, a satisfying emotional or funny payoff, then a brief
  natural question that invites comments.
- Characters' words are short quoted lines the narrator performs, at most one or
  two per scene, clearly introduced. Never write a script for actors.
- Every three or four scenes add a small surprise that keeps viewers watching.
- Keep claims responsible. For real culture, history or places use only
  well-established facts. Do not fabricate real news or present fiction as fact.""",
    ),
    VideoPurpose.PRODUCT_DEMO: PurposeTemplate(
        key=VideoPurpose.PRODUCT_DEMO,
        label="Product demo",
        description="Show what a product does, why it matters, and what to do next.",
        aspect_ratio=AspectRatio.LANDSCAPE,
        duration=60,
        style=VideoStyle.TECHNOLOGY,
        tone="clear, confident and friendly",
        audience="potential customers",
        presenter=True,
        cta_text="Try it today",
        scene_seconds=8,
        example_prompt=(
            "Demo of Sorya, an app that turns a text prompt into a finished video "
            "for small businesses."
        ),
        guide="""Purpose: product demo or launch video for potential customers.
- Use ONLY facts the user gave about the product. Never invent features, prices,
  statistics, customer names, awards or testimonials. If a detail is missing, talk
  about the benefit in general terms instead of making one up.
- Structure: hook with the customer's problem (scene 1), the product in one line,
  two to four key features each shown as a concrete benefit ("save an hour a day"),
  a short how-it-works moment, then a closing call to action.
- Benefits before features. Plain words, no hype or superlatives that cannot be
  backed up. One idea per scene.
- on_screen_text is the feature or benefit name in at most 4 words.
- visual_prompt describes a clean product-style visual: the interface, the device,
  the product in use, or the result. No people's faces needed.
- The last scene is the call to action and says what the viewer should do next.""",
    ),
    VideoPurpose.SOCIAL_POST: PurposeTemplate(
        key=VideoPurpose.SOCIAL_POST,
        label="Social media post",
        description="A short, punchy vertical video built to stop the scroll.",
        aspect_ratio=AspectRatio.PORTRAIT,
        duration=30,
        style=VideoStyle.SOCIAL_MEDIA,
        tone="energetic, punchy and relatable",
        audience="social media viewers",
        presenter=True,
        cta_text=None,
        scene_seconds=5,
        example_prompt="Three quick tips to stay focused while studying at home.",
        guide="""Purpose: a short social media post (Reels, TikTok, Shorts, Facebook).
- The first line must stop the scroll within two seconds: a bold claim, a question
  or a surprising fact. Never open with a greeting or an introduction.
- Short, punchy lines. One idea per scene, five seconds each. No filler.
- Deliver real value or a real feeling: a tip, a list, a before/after, a take, a
  joke. Do not pad. A numbered list ("3 tips") must have exactly that many items.
- Do not fabricate statistics, quotes or news.
- on_screen_text is the key phrase for the scene in at most 4 words.
- End with a clear single ask: follow, save, share or comment.""",
    ),
    VideoPurpose.CREATOR: PurposeTemplate(
        key=VideoPurpose.CREATOR,
        label="Creator video",
        description="Tutorials, commentary and listicles for YouTube and Shorts creators.",
        aspect_ratio=AspectRatio.LANDSCAPE,
        duration=180,
        style=VideoStyle.SOCIAL_MEDIA,
        tone="conversational, personal and upbeat",
        audience="a creator's subscribers",
        presenter=True,
        cta_text="Subscribe",
        scene_seconds=10,
        example_prompt="5 editing habits that made my videos look more professional.",
        guide="""Purpose: a video from a content creator (YouTube, Shorts, tutorials,
commentary, listicles, vlog-style talks).
- Write in the creator's own first-person voice, talking to the viewer like a friend.
- Open with the promise of the video and a reason to stay to the end, then deliver
  the content in clearly separated segments, each opening with a short beat that
  signals the change ("Tip number two", "Here is where it gets interesting").
- Use pattern interrupts every few scenes: a question, a surprise, a quick recap.
- Be specific and useful: concrete steps, examples and reasons, not generalities.
- Do not invent personal experiences, results or statistics the user did not give.
- on_screen_text marks the current segment or key takeaway in at most 5 words.
- Close with a short recap and an invitation to subscribe, like or comment.""",
    ),
    VideoPurpose.EXPLAINER: PurposeTemplate(
        key=VideoPurpose.EXPLAINER,
        label="Explainer",
        description="Teach a topic clearly, step by step.",
        aspect_ratio=AspectRatio.LANDSCAPE,
        duration=90,
        style=VideoStyle.EDUCATIONAL,
        tone="clear, patient and encouraging",
        audience="curious beginners",
        presenter=True,
        cta_text=None,
        scene_seconds=10,
        example_prompt="Explain how vaccines train the immune system, for beginners.",
        guide="""Purpose: educational explainer for beginners.
- Start with a question or a surprising fact that makes the topic matter, then
  teach in a logical order from the simple idea to the detail.
- One idea per scene. Define a term the first time it appears, with an everyday
  example or analogy. Prefer concrete examples to abstractions.
- Use only well-established facts. Do not invent numbers, studies or quotes. If
  something is uncertain or debated, say so.
- on_screen_text is the term or key idea of the scene in at most 4 words.
- Finish with a one-sentence summary of what the viewer now understands.""",
    ),
}

DEFAULT_PURPOSE = VideoPurpose.STORY


def get_purpose(value: str | VideoPurpose | None) -> PurposeTemplate:
    """The template for `value`, falling back to the default for unknown values."""
    try:
        return PURPOSES[VideoPurpose(value)] if value else PURPOSES[DEFAULT_PURPOSE]
    except ValueError:
        return PURPOSES[DEFAULT_PURPOSE]
