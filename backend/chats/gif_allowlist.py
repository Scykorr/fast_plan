"""Allowed hosts for GIF reaction URLs (SSRFsafe allowlist)."""

from urllib.parse import urlparse

ALLOWED_GIF_HOSTS = frozenset(
    {
        "giphy.com",
        "www.giphy.com",
        "media.giphy.com",
        "media0.giphy.com",
        "media1.giphy.com",
        "media2.giphy.com",
        "media3.giphy.com",
        "media4.giphy.com",
        "i.giphy.com",
        "tenor.com",
        "www.tenor.com",
        "media.tenor.com",
        "c.tenor.com",
        "media1.tenor.com",
    }
)


def validate_gif_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        raise ValueError("GIF URL must use https.")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_GIF_HOSTS:
        raise ValueError(
            "GIF host is not allowed. Use giphy.com or tenor.com media URLs."
        )
    return url.strip()
