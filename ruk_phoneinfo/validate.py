"""Number parsing and validation against the bundled numbering plans.

Everything here is offline: the input string is normalised, the country
calling code is resolved from the bundled ITU table, and the National
Significant Number is checked against the published length rules.
"""

from __future__ import annotations

from . import datasets
from .utils import digits_only

MAX_E164_DIGITS = 15
MIN_E164_DIGITS = 4


def _intl_prefixes() -> list:
    """Every international dialling prefix we know, shortest first.

    Shortest first matters: for ``00923001234567`` the correct strip is
    ``00`` (Pakistan), not ``009`` (Mauritania).  The caller additionally
    requires the resulting parse to be valid before accepting it.
    """
    prefixes = {"00", "011", "0011", "810", "000", "001", "002", "009",
                "119", "010", "0010", "0012"}
    for info in datasets.COUNTRIES.values():
        value = info.get("intl")
        if value:
            prefixes.add(value)
    return sorted(prefixes, key=len)


INTL_PREFIXES = _intl_prefixes()


def _base(raw) -> dict:
    return {
        "ok": False,
        "error": None,
        "message": None,
        "input": str(raw or ""),
        "e164": None,
        "country_code": None,
        "iso": None,
        "nsn": None,
        "national": None,
        "trunk_prefix": None,
        "valid": False,
        "length": None,
        "expected_lengths": [],
        "possible_countries": [],
        "ambiguous": False,
        "notes": [],
    }


def _fail(result: dict, code: str, message: str) -> dict:
    result["ok"] = False
    result["error"] = code
    result["message"] = message
    return result


def _finish(result: dict, iso: str, code: str, nsn: str, notes: list) -> dict:
    """Populate a result once the country and NSN are known."""
    info = datasets.country_by_iso(iso) or {}
    expected = list(info.get("nsn") or [])
    trunk = info.get("trunk") or ""

    result["iso"] = iso
    result["country_code"] = code
    result["nsn"] = nsn
    result["length"] = len(nsn)
    result["expected_lengths"] = expected
    result["trunk_prefix"] = trunk or None
    result["e164"] = "+" + code + nsn
    result["national"] = (trunk + nsn) if trunk else nsn
    result["notes"] = notes

    shared = datasets.country_by_calling_code(code)
    if len(shared) > 1:
        result["ambiguous"] = True
        result["possible_countries"] = [
            {"iso": s_iso, "name": s_info["name"]} for s_iso, s_info in shared
        ]
        notes.append(
            "Calling code +%s is shared by %d territories; the country shown "
            "is the first match. Use --country to disambiguate."
            % (code, len(shared))
        )

    if not expected:
        result["valid"] = True
        result["ok"] = True
        notes.append("No published length rule bundled for this country.")
        return result

    if len(nsn) in expected:
        result["valid"] = True
        result["ok"] = True
        return result

    result["valid"] = False
    return _fail(
        result,
        "invalid_length",
        "National number has %d digits but %s expects %s."
        % (len(nsn), info.get("name", iso),
           " or ".join(str(n) for n in expected)),
    )


def _try_international(digits: str, notes: list) -> dict | None:
    """Parse ``digits`` as an international number, or return None."""
    split = datasets.split_calling_code(digits)
    if not split:
        return None
    iso, code, nsn = split
    if not nsn:
        return None
    result = _base("+" + digits)
    return _finish(result, iso, code, nsn, notes)


def _try_national(digits: str, iso: str, notes: list) -> dict | None:
    """Parse ``digits`` as a national number for ``iso``, or return None."""
    info = datasets.country_by_iso(iso)
    if not info:
        return None
    trunk = info.get("trunk") or ""
    nsn = digits
    if trunk and digits.startswith(trunk) and len(digits) > len(trunk):
        nsn = digits[len(trunk):]
        notes.append("National trunk prefix '%s' removed." % trunk)
    expected = info.get("nsn") or []
    if expected and len(nsn) not in expected:
        return None
    result = _base(digits)
    return _finish(result, iso, info["code"], nsn, notes)


