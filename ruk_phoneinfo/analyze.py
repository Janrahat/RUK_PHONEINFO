"""Orchestrator: run every offline analysis stage over one number."""

from __future__ import annotations

from . import carrier, exposure, formatting, region, validate


def analyze(raw, default_country: str | None = None, local_list=None,
            local_list_path=None) -> dict:
    """Full offline analysis of a single number.

    Returns one plain dict consumed by the CLI, the report writers and the
    tests.  Never raises for bad input - failures are reported in ``ok`` /
    ``error``.
    """
    parsed = validate.parse_number(raw, default_country)

    out = {
        "ok": parsed["ok"],
        "input": parsed["input"],
        "error": parsed["error"],
        "message": parsed["message"],
        "valid": parsed["valid"],
        "e164": parsed["e164"],
        "iso": parsed["iso"],
        "country_code": parsed["country_code"],
        "nsn": parsed["nsn"],
        "length": parsed["length"],
        "expected_lengths": parsed["expected_lengths"],
        "possible_countries": parsed["possible_countries"],
        "ambiguous": parsed["ambiguous"],
        "notes": list(parsed["notes"]),
        "country": None,
        "region": None,
        "carrier": None,
        "line_type": "unknown",
        "line_type_label": None,
        "formats": None,
        "exposure": None,
        "warnings": [],
    }

    if not parsed["iso"] or not parsed["nsn"]:
        out["warnings"].append(
            "Country or national number could not be resolved, so carrier, "
            "region and formatting stages were skipped."
        )
        return out

    iso = parsed["iso"]
    nsn = parsed["nsn"]
    cc = parsed["country_code"]

    out["region"] = region.lookup_region(iso, nsn)
    out["country"] = out["region"].get("country")

    out["carrier"] = carrier.lookup_carrier(iso, nsn)
    out["line_type"] = out["carrier"]["line_type"]
    out["line_type_label"] = out["carrier"]["line_type_label"]

    out["formats"] = formatting.formats(iso, cc, nsn)

    out["exposure"] = exposure.exposure_report(
        iso, nsn, parsed["e164"], out["line_type"],
        local_list=local_list, local_list_path=local_list_path,
    )

    if not parsed["valid"]:
        out["warnings"].append(
            "The number does not match the published length rules for %s; "
            "treat the derived attributes as indicative only."
            % (out["country"] or iso)
        )
    if parsed["ambiguous"]:
        out["warnings"].append(
            "The calling code is shared by several territories; the country "
            "shown is the first match."
        )
    return out


def analyze_many(numbers, default_country: str | None = None,
                 local_list=None, local_list_path=None) -> list:
    """Analyse a sequence of numbers, preserving input order."""
    return [
        analyze(item, default_country=default_country,
                local_list=local_list, local_list_path=local_list_path)
        for item in numbers
    ]
