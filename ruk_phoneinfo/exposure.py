"""Offline exposure assessment.

IMPORTANT - what this module deliberately does NOT do
-----------------------------------------------------
RUK_PHONEINFO never queries an online breach or leak database.  There are
three reasons, and they are not negotiable:

1. Privacy.  Sending a phone number to a third-party service is itself a
   disclosure of that number, and it would happen without the owner's
   consent.
2. No legitimate free API.  Public breach-notification services are built
   around email addresses and require an API key plus the data subject's
   own consent; there is no lawful open endpoint for phone-number lookups.
3. Accuracy.  Any tool that claims to answer "is this number in a breach?"
   from a bundled static list is guessing.  This tool does not guess.

What it DOES do is a purely local, deterministic risk assessment: it flags
number characteristics that are known to correlate with abuse, and it can
check the number against a list file that the user supplies from their own
data (for example an export of their own accounts).
"""

from __future__ import annotations

import os

from . import datasets
from .utils import digits_only, read_lines


def _risk_indicators(iso: str, nsn: str, line_type: str) -> list:
    """Deterministic, explainable risk flags derived from the number itself."""
    flags = []
    nsn = str(nsn or "")

    if line_type == "voip":
        flags.append({
            "id": "voip_range",
            "severity": "medium",
            "detail": "Number sits in a VoIP / fixed-wireless range, which is "
                      "cheap to obtain anonymously and commonly used for "
                      "one-time-verification abuse.",
        })
    if line_type == "premium":
        flags.append({
            "id": "premium_rate",
            "severity": "high",
            "detail": "Premium-rate range. Calling or returning a call to "
                      "this number can incur significant charges.",
        })
    if line_type == "tollfree":
        flags.append({
            "id": "tollfree",
            "severity": "info",
            "detail": "Toll-free range: the subscriber is an organisation "
                      "rather than an individual.",
        })

    if len(set(nsn)) == 1 and len(nsn) >= 6:
        flags.append({
            "id": "repeated_digits",
            "severity": "low",
            "detail": "Every digit is identical, which is typical of "
                      "spoofed, test or placeholder numbers.",
        })

    if len(nsn) >= 6:
        ascending = all(int(nsn[i + 1]) - int(nsn[i]) == 1 for i in range(len(nsn) - 1))
        descending = all(int(nsn[i]) - int(nsn[i + 1]) == 1 for i in range(len(nsn) - 1))
        if ascending or descending:
            flags.append({
                "id": "sequential_digits",
                "severity": "low",
                "detail": "Digits run in sequence, which is typical of test "
                          "or placeholder numbers.",
            })

    info = datasets.country_by_iso(iso) or {}
    if info.get("note"):
        flags.append({
            "id": "portability",
            "severity": "info",
            "detail": info["note"],
        })
    return flags


def _check_local_list(e164: str, local_list, local_list_path) -> dict:
    """Check the number against a user-supplied list file.

    The file is read locally and never transmitted.  Matching is done on
    digits only so that formatting differences do not cause false negatives.
    """
    out = {
        "checked": False,
        "source": None,
        "match": None,
        "entries": 0,
        "error": None,
    }
    entries = None
    if local_list:
        entries = list(local_list)
        out["source"] = "inline list"
    elif local_list_path:
        out["source"] = str(local_list_path)
        if not os.path.exists(local_list_path):
            out["error"] = "list_not_found"
            return out
        try:
            entries = read_lines(local_list_path)
        except OSError as exc:
            out["error"] = "list_unreadable: %s" % exc
            return out
    else:
        return out

    target = digits_only(e164)
    normalised = {digits_only(item) for item in entries if digits_only(item)}
    out["checked"] = True
    out["entries"] = len(normalised)
    out["match"] = target in normalised
    return out


def exposure_report(iso: str, nsn: str, e164: str, line_type: str = "unknown",
                    local_list=None, local_list_path=None) -> dict:
    """Build the offline exposure assessment for a parsed number."""
    local = _check_local_list(e164, local_list, local_list_path)
    indicators = _risk_indicators(iso, nsn, line_type)

    recommendations = [
        "Never share a one-time verification code with anyone, including "
        "someone claiming to be from your bank or operator.",
        "Enable a SIM PIN and your operator's port-out lock to make SIM-swap "
        "attacks harder.",
        "Use an app-based second factor instead of SMS where the service "
        "supports it.",
        "If you suspect your number is being abused, report it to your "
        "operator and to your national CERT.",
    ]

    return {
        "ok": True,
        "online_lookup_performed": False,
        "online_lookup_reason": (
            "No online breach database is queried. Doing so would disclose the "
            "number to a third party without the owner's consent, and no "
            "lawful open API exists for phone-number breach lookups. Any tool "
            "claiming otherwise from a static list is guessing."
        ),
        "local_list": local,
        "risk_indicators": indicators,
        "risk_level": _risk_level(indicators),
        "recommendations": recommendations,
    }


def _risk_level(indicators: list) -> str:
    severities = {item["severity"] for item in indicators}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    if "low" in severities:
        return "low"
    return "informational"
