"""Terminal presentation helpers: colours, banner, tables and prompts."""

from __future__ import annotations

import os
import shutil
import sys
import unicodedata

from . import config

_COLOR_ENABLED = None


def color_enabled() -> bool:
    """Resolve colour support once, honouring NO_COLOR and RUK_FORCE_COLOR."""
    global _COLOR_ENABLED
    if _COLOR_ENABLED is None:
        if os.environ.get("NO_COLOR"):
            _COLOR_ENABLED = False
        elif os.environ.get("RUK_FORCE_COLOR") == "1":
            _COLOR_ENABLED = True
        else:
            _COLOR_ENABLED = bool(getattr(sys.stdout, "isatty", lambda: False)())
    return _COLOR_ENABLED


def set_color(enabled: bool) -> None:
    """Force colour on or off (used by --no-color / --color)."""
    global _COLOR_ENABLED
    _COLOR_ENABLED = bool(enabled)


_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "italic": "\033[3m",
    "red": "\033[38;5;203m",
    "green": "\033[38;5;114m",
    "yellow": "\033[38;5;221m",
    "blue": "\033[38;5;75m",
    "magenta": "\033[38;5;176m",
    "cyan": "\033[38;5;80m",
    "white": "\033[38;5;255m",
    "grey": "\033[38;5;245m",
    "orange": "\033[38;5;215m",
}


def c(text, *styles) -> str:
    """Wrap text in ANSI styles, or return it unchanged when colour is off."""
    if not color_enabled() or not styles:
        return str(text)
    prefix = "".join(_CODES.get(s, "") for s in styles)
    return "%s%s%s" % (prefix, text, _CODES["reset"])


def _dwidth(text) -> int:
    """Display width of a string, counting wide glyphs as 2 and marks as 0."""
    width = 0
    for ch in str(text):
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def _pad(text, width, align="left") -> str:
    text = str(text)
    gap = max(0, width - _dwidth(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def term_width(default: int = 78) -> int:
    """Usable terminal width, clamped to a readable range."""
    try:
        cols = shutil.get_terminal_size((default, 24)).columns
    except OSError:
        cols = default
    return max(40, min(cols, 120))


BANNER = r"""
  ██████╗ ██╗   ██╗██╗  ██╗    ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗███████╗
  ██╔══██╗██║   ██║██║ ██╔╝    ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔════╝
  ██████╔╝██║   ██║█████╔╝     ██████╔╝███████║██║   ██║██╔██╗ ██║█████╗
  ██╔══██╗██║   ██║██╔═██╗     ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██╔══╝
  ██║  ██║╚██████╔╝██║  ██╗    ██║     ██║  ██║╚██████╔╝██║ ╚████║███████╗
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
"""


def banner(subtitle: str = "") -> str:
    """Return the coloured application banner."""
    lines = [c(BANNER.rstrip("\n"), "cyan", "bold")]
    tag = "Phone Number OSINT Toolkit  |  v%s  |  Termux / Android" % config.VERSION
    lines.append("  " + c(tag, "grey"))
    lines.append("  " + c("Offline public-data analysis only - no live location tracking", "yellow"))
    if subtitle:
        lines.append("  " + c(subtitle, "white", "bold"))
    return "\n".join(lines)


def rule(char: str = "-", width: int | None = None) -> str:
    return c(char * (width or term_width()), "grey")


def section(title: str) -> str:
    """A titled horizontal rule."""
    width = term_width()
    label = " %s " % title
    fill = max(0, width - _dwidth(label) - 2)
    left = fill // 2
    return c("=" * left + label + "=" * (fill - left), "blue", "bold")


def kv(pairs, indent: int = 2, key_width: int = 22) -> str:
    """Render an aligned key/value block."""
    out = []
    for key, value in pairs:
        if value is None or value == "":
            value = c("-", "grey")
        out.append(" " * indent + c(_pad(str(key), key_width), "grey") + str(value))
    return "\n".join(out)


def table(headers, rows, aligns=None) -> str:
    """Render a bordered table with correct display-width padding."""
    headers = [str(h) for h in headers]
    rows = [["" if v is None else str(v) for v in row] for row in rows]
    cols = len(headers)
    aligns = list(aligns or ["left"] * cols)
    widths = [_dwidth(h) for h in headers]
    for row in rows:
        for i in range(cols):
            widths[i] = max(widths[i], _dwidth(row[i]))

    def line(left, mid, right):
        return c(left + mid.join("-" * (w + 2) for w in widths) + right, "grey")

    out = [line("+", "+", "+")]
    out.append(
        c("|", "grey")
        + c("|", "grey").join(
            " " + c(_pad(h, widths[i]), "bold", "white") + " "
            for i, h in enumerate(headers)
        )
        + c("|", "grey")
    )
    out.append(line("+", "+", "+"))
    for row in rows:
        out.append(
            c("|", "grey")
            + c("|", "grey").join(
                " " + _pad(row[i], widths[i], aligns[i]) + " " for i in range(cols)
            )
            + c("|", "grey")
        )
    out.append(line("+", "+", "+"))
    return "\n".join(out)


def ok(msg: str) -> str:
    return c("[+] ", "green", "bold") + str(msg)


def warn(msg: str) -> str:
    return c("[!] ", "yellow", "bold") + str(msg)


def err(msg: str) -> str:
    return c("[-] ", "red", "bold") + str(msg)


def info(msg: str) -> str:
    return c("[*] ", "cyan", "bold") + str(msg)


def bullet(msg: str, indent: int = 2) -> str:
    return " " * indent + c("* ", "grey") + str(msg)


def print_(*parts) -> None:
    """print() that tolerates non-UTF8 terminals."""
    text = " ".join(str(p) for p in parts)
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(enc, "replace").decode(enc, "replace"))
