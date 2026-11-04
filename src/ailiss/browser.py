from collections.abc import Callable
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlparse


@dataclass(frozen=True)
class BrowserOutcome:
    status: str
    status_code: int | None
    content_type: str | None
    byte_count: int
    artifact_hash: str
    browser_version: str
    reason: str | None = None


def destination_allowed(url: str, allowed_domains: set[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return False
    try:
        address = ip_address(hostname)
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            return False
    except ValueError:
        pass
    return any(
        hostname == domain.lower().lstrip(".")
        or hostname.endswith("." + domain.lower().lstrip("."))
        for domain in allowed_domains
    )


def playwright_fetch_fixture(
    url: str,
    allowed_domains: set[str],
    fetch: Callable[[], str | None],
    timeout_ms: int = 15_000,
    max_bytes: int = 2 * 1024 * 1024,
) -> BrowserOutcome:
    if timeout_ms <= 0 or timeout_ms > 30_000:
        raise ValueError("invalid_browser_timeout")
    if max_bytes <= 0 or max_bytes > 2 * 1024 * 1024:
        raise ValueError("invalid_artifact_limit")
    if not destination_allowed(url, allowed_domains):
        return BrowserOutcome(
            "policy_rejected", None, None, 0, "", "fixture", "destination not approved"
        )

    html = fetch()
    if html is None:
        return BrowserOutcome(
            "challenge", None, None, 0, "", "fixture", "challenge or content unavailable"
        )

    raw = html.encode("utf-8")
    if len(raw) > max_bytes:
        return BrowserOutcome(
            "blocked", None, None, len(raw), "", "fixture", "artifact limit exceeded"
        )
    import hashlib

    return BrowserOutcome(
        status="complete",
        status_code=200,
        content_type="text/html",
        byte_count=len(raw),
        artifact_hash=hashlib.sha256(raw).hexdigest(),
        browser_version="fixture",
    )


def playwright_fetch(
    url: str,
    allowed_domains: set[str],
    timeout_ms: int = 15_000,
    max_bytes: int = 2 * 1024 * 1024,
) -> BrowserOutcome:
    if timeout_ms <= 0 or timeout_ms > 30_000:
        raise ValueError("invalid_browser_timeout")
    if max_bytes <= 0 or max_bytes > 2 * 1024 * 1024:
        raise ValueError("invalid_artifact_limit")
    if not destination_allowed(url, allowed_domains):
        return BrowserOutcome(
            "policy_rejected", None, None, 0, "", "unknown", "destination not approved"
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright_browser_extra_not_installed") from exc

    import hashlib

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            locale="en-US",
            timezone_id="UTC",
            java_script_enabled=True,
            accept_downloads=False,
            service_workers="block",
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if response is None:
                return BrowserOutcome("blocked", None, None, 0, "", "chromium", "no response")
            if not destination_allowed(response.url, allowed_domains):
                return BrowserOutcome(
                    "policy_rejected",
                    response.status,
                    response.headers.get("content-type"),
                    0,
                    "",
                    browser.version,
                    "redirect destination not approved",
                )
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type:
                return BrowserOutcome(
                    "unsupported", response.status, content_type, 0, "", browser.version
                )
            content_length = response.headers.get("content-length")
            if content_length is not None and int(content_length) > max_bytes:
                return BrowserOutcome(
                    "blocked",
                    response.status,
                    content_type,
                    int(content_length),
                    "",
                    browser.version,
                    "artifact limit exceeded",
                )
            html = page.content()
            raw = html.encode("utf-8")
            if len(raw) > max_bytes:
                return BrowserOutcome(
                    "blocked",
                    response.status,
                    content_type,
                    len(raw),
                    "",
                    browser.version,
                    "artifact limit exceeded",
                )
            lower_html = html.lower()
            if any(
                marker in lower_html
                for marker in ("captcha", "verify you are human", "access denied")
            ):
                return BrowserOutcome(
                    "challenge",
                    response.status,
                    content_type,
                    len(raw),
                    hashlib.sha256(raw).hexdigest(),
                    browser.version,
                    "challenge detected",
                )
            return BrowserOutcome(
                "complete",
                response.status,
                content_type,
                len(raw),
                hashlib.sha256(raw).hexdigest(),
                browser.version,
            )
        finally:
            context.close()
            browser.close()
