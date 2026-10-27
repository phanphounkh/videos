"""The template gallery: ready-made starting points, grouped by who they are for.

A template is a purpose (see purposes.py) plus a concrete idea: Sorya fills in the shape,
length, tone and host from the purpose, and the person can still change everything. The
thumbnails are drawn by the renderer (scripts/render_template_thumbnails.py) and served
by the web app from /templates/<key>.jpg.
"""

from dataclasses import dataclass

CATEGORIES = ("social", "business", "education", "story")


@dataclass(frozen=True, slots=True)
class Template:
    key: str
    title: str
    category: str
    purpose: str
    aspect_ratio: str
    duration: int
    prompt: str
    # The big words on the thumbnail.
    headline: str


TEMPLATES: tuple[Template, ...] = (
    Template(
        "viral-hook",
        "Viral hook",
        "social",
        "social_post",
        "9:16",
        30,
        "Three surprising facts about coffee that will make you rethink your morning cup.",
        "3 coffee facts",
    ),
    Template(
        "behind-the-scenes",
        "Behind the scenes",
        "social",
        "social_post",
        "9:16",
        30,
        "A behind-the-scenes look at how a small bakery prepares for opening at 6am.",
        "Before we open",
    ),
    Template(
        "travel-reel",
        "Travel reel",
        "social",
        "social_post",
        "9:16",
        30,
        "A 30-second reel of the best street food and sunrise spots in Phnom Penh.",
        "Phnom Penh in 30s",
    ),
    Template(
        "product-launch",
        "Product launch",
        "business",
        "product_demo",
        "16:9",
        60,
        "Launch video for a new mobile app that helps small shops track their stock.",
        "Meet StockEasy",
    ),
    Template(
        "feature-tour",
        "Feature tour",
        "business",
        "product_demo",
        "16:9",
        60,
        "A quick tour of the three features customers love most in our scheduling tool.",
        "Three features",
    ),
    Template(
        "business-pitch",
        "Business pitch",
        "business",
        "explainer",
        "16:9",
        90,
        "A 90-second pitch for a local delivery startup: the problem, our idea and the ask.",
        "Our pitch",
    ),
    Template(
        "how-it-works",
        "How it works",
        "education",
        "explainer",
        "16:9",
        60,
        "Explain how solar panels turn sunlight into electricity, for school students.",
        "How solar works",
    ),
    Template(
        "lesson-recap",
        "Lesson recap",
        "education",
        "explainer",
        "9:16",
        60,
        "A one-minute recap of the water cycle with simple examples a child can remember.",
        "The water cycle",
    ),
    Template(
        "study-tips",
        "Study tips",
        "education",
        "creator",
        "9:16",
        60,
        "Five study habits that helped me pass my exams, explained quickly.",
        "5 study habits",
    ),
    Template(
        "funny-story",
        "Funny story",
        "story",
        "story",
        "9:16",
        60,
        "A funny short story about a young man who thinks his cat can talk.",
        "Can the cat talk?",
    ),
    Template(
        "bedtime-tale",
        "Bedtime tale",
        "story",
        "story",
        "9:16",
        90,
        "A gentle bedtime story about a little elephant who is afraid of the dark.",
        "The brave elephant",
    ),
    Template(
        "youtube-intro",
        "YouTube intro",
        "story",
        "creator",
        "16:9",
        30,
        "A punchy channel intro for a creator who reviews budget gadgets every week.",
        "Gadget Review",
    ),
)

BY_KEY = {t.key: t for t in TEMPLATES}

# One colour mood per template so the gallery is not a wall of the same dark card. Used by the
# thumbnail script and by the live hover preview, so both draw the same picture.
MOODS = ("hook", "setup", "rising", "twist", "climax", "payoff")


def mood_of(index: int) -> str:
    return MOODS[index % len(MOODS)]
