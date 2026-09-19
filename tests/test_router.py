"""Keyword + slash-command router. Grok classify is last resort only."""

from __future__ import annotations

import pytest

from helpinghand.router import Router, score_keywords
from tests.helpers import FakeGrok


@pytest.fixture
def router() -> Router:
    return Router()


@pytest.mark.asyncio
async def test_exam_question_goes_to_tutor(router: Router) -> None:
    route = await router.route(text="Explain this midterm physics formula")
    assert route.specialist == "tutor"
    assert route.source == "keyword"


@pytest.mark.asyncio
async def test_bangla_exam_goes_to_tutor(router: Router) -> None:
    route = await router.route(text="কালকের পরীক্ষা আর কনসেপ্ট বুঝি না")
    assert route.specialist == "tutor"


@pytest.mark.asyncio
async def test_assignment_outline_goes_to_writer(router: Router) -> None:
    route = await router.route(text="Need an outline and Harvard citation for my assignment")
    assert route.specialist == "writer"


@pytest.mark.asyncio
async def test_bangla_assignment_goes_to_writer(router: Router) -> None:
    route = await router.route(text="অ্যাসাইনমেন্ট এর আউটলাইন চাই")
    assert route.specialist == "writer"


@pytest.mark.asyncio
async def test_scholarship_goes_to_campus(router: Router) -> None:
    route = await router.route(text="When is the scholarship waiver deadline?")
    assert route.specialist == "campus"


@pytest.mark.asyncio
async def test_study_plan_goes_to_focus(router: Router) -> None:
    route = await router.route(text="Make a study plan and exam countdown reminder")
    assert route.specialist == "focus"


@pytest.mark.asyncio
async def test_hello_goes_to_captain(router: Router) -> None:
    route = await router.route(text="hello")
    assert route.specialist == "captain"
    assert route.source == "greeting"


@pytest.mark.asyncio
async def test_slash_quiz_maps_to_tutor(router: Router) -> None:
    route = await router.route(text="anything", command="quiz")
    assert route.specialist == "tutor"
    assert route.source == "command"


@pytest.mark.asyncio
async def test_slash_outline_and_cite_map_to_writer(router: Router) -> None:
    assert (await router.route(command="outline")).specialist == "writer"
    assert (await router.route(command="cite")).specialist == "writer"
    assert (await router.route(command="cv")).specialist == "writer"


@pytest.mark.asyncio
async def test_slash_plan_maps_to_focus(router: Router) -> None:
    assert (await router.route(command="plan")).specialist == "focus"


@pytest.mark.asyncio
async def test_ask_still_keyword_routes(router: Router) -> None:
    route = await router.route(text="campus scholarship notice", command="ask")
    assert route.specialist == "campus"
    assert route.source == "keyword"


@pytest.mark.asyncio
async def test_channel_hint_when_no_keywords(router: Router) -> None:
    route = await router.route(text="what about this?", channel_name="study-lab")
    assert route.specialist == "tutor"
    assert route.source == "channel"


@pytest.mark.asyncio
async def test_mention_overrides_channel(router: Router) -> None:
    route = await router.route(
        text="help",
        channel_name="study-lab",
        mentioned_specialist="writer",
    )
    assert route.specialist == "writer"
    assert route.source == "mention"


@pytest.mark.asyncio
async def test_unknown_falls_back_to_captain_without_classifier(router: Router) -> None:
    route = await router.route(text="hmm unclear blob xyz", allow_classify=False)
    assert route.specialist == "captain"
    assert route.source == "default"


@pytest.mark.asyncio
async def test_classifier_only_when_keywords_fail(router: Router) -> None:
    grok = FakeGrok(classify_as="campus")
    route = await router.route(text="what about the thing", classifier=grok)
    assert route.specialist == "campus"
    assert route.source == "classify"
    assert grok.classify_calls == ["what about the thing"]


@pytest.mark.asyncio
async def test_keywords_skip_classifier(router: Router) -> None:
    grok = FakeGrok(classify_as="focus")
    route = await router.route(text="explain this exam theorem", classifier=grok)
    assert route.specialist == "tutor"
    assert grok.classify_calls == []


@pytest.mark.asyncio
async def test_one_specialist_never_a_list(router: Router) -> None:
    route = await router.route(text="quiz me on calculus before the exam")
    assert route.specialist in {"captain", "tutor", "writer", "campus", "focus"}
    assert isinstance(route.specialist, str)


def test_score_keywords_counts_bangla_and_english() -> None:
    scores = score_keywords("পরীক্ষা exam scholarship")
    assert scores["tutor"] > 0
    assert scores["campus"] > 0
