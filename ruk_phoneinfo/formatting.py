"""Number formatting: E.164, international, national, RFC 3966 and pretty."""

from __future__ import annotations

from . import datasets


def _group(nsn: str) -> str:
    """Group an NSN into readable chunks of three, remainder last."""
    nsn = str(nsn or "")
    if len(nsn) <= 4:
        return nsn
    chunks = [nsn[i:i + 3] for i in range(0, len(nsn), 3)]
    if len(chunks) > 1 and len(chunks[-1]) == 1:
        chunks[-2] = chunks[-2] + chunks[-1]
        chunks.pop()
    return " ".join(chunks)


def formats(iso: str, country_code: str, nsn: str) -> dict:
    """Return every common representation of a parsed number."""
    info = datasets.country_by_iso(iso) or {}
    trunk = info.get("trunk") or ""
    nsn = str(nsn or "")
    cc = str(country_code or "")

    e164 = "+" + cc + nsn if cc and nsn else None
    national = (trunk + nsn) if trunk else nsn

    return {
        "ok": bool(e164),
        "e164": e164,
        "international": ("+%s %s" % (cc, _group(nsn))) if e164 else None,
        "national": national or None,
        "national_pretty": _group(national) if national else None,
        "rfc3966": ("tel:%s" % e164) if e164 else None,
        "pretty": ("+%s %s" % (cc, _group(nsn))) if e164 else None,
        "country_code": cc or None,
        "nsn": nsn or None,
        "trunk_prefix": trunk or None,
        "digits_only": (cc + nsn) if e164 else None,
        "length": len(nsn) if nsn else None,
    }


def to_e164(iso: str, country_code: str, nsn: str) -> str | None:
    return formats(iso, country_code, nsn)["e164"]


def to_national(iso: str, nsn: str) -> str | None:
    info = datasets.country_by_iso(iso) or {}
    trunk = info.get("trunk") or ""
    return (trunk + str(nsn)) if nsn else None
