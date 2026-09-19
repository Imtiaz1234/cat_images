from helpinghand.specialists.prompts import TUTOR_SYSTEM, grok_specialist_reply


class Tutor:
    name = "tutor"

    async def handle(self, turn, grok) -> str:
        return await grok_specialist_reply(
            grok, turn, name=self.name, system=TUTOR_SYSTEM, conv_id="helpinghand-tutor"
        )
