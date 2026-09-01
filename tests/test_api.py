from fastapi.testclient import TestClient

from mdpub.web.app import create_app

client = TestClient(create_app())


def test_health_lists_presets():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "hugo" in data["presets"]


def test_index_serves_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "mdpub" in response.text
    assert "Polish" in response.text


def test_polish_round_trip():
    response = client.post(
        "/api/polish",
        json={
            "markdown": "Garden notes\n============\n\n#### Soil\n\nMulch helps.\n",
            "preset": "hugo",
            "site_url": "https://example.com",
            "toc": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["frontmatter"]["title"] == "Garden notes"
    assert data["frontmatter"]["canonicalURL"].startswith("https://example.com/")
    assert data["markdown"].startswith("---\n")
    assert "Table of Contents" in data["markdown"]
    assert isinstance(data["warnings"], list)


def test_polish_rejects_unknown_preset():
    response = client.post(
        "/api/polish",
        json={"markdown": "# Hi\n", "preset": "ghost"},
    )
    assert response.status_code == 400
