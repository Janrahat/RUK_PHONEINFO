"""Country, region, time-zone and area-code resolution.

All values come from the bundled numbering-plan tables.  Nothing here
contacts a network service, and no value is ever guessed: when a fact is
not bundled the field is reported as unknown.
"""

from __future__ import annotations

from . import datasets


def lookup_region(iso: str, nsn: str) -> dict:
    """Resolve geographic metadata for an NSN.

    ``area`` is only meaningful for fixed lines; for mobile ranges the
    numbering plan does not encode a location, which is stated explicitly.
    """
    out = {
        "ok": False,
        "iso": iso,
        "country": None,
        "country_ur": None,
        "flag": None,
        "region": None,
        "timezones": [],
        "area_code": None,
        "area_name": None,
        "area_applicable": False,
        "note": None,
        "error": None,
    }
    info = datasets.country_by_iso(iso)
    if not info:
        out["error"] = "unknown_country"
        return out

    out["ok"] = True
    out["country"] = info["name"]
    out["country_ur"] = info.get("name_ur")
    out["flag"] = info.get("flag")
    out["region"] = info.get("region")
    out["timezones"] = list(info.get("tz") or [])

    hit = datasets.area_for(iso, nsn)
    if hit:
        out["area_code"] = hit[0]
        out["area_name"] = hit[1]
        out["area_applicable"] = True
        out["note"] = (
            "Area code derived from the fixed-line numbering plan. Mobile "
            "numbers do not encode a geographic area."
        )
    else:
        out["note"] = (
            "No area code is bundled for this prefix. Mobile and VoIP ranges "
            "carry no geographic information in the numbering plan."
        )
    return out


def country_name(iso: str) -> str | None:
    info = datasets.country_by_iso(iso)
    return info["name"] if info else None


def timezones(iso: str) -> list:
    info = datasets.country_by_iso(iso)
    return list(info.get("tz") or []) if info else []


def area_name(iso: str, nsn: str) -> str | None:
    hit = datasets.area_for(iso, nsn)
    return hit[1] if hit else None
