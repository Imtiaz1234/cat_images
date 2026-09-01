from unittest.mock import MagicMock, patch

from mdpub.ai import _parse_json, generate_metadata


def test_parse_json_from_fenced_and_prose():
    assert _parse_json('```json\n{"title": "A"}\n```')["title"] == "A"
    assert _parse_json('Here you go:\n{"slug": "a-b"}\nThanks')["slug"] == "a-b"


def test_generate_metadata_keeps_only_missing_fields():
    choice = MagicMock()
    choice.message.content = '{"title": "T", "description": "D", "tags": ["a", "b"], "slug": "t"}'
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = response

    with patch("mdpub.ai._client", return_value=client):
        data = generate_metadata(title=None, body="# Hello\n\nBody.\n", missing=["description", "tags"])

    assert data == {"description": "D", "tags": ["a", "b"]}
    assert "title" not in data
