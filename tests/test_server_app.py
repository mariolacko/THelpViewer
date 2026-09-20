from fastapi.testclient import TestClient

from thelpviewer.server.app import create_app
from thelpviewer.server.config import AppConfig


def test_docs_route_rejects_encoded_parent_traversal(tmp_path):
    web_dir = tmp_path / "www"
    docs_dir = tmp_path / "docs"
    assets_dir = web_dir / "assets"
    helps_dir = tmp_path / "helps"
    for directory in (web_dir, docs_dir, assets_dir, helps_dir):
        directory.mkdir(parents=True, exist_ok=True)
    index_path = web_dir / "index.html"
    index_path.write_text("index", encoding="utf-8")
    (docs_dir / "inside.md").write_text("inside", encoding="utf-8")
    (docs_dir / "Runtime Audit.md").write_text("private audit", encoding="utf-8")
    (docs_dir / "Format RE Notes.md").write_text("private notes", encoding="utf-8")
    (docs_dir / "private.txt").write_text("private", encoding="utf-8")
    (tmp_path / "docs-secret.md").write_text("secret", encoding="utf-8")

    config = AppConfig(
        host="127.0.0.1",
        port=5448,
        web_dir=web_dir,
        index_path=index_path,
        assets_dir=assets_dir,
        helps_dir=helps_dir,
        docs_dir=docs_dir,
        readme_path=tmp_path / "README.md",
        changelog_path=tmp_path / "CHANGELOG.md",
        state_dir=tmp_path / "var",
        virtual_docs=(),
    )
    client = TestClient(create_app(config))

    assert client.get("/docs/inside.md").status_code == 200
    assert client.get("/docs/Runtime%20Audit.md").status_code == 404
    assert client.get("/docs/Format%20RE%20Notes.md").status_code == 404
    assert client.get("/docs/private.txt").status_code == 404
    assert client.get("/docs/%2e%2e/docs-secret.md").status_code == 404

    runtime_config = client.get("/config.json")
    assert runtime_config.status_code == 200
    assert runtime_config.json() == {
        "index_url": "/",
        "assets_url": "/assets/",
        "helps_url": "/helps/",
        "docs_url": "/docs/",
        "virtual_docs": [],
    }
    assert str(tmp_path) not in runtime_config.text

    catalog = client.get("/docs/catalog.json")
    assert catalog.status_code == 200
    assert catalog.json() == [{"file": "inside.md", "name": "inside"}]
