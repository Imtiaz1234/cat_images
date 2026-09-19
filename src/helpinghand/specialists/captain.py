from helpinghand.i18n import t
from helpinghand.specialists.prompts import grok_specialist_reply


class Captain:
    name = "captain"

    async def handle(self, turn, grok) -> str:
        text = (turn.content or "").strip()
        if not text or _short_hello(text):
            return t("greet", turn.language)
        return await grok_specialist_reply(
            grok, turn, name=self.name, system=None, conv_id="helpinghand-crew"
        )


def _short_hello(text: str) -> bool:
    compact = text.lower().strip(" !.?,")
    return compact in {
        "hi",
        "hello",
        "hey",
        "yo",
        "salam",
        "help",
        "হ্যালো",
        "হাই",
        "সালাম",
        "সাহায্য",
    }
