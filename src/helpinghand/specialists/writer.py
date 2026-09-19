from helpinghand.i18n import t
from helpinghand.integrity import is_full_assignment_request
from helpinghand.specialists.prompts import WRITER_SYSTEM, grok_specialist_reply


class Writer:
    name = "writer"

    async def handle(self, turn, grok) -> str:
        if is_full_assignment_request(turn.content):
            return t("integrity_refuse", turn.language)
        return await grok_specialist_reply(
            grok, turn, name=self.name, system=WRITER_SYSTEM, conv_id="helpinghand-writer"
        )
