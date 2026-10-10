"""Hash-pinned DOS archives, including sites with HTML download forms."""

from http.cookiejar import CookieJar
from http.client import HTTPSConnection
from ipaddress import ip_address
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from bs4 import BeautifulSoup
from soupsieve.util import SelectorSyntaxError

def _public_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost")):
        raise ValueError("DOS downloads require public HTTPS URLs without credentials")
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        return  # The connection below also verifies the actual resolved peer.
    if not address.is_global:
        raise ValueError("DOS downloads must not access private network addresses")


class _PublicHTTPSConnection(HTTPSConnection):
    def connect(self) -> None:
        super().connect()
        self._check_peer()

    def _check_peer(self) -> None:
        if self.sock is None or not ip_address(self.sock.getpeername()[0]).is_global:
            self.close()
            raise ValueError("DOS downloads must not access private network addresses")


class _PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_PublicHTTPSConnection, request, context=self._context)


class _HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        _public_https_url(newurl)
        return super().redirect_request(request, fp, code, message, headers, newurl)


def fetch_dos_source(source: dict, limit: int, on_progress=None) -> bytes:
    url = source["url"]
    selectors = source.get("download_forms", [])
    if (not isinstance(selectors, list) or len(selectors) > 3
            or not all(isinstance(value, str) for value in selectors)):
        raise ValueError("DOS download_forms must be a list of up to three form selectors")
    opener = build_opener(_HTTPSRedirect(), _PublicHTTPSHandler(), HTTPCookieProcessor(CookieJar()))

    def fetch(address: str, fields: dict | None = None, *, download: bool = False) -> tuple[bytes, str]:
        _public_https_url(address)
        request = Request(address, data=urlencode(fields).encode() if fields is not None else None,
                          headers={"User-Agent": "THelpViewer DOS software downloader"})
        with opener.open(request, timeout=30) as response:
            contents = bytearray()
            total = int(response.headers.get("Content-Length", "0"))
            while len(contents) <= limit:
                chunk = response.read(min(65536, limit + 1 - len(contents)))
                if not chunk:
                    break
                contents.extend(chunk)
                if download and on_progress:
                    on_progress(len(contents), total)
            final_url = response.url
        if len(contents) > limit:
            raise ValueError("DOS software download exceeds its size limit")
        return bytes(contents), final_url

    data, url = fetch(url, download=not selectors)
    for index, selector in enumerate(selectors):
        if len(data) > 4 * 1024 * 1024:
            raise ValueError("DOS download HTML exceeds its size limit")
        page = BeautifulSoup(data, "html.parser")
        try:
            form = page.select_one(selector)
        except SelectorSyntaxError as error:
            raise ValueError("Invalid DOS download form selector") from error
        if form is None or form.name != "form" or form.get("method", "get").lower() != "post":
            raise ValueError("DOS download form is unavailable; inspect the source page")
        fields = {item["name"]: item.get("value", "")
                  for item in form.select('input[type="hidden"][name]:not([disabled])')}
        button = form.select_one('button[name]:not([disabled]), input[type="submit"][name]:not([disabled])')
        if button:
            fields[button["name"]] = button.get("value", "")
        data, url = fetch(urljoin(url, form.get("action", "")), fields, download=index == len(selectors) - 1)
    return data
