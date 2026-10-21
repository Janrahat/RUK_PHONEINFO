"""Shared helpers: rate limiting, thread pools, text and number utilities."""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_DIGITS_RE = re.compile(r"\d")
_NON_DIGIT_RE = re.compile(r"[^\d]")


class RateLimiter:
    """Thread-safe token-free rate limiter.

    ``rate`` is operations per second; 0 or negative disables limiting.
    """

    def __init__(self, rate: float = 0.0):
        self.rate = float(rate or 0.0)
        self.interval = (1.0 / self.rate) if self.rate > 0 else 0.0
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        if self.interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if self._next <= now:
                self._next = now + self.interval
                return
            delay = self._next - now
            self._next += self.interval
        time.sleep(delay)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return "RateLimiter(rate=%s)" % self.rate


def run_threaded(func, items, threads: int = 8, limiter: RateLimiter | None = None,
                 on_progress=None):
    """Map ``func`` over ``items`` concurrently.

    Returns a list of ``(item, value, error)`` tuples in input order.
    A failure in one item never aborts the batch.
    """
    items = list(items)
    if not items:
        return []
    threads = max(1, min(int(threads or 1), 64))
    results = [None] * len(items)

    def worker(index, item):
        if limiter is not None:
            limiter.wait()
        try:
            return index, item, func(item), None
        except Exception as exc:  # noqa: BLE001 - one bad item must not kill the run
            return index, item, None, exc

    if threads == 1 or len(items) == 1:
        for index, item in enumerate(items):
            idx, itm, value, error = worker(index, item)
            results[idx] = (itm, value, error)
            if on_progress:
                on_progress(idx + 1, len(items), itm, value, error)
        return results

    done = 0
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = [pool.submit(worker, i, item) for i, item in enumerate(items)]
        for future in as_completed(futures):
            idx, itm, value, error = future.result()
            results[idx] = (itm, value, error)
            done += 1
            if on_progress:
                on_progress(done, len(items), itm, value, error)
    return results


def digits_only(text) -> str:
    """Keep only ASCII digits."""
    return _NON_DIGIT_RE.sub("", str(text or ""))


def has_digits(text) -> bool:
    return bool(_DIGITS_RE.search(str(text or "")))


def chunk(seq, size: int):
    """Yield successive lists of at most ``size`` items."""
    seq = list(seq)
    size = max(1, int(size))
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def truncate(text, limit: int = 60) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def human_int(value) -> str:
    """Group an integer with thousands separators."""
    try:
        return "{:,}".format(int(value))
    except (TypeError, ValueError):
        return str(value)


def read_lines(path) -> list:
    """Read a text file, skipping blanks and ``#`` comments.

    Raises FileNotFoundError / OSError for the caller to translate.
    """
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line)
    return out


def unique_preserve(seq):
    """De-duplicate while keeping first-seen order."""
    seen = set()
    out = []
    for item in seq:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
