"""Report writers: console, JSON, HTML and plain text.

Every writer consumes the plain dict produced by :mod:`ruk_phoneinfo.analyze`,
so the console view, the JSON export and the HTML page can never disagree.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

from . import config, datasets, ui

DISCLAIMER = (
    "RUK_PHONEINFO performs OFFLINE analysis of public numbering-plan data. "
    "It does NOT and CANNOT determine a phone's live GPS location. Use it "
    "only on your own numbers, or on numbers for which you hold written "
    "authorisation from the owner."
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _dash(value):
    return "-" if value in (None, "", [], {}) else value


def _yesno(value) -> str:
    return "Yes" if value else "No"


# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

_RISK_COLOR = {
    "high": "red",
    "medium": "orange",
    "low": "yellow",
    "informational": "cyan",
}


def console_report(result: dict, show_exposure: bool = True,
                   show_notes: bool = True) -> str:
    """Render one analysis result as a coloured terminal report."""
    out = []
    header = result.get("e164") or result.get("input") or "?"
    out.append(ui.section("RUK_PHONEINFO  |  %s" % header))

    valid = result.get("valid")
    valid_text = ui.c("VALID", "green", "bold") if valid else ui.c(
        "NOT VALID", "red", "bold")
    if result.get("error"):
        valid_text += "  " + ui.c("(%s)" % result["error"], "grey")

    out.append(ui.kv([
        ("Input", result.get("input")),
        ("Status", valid_text),
        ("E.164", result.get("e164")),
        ("Country code", ("+" + result["country_code"])
         if result.get("country_code") else None),
        ("National (NSN)", result.get("nsn")),
        ("NSN length", result.get("length")),
        ("Expected length", ", ".join(str(n) for n in
                                       (result.get("expected_lengths") or [])) or None),
    ]))

    if result.get("message"):
        out.append("")
        out.append("  " + ui.warn(result["message"]))

    region = result.get("region") or {}
    if region.get("ok"):
        out.append("")
        out.append(ui.section("Country & Region"))
        out.append(ui.kv([
            ("Country", "%s %s" % (region.get("flag") or "",
                                    region.get("country") or "")),
            ("Country (Urdu)", region.get("country_ur")),
            ("ISO code", region.get("iso")),
            ("Region", region.get("region")),
            ("Time zone(s)", ", ".join(region.get("timezones") or []) or None),
            ("Area code", region.get("area_code")),
            ("Area name", region.get("area_name")),
        ]))

    carrier = result.get("carrier") or {}
    out.append("")
    out.append(ui.section("Carrier & Line Type"))
    out.append(ui.kv([
        ("Operator", carrier.get("operator")),
        ("Line type", result.get("line_type_label")),
        ("Matched prefix", carrier.get("prefix")),
        ("Confidence", carrier.get("confidence")),
    ]))
    if carrier.get("note"):
        out.append("  " + ui.c(carrier["note"], "grey"))

    fmt = result.get("formats") or {}
    if fmt.get("ok"):
        out.append("")
        out.append(ui.section("Formats"))
        out.append(ui.kv([
            ("E.164", fmt.get("e164")),
            ("International", fmt.get("international")),
            ("National", fmt.get("national")),
            ("National (pretty)", fmt.get("national_pretty")),
            ("RFC 3966 URI", fmt.get("rfc3966")),
            ("Digits only", fmt.get("digits_only")),
        ]))

    if show_exposure and result.get("exposure"):
        exp = result["exposure"]
        out.append("")
        out.append(ui.section("Exposure Assessment (offline)"))
        level = exp.get("risk_level", "informational")
        out.append(ui.kv([
            ("Risk level", ui.c(str(level).upper(),
                                 _RISK_COLOR.get(level, "cyan"), "bold")),
            ("Online lookup", ui.c("NOT PERFORMED", "yellow", "bold")),
        ]))
        out.append("  " + ui.c(exp.get("online_lookup_reason", ""), "grey"))

        local = exp.get("local_list") or {}
        if local.get("checked"):
            verdict = (ui.c("FOUND", "red", "bold") if local.get("match")
                       else ui.c("not found", "green"))
            out.append("")
            out.append(ui.kv([
                ("Local list", local.get("source")),
                ("Entries checked", local.get("entries")),
                ("Result", verdict),
            ]))
        elif local.get("error"):
            out.append("  " + ui.warn("Local list: %s" % local["error"]))

        indicators = exp.get("risk_indicators") or []
        if indicators:
            out.append("")
            out.append("  " + ui.c("Indicators", "bold", "white"))
            for item in indicators:
                colour = _RISK_COLOR.get(item.get("severity"), "cyan")
                out.append("    " + ui.c("[%s]" % item.get("severity", "?").upper(),
                                          colour, "bold") + " "
                           + ui.c(item.get("id", ""), "white"))
                out.append("        " + ui.c(item.get("detail", ""), "grey"))

        recs = exp.get("recommendations") or []
        if recs:
            out.append("")
            out.append("  " + ui.c("Recommendations", "bold", "white"))
            for rec in recs:
                out.append(ui.bullet(ui.c(rec, "grey"), indent=4))

    if show_notes:
        notes = list(result.get("notes") or []) + list(result.get("warnings") or [])
        if notes:
            out.append("")
            out.append(ui.section("Notes"))
            for note in notes:
                out.append(ui.bullet(ui.c(note, "grey")))

    out.append("")
    out.append("  " + ui.c(DISCLAIMER, "yellow"))
    return "\n".join(out)


def console_batch(results: list, show_exposure: bool = False) -> str:
    """Render a compact table for many results."""
    rows = []
    for res in results:
        region = res.get("region") or {}
        carrier = res.get("carrier") or {}
        rows.append([
            res.get("input") or "",
            res.get("e164") or "-",
            region.get("country") or "-",
            carrier.get("operator") or "-",
            res.get("line_type_label") or "-",
            "yes" if res.get("valid") else "no",
        ])
    out = [ui.section("Batch Results (%d)" % len(results))]
    out.append(ui.table(
        ["Input", "E.164", "Country", "Operator", "Line type", "Valid"],
        rows,
        aligns=["left", "left", "left", "left", "left", "center"],
    ))
    valid = sum(1 for r in results if r.get("valid"))
    out.append("")
    out.append(ui.kv([
        ("Total", len(results)),
        ("Valid", ui.c(valid, "green", "bold")),
        ("Invalid", ui.c(len(results) - valid, "red", "bold")),
    ]))
    out.append("")
    out.append("  " + ui.c(DISCLAIMER, "yellow"))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def write_json(results: list, path: str) -> str:
    payload = {
        "tool": config.APP_NAME,
        "version": config.VERSION,
        "generated_at": _now(),
        "disclaimer": DISCLAIMER,
        "live_location_tracking": False,
        "count": len(results),
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


# ---------------------------------------------------------------------------
# Plain text
# ---------------------------------------------------------------------------


def _txt_block(result: dict) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("NUMBER: %s" % (result.get("e164") or result.get("input")))
    lines.append("=" * 72)
    lines.append("Input            : %s" % _dash(result.get("input")))
    lines.append("Valid            : %s" % _yesno(result.get("valid")))
    lines.append("E.164            : %s" % _dash(result.get("e164")))
    lines.append("Country code     : %s" % (
        "+" + result["country_code"] if result.get("country_code") else "-"))
    lines.append("NSN              : %s" % _dash(result.get("nsn")))
    lines.append("NSN length       : %s" % _dash(result.get("length")))
    if result.get("message"):
        lines.append("Message          : %s" % result["message"])

    region = result.get("region") or {}
    if region.get("ok"):
        lines.append("")
        lines.append("-- Country & Region --")
        lines.append("Country          : %s" % _dash(region.get("country")))
        lines.append("ISO              : %s" % _dash(region.get("iso")))
        lines.append("Region           : %s" % _dash(region.get("region")))
        lines.append("Time zone(s)     : %s" % (
            ", ".join(region.get("timezones") or []) or "-"))
        lines.append("Area code        : %s" % _dash(region.get("area_code")))
        lines.append("Area name        : %s" % _dash(region.get("area_name")))

    carrier = result.get("carrier") or {}
    lines.append("")
    lines.append("-- Carrier & Line Type --")
    lines.append("Operator         : %s" % _dash(carrier.get("operator")))
    lines.append("Line type        : %s" % _dash(result.get("line_type_label")))
    lines.append("Confidence       : %s" % _dash(carrier.get("confidence")))
    if carrier.get("note"):
        lines.append("Note             : %s" % carrier["note"])

    fmt = result.get("formats") or {}
    if fmt.get("ok"):
        lines.append("")
        lines.append("-- Formats --")
        lines.append("E.164            : %s" % _dash(fmt.get("e164")))
        lines.append("International    : %s" % _dash(fmt.get("international")))
        lines.append("National         : %s" % _dash(fmt.get("national")))
        lines.append("RFC 3966         : %s" % _dash(fmt.get("rfc3966")))

    exp = result.get("exposure") or {}
    if exp:
        lines.append("")
        lines.append("-- Exposure (offline) --")
        lines.append("Risk level       : %s" % _dash(exp.get("risk_level")))
        lines.append("Online lookup    : NOT PERFORMED")
        for item in exp.get("risk_indicators") or []:
            lines.append("  [%s] %s - %s" % (item.get("severity", "?").upper(),
                                               item.get("id", ""),
                                               item.get("detail", "")))

    notes = list(result.get("notes") or []) + list(result.get("warnings") or [])
    if notes:
        lines.append("")
        lines.append("-- Notes --")
        for note in notes:
            lines.append("  * %s" % note)
    return "\n".join(lines)


def write_txt(results: list, path: str) -> str:
    parts = [
        "%s v%s" % (config.APP_NAME, config.VERSION),
        "Generated: %s" % _now(),
        "Numbers analysed: %d" % len(results),
        "",
        DISCLAIMER,
        "",
    ]
    for res in results:
        parts.append(_txt_block(res))
        parts.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return path


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_HTML_CSS = """
:root{--bg:#0b0f14;--panel:#141a22;--panel2:#1b232d;--border:#2a3441;
--fg:#e6edf3;--muted:#8b98a8;--accent:#4da3ff;--ok:#3fb950;--warn:#d29922;
--err:#f85149;--info:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
"Noto Naskh Arabic","Noto Sans Arabic",sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:28px 18px 60px}
header{border-bottom:1px solid var(--border);padding-bottom:18px;margin-bottom:24px}
h1{margin:0 0 6px;font-size:26px;letter-spacing:.5px}
h1 span{color:var(--accent)}
.meta{color:var(--muted);font-size:13px}
.notice{background:#2a1f0a;border:1px solid #6b4d10;border-left:4px solid var(--warn);
padding:12px 16px;border-radius:8px;margin:18px 0;font-size:13.5px;color:#f0d9a8}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;
padding:20px 22px;margin:0 0 22px}
.card h2{margin:0 0 4px;font-size:19px;color:var(--accent);word-break:break-all}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;
font-weight:600;margin-left:8px;vertical-align:middle}
.badge.ok{background:rgba(63,185,80,.15);color:var(--ok);border:1px solid rgba(63,185,80,.4)}
.badge.bad{background:rgba(248,81,73,.15);color:var(--err);border:1px solid rgba(248,81,73,.4)}
.badge.warn{background:rgba(210,153,34,.15);color:var(--warn);border:1px solid rgba(210,153,34,.4)}
.badge.info{background:rgba(88,166,255,.15);color:var(--info);border:1px solid rgba(88,166,255,.4)}
h3{font-size:13px;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);
margin:22px 0 10px;border-bottom:1px solid var(--border);padding-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:14px}
td{padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
td.k{color:var(--muted);width:210px;white-space:nowrap}
tr:last-child td{border-bottom:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13.5px}
ul{margin:8px 0 0;padding-left:20px}
li{margin:5px 0;color:#c9d4e0}
.flag{font-size:20px;margin-right:6px}
footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--border);
color:var(--muted);font-size:12.5px;text-align:center}
@media print{body{background:#fff;color:#111}.card{border-color:#ccc;background:#fff}
.notice{background:#fff8e6;color:#5a4300}}
"""


def _html_rows(pairs) -> str:
    out = []
    for key, value in pairs:
        out.append("<tr><td class=\"k\">%s</td><td>%s</td></tr>"
                   % (_esc(key), _esc(_dash(value))))
    return "".join(out)


def _html_card(result: dict) -> str:
    parts = []
    valid = result.get("valid")
    badge = ("<span class=\"badge ok\">VALID</span>" if valid
             else "<span class=\"badge bad\">NOT VALID</span>")
    parts.append("<div class=\"card\">")
    parts.append("<h2>%s%s</h2>" % (_esc(result.get("e164")
                                       or result.get("input")), badge))
    if result.get("message"):
        parts.append("<p class=\"meta\">%s</p>" % _esc(result["message"]))

    parts.append("<h3>Identity</h3><table>")
    parts.append(_html_rows([
        ("Input", result.get("input")),
        ("E.164", result.get("e164")),
        ("Country code", ("+" + result["country_code"])
         if result.get("country_code") else None),
        ("National (NSN)", result.get("nsn")),
        ("NSN length", result.get("length")),
        ("Expected length", ", ".join(str(n) for n in
                                       (result.get("expected_lengths") or []))),
    ]))
    parts.append("</table>")

    region = result.get("region") or {}
    if region.get("ok"):
        parts.append("<h3>Country &amp; Region</h3><table>")
        parts.append(_html_rows([
            ("Country", "%s %s" % (region.get("flag") or "",
                                    region.get("country") or "")),
            ("Country (Urdu)", region.get("country_ur")),
            ("ISO code", region.get("iso")),
            ("Region", region.get("region")),
            ("Time zone(s)", ", ".join(region.get("timezones") or [])),
            ("Area code", region.get("area_code")),
            ("Area name", region.get("area_name")),
        ]))
        parts.append("</table>")

    carrier = result.get("carrier") or {}
    parts.append("<h3>Carrier &amp; Line Type</h3><table>")
    parts.append(_html_rows([
        ("Operator", carrier.get("operator")),
        ("Line type", result.get("line_type_label")),
        ("Matched prefix", carrier.get("prefix")),
        ("Confidence", carrier.get("confidence")),
        ("Note", carrier.get("note")),
    ]))
    parts.append("</table>")

    fmt = result.get("formats") or {}
    if fmt.get("ok"):
        parts.append("<h3>Formats</h3><table>")
        parts.append(_html_rows([
            ("E.164", fmt.get("e164")),
            ("International", fmt.get("international")),
            ("National", fmt.get("national")),
            ("National (pretty)", fmt.get("national_pretty")),
            ("RFC 3966 URI", fmt.get("rfc3966")),
            ("Digits only", fmt.get("digits_only")),
        ]))
        parts.append("</table>")

    exp = result.get("exposure") or {}
    if exp:
        level = str(exp.get("risk_level", "informational"))
        cls = {"high": "bad", "medium": "warn", "low": "warn"}.get(level, "info")
        parts.append("<h3>Exposure Assessment (offline)</h3>")
        parts.append("<p><span class=\"badge %s\">RISK: %s</span> "
                     "<span class=\"badge info\">NO ONLINE LOOKUP</span></p>"
                     % (cls, _esc(level.upper())))
        parts.append("<p class=\"meta\">%s</p>" % _esc(exp.get("online_lookup_reason")))

        local = exp.get("local_list") or {}
        if local.get("checked"):
            parts.append("<table>")
            parts.append(_html_rows([
                ("Local list", local.get("source")),
                ("Entries checked", local.get("entries")),
                ("Result", "FOUND" if local.get("match") else "not found"),
            ]))
            parts.append("</table>")

        indicators = exp.get("risk_indicators") or []
        if indicators:
            parts.append("<ul>")
            for item in indicators:
                parts.append("<li><strong>[%s] %s</strong> &mdash; %s</li>"
                             % (_esc(str(item.get("severity", "?")).upper()),
                                _esc(item.get("id")), _esc(item.get("detail"))))
            parts.append("</ul>")

        recs = exp.get("recommendations") or []
        if recs:
            parts.append("<h3>Recommendations</h3><ul>")
            for rec in recs:
                parts.append("<li>%s</li>" % _esc(rec))
            parts.append("</ul>")

    notes = list(result.get("notes") or []) + list(result.get("warnings") or [])
    if notes:
        parts.append("<h3>Notes</h3><ul>")
        for note in notes:
            parts.append("<li>%s</li>" % _esc(note))
        parts.append("</ul>")

    parts.append("</div>")
    return "".join(parts)


def write_html(results: list, path: str, title: str | None = None) -> str:
    title = title or "%s Report" % config.APP_NAME
    body = [
        "<!DOCTYPE html>",
        "<html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        "<title>%s</title>" % _esc(title),
        "<style>%s</style></head><body><div class=\"wrap\">" % _HTML_CSS,
        "<header><h1>RUK_<span>PHONEINFO</span></h1>",
        "<div class=\"meta\">v%s &middot; generated %s &middot; %d number(s) "
        "analysed</div></header>" % (_esc(config.VERSION), _esc(_now()), len(results)),
        "<div class=\"notice\"><strong>Offline public-data analysis only.</strong> "
        "%s</div>" % _esc(DISCLAIMER),
    ]
    for res in results:
        body.append(_html_card(res))
    body.append("<footer>%s v%s &middot; %s</footer>"
                % (_esc(config.APP_NAME), _esc(config.VERSION),
                   _esc(config.REPO_URL)))
    body.append("</div></body></html>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))
    return path


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

FORMATS = ("json", "html", "txt")


def write_report(results: list, fmt: str = "json", out: str | None = None,
                 title: str | None = None) -> dict:
    """Write a report in one or all formats.

    ``fmt`` is ``json``, ``html``, ``txt`` or ``all``.  ``out`` is a path stem;
    the extension is added per format.  Returns ``{format: path}``.
    """
    fmt = (fmt or "json").lower()
    if fmt not in FORMATS + ("all",):
        raise ValueError("Unsupported format '%s'. Use one of: %s, all"
                         % (fmt, ", ".join(FORMATS)))
    stem = out or "ruk_phoneinfo_report"
    if stem.endswith(tuple("." + f for f in FORMATS)):
        stem = os.path.splitext(stem)[0]

    wanted = list(FORMATS) if fmt == "all" else [fmt]
    written = {}
    for one in wanted:
        path = "%s.%s" % (stem, one)
        if one == "json":
            write_json(results, path)
        elif one == "html":
            write_html(results, path, title=title)
        else:
            write_txt(results, path)
        written[one] = path
    return written
