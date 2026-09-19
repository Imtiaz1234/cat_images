"""SQLite FTS5 campus knowledge base."""

from __future__ import annotations

from helpinghand.db import connect
from helpinghand.kb import KnowledgeBase


def test_add_and_search(tmp_path) -> None:
    kb = KnowledgeBase(connect(tmp_path / "kb.db"))
    kb.add("Merit scholarship", "Apply by 30 November with CGPA 3.75.", added_by="admin")
    kb.add("Hall fees", "Male hall seat 1200 BDT per month.", added_by="admin")
    hits = kb.search("scholarship CGPA")
    assert hits
    assert "3.75" in hits[0].body
    assert "Hall" not in hits[0].title


def test_seed_sample_once(tmp_path) -> None:
    kb = KnowledgeBase(connect(tmp_path / "kb.db"))
    first = kb.seed_sample_faqs()
    second = kb.seed_sample_faqs()
    assert first >= 1
    assert second == 0
    hits = kb.search("scholarship")
    assert hits


def test_empty_query(tmp_path) -> None:
    kb = KnowledgeBase(connect(tmp_path / "kb.db"))
    assert kb.search("   ") == []
