"""Command-line interface: argparse subcommands plus an interactive menu.

Both entry points call the same ``cmd_*`` handlers, so the menu and the
subcommands can never drift apart.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import (analyze, batch, carrier, config, datasets, formatting, region,
               report, ui, validate)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_TERMS = 3
EXIT_ERROR = 1


def _common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--country", "-c", metavar="ISO",
                        help="ISO country code used to interpret national "
                             "numbers (e.g. PK, US, GB).")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON on stdout.")
    parser.add_argument("--out", metavar="PATH",
                        help="Write a report to PATH (extension added per format).")
    parser.add_argument("--format", "-f", default="json",
                        choices=["json", "html", "txt", "all"],
                        help="Report format for --out (default: json).")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colours.")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress the banner and progress output.")
    parser.add_argument("--accept-terms", action="store_true",
                        help="Accept the legal notice non-interactively.")
    parser.add_argument("--list", metavar="FILE",
                        help="Check the number against a local list file "
                             "(never transmitted).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ruk_phoneinfo",
        description="RUK_PHONEINFO - offline phone number OSINT toolkit for "
                    "Termux. Public numbering-plan data only; no live "
                    "location tracking.",
        epilog="Use only on your own numbers or numbers you are authorised to "
               "analyse.",
    )
    parser.add_argument("--version", "-V", action="store_true",
                        help="Show the version and exit.")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_info = sub.add_parser("info", help="Full offline analysis of a number.")
    p_info.add_argument("number", help="Phone number to analyse.")
    p_info.add_argument("--no-exposure", action="store_true",
                        help="Skip the exposure assessment section.")
    _common_options(p_info)
    p_info.set_defaults(func=cmd_info)

    p_val = sub.add_parser("validate", help="Check whether a number is valid.")
    p_val.add_argument("number")
    _common_options(p_val)
    p_val.set_defaults(func=cmd_validate)

    p_car = sub.add_parser("carrier", help="Resolve operator and line type.")
    p_car.add_argument("number")
    _common_options(p_car)
    p_car.set_defaults(func=cmd_carrier)

    p_fmt = sub.add_parser("format", help="Show every number format.")
    p_fmt.add_argument("number")
    _common_options(p_fmt)
    p_fmt.set_defaults(func=cmd_format)

    p_reg = sub.add_parser("region", help="Country, region, time zone, area.")
    p_reg.add_argument("number")
    _common_options(p_reg)
    p_reg.set_defaults(func=cmd_region)

    p_batch = sub.add_parser("batch", help="Analyse many numbers from a file.")
    p_batch.add_argument("file", nargs="?", help="File with one number per line.")
    p_batch.add_argument("--stdin", action="store_true",
                         help="Also read numbers from stdin.")
    _common_options(p_batch)
    p_batch.set_defaults(func=cmd_batch)

    p_rep = sub.add_parser("report", help="Analyse and write a report file.")
    p_rep.add_argument("number", nargs="?", help="A single number.")
    p_rep.add_argument("--file", metavar="FILE",
                       help="Or a file with one number per line.")
    p_rep.add_argument("--title", help="Report title (HTML).")
    _common_options(p_rep)
    p_rep.set_defaults(func=cmd_report)

    p_menu = sub.add_parser("menu", help="Open the interactive menu.")
    _common_options(p_menu)
    p_menu.set_defaults(func=cmd_menu)

    p_ver = sub.add_parser("version", help="Show version information.")
    p_ver.set_defaults(func=cmd_version)

    p_ds = sub.add_parser("datasets", help="Show bundled dataset statistics.")
    p_ds.add_argument("--countries", action="store_true",
                      help="List every bundled country.")
    _common_options(p_ds)
    p_ds.set_defaults(func=cmd_datasets)

    return parser


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _ns(**overrides):
    """A namespace seeded with every field the handlers read.

    The interactive menu calls ``cmd_*`` directly, bypassing argparse, so
    every attribute must exist or the handler raises AttributeError.
    """
    base = {
        "number": None,
        "file": None,
        "stdin": False,
        "country": None,
        "json": False,
        "out": None,
        "format": "json",
        "no_color": False,
        "quiet": False,
        "accept_terms": False,
        "list": None,
        "no_exposure": False,
        "title": None,
        "countries": False,
        "command": None,
        "func": None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _apply_ui(args) -> None:
    if getattr(args, "no_color", False):
        ui.set_color(False)


def _gate(args) -> bool:
    """Run the consent gate, non-interactive safe."""
    interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())
    accepted = config.legal_gate(
        interactive=interactive,
        force_accept=getattr(args, "accept_terms", False),
        quiet=getattr(args, "quiet", False),
    )
    if accepted:
        return True
    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps({
            "ok": False,
            "error": "terms_not_accepted",
            "message": "The legal notice has not been accepted. Re-run with "
                       "--accept-terms or set RUK_ACCEPT_TERMS=1.",
        }, indent=2))
    else:
        print(ui.err("Legal notice not accepted - refusing to continue."))
        print(ui.info("Re-run with --accept-terms, or set RUK_ACCEPT_TERMS=1."))
    return False


def _emit(args, results: list, single: bool = True) -> int:
    """Print results and optionally write a report file."""
    if getattr(args, "json", False):
        import json as _json
        payload = results[0] if (single and len(results) == 1) else results
        print(_json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if single and len(results) == 1:
            print(report.console_report(
                results[0],
                show_exposure=not getattr(args, "no_exposure", False),
            ))
        else:
            print(report.console_batch(results))

    out = getattr(args, "out", None)
    if out:
        try:
            written = report.write_report(
                results, fmt=getattr(args, "format", "json"), out=out,
                title=getattr(args, "title", None),
            )
        except (OSError, ValueError) as exc:
            print(ui.err("Could not write report: %s" % exc))
            return EXIT_ERROR
        if not getattr(args, "quiet", False):
            for fmt, path in written.items():
                print(ui.ok("Wrote %s report: %s" % (fmt.upper(), path)))
    return EXIT_OK


def _analyse_one(args, number: str) -> dict:
    return analyze.analyze(
        number,
        default_country=getattr(args, "country", None),
        local_list_path=getattr(args, "list", None),
    )


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_info(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    if not getattr(args, "quiet", False) and not getattr(args, "json", False):
        print(ui.banner())
    result = _analyse_one(args, args.number)
    return _emit(args, [result])


def cmd_validate(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    verdict = validate.validate_number(args.number,
                                       getattr(args, "country", None))
    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps(verdict, indent=2, ensure_ascii=False))
    else:
        if not getattr(args, "quiet", False):
            print(ui.banner())
        print(ui.section("Validation"))
        print(ui.kv([
            ("Input", verdict["input"]),
            ("Valid", ui.c("YES", "green", "bold") if verdict["valid"]
             else ui.c("NO", "red", "bold")),
            ("E.164", verdict["e164"]),
            ("Country code", ("+" + verdict["country_code"])
             if verdict["country_code"] else None),
            ("NSN", verdict["nsn"]),
            ("NSN length", verdict["length"]),
            ("Expected", ", ".join(str(n) for n in verdict["expected_lengths"])
             or None),
        ]))
        if verdict["message"]:
            print("  " + ui.warn(verdict["message"]))
        if verdict["possible_countries"]:
            print("")
            print("  " + ui.c("Possible countries", "bold", "white"))
            for item in verdict["possible_countries"][:15]:
                print(ui.bullet("%s (%s) +%s" % (item["name"], item["iso"],
                                                  item["country_code"]), indent=4))
    if getattr(args, "out", None):
        return _emit(args, [_analyse_one(args, args.number)])
    return EXIT_OK


def cmd_carrier(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    parsed = validate.parse_number(args.number, getattr(args, "country", None))
    if not parsed["iso"]:
        if getattr(args, "json", False):
            import json as _json
            print(_json.dumps(parsed, indent=2, ensure_ascii=False))
        else:
            print(ui.err(parsed["message"] or "Could not parse the number."))
        return EXIT_ERROR
    res = carrier.lookup_carrier(parsed["iso"], parsed["nsn"])
    res["e164"] = parsed["e164"]
    res["iso"] = parsed["iso"]
    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if not getattr(args, "quiet", False):
            print(ui.banner())
        print(ui.section("Carrier & Line Type"))
        print(ui.kv([
            ("Number", parsed["e164"]),
            ("Operator", res["operator"]),
            ("Line type", res["line_type_label"]),
            ("Matched prefix", res["prefix"]),
            ("Confidence", res["confidence"]),
        ]))
        if res["note"]:
            print("  " + ui.c(res["note"], "grey"))
    if getattr(args, "out", None):
        return _emit(args, [_analyse_one(args, args.number)])
    return EXIT_OK


def cmd_format(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    parsed = validate.parse_number(args.number, getattr(args, "country", None))
    if not parsed["iso"]:
        if getattr(args, "json", False):
            import json as _json
            print(_json.dumps(parsed, indent=2, ensure_ascii=False))
        else:
            print(ui.err(parsed["message"] or "Could not parse the number."))
        return EXIT_ERROR
    res = formatting.formats(parsed["iso"], parsed["country_code"], parsed["nsn"])
    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if not getattr(args, "quiet", False):
            print(ui.banner())
        print(ui.section("Formats"))
        print(ui.kv([
            ("E.164", res["e164"]),
            ("International", res["international"]),
            ("National", res["national"]),
            ("National (pretty)", res["national_pretty"]),
            ("RFC 3966 URI", res["rfc3966"]),
            ("Digits only", res["digits_only"]),
            ("Trunk prefix", res["trunk_prefix"]),
        ]))
    if getattr(args, "out", None):
        return _emit(args, [_analyse_one(args, args.number)])
    return EXIT_OK


def cmd_region(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    parsed = validate.parse_number(args.number, getattr(args, "country", None))
    if not parsed["iso"]:
        if getattr(args, "json", False):
            import json as _json
            print(_json.dumps(parsed, indent=2, ensure_ascii=False))
        else:
            print(ui.err(parsed["message"] or "Could not parse the number."))
        return EXIT_ERROR
    res = region.lookup_region(parsed["iso"], parsed["nsn"])
    res["e164"] = parsed["e164"]
    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if not getattr(args, "quiet", False):
            print(ui.banner())
        print(ui.section("Country & Region"))
        print(ui.kv([
            ("Number", parsed["e164"]),
            ("Country", "%s %s" % (res["flag"] or "", res["country"] or "")),
            ("Country (Urdu)", res["country_ur"]),
            ("ISO code", res["iso"]),
            ("Region", res["region"]),
            ("Time zone(s)", ", ".join(res["timezones"]) or None),
            ("Area code", res["area_code"]),
            ("Area name", res["area_name"]),
        ]))
        if res["note"]:
            print("  " + ui.c(res["note"], "grey"))
    if getattr(args, "out", None):
        return _emit(args, [_analyse_one(args, args.number)])
    return EXIT_OK


def cmd_batch(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    numbers, errors = batch.load_numbers(
        path=getattr(args, "file", None),
        use_stdin=bool(getattr(args, "stdin", False)),
    )
    for err in errors:
        print(ui.err(err))
    if not numbers:
        print(ui.warn("No numbers to analyse. Pass a file or use --stdin."))
        return EXIT_USAGE

    if not getattr(args, "quiet", False) and not getattr(args, "json", False):
        print(ui.banner())
        print(ui.info("Analysing %d number(s)..." % len(numbers)))

    results = batch.run_batch(
        numbers,
        default_country=getattr(args, "country", None),
        local_list_path=getattr(args, "list", None),
    )
    code = _emit(args, results, single=False)
    if not getattr(args, "json", False) and not getattr(args, "quiet", False):
        summary = batch.batch_summary(results)
        print("")
        print(ui.section("Summary"))
        print(ui.kv([
            ("Total", summary["total"]),
            ("Valid", ui.c(summary["valid"], "green", "bold")),
            ("Invalid", ui.c(summary["invalid"], "red", "bold")),
            ("Countries", ", ".join("%s:%d" % (k, v)
                                     for k, v in summary["countries"].items()) or None),
        ]))
    return code


def cmd_report(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    numbers = []
    if getattr(args, "number", None):
        numbers.append(args.number)
    if getattr(args, "file", None):
        loaded, errors = batch.load_numbers(path=args.file)
        for err in errors:
            print(ui.err(err))
        numbers.extend(loaded)
    if not numbers:
        print(ui.warn("Nothing to report on. Pass a number or --file."))
        return EXIT_USAGE

    results = batch.run_batch(
        numbers,
        default_country=getattr(args, "country", None),
        local_list_path=getattr(args, "list", None),
    )
    out = getattr(args, "out", None) or "ruk_phoneinfo_report"
    try:
        written = report.write_report(
            results, fmt=getattr(args, "format", "json"), out=out,
            title=getattr(args, "title", None),
        )
    except (OSError, ValueError) as exc:
        print(ui.err("Could not write report: %s" % exc))
        return EXIT_ERROR

    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps({"ok": True, "written": written,
                           "count": len(results)}, indent=2))
    else:
        if not getattr(args, "quiet", False):
            print(ui.banner())
        print(ui.section("Report Written"))
        for fmt, path in written.items():
            print(ui.ok("%s -> %s" % (fmt.upper(), path)))
        print("")
        print("  " + ui.c(report.DISCLAIMER, "yellow"))
    return EXIT_OK


def cmd_datasets(args) -> int:
    _apply_ui(args)
    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps({
            "countries": datasets.country_count(),
            "carrier_tables": datasets.carrier_country_count(),
            "line_types": datasets.LINE_TYPES,
        }, indent=2, ensure_ascii=False))
        return EXIT_OK
    if not getattr(args, "quiet", False):
        print(ui.banner())
    print(ui.section("Bundled Datasets"))
    print(ui.kv([
        ("Countries", datasets.country_count()),
        ("Carrier tables", datasets.carrier_country_count()),
        ("Line types", ", ".join(datasets.LINE_TYPES.values())),
        ("Network access", ui.c("NONE - fully offline", "green", "bold")),
    ]))
    if getattr(args, "countries", False):
        rows = [[iso, info["name"], "+" + info["code"],
                 ", ".join(str(n) for n in info["nsn"])]
                for iso, info in datasets.all_countries()]
        print("")
        print(ui.table(["ISO", "Country", "Code", "NSN length"], rows))
    return EXIT_OK


def cmd_version(args) -> int:
    _apply_ui(args)
    print("%s v%s" % (config.APP_NAME, config.VERSION))
    print("Released: %s" % config.RELEASE_DATE)
    print("Repository: %s" % config.REPO_URL)
    print("Python: %s" % sys.version.split()[0])
    print("Mode: offline public-data analysis (no live location tracking)")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

MENU_ITEMS = [
    ("1", "Full number info", "info"),
    ("2", "Validate a number", "validate"),
    ("3", "Carrier & line type", "carrier"),
    ("4", "Number formats", "format"),
    ("5", "Country / region / area", "region"),
    ("6", "Batch from a file", "batch"),
    ("7", "Write a report", "report"),
    ("8", "Bundled dataset stats", "datasets"),
    ("9", "Version information", "version"),
    ("0", "Exit", None),
]


def _menu_banner() -> None:
    print(ui.banner())
    print(ui.section("Main Menu"))
    for key, label, _ in MENU_ITEMS:
        print("   " + ui.c("[%s]" % key, "cyan", "bold") + " " + label)
    print("")
    print("  " + ui.c("Offline public-data analysis only. No live location "
                        "tracking is possible or performed.", "yellow"))
    print("")


def _prompt(text: str, default: str = "") -> str:
    try:
        value = input(ui.c(text, "white", "bold")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""
    return value or default


def cmd_menu(args) -> int:
    _apply_ui(args)
    if not _gate(args):
        return EXIT_TERMS
    while True:
        _menu_banner()
        choice = _prompt("  Select an option: ")
        if choice in ("0", "q", "quit", "exit"):
            print(ui.info("Goodbye."))
            return EXIT_OK

        if choice == "9":
            cmd_version(_ns(quiet=True))
            _prompt("  Press Enter to continue...")
            continue
        if choice == "8":
            cmd_datasets(_ns(quiet=True))
            _prompt("  Press Enter to continue...")
            continue
        if choice == "6":
            path = _prompt("  Path to the number list file: ")
            if not path:
                print(ui.warn("No file given."))
                continue
            cmd_batch(_ns(file=path, quiet=True))
            _prompt("  Press Enter to continue...")
            continue
        if choice == "7":
            number = _prompt("  Number (blank to use a file): ")
            path = None
            if not number:
                path = _prompt("  Path to the number list file: ")
            fmt = _prompt("  Format [json/html/txt/all] (default json): ", "json")
            out = _prompt("  Output path stem (default ruk_phoneinfo_report): ",
                          "ruk_phoneinfo_report")
            cmd_report(_ns(number=number or None, file=path, format=fmt,
                           out=out, quiet=True))
            _prompt("  Press Enter to continue...")
            continue

        handler = {
            "1": cmd_info, "2": cmd_validate, "3": cmd_carrier,
            "4": cmd_format, "5": cmd_region,
        }.get(choice)
        if handler is None:
            print(ui.warn("Unknown option '%s'." % choice))
            continue

        number = _prompt("  Enter the phone number: ")
        if not number:
            print(ui.warn("No number given."))
            continue
        country = _prompt("  Country ISO code (blank to auto-detect): ") or None
        handler(_ns(number=number, country=country, quiet=True))
        _prompt("  Press Enter to continue...")


def main(argv=None) -> int:
    """Entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False) and not getattr(args, "command", None):
        return cmd_version(_ns(quiet=True))

    if not getattr(args, "command", None):
        # No subcommand: open the menu when interactive, else show help.
        if sys.stdin and sys.stdin.isatty():
            return cmd_menu(_ns())
        parser.print_help()
        return EXIT_USAGE

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print()
        print(ui.warn("Interrupted."))
        return 130
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except OSError:
            pass
        return EXIT_OK
    except Exception as exc:  # noqa: BLE001 - never show a traceback to the user
        if getattr(args, "json", False):
            import json as _json
            print(_json.dumps({"ok": False, "error": "internal_error",
                               "message": str(exc)}, indent=2))
        else:
            print(ui.err("Unexpected error: %s" % exc))
        return EXIT_ERROR
