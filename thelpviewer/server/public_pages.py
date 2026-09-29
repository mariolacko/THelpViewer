"""Crawlable viewer pages, robots.txt and XML sitemaps."""

from __future__ import annotations

import re
from html import escape
from math import ceil
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..public_docs import is_public_doc_path
from .config import AppConfig
from .search_index import GlobalSearchIndex


SITEMAP_TOPIC_PAGE_SIZE = 49_999


def create_public_router(
    config: AppConfig,
    search_index: GlobalSearchIndex,
    help_display_names: dict[str, str],
) -> APIRouter:
    """Add public preview and discovery routes to the main FastAPI app."""
    router = APIRouter()

    def verified_html(page: str) -> str:
        if not config.google_site_verification:
            return page
        if "</head>" not in page:
            raise HTTPException(status_code=500, detail="Viewer HTML template is incomplete")
        tag = (f'<meta name="google-site-verification" '
               f'content="{escape(config.google_site_verification, quote=True)}" />\n')
        return page.replace("</head>", tag + "</head>", 1)

    def public_base(request: Request) -> str:
        if config.public_base_url:
            return config.public_base_url
        if request.headers.get("host", "").lower() == urlparse(config.auth_origin).netloc.lower():
            return config.auth_origin
        return str(request.base_url).rstrip("/")

    def public_viewer_page(title: str, description: str, url: str, content: str) -> Response:
        if not config.index_path.is_file():
            raise HTTPException(status_code=404)
        page = config.index_path.read_text(encoding="utf-8")
        page, titles = re.subn(
            r"<title>.*?</title>", lambda _: f"<title>{escape(title)}</title>", page, count=1, flags=re.S,
        )
        page, descriptions = re.subn(
            r'<meta name="description" content="[^"]*">',
            lambda _: f'<meta name="description" content="{escape(description, quote=True)}">',
            page, count=1,
        )
        desktop = '<div class="tv-desktop" data-tv-bundle-desktop>'
        if not titles or not descriptions or desktop not in page or "</head>" not in page:
            raise HTTPException(status_code=500, detail="Viewer HTML template is incomplete")
        page = page.replace("</head>", f'<link rel="canonical" href="{escape(url, quote=True)}"></head>', 1)
        page = page.replace(desktop, desktop + f'<main id="tv-public-fallback">{content}</main>', 1)
        return Response(verified_html(page), media_type="text/html")

    def public_topic(file_path: str, request: Request, topic: str = "") -> Response:
        if len(file_path) > 512 or len(topic) > 64:
            raise HTTPException(status_code=404)
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        entry = search_index.topic(file_path, topic)
        if entry is None or not entry["body"]:
            raise HTTPException(status_code=404)
        url = public_base(request) + "/?" + urlencode({"file": file_path, "topic": topic})
        overview = "/?" + urlencode({"file": file_path})
        title = f'{entry["title"]} — {entry["help_name"]}'
        content = (
            f'<nav><a href="/">THelpViewer</a></nav><h1>{escape(entry["title"])}</h1>'
            f'<p><a href="{escape(overview, quote=True)}">{escape(entry["help_name"])}</a></p>'
            f'<pre style="white-space:pre-wrap">{escape(entry["body"])}</pre>'
        )
        return public_viewer_page(title, entry["preview"], url, content)

    def public_file(file_path: str, request: Request) -> Response:
        if len(file_path) > 512:
            raise HTTPException(status_code=404)
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        topics = search_index.file_topic_rows(file_path)
        if not topics:
            raise HTTPException(status_code=404)
        name = topics[0][2]
        url = public_base(request) + "/?" + urlencode({"file": file_path})
        links = "".join(
            f'<li><a href="{escape("/?" + urlencode({"file": file_path, "topic": context_id}), quote=True)}">'
            f'{escape(title)}</a></li>'
            for context_id, title, _help_name in topics
        )
        content = (
            f'<nav><a href="/">THelpViewer</a></nav><h1>{escape(name)}</h1>'
            f'<p>{len(topics)} topics</p><ol>{links}</ol>'
        )
        return public_viewer_page(f"{name} — THelpViewer", f"Topics in {name}", url, content)

    def public_document(doc_path: str, request: Request) -> Response:
        if len(doc_path) > 512 or not is_public_doc_path(doc_path):
            raise HTTPException(status_code=404)
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        entry = search_index.document(doc_path)
        if entry is None or not entry["body"]:
            raise HTTPException(status_code=404)
        url = public_base(request) + "/?" + urlencode({"doc": doc_path})
        content = (
            f'<nav><a href="/">THelpViewer</a></nav><h1>{escape(entry["title"])}</h1>'
            f'<pre style="white-space:pre-wrap">{escape(entry["body"])}</pre>'
        )
        return public_viewer_page(f'{entry["title"]} — THelpViewer Docs', entry["preview"], url, content)

    @router.get("/")
    async def index(request: Request, file: str = "", topic: str = "", doc: str = "") -> Response:
        if doc:
            return public_document(doc, request)
        if file:
            return public_topic(file, request, topic) if topic else public_file(file, request)
        if topic or any(key in request.query_params for key in ("file", "topic", "doc")):
            raise HTTPException(status_code=404)
        if not config.index_path.is_file():
            raise HTTPException(status_code=404)
        if search_index.status()["state"] != "ready":
            return Response(verified_html(config.index_path.read_text(encoding="utf-8")), media_type="text/html")
        help_links = "".join(
            f'<li><a href="{escape("/?" + urlencode({"file": file_path}), quote=True)}">'
            f'{escape(help_display_names.get(file_path.casefold(), file_path))}</a></li>'
            for file_path, _count in search_index.file_sitemap_counts()
        )
        doc_links = "".join(
            f'<li><a href="{escape("/?" + urlencode({"doc": doc_path}), quote=True)}">'
            f'{escape(doc_path)}</a></li>'
            for doc_path in search_index.document_paths()
        )
        content = (
            '<h1>THelpViewer</h1><p>Browse HELP files and documentation.</p>'
            f'<h2>HELP files</h2><ul>{help_links}</ul>'
            f'<h2>Docs</h2><ul>{doc_links}</ul>'
        )
        return public_viewer_page(
            "THelpViewer — TurboVision-style Help File Viewer",
            "Browse HELP files and documentation in THelpViewer.",
            public_base(request) + "/", content,
        )

    @router.get("/robots.txt")
    def robots(request: Request) -> Response:
        return Response(
            f"User-agent: *\nAllow: /\nSitemap: {public_base(request)}/sitemap.xml\n",
            media_type="text/plain",
        )

    @router.get("/sitemap.xml")
    def sitemap_index(request: Request) -> Response:
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        base = public_base(request)
        entries = f"<sitemap><loc>{escape(base + '/sitemaps/site.xml')}</loc></sitemap>"
        entries += "".join(
            f"<sitemap><loc>{escape(base + '/sitemaps/file.xml?' + urlencode({'file': file_path, 'page': page}))}</loc></sitemap>"
            for file_path, count in search_index.file_sitemap_counts()
            for page in range(1, ceil(count / SITEMAP_TOPIC_PAGE_SIZE) + 1)
        )
        doc_count = len(search_index.document_paths())
        entries += "".join(
            f"<sitemap><loc>{escape(base + '/sitemaps/docs.xml?' + urlencode({'page': page}))}</loc></sitemap>"
            for page in range(1, ceil(doc_count / 50_000) + 1)
        )
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{entries}</sitemapindex>",
            media_type="application/xml",
        )

    @router.get("/sitemaps/site.xml")
    def sitemap_site(request: Request) -> Response:
        url = public_base(request) + "/"
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{escape(url)}</loc></url></urlset>",
            media_type="application/xml",
        )

    @router.get("/sitemaps/file.xml")
    def sitemap_file(request: Request, file: str = "", page: int = 1) -> Response:
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        count = dict(search_index.file_sitemap_counts()).get(file)
        if count is None or page < 1 or page > ceil(count / SITEMAP_TOPIC_PAGE_SIZE):
            raise HTTPException(status_code=404)
        base = public_base(request)
        urls = [base + "/?" + urlencode({"file": file})] if page == 1 else []
        urls.extend(
            base + "/?" + urlencode({"file": file, "topic": context_id})
            for context_id, _title, _help_name in search_index.file_topic_rows(
                file, (page - 1) * SITEMAP_TOPIC_PAGE_SIZE, SITEMAP_TOPIC_PAGE_SIZE
            )
        )
        entries = "".join(f"<url><loc>{escape(url)}</loc></url>" for url in urls)
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{entries}</urlset>",
            media_type="application/xml",
        )

    @router.get("/sitemaps/docs.xml")
    def sitemap_docs(request: Request, page: int = 1) -> Response:
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        paths = search_index.document_paths()
        if page < 1 or page > ceil(len(paths) / 50_000):
            raise HTTPException(status_code=404)
        base = public_base(request)
        entries = "".join(
            f"<url><loc>{escape(base + '/?' + urlencode({'doc': doc_path}))}</loc></url>"
            for doc_path in paths[(page - 1) * 50_000:page * 50_000]
        )
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{entries}</urlset>",
            media_type="application/xml",
        )

    @router.get("/sitemap-{page}.xml")
    def sitemap_topics(page: int, request: Request) -> Response:
        if search_index.status()["state"] != "ready":
            return Response("Index is being built", status_code=503, media_type="text/plain")
        count = search_index.sitemap_count()
        if page < 1 or page > ceil(count / 50_000):
            raise HTTPException(status_code=404)
        base = public_base(request)
        entries = "".join(
            f"<url><loc>{escape(base + '/?' + urlencode({'file': file_path, 'topic': context_id}))}</loc></url>"
            for file_path, context_id in search_index.sitemap_rows((page - 1) * 50_000, 50_000)
        )
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{entries}</urlset>",
            media_type="application/xml",
        )

    return router
