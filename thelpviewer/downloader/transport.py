"""Public-network transport shared by HELP providers and DOS packages."""

from http.cookiejar import CookieJar
from http.client import HTTPConnection, HTTPSConnection
from ipaddress import ip_address
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, HTTPHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from bs4 import BeautifulSoup
from soupsieve.util import SelectorSyntaxError

def public_url(url: str, *, https_only: bool = True) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme not in ({"https"} if https_only else {"http", "https"}) or not parsed.hostname or parsed.username or parsed.password
            or parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost")):
        raise ValueError("Downloads require public HTTPS URLs without credentials" if https_only
                         else "Downloads require public HTTP(S) URLs without credentials")
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        return  # The connection below also verifies the actual resolved peer.
    if not address.is_global:
        raise ValueError("Downloads must not access private network addresses")


class _PublicPeer:
    def connect(self) -> None:
        super().connect()
        self._check_peer()

    def _check_peer(self) -> None:
        if self.sock is None or not ip_address(self.sock.getpeername()[0]).is_global:
            self.close()
            raise ValueError("Downloads must not access private network addresses")


class _PublicHTTPSConnection(_PublicPeer, HTTPSConnection):
    pass


class _PublicHTTPConnection(_PublicPeer, HTTPConnection):
    pass


class _PublicHTTPHandler(HTTPHandler):
    def http_open(self, request):
        public_url(request.full_url, https_only=False)
        return self.do_open(_PublicHTTPConnection, request)


class _PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        public_url(request.full_url)
        return self.do_open(_PublicHTTPSConnection, request, context=self._context)


class _HTTPSRedirect(HTTPRedirectHandler):
    def __init__(self, https_only=True):
        self.https_only = https_only

    def redirect_request(self, request, fp, code, message, headers, newurl):
        public_url(newurl, https_only=self.https_only or urlsplit(request.full_url).scheme == "https")
        return super().redirect_request(request, fp, code, message, headers, newurl)


def create_opener(*, https_only=True):
    return build_opener(ProxyHandler({}), _HTTPSRedirect(https_only), _PublicHTTPHandler(),
                        _PublicHTTPSHandler(), HTTPCookieProcessor(CookieJar()))


def download_chunks(response, limit: int, on_progress=None):
    total = int(response.headers.get("Content-Length") or 0)
    if total > limit:
        raise ValueError("Download exceeds its size limit")
    received = 0
    while chunk := response.read(min(65536, limit + 1 - received)):
        received += len(chunk)
        if received > limit:
            raise ValueError("Download exceeds its size limit")
        if on_progress:
            on_progress(received, total)
        yield chunk
    if total and received != total:
        raise ValueError("Download is incomplete")


def fetch_source(source: dict, limit: int, on_progress=None) -> bytes:
    url = source["url"]
    selectors = source.get("download_forms", [])
    if (not isinstance(selectors, list) or len(selectors) > 3
            or not all(isinstance(value, str) for value in selectors)):
        raise ValueError("download_forms must be a list of up to three form selectors")
    opener = create_opener()

    def fetch(address: str, fields: dict | None = None, *, download: bool = False) -> tuple[bytes, str]:
        public_url(address)
        request = Request(address, data=urlencode(fields).encode() if fields is not None else None,
                          headers={"User-Agent": "THelpViewer software downloader"})
        with opener.open(request, timeout=30) as response:
            contents = b"".join(download_chunks(response, limit, on_progress if download else None))
            final_url = response.url
        return bytes(contents), final_url

    data, url = fetch(url, download=not selectors)
    for index, selector in enumerate(selectors):
        if len(data) > 4 * 1024 * 1024:
            raise ValueError("Download HTML exceeds its size limit")
        page = BeautifulSoup(data, "html.parser")
        try:
            form = page.select_one(selector)
        except SelectorSyntaxError as error:
            raise ValueError("Invalid download form selector") from error
        if form is None or form.name != "form" or form.get("method", "get").lower() != "post":
            raise ValueError("Download form is unavailable; inspect the source page")
        fields = {item["name"]: item.get("value", "")
                  for item in form.select('input[type="hidden"][name]:not([disabled])')}
        button = form.select_one('button[name]:not([disabled]), input[type="submit"][name]:not([disabled])')
        if button:
            fields[button["name"]] = button.get("value", "")
        data, url = fetch(urljoin(url, form.get("action", "")), fields, download=index == len(selectors) - 1)
    return data
