"""Smoke tests: real subprocesses, real files, real report output.

No network access is required - every test runs against the local filesystem
and the tool's own CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")


def run_cli(args, home=None, extra_env=None, stdin_text=None):
    """Run the CLI as a subprocess with an isolated HOME."""
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    env["RUK_ACCEPT_TERMS"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if home:
        env["HOME"] = home
        env["RUK_PHONEINFO_HOME"] = os.path.join(home, ".ruk_phoneinfo")
    if extra_env:
        env.update(extra_env)
    if stdin_text is None:
        # Never inherit the parent's stdin: under a tty the CLI would open the
        # interactive menu and block forever.
        return subprocess.run(
            [sys.executable, APP] + list(args),
            capture_output=True, text=True, env=env, cwd=ROOT,
            stdin=subprocess.DEVNULL, timeout=90,
        )
    return subprocess.run(
        [sys.executable, APP] + list(args),
        capture_output=True, text=True, env=env, cwd=ROOT,
        input=stdin_text, timeout=90,
    )


class TestCliBasics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="ruk_smoke_home_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)

    def test_version(self):
        proc = run_cli(["version"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("RUK_PHONEINFO v1.0.0", proc.stdout)
        self.assertIn("offline", proc.stdout.lower())

    def test_version_flag(self):
        proc = run_cli(["--version"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("RUK_PHONEINFO", proc.stdout)

    def test_help_lists_subcommands(self):
        proc = run_cli(["--help"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for cmd in ("info", "validate", "carrier", "format", "region",
                    "batch", "report", "version"):
            self.assertIn(cmd, proc.stdout)

    def test_no_args_non_interactive_shows_help(self):
        proc = run_cli([], home=self.home)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage", proc.stdout.lower())

    def test_datasets_command(self):
        proc = run_cli(["datasets"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Countries", proc.stdout)
        self.assertIn("NONE - fully offline", proc.stdout)

    def test_datasets_json(self):
        proc = run_cli(["datasets", "--json"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertGreater(payload["countries"], 150)


class TestCliAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="ruk_smoke_home_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)

    def test_info_pakistan(self):
        proc = run_cli(["info", "+923001234567"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("+923001234567", proc.stdout)
        self.assertIn("Pakistan", proc.stdout)
        self.assertIn("Jazz", proc.stdout)
        self.assertIn("NOT PERFORMED", proc.stdout)

    def test_info_json_is_valid(self):
        proc = run_cli(["info", "+923001234567", "--json"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["iso"], "PK")
        self.assertEqual(payload["carrier"]["operator"], "Jazz (Mobilink)")
        self.assertFalse(payload["exposure"]["online_lookup_performed"])

    def test_validate_valid(self):
        proc = run_cli(["validate", "+923001234567"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("YES", proc.stdout)

    def test_validate_invalid(self):
        proc = run_cli(["validate", "+9230012345"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NO", proc.stdout)

    def test_validate_json(self):
        proc = run_cli(["validate", "+923001234567", "--json"], home=self.home)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["valid"])

    def test_carrier_command(self):
        proc = run_cli(["carrier", "+923001234567"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Jazz (Mobilink)", proc.stdout)
        self.assertIn("Mobile", proc.stdout)

    def test_format_command(self):
        proc = run_cli(["format", "+923001234567"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("tel:+923001234567", proc.stdout)
        self.assertIn("03001234567", proc.stdout)

    def test_region_command(self):
        proc = run_cli(["region", "+923001234567"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Pakistan", proc.stdout)
        self.assertIn("Asia/Karachi", proc.stdout)

    def test_country_flag_for_national_number(self):
        proc = run_cli(["info", "03001234567", "--country", "PK"],
                       home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("+923001234567", proc.stdout)

    def test_bad_number_exits_cleanly(self):
        proc = run_cli(["info", "not-a-number"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn("NOT VALID", proc.stdout)

    def test_no_traceback_on_weird_input(self):
        for weird in ("+++", "0", "x" * 100, "+999999999999"):
            proc = run_cli(["info", weird], home=self.home)
            self.assertNotIn("Traceback", proc.stderr, weird)

    def test_local_list_flag(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("+923001234567\n")
            path = fh.name
        try:
            proc = run_cli(["info", "+923001234567", "--list", path],
                           home=self.home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("FOUND", proc.stdout)
        finally:
            os.unlink(path)


class TestCliBatchAndReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="ruk_smoke_home_")
        cls.work = tempfile.mkdtemp(prefix="ruk_smoke_work_")
        cls.list_path = os.path.join(cls.work, "numbers.txt")
        with open(cls.list_path, "w", encoding="utf-8") as fh:
            fh.write("# test numbers\n")
            fh.write("+923001234567\n")
            fh.write("+442071234567\n")
            fh.write("+12125551234\n")
            fh.write("garbage\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_batch_from_file(self):
        proc = run_cli(["batch", self.list_path], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Batch Results (4)", proc.stdout)
        self.assertIn("Pakistan", proc.stdout)
        self.assertIn("United Kingdom", proc.stdout)
        self.assertIn("Total", proc.stdout)

    def test_batch_json(self):
        proc = run_cli(["batch", self.list_path, "--json"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(len(payload), 4)
        self.assertTrue(payload[0]["valid"])
        self.assertFalse(payload[3]["valid"])

    def test_batch_from_stdin(self):
        proc = run_cli(["batch", "--stdin"], home=self.home,
                       stdin_text="+923001234567\n+442071234567\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Batch Results (2)", proc.stdout)

    def test_batch_missing_file(self):
        proc = run_cli(["batch", "/nope/missing.txt"], home=self.home)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("No numbers", proc.stdout)

    def test_report_json(self):
        out = os.path.join(self.work, "rep_json")
        proc = run_cli(["report", "+923001234567", "--out", out,
                        "--format", "json"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = out + ".json"
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["count"], 1)
        self.assertFalse(payload["live_location_tracking"])

    def test_report_html(self):
        out = os.path.join(self.work, "rep_html")
        proc = run_cli(["report", "+923001234567", "--out", out,
                        "--format", "html", "--title", "Smoke Report"],
                       home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = out + ".html"
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Smoke Report", text)
        self.assertIn("+923001234567", text)

    def test_report_txt(self):
        out = os.path.join(self.work, "rep_txt")
        proc = run_cli(["report", "+923001234567", "--out", out,
                        "--format", "txt"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = out + ".txt"
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            self.assertIn("NUMBER: +923001234567", fh.read())

    def test_report_all_formats(self):
        out = os.path.join(self.work, "rep_all")
        proc = run_cli(["report", "+923001234567", "--out", out,
                        "--format", "all"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for ext in ("json", "html", "txt"):
            self.assertTrue(os.path.exists("%s.%s" % (out, ext)), ext)

    def test_report_from_file(self):
        out = os.path.join(self.work, "rep_file")
        proc = run_cli(["report", "--file", self.list_path, "--out", out,
                        "--format", "json"], home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(out + ".json", encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["count"], 4)

    def test_report_nothing_to_do(self):
        proc = run_cli(["report"], home=self.home)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Nothing to report", proc.stdout)


class TestConsentGate(unittest.TestCase):
    def test_refuses_without_acceptance(self):
        home = tempfile.mkdtemp(prefix="ruk_gate_")
        try:
            proc = run_cli(["info", "+923001234567"], home=home,
                           extra_env={"RUK_ACCEPT_TERMS": "0"})
            self.assertEqual(proc.returncode, 3)
            self.assertIn("not accepted", proc.stdout.lower())
        finally:
            shutil.rmtree(home, ignore_errors=True)

    def test_json_refusal_is_machine_readable(self):
        home = tempfile.mkdtemp(prefix="ruk_gate_")
        try:
            proc = run_cli(["info", "+923001234567", "--json"], home=home,
                           extra_env={"RUK_ACCEPT_TERMS": "0"})
            self.assertEqual(proc.returncode, 3)
            payload = json.loads(proc.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"], "terms_not_accepted")
        finally:
            shutil.rmtree(home, ignore_errors=True)

    def test_accept_terms_flag_persists(self):
        home = tempfile.mkdtemp(prefix="ruk_gate_")
        try:
            proc = run_cli(["info", "+923001234567", "--accept-terms"],
                           home=home, extra_env={"RUK_ACCEPT_TERMS": "0"})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            cfg = os.path.join(home, ".ruk_phoneinfo", "config.json")
            self.assertTrue(os.path.exists(cfg))
            with open(cfg, encoding="utf-8") as fh:
                self.assertTrue(json.load(fh)["terms_accepted"])
        finally:
            shutil.rmtree(home, ignore_errors=True)

    def test_piped_stdin_does_not_hang(self):
        """A non-tty stdin must never block on input()."""
        home = tempfile.mkdtemp(prefix="ruk_gate_")
        try:
            proc = run_cli(["info", "+923001234567"], home=home,
                           extra_env={"RUK_ACCEPT_TERMS": "0"},
                           stdin_text="")
            self.assertEqual(proc.returncode, 3)
        finally:
            shutil.rmtree(home, ignore_errors=True)


class TestPackaging(unittest.TestCase):
    def test_expected_files_exist(self):
        for name in ("app.py", "install.sh", "uninstall.sh", "run_tests.sh",
                     "README.md", "LICENSE", "CHANGELOG.md", ".gitignore"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, name)), name)

    def test_package_modules_exist(self):
        pkg = os.path.join(ROOT, "ruk_phoneinfo")
        for name in ("__init__.py", "config.py", "ui.py", "utils.py",
                     "datasets.py", "validate.py", "carrier.py", "region.py",
                     "formatting.py", "exposure.py", "analyze.py", "batch.py",
                     "report.py", "cli.py"):
            self.assertTrue(os.path.exists(os.path.join(pkg, name)), name)

    def test_shell_scripts_are_syntactically_valid(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not available")
        for name in ("install.sh", "uninstall.sh", "run_tests.sh"):
            proc = subprocess.run([bash, "-n", os.path.join(ROOT, name)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0,
                             "%s: %s" % (name, proc.stderr))

    def test_uninstall_dry_run(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not available")
        home = tempfile.mkdtemp(prefix="ruk_uninst_")
        try:
            env = dict(os.environ)
            env["HOME"] = home
            proc = subprocess.run(
                [bash, os.path.join(ROOT, "uninstall.sh"), "--dry-run"],
                capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Dry run", proc.stdout)
        finally:
            shutil.rmtree(home, ignore_errors=True)

    def test_install_help(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not available")
        proc = subprocess.run([bash, os.path.join(ROOT, "install.sh"), "--help"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("install.sh", proc.stdout)

    def test_no_network_imports_in_package(self):
        """The tool must stay offline: no socket/urllib/requests imports."""
        pkg = os.path.join(ROOT, "ruk_phoneinfo")
        banned = ("import socket", "import urllib", "import requests",
                  "import http.client", "from urllib")
        for name in sorted(os.listdir(pkg)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(pkg, name), encoding="utf-8") as fh:
                text = fh.read()
            for token in banned:
                self.assertNotIn(token, text,
                                 "%s must not import %s" % (name, token))

    def test_no_location_tracking_claims(self):
        """No module may claim to provide live location tracking."""
        pkg = os.path.join(ROOT, "ruk_phoneinfo")
        for name in sorted(os.listdir(pkg)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(pkg, name), encoding="utf-8") as fh:
                lowered = fh.read().lower()
            for phrase in ("live location:", "gps coordinates",
                           "track the device", "real-time location"):
                self.assertNotIn(phrase, lowered, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
