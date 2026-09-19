from helpinghand.i18n import t
from helpinghand.kb import KnowledgeBase


class Campus:
    name = "campus"

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    async def handle(self, turn, grok=None) -> str:
        hits = turn.kb_hits or self.kb.search(turn.content)
        formatted = self.kb.format_hits(hits, lang=turn.language)
        if formatted:
            return formatted
        return t("campus_empty", turn.language)
