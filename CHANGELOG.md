# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-22

### Added

- **Offline number analysis** — parse and validate phone numbers against bundled
  ITU numbering plans. Accepts `+CC…`, `00CC…`, `011CC…`, bare `CC…` and national
  forms with or without the trunk prefix.
- **Country & region resolution** — country name (English + Urdu), ISO code, flag,
  broad region, IANA time zone(s) and fixed-line area code/name.
- **Carrier & line-type lookup** — operator name, line type (mobile / fixed / VoIP /
  toll-free / premium), matched prefix, confidence level and a portability note.
- **Number formatting** — E.164, international, national, national-pretty, RFC 3966
  URI and digits-only representations.
- **Exposure assessment** — purely local, deterministic risk indicators
  (`voip_range`, `premium_rate`, `tollfree`, `repeated_digits`, `sequential_digits`,
  `portability`) plus an optional check against a user-supplied local list file.
  **No online breach database is ever queried.**
- **Reports** — JSON, standalone offline HTML and plain text, individually or all at
  once via `--format all`.
- **CLI** — 10 subcommands (`info`, `validate`, `carrier`, `format`, `region`,
  `batch`, `report`, `menu`, `version`, `datasets`) plus a coloured interactive menu
  that shares the same handlers.
- **Batch mode** — analyse many numbers from a file or stdin, with a summary table.
- **Bundled datasets** — 190+ country numbering plans, 130+ carrier prefix tables,
  area codes and line-type ranges. Fully static; nothing is fetched at runtime.
- **Consent gate** — one-time legal notice acceptance stored at mode `0600`, with
  `--accept-terms` and `RUK_ACCEPT_TERMS=1` escape hatches. Non-interactive safe:
  never calls `input()` when stdin is not a tty.
- **Installer** — `install.sh` (Python check, optional packages, file copy, command
  creation, self-test) and `uninstall.sh` (`--dry-run`, `--purge`).
- **Test suite** — offline unit tests plus CLI/packaging smoke tests, runnable via
  `run_tests.sh` or `python3 -m unittest discover -s tests`.
- **CI** — GitHub Actions workflow running the suite on Python 3.9–3.12.

### Security

- The package imports no networking modules (`socket`, `urllib`, `http.client`,
  `requests`). A test enforces this so the tool can never silently start phoning home.
- HTML reports escape all interpolated values, so a malicious input string cannot
  inject markup into a generated report.
- The config file is written with `0600` permissions.

### Notes

- **This tool cannot track a phone's live GPS location.** Live location exists only
  inside the carrier's network and requires a warrant or the carrier's cooperation.
  No feature, output field or claim in this project provides or implies location
  tracking.
- Mobile number portability means the operator shown is the one that originally
  received the prefix; the current operator may differ. Every carrier result carries
  a confidence level and a note stating this.

[1.0.0]: https://github.com/Janrahat/RUK_PHONEINFO/releases/tag/v1.0.0