def _guess_countries(digits: str) -> list:
    """Countries whose numbering plan could accept ``digits`` as a national number."""
    out = []
    for iso, info in datasets.all_countries():
        expected = info.get("nsn") or []
        trunk = info.get("trunk") or ""
        candidates = {len(digits)}
        if trunk and digits.startswith(trunk):
            candidates.add(len(digits) - len(trunk))
        if candidates & set(expected):
            out.append({"iso": iso, "name": info["name"],
                        "country_code": info["code"]})
    return out


def parse_number(raw, default_country: str | None = None) -> dict:
    """Parse and validate a phone number.

    Accepts ``+CC...``, ``00CC...``, ``CC...`` and national forms with or
    without the trunk prefix.  Returns a plain dict; never raises.
    """
    original = str(raw or "").strip()
    result = _base(original)

    if not original:
        return _fail(result, "empty_input", "No number supplied.")

    explicit_plus = original.startswith("+")
    digits = digits_only(original)

    if not digits:
        return _fail(result, "no_digits", "Input contains no digits.")
    if len(digits) < MIN_E164_DIGITS:
        return _fail(result, "too_short",
                     "Only %d digits - too short to be a phone number." % len(digits))
    if len(digits) > MAX_E164_DIGITS:
        return _fail(result, "too_long",
                     "%d digits exceeds the E.164 maximum of %d."
                     % (len(digits), MAX_E164_DIGITS))

    notes: list = []

    # 1. Explicit international form.
    if explicit_plus:
        parsed = _try_international(digits, notes)
        if parsed:
            return parsed
        return _fail(result, "unknown_country_code",
                     "No bundled numbering plan matches the calling code in "
                     "'%s'." % original)

    # 2. National form when the caller told us the country.
    if default_country:
        parsed = _try_national(digits, default_country, notes)
        if parsed:
            return parsed
        notes = []

    # 3. International dialling prefix (00, 011, 810, ...).
    #    Shortest prefix first, and only accept a parse that is actually
    #    valid: otherwise "00923001234567" would strip "009" and resolve to
    #    Mauritania instead of stripping "00" and resolving to Pakistan.
    for prefix in INTL_PREFIXES:
        if digits.startswith(prefix) and len(digits) > len(prefix) + 3:
            attempt_notes: list = []
            parsed = _try_international(digits[len(prefix):], attempt_notes)
            if parsed and parsed["ok"]:
                attempt_notes.append(
                    "International dialling prefix '%s' removed." % prefix)
                return parsed

    # 4. Bare calling code without '+'.
    parsed = _try_international(digits, notes)
    if parsed:
        notes.append("Parsed as an international number without a leading '+'.")
        return parsed

    # 5. Give up, but tell the user which countries could match.
    guesses = _guess_countries(digits)
    result["possible_countries"] = guesses
    if guesses:
        return _fail(
            result, "country_required",
            "Cannot determine the country. Add a leading '+' with the calling "
            "code, or pass --country. %d bundled plan(s) could match this "
            "length." % len(guesses),
        )
    return _fail(result, "unrecognised",
                 "No bundled numbering plan matches '%s'." % original)


def validate_number(raw, default_country: str | None = None) -> dict:
    """Return a compact validity verdict for a number."""
    parsed = parse_number(raw, default_country)
    return {
        "ok": parsed["ok"],
        "input": parsed["input"],
        "valid": parsed["valid"],
        "error": parsed["error"],
        "message": parsed["message"],
        "e164": parsed["e164"],
        "iso": parsed["iso"],
        "country_code": parsed["country_code"],
        "nsn": parsed["nsn"],
        "length": parsed["length"],
        "expected_lengths": parsed["expected_lengths"],
        "possible_countries": parsed["possible_countries"],
        "ambiguous": parsed["ambiguous"],
        "notes": parsed["notes"],
    }


def is_valid(raw, default_country: str | None = None) -> bool:
    """True when the number parses and matches its plan's length rules."""
    return bool(parse_number(raw, default_country).get("valid"))
