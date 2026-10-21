"""Global configuration, filesystem paths and the legal/ethical consent gate.

RUK_PHONEINFO is an OFFLINE, public-data phone number analysis toolkit.
It never contacts a carrier, never queries a live location service and
cannot track a device.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

APP_NAME = "RUK_PHONEINFO"
APP_SLUG = "ruk_phoneinfo"
VERSION = "1.0.0"
RELEASE_DATE = "2026-10-22"
REPO_URL = "https://github.com/Janrahat/RUK_PHONEINFO"
AUTHOR = "RUK_PHONEINFO Project"

DEFAULT_TIMEOUT = 8.0
DEFAULT_RATE = 5.0
DEFAULT_THREADS = 8
MAX_THREADS = 32
DEFAULT_COUNTRY = "PK"

CONFIG_DIR = Path(
    os.environ.get("RUK_PHONEINFO_HOME") or (Path.home() / ".ruk_phoneinfo")
)
CONFIG_FILE = CONFIG_DIR / "config.json"

LEGAL_NOTICE_EN = """
  RUK_PHONEINFO - LEGAL & ETHICAL USE NOTICE
  ------------------------------------------------------------------
  This tool performs OFFLINE analysis of PUBLIC numbering-plan data.
  It does NOT and CANNOT track a phone's live GPS location.

  Allowed use:
    * your own phone numbers
    * numbers for which you hold WRITTEN authorisation from the owner

  Prohibited use:
    * surveilling, stalking, doxing, harassing or profiling any person
    * any use without the number owner's informed consent

  Unauthorised tracking is a criminal offence in most jurisdictions.
  The authors accept no liability for misuse.
"""

LEGAL_NOTICE_UR = """
  RUK_PHONEINFO - قانونی اور اخلاقی استعمال کا نوٹس
  ------------------------------------------------------------------
  یہ ٹول صرف عوامی نمبرنگ پلان ڈیٹا کا آف لائن تجزیہ کرتا ہے۔
  یہ کسی فون کی لائیو GPS لوکیشن ٹریک نہیں کر سکتا اور نہ کرتا ہے۔

  جائز استعمال:
    * آپ کے اپنے فون نمبر
    * وہ نمبر جن کے مالک سے آپ کے پاس تحریری اجازت ہو

  ممنوع استعمال:
    * کسی شخص کی جاسوسی، ٹریکنگ، ڈوکسنگ یا ہراسانی
    * مالک کی باخبر رضامندی کے بغیر کوئی بھی استعمال

  اجازت کے بغیر ٹریکنگ زیادہ تر ممالک میں جرم ہے۔
  غلط استعمال کی ذمہ داری مصنفین پر نہیں ہوگی۔
"""


def legal_notice(lang: str = "en") -> str:
    """Return the legal notice in the requested language."""
    return LEGAL_NOTICE_UR if str(lang).lower().startswith("ur") else LEGAL_NOTICE_EN


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_config() -> dict:
    """Read the persisted config, returning defaults when absent or corrupt."""
    cfg = {
        "terms_accepted": False,
        "accepted_at": None,
        "default_country": DEFAULT_COUNTRY,
        "rate": DEFAULT_RATE,
        "threads": DEFAULT_THREADS,
        "timeout": DEFAULT_TIMEOUT,
    }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            cfg.update(stored)
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> bool:
    """Persist config to disk with 0600 permissions. Never raises."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, CONFIG_FILE)
        return True
    except OSError:
        return False


def terms_accepted() -> bool:
    """True when the user has already accepted the legal notice."""
    return bool(load_config().get("terms_accepted"))


def accept_terms() -> bool:
    """Record acceptance of the legal notice."""
    cfg = load_config()
    cfg["terms_accepted"] = True
    cfg["accepted_at"] = _now_iso()
    return save_config(cfg)


def legal_gate(interactive: bool = True, force_accept: bool = False,
               quiet: bool = False) -> bool:
    """Return True when the user may proceed.

    Non-interactive safe: never calls input() unless stdin is a real tty,
    so piping output or running under CI cannot hang the process.
    """
    if force_accept or os.environ.get("RUK_ACCEPT_TERMS") == "1":
        if not terms_accepted():
            accept_terms()
        return True
    if terms_accepted():
        return True
    if not interactive:
        return False
    if not quiet:
        print(legal_notice())
    try:
        answer = input("  Type 'I AGREE' to accept and continue: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if answer.upper() in ("I AGREE", "IAGREE", "AGREE", "YES", "Y"):
        accept_terms()
        return True
    return False
