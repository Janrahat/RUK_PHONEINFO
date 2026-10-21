"""Carrier / operator and line-type resolution from bundled prefix tables.

Mobile number portability means the operator that originally received a
prefix is not necessarily the operator serving the number today.  Every
result therefore carries a confidence level and a portability note.
"""

from __future__ import annotations

from . import datasets


def lookup_carrier(iso: str, nsn: str) -> dict:
    """Resolve the operator and line type for an NSN.

    Returns a dict with ``ok``, ``operator``, ``line_type``, ``line_type_label``,
    ``prefix``, ``confidence`` and ``note``.
    """
    out = {
        "ok": False,
        "operator": None,
        "line_type": "unknown",
        "line_type_label": datasets.LINE_TYPES["unknown"],
        "prefix": None,
        "confidence": "none",
        "note": None,
        "error": None,
    }
    info = datasets.country_by_iso(iso)
    if not info:
        out["error"] = "unknown_country"
        return out
    if not nsn:
        out["error"] = "no_nsn"
        return out

    hit = datasets.carrier_for(iso, nsn)
    if hit:
        operator, line_type, note = hit
        out["ok"] = True
        out["operator"] = operator
        out["line_type"] = line_type
        out["line_type_label"] = datasets.LINE_TYPES.get(line_type, line_type)
        out["prefix"] = nsn[:4] if len(nsn) >= 4 else nsn
        out["confidence"] = "medium" if "Ported" in note else "high"
        out["note"] = note
        return out

    # Fall back to the plan's own prefix categories.
    for key in ("tollfree", "premium", "voip", "mobile", "fixed"):
        for prefix in info.get(key) or []:
            if nsn.startswith(prefix):
                out["ok"] = True
                out["line_type"] = key
                out["line_type_label"] = datasets.LINE_TYPES.get(key, key)
                out["prefix"] = prefix
                out["confidence"] = "low"
                out["note"] = (
                    "Derived from the national numbering plan's %s range; the "
                    "specific operator is not bundled for this prefix." % key
                )
                return out

    out["error"] = "no_match"
    out["note"] = (
        "No bundled prefix table entry for this range. The number may still "
        "be valid - only the operator/line-type mapping is unavailable."
    )
    return out


def line_type(iso: str, nsn: str) -> str:
    """Return just the line-type key for an NSN."""
    return lookup_carrier(iso, nsn)["line_type"]


def carrier_summary(iso: str, nsn: str) -> str:
    """One-line human summary of the carrier lookup."""
    res = lookup_carrier(iso, nsn)
    if res["ok"] and res["operator"]:
        return "%s (%s)" % (res["operator"], res["line_type_label"])
    if res["ok"]:
        return res["line_type_label"]
    return "Unknown"
