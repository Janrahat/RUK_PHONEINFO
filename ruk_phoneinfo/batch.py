"""Batch processing: analyse many numbers from a file, a list or stdin."""

from __future__ import annotations

import os
import sys

from . import analyze
from .utils import read_lines, unique_preserve


def load_numbers(path=None, inline=None, use_stdin: bool = False):
    """Collect numbers from a file, an inline list and/or stdin.

    Returns ``(numbers, errors)``.  Blank lines and ``#`` comments are
    ignored, duplicates are removed and input order is preserved.
    """
    numbers = []
    errors = []

    if inline:
        numbers.extend(str(item) for item in inline)

    if path:
        if not os.path.exists(path):
            errors.append("File not found: %s" % path)
        else:
            try:
                numbers.extend(read_lines(path))
            except OSError as exc:
                errors.append("Could not read %s: %s" % (path, exc))

    if use_stdin:
        try:
            for raw in sys.stdin:
                line = raw.strip()
                if line and not line.startswith("#"):
                    numbers.append(line)
        except (OSError, KeyboardInterrupt):
            pass

    return unique_preserve(numbers), errors


def run_batch(numbers, default_country: str | None = None, local_list=None,
              local_list_path=None, on_progress=None) -> list:
    """Analyse every number, preserving input order.

    A failure on one number never aborts the batch - the error is recorded in
    that number's result dict.
    """
    numbers = list(numbers)
    results = []
    total = len(numbers)
    for index, item in enumerate(numbers, start=1):
        try:
            res = analyze.analyze(item, default_country=default_country,
                                  local_list=local_list,
                                  local_list_path=local_list_path)
        except Exception as exc:  # noqa: BLE001 - one bad row must not kill the run
            res = {
                "ok": False,
                "input": str(item),
                "error": "internal_error",
                "message": str(exc),
                "valid": False,
                "e164": None,
                "iso": None,
                "country_code": None,
                "nsn": None,
                "length": None,
                "expected_lengths": [],
                "possible_countries": [],
                "ambiguous": False,
                "notes": [],
                "country": None,
                "region": None,
                "carrier": None,
                "line_type": "unknown",
                "line_type_label": None,
                "formats": None,
                "exposure": None,
                "warnings": [],
            }
        results.append(res)
        if on_progress:
            on_progress(index, total, res)
    return results


def batch_summary(results: list) -> dict:
    """Aggregate counts for a batch run."""
    total = len(results)
    valid = sum(1 for r in results if r.get("valid"))
    countries = {}
    line_types = {}
    for res in results:
        iso = res.get("iso")
        if iso:
            countries[iso] = countries.get(iso, 0) + 1
        lt = res.get("line_type") or "unknown"
        line_types[lt] = line_types.get(lt, 0) + 1
    return {
        "total": total,
        "valid": valid,
        "invalid": total - valid,
        "countries": dict(sorted(countries.items(), key=lambda p: -p[1])),
        "line_types": dict(sorted(line_types.items(), key=lambda p: -p[1])),
    }
