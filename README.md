# RUK_PHONEINFO

> **Offline phone-number OSINT toolkit for Termux (Android).**
> Pure Python 3 standard library · no root · no `pip install` · no network access.

<p align="center">
  <img alt="Python 3.8+" src="https://img.shields.io/badge/python-3.8%2B-blue">
  <img alt="Dependencies: none" src="https://img.shields.io/badge/dependencies-none-brightgreen">
  <img alt="Platform: Termux" src="https://img.shields.io/badge/platform-Termux%20%7C%20Linux-lightgrey">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## ⚠️ اہم: یہ ٹول کیا نہیں کر سکتا (پہلے پڑھیں)

**یہ ٹول کسی فون کی لائیو GPS لوکیشن ٹریک نہیں کر سکتا — اور نہ کرے گا۔**

یہ کوئی "کمی" نہیں، یہ تکنیکی حقیقت ہے:

1. **لائیو لوکیشن صرف کیریئر کے پاس ہوتی ہے۔** موبائل نیٹ ورک جانتا ہے کہ آپ کس ٹاور سے جڑے ہیں، لیکن یہ ڈیٹا صرف کیریئر کے اندرونی سسٹمز میں ہے۔ اس تک رسائی کے لیے قانون نافذ کرنے والے ادارے کا وارنٹ یا کیریئر کا تعاون درکار ہے۔
2. **نمبر خود کوئی جگہ نہیں بتاتا۔** ایک فون نمبر محض ایک عددی شناخت ہے۔ اس میں کوئی GPS کوآرڈینیٹ، کوئی پتہ، کوئی لائیو ڈیٹا نہیں ہوتا۔
3. **جو ٹولز "لائیو لوکیشن" کا دعویٰ کرتے ہیں وہ جھوٹ بولتے ہیں۔** عام طور پر وہ یا تو (الف) آپ سے پیسے لے کر کچھ نہیں دیتے، (ب) آپ کے ڈیوائس پر مالویئر انسٹال کرتے ہیں، یا (ج) کسی اور کی رضامندی کے بغیر ٹریکنگ کر کے آپ کو مجرم بناتے ہیں۔
4. **رضامندی کے بغیر ٹریکنگ جرم ہے۔** پاکستان (PECA 2016)، بھارت (IT Act)، برطانیہ (Computer Misuse Act) اور تقریباً ہر ملک میں کسی شخص کی رضامندی کے بغیر اس کی لوکیشن ٹریک کرنا قابلِ سزا جرم ہے۔

### یہ ٹول اصل میں کیا دیتا ہے

یہ **عوامی نمبرنگ پلان ڈیٹا** کا مکمل، آف لائن تجزیہ کرتا ہے — وہی معلومات جو ITU اور قومی ٹیلی کام اتھارٹیز عوامی طور پر شائع کرتی ہیں:

| معلومات | تفصیل |
|---|---|
| **Validity** | نمبر درست ہے یا نہیں، E.164 لمبائی کے قواعد کے مطابق |
| **Country** | ملک، ISO کوڈ، خطہ، جھنڈا |
| **Region / Area** | فکسڈ لائن کے لیے شہر/علاقہ (موبائل نمبر میں علاقہ نہیں ہوتا) |
| **Carrier / Network** | آپریٹر کا نام اور لائن کی قسم |
| **Line type** | Mobile / Fixed / VoIP / Toll-free / Premium |
| **Timezone** | متعلقہ IANA ٹائم زون |
| **Formatting** | E.164، International، National، RFC 3966 |
| **Exposure** | آف لائن رسک اشارے (نیچے تفصیل) |

---

## English

### What this tool is

`RUK_PHONEINFO` is a **fully offline** phone-number analysis CLI for Termux and any
Linux shell. It parses a number, resolves its country calling code against a bundled
ITU table, validates the National Significant Number against published length rules,
and reports the operator, line type, region, time zone and every common format.

It ships **zero third-party dependencies** — only the Python 3 standard library —
so it runs on a stock Termux install with no `pip`, no compiler and no root.

### What this tool is NOT

**It cannot and will not track a phone's live GPS location.** This is a technical
fact, not a missing feature:

- Live location exists only inside the carrier's network (cell-tower / HLR data).
  Reaching it requires a warrant or the carrier's cooperation — no app can do it.
- A phone number contains no coordinates. It is an identifier, not a position.
- Tools advertising "live location tracking" are either scams, malware, or they
  make *you* the criminal.
