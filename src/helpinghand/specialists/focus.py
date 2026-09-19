from datetime import date, datetime, timezone

from helpinghand.focus_plan import build_study_plan
from helpinghand.reminders import ReminderStore


class Focus:
    name = "focus"

    def __init__(self, reminders: ReminderStore | None = None) -> None:
        self.reminders = reminders

    async def handle(self, turn, grok=None) -> str:
        del grok  # template only — never Grok when a plan can be built locally
        exam = None
        extra_date = turn.extra.get("exam_date")
        if extra_date:
            try:
                exam = date.fromisoformat(extra_date)
            except ValueError:
                exam = None
        subjects = None
        if turn.extra.get("subjects"):
            subjects = [s.strip() for s in turn.extra["subjects"].split(",") if s.strip()]
        plan = build_study_plan(
            turn.content,
            exam_date=exam,
            subjects=subjects,
            lang=turn.language,
        )
        if self.reminders and plan.reminder_at:
            when = plan.reminder_at
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when > datetime.now(timezone.utc):
                line = f"exam tomorrow ({plan.exam_on}): {', '.join(plan.subjects)}"
                self.reminders.add(
                    user_id=turn.user_id,
                    fire_at=when,
                    line=line,
                    kind="reminder",
                    sender="focus",
                )
        return plan.text
