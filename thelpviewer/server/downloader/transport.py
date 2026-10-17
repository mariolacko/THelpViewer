"""Public-network transport shared by HELP providers and DOS packages."""

from http.cookiejar import CookieJar
from http.client import HTTPConnection, HTTPSConnection
from ipaddress import ip_address
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, HTTPHandler, HTTPSHandler, ProxyHandler, Request, build_opener
from urllib.error import HTTPError, URLError
import time

from bs4 import BeautifulSoup
from soupsieve.util import SelectorSyntaxError
from ..file_storage import atomic_file
from .online import defer_source, report_transfer, run_download, source_key, transfer_slot
from .errors import DownloadSecurityError, SourceRateLimited, SourceUnavailable

MAX_RETRY_AFTER = 300
_limited_sources = ContextVar("limited_download_sources", default=None)


@contextmanager
def defer_limited_sources(sources):
    """Share exhausted site limits across alternative sources in one job."""
    token = _limited_sources.set(sources)
    try:
        yield
    finally:
        _limited_sources.reset(token)


def check_source_limit(url):
    sources = _limited_sources.get()
    if sources is not None and source_key(url) in sources:
        raise SourceRateLimited(url)


def retry_delay(headers: object, default: int) -> int:
    """Bound a server's numeric Retry-After delay for all download clients."""
    try:
        value = int(getattr(headers, "get")("Retry-After", default))
    except (AttributeError, TypeError, ValueError):
        value = default
    return min(max(value, 0), MAX_RETRY_AFTER)

def public_url(url: str, *, https_only: bool = True) -> None:
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise DownloadSecurityError("Download URLs must not contain control characters")
    parsed = urlsplit(url)
    if (parsed.scheme not in ({"https"} if https_only else {"http", "https"}) or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost")):
        raise DownloadSecurityError("Downloads require public HTTPS URLs without credentials" if https_only
                         else "Downloads require public HTTP(S) URLs without credentials")
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        return  # The connection below also verifies the actual resolved peer.
    if not address.is_global:
        raise DownloadSecurityError("Downloads must not access private network addresses")


def _encoded_url(url: str) -> str:
    """Convert an HTML IRI to a wire URL without re-encoding escapes/delimiters."""
    public_url(url, https_only=False)
    parsed = urlsplit(url)
    if not parsed.netloc.isascii():
        host = parsed.hostname.encode("idna").decode("ascii")
        authority = f"{host}:{parsed.port}" if parsed.port is not None else host
        url = urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, parsed.fragment))
    encoded = quote(url, safe=":/?#[]@!$&'()*+,;=%")
    # IDNA can map Unicode host names to localhost or a private IP literal.
    public_url(encoded, https_only=False)
    return encoded


class _PublicPeer:
    def connect(self) -> None:
        super().connect()
        self._check_peer()

    def _check_peer(self) -> None:
        if self.sock is None or not ip_address(self.sock.getpeername()[0]).is_global:
            self.close()
            raise DownloadSecurityError("Downloads must not access private network addresses")


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
    def __init__(self, https_only=True, allowed_hosts=None):
        self.https_only = https_only
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, request, fp, code, message, headers, newurl):
        newurl = _encoded_url(newurl)
        public_url(newurl, https_only=self.https_only or urlsplit(request.full_url).scheme == "https")
        if self.allowed_hosts is not None and urlsplit(newurl).hostname not in self.allowed_hosts:
            raise DownloadSecurityError("Download redirected outside its configured hosts")
        check_source_limit(newurl)
        return super().redirect_request(request, fp, code, message, headers, newurl)


def create_opener(*, https_only=True, allowed_hosts=None):
    return build_opener(ProxyHandler({}), _HTTPSRedirect(https_only, allowed_hosts), _PublicHTTPHandler(),
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
        raise SourceUnavailable("Download is incomplete")


def read_request(opener, request, limit, *, timeout=30, retries=3, retry_after=30,
                 on_progress=None, on_status=None, phase="Downloading", destination=None):
    """Queued, bounded GET/POST transfer, optionally atomically written to disk."""
    if isinstance(request, Request):
        request.full_url = _encoded_url(request.full_url)
    else:
        request = _encoded_url(request)
    # Check before queueing: a deferred site must not first wait in its cooldown.
    check_source_limit(getattr(request, "full_url", request))
    def status(value, *, waiting=False):
        if on_status:
            on_status(value)
        report_transfer(value, state="waiting" if waiting else "running")
    def progress(received, total):
        report_transfer(phase, received, total)
        if on_progress:
            on_progress(received, total)
    def transfer():
        for attempt in range(retries):
            status(phase)
            try:
                check_source_limit(getattr(request, "full_url", request))
                with opener.open(request, timeout=timeout) as response:
                    final_url = getattr(response, "url", getattr(request, "full_url", request))
                    with transfer_slot(final_url):
                        chunks = download_chunks(response, limit, progress)
                        if destination is None:
                            data = b"".join(chunks)
                        else:
                            with atomic_file(destination) as output:
                                for chunk in chunks:
                                    output.write(chunk)
                            data = destination
                        return data, final_url, response.headers
            except SourceRateLimited:
                raise
            except HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code < 600
                delay = retry_delay(error.headers, retry_after) if error.code == 429 else 5
                waiting = "Rate limited (HTTP 429), retry" if error.code == 429 else "Retrying"
                if error.code == 429:
                    defer_source(error.url, delay)
                    sources = _limited_sources.get()
                    if sources is not None and attempt == retries - 1:
                        sources.add(source_key(error.url))
                        error.close()
                        raise SourceRateLimited(error.url) from None
                if not retryable or attempt == retries - 1:
                    raise
                error.close()
            except (OSError, URLError):
                if attempt == retries - 1:
                    raise
                delay, waiting = 5, "Retrying"
            for remaining in range(delay, 0, -1):
                status(f"{waiting} in {remaining}s", waiting=True)
                time.sleep(1)
        raise ValueError("Download needs at least one attempt")
    return run_download(transfer, source=getattr(request, "full_url", request),
        check=lambda: check_source_limit(getattr(request, "full_url", request)))


def fetch_bytes(url, hosts, limit, *, on_progress=None, on_status=None, user_agent="THelpViewer downloader"):
    public_url(url)
    if urlsplit(url).hostname not in hosts:
        raise DownloadSecurityError("Download URL is outside its configured HTTPS hosts")
    request = Request(url, headers={"User-Agent": user_agent})
    data, _url, _headers = read_request(create_opener(allowed_hosts=hosts), request, limit,
        on_progress=on_progress, on_status=on_status)
    return data


def fetch_source(source: dict, limit: int, on_progress=None, *, on_status=None) -> bytes:
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
        try:
            contents, final_url, _headers = read_request(opener, request, limit,
                on_progress=on_progress if download else None, on_status=on_status)
        except SourceRateLimited:
            raise
        except HTTPError as error:
            if error.code != 429:
                raise
            error.close()
            raise SourceUnavailable(f"Download of {source.get('title', source.get('id', 'package'))} is rate limited (HTTP 429). Try again later; installed files are unchanged.") from None
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
            raise SourceUnavailable("Download form is unavailable; inspect the source page")
        fields = {item["name"]: item.get("value", "")
                  for item in form.select('input[type="hidden"][name]:not([disabled])')}
        button = form.select_one('button[name]:not([disabled]), input[type="submit"][name]:not([disabled])')
        if button:
            fields[button["name"]] = button.get("value", "")
        data, url = fetch(urljoin(url, form.get("action", "")), fields, download=index == len(selectors) - 1)
    return data