- Tracking a person without their informed consent is a criminal offence in
  Pakistan (PECA 2016), India (IT Act), the UK (Computer Misuse Act) and
  essentially everywhere else.

### What it actually does

| Capability | Detail |
|---|---|
| **Validation** | E.164 length + pattern rules per country |
| **Country / region** | Country, ISO code, region, flag, time zone(s) |
| **Area code** | City/area for fixed lines (mobile ranges carry no area) |
| **Carrier** | Operator name, line type, confidence, portability note |
| **Line type** | Mobile, fixed, VoIP, toll-free, premium rate |
| **Formatting** | E.164, international, national, RFC 3966 URI, digits-only |
| **Exposure** | Offline risk indicators + optional local list check |
| **Reports** | JSON, standalone HTML, plain text |

---

## Installation (Termux)

```bash
pkg update -y && pkg install -y python git

git clone https://github.com/Janrahat/RUK_PHONEINFO.git
cd RUK_PHONEINFO
bash install.sh
```

The installer checks Python, optionally installs `termux-api`, copies the files to
`~/.local/lib/ruk_phoneinfo`, creates the `ruk_phoneinfo` and `ruk` commands, and
runs the test suite.

```bash
bash install.sh --no-deps          # skip optional package installation
bash install.sh --prefix /data/data/com.termux/files/usr   # custom prefix
```

### Run without installing

```bash
python3 app.py info +923001234567
```

### Uninstall

```bash
bash uninstall.sh --dry-run   # show what would be removed
bash uninstall.sh             # remove the installed files
bash uninstall.sh --purge     # also remove ~/.ruk_phoneinfo
```

---

## Usage

### Interactive menu

```bash
ruk
```

```
  ██████╗ ██╗   ██╗██╗  ██╗    ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗███████╗
  ██╔══██╗██║   ██║██║ ██╔╝    ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔════╝
  ██████╔╝██║   ██║█████╔╝     ██████╔╝███████║██║   ██║██╔██╗ ██║█████╗
  ██╔══██╗██║   ██║██╔═██╗     ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██╔══╝
  ██║  ██║╚██████╔╝██║  ██╗    ██║     ██║  ██║╚██████╔╝██║ ╚████║███████╗
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
  Phone Number OSINT Toolkit  |  v1.0.0  |  Termux / Android
  Offline public-data analysis only - no live location tracking

============================== Main Menu ==============================
   [1] Full number info
   [2] Validate a number
   [3] Carrier & line type
   [4] Number formats
   [5] Country / region / area
   [6] Batch from a file
   [7] Write a report
   [8] Bundled dataset stats
   [9] Version information
   [0] Exit
```

### Subcommands

```bash
ruk_phoneinfo info     +923001234567      # full analysis
ruk_phoneinfo validate +923001234567      # validity verdict only
ruk_phoneinfo carrier  +923001234567      # operator + line type
ruk_phoneinfo format   +923001234567      # every representation
ruk_phoneinfo region   +923001234567      # country / region / area
ruk_phoneinfo batch    numbers.txt        # many numbers from a file
ruk_phoneinfo report   +923001234567 --out audit --format all
ruk_phoneinfo datasets --countries        # bundled data statistics
ruk_phoneinfo version
```

### Common options

| Option | Meaning |
|---|---|
| `--country ISO` / `-c` | Interpret a national number (e.g. `PK`, `US`, `GB`) |
| `--json` | Machine-readable JSON on stdout |
| `--out PATH` | Write a report (extension added per format) |
| `--format json\|html\|txt\|all` / `-f` | Report format |
| `--list FILE` | Check against a local list file (never transmitted) |
| `--no-color` | Disable ANSI colours |
| `--quiet` / `-q` | Suppress the banner |
| `--accept-terms` | Accept the legal notice non-interactively |

---

## Examples

### 1. Full analysis

```bash
$ ruk_phoneinfo info +923001234567
```

```
==================== RUK_PHONEINFO  |  +923001234567 ====================
  Input                 +923001234567
  Status                VALID
  E.164                 +923001234567
  Country code          +92
  National (NSN)        3001234567
  NSN length            10
  Expected length       10

=========================== Country & Region ===========================
  Country               🇵🇰 Pakistan
  Country (Urdu)        پاکستان
  ISO code              PK
  Region                Southern Asia
  Time zone(s)          Asia/Karachi
  Area code             -
  Area name             -

======================== Carrier & Line Type ==========================
  Operator              Jazz (Mobilink)
  Line type             Mobile
  Matched prefix        300
  Confidence            high
  Original allocation

=============================== Formats ===============================
  E.164                 +923001234567
  International         +92 300 123 4567
  National              03001234567
  National (pretty)     030 012 345 67
  RFC 3966 URI          tel:+923001234567
  Digits only           923001234567

==================== Exposure Assessment (offline) ====================
  Risk level            INFORMATIONAL
  Online lookup         NOT PERFORMED
  No online breach database is queried. Doing so would disclose the number
  to a third party without the owner's consent, and no lawful open API
  exists for phone-number breach lookups. Any tool claiming otherwise from
  a static list is guessing.

  Recommendations
    * Never share a one-time verification code with anyone, including
      someone claiming to be from your bank or operator.
    * Enable a SIM PIN and your operator's port-out lock to make SIM-swap
      attacks harder.
    * Use an app-based second factor instead of SMS where the service
      supports it.
    * If you suspect your number is being abused, report it to your
      operator and to your national CERT.

  RUK_PHONEINFO performs OFFLINE analysis of public numbering-plan data.
  It does NOT and CANNOT determine a phone's live GPS location.
```

### 2. National number with a country hint

```bash
$ ruk_phoneinfo info 03001234567 --country PK --json
```

```json
{
  "ok": true,
  "valid": true,
  "e164": "+923001234567",
  "iso": "PK",
  "country_code": "92",
  "nsn": "3001234567",
  "country": "Pakistan",
  "line_type": "mobile",
  "line_type_label": "Mobile",
  "carrier": {
    "operator": "Jazz (Mobilink)",
    "line_type": "mobile",
    "confidence": "high",
    "note": "Original allocation"
  },
  "formats": {
    "e164": "+923001234567",
    "international": "+92 300 123 4567",
    "national": "03001234567",
    "rfc3966": "tel:+923001234567"
  },
  "exposure": {
    "online_lookup_performed": false,
    "risk_level": "informational"
  }
}
```

### 3. Batch from a file

```bash
$ cat numbers.txt
# my own numbers
+923001234567
+442071234567
+12125551234

$ ruk_phoneinfo batch numbers.txt
```

```
========================= Batch Results (3) ==========================
+--------------+--------------+----------------+-----------+-----------+-------+
| Input        | E.164        | Country        | Operator  | Line type | Valid |
+--------------+--------------+----------------+-----------+-----------+-------+
| +923001234567| +923001234567| Pakistan       | Jazz (Mo… | Mobile    |  yes  |
| +442071234567| +442071234567| United Kingdom | Various … | Mobile    |  yes  |
| +12125551234 | +12125551234 | United States  | -         | Unknown … |  yes  |
+--------------+--------------+----------------+-----------+-----------+-------+

  Total                 3
  Valid                 3
  Invalid               0
```

### 4. Reports

```bash
ruk_phoneinfo report +923001234567 --out audit --format all
# -> audit.json, audit.html, audit.txt
```

The HTML report is a single self-contained file (no CDN, no external assets) that
opens offline in any browser and prints cleanly.

### 5. Local list check

```bash
# A file of numbers you own, e.g. exported from your own accounts
ruk_phoneinfo info +923001234567 --list my_numbers.txt
```

---

## Exposure assessment — what it does and does not do

`RUK_PHONEINFO` **never queries an online breach or leak database.** Three reasons:

1. **Privacy.** Sending a phone number to a third-party service is itself a
   disclosure of that number, and it would happen without the owner's consent.
2. **No legitimate free API.** Public breach-notification services are built around
   email addresses and require an API key plus the data subject's own consent. There is
   no lawful open endpoint for phone-number lookups.
3. **Accuracy.** Any tool that answers "is this number in a breach?" from a bundled
   static list is guessing. This tool does not guess.

Instead it performs a **purely local, deterministic risk assessment**:

| Indicator | Severity | Meaning |
|---|---|---|
| `voip_range` | medium | VoIP ranges are cheap to obtain anonymously |
| `premium_rate` | high | Calling this number can incur large charges |
| `tollfree` | info | The subscriber is an organisation |
| `repeated_digits` | low | Typical of spoofed/test numbers |
| `sequential_digits` | low | Typical of placeholder numbers |
| `portability` | info | Number portability applies in this country |

You can additionally check a number against **your own** list file with `--list`.
That file is read locally and never transmitted.

---

## Bundled datasets

| Dataset | Coverage |
|---|---|
| Country numbering plans | 190+ countries and territories |
| Carrier / operator prefixes | 130+ countries |
| Area codes | Major fixed-line areas per country |
| Line-type ranges | Mobile, fixed, VoIP, toll-free, premium |

All data is static, public numbering-plan information shipped with the tool. When a
fact is not bundled the field is reported as **unknown** — never guessed.

```bash
ruk_phoneinfo datasets --countries
```

---

## Testing

```bash
bash run_tests.sh          # unit + smoke
bash run_tests.sh units    # offline unit tests only
bash run_tests.sh smoke    # CLI / packaging smoke tests
```

Or directly:

```bash
NO_COLOR=1 RUK_ACCEPT_TERMS=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The suite covers number parsing (E.164, national, trunk prefixes, international
dialling prefixes, shared calling codes), validation edge cases, carrier and area
lookups, formatting, the exposure engine, all three report writers, the consent gate
(including the non-tty case), the CLI as a subprocess, and the packaging scripts.

---

## Project layout

```
RUK_PHONEINFO/
├── app.py                  # launcher
├── ruk_phoneinfo/
│   ├── config.py           # settings, paths, legal consent gate
│   ├── ui.py               # colours, banner, tables
│   ├── utils.py            # rate limiter, thread pool, text helpers
│   ├── datasets.py         # bundled numbering plans, carriers, area codes
│   ├── validate.py         # parsing + validation
│   ├── carrier.py          # operator / line type
│   ├── region.py           # country / region / area / time zone
│   ├── formatting.py       # E.164 / national / RFC 3966
│   ├── exposure.py         # offline risk assessment
│   ├── analyze.py          # orchestrator
│   ├── batch.py            # multi-number processing
│   ├── report.py           # JSON / HTML / TXT writers
│   └── cli.py              # argparse subcommands + interactive menu
├── tests/
│   ├── test_units.py       # offline unit tests
│   └── test_smoke.py       # CLI + packaging smoke tests
├── install.sh / uninstall.sh / run_tests.sh
├── LICENSE / CHANGELOG.md / .gitignore
└── .github/workflows/tests.yml
```

---

## Ethics & legal use

### اردو

**صرف اپنے نمبروں پر، یا اُن نمبروں پر استعمال کریں جن کے مالک سے آپ کے پاس تحریری اجازت ہو۔**

- کسی شخص کی رضامندی کے بغیر اس کا نمبر ٹریک کرنا، پروفائل بنانا یا ڈوکس کرنا **جرم** ہے۔
- یہ ٹول صرف **پڑھتا** ہے — کسی ہدف پر کچھ لکھتا، تبدیل کرتا یا بھیجتا نہیں۔
- یہ کوئی نیٹ ورک ریکوئسٹ نہیں بھیجتا، اس لیے آپ کا استعمال کسی تیسرے فریق کو معلوم نہیں ہوتا۔
- غلط استعمال کی ذمہ داری مکمل طور پر صارف پر ہے۔ مصنفین کوئی ذمہ داری قبول نہیں کرتے۔

### English

**Use this tool only on your own numbers, or on numbers for which you hold written
authorisation from the owner.**

- Profiling, stalking, doxing or harassing any person is a criminal offence.
- The tool is **read-only**: it never writes to, modifies or contacts a target.
- It makes **no network requests**, so your usage is never disclosed to a third party.
- You are solely responsible for how you use it. The authors accept no liability
  for misuse.

### Consent gate

On first run the tool prints the legal notice and requires you to type `I AGREE`.
Acceptance is stored in `~/.ruk_phoneinfo/config.json` (mode `0600`). For scripting:

```bash
ruk_phoneinfo info +923001234567 --accept-terms
# or
RUK_ACCEPT_TERMS=1 ruk_phoneinfo info +923001234567
```

When stdin is not a terminal the tool **never** prompts — it exits with code `3`
and, under `--json`, prints a machine-readable refusal.

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Runtime error (e.g. report could not be written) |
| `2` | Usage error (bad arguments, nothing to process) |
| `3` | Legal notice not accepted |
| `130` | Interrupted (Ctrl-C) |

---

## Requirements

- Python 3.8 or newer (Termux: `pkg install python`)
- No third-party packages, no root, no network access

---

## License

MIT — see [LICENSE](LICENSE).

---

## Disclaimer

This tool performs offline analysis of public numbering-plan data. It does not and
cannot determine a phone's live GPS location. It is provided for educational and
legitimate security-research purposes only. The authors accept no liability for
misuse or for any damage arising from its use.
