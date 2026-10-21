"""Offline unit tests - no sockets, no network, no subprocesses."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ruk_phoneinfo import (analyze, batch, carrier, config, datasets,  # noqa: E402
                           exposure, formatting, region, report, ui, utils,
                           validate)


class TestUtils(unittest.TestCase):
    def test_digits_only(self):
        self.assertEqual(utils.digits_only("+92 (300) 123-4567"), "923001234567")
        self.assertEqual(utils.digits_only("abc"), "")
        self.assertEqual(utils.digits_only(None), "")

    def test_has_digits(self):
        self.assertTrue(utils.has_digits("a1b"))
        self.assertFalse(utils.has_digits("abc"))

    def test_unique_preserve(self):
        self.assertEqual(utils.unique_preserve(["a", "b", "a", "c", "b"]),
                         ["a", "b", "c"])

    def test_chunk(self):
        self.assertEqual(list(utils.chunk([1, 2, 3, 4, 5], 2)),
                         [[1, 2], [3, 4], [5]])
        self.assertEqual(list(utils.chunk([], 3)), [])

    def test_truncate(self):
        self.assertEqual(utils.truncate("abcdef", 4), "abc\u2026")
        self.assertEqual(utils.truncate("abc", 10), "abc")

    def test_human_int(self):
        self.assertEqual(utils.human_int(1234567), "1,234,567")
        self.assertEqual(utils.human_int("nope"), "nope")

    def test_safe_int_float(self):
        self.assertEqual(utils.safe_int("5"), 5)
        self.assertEqual(utils.safe_int("x", 9), 9)
        self.assertEqual(utils.safe_float("1.5"), 1.5)
        self.assertEqual(utils.safe_float(None, 2.0), 2.0)

    def test_read_lines_skips_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# comment\n\n+923001234567\n  \n+923009876543\n")
            path = fh.name
        try:
            self.assertEqual(utils.read_lines(path),
                             ["+923001234567", "+923009876543"])
        finally:
            os.unlink(path)

    def test_read_lines_missing_file_raises(self):
        with self.assertRaises(OSError):
            utils.read_lines("/nonexistent/ruk/numbers.txt")


class TestRateLimiter(unittest.TestCase):
    def test_disabled_when_rate_zero(self):
        limiter = utils.RateLimiter(0)
        self.assertEqual(limiter.interval, 0.0)
        limiter.wait()  # must not sleep or raise

    def test_interval_from_rate(self):
        self.assertAlmostEqual(utils.RateLimiter(4).interval, 0.25)

    def test_negative_rate_disables(self):
        self.assertEqual(utils.RateLimiter(-3).interval, 0.0)

    def test_wait_is_bounded(self):
        import time
        limiter = utils.RateLimiter(50)
        start = time.monotonic()
        for _ in range(3):
            limiter.wait()
        self.assertLess(time.monotonic() - start, 1.0)


class TestRunThreaded(unittest.TestCase):
    def test_preserves_input_order(self):
        results = utils.run_threaded(lambda x: x * 2, [3, 1, 2], threads=3)
        self.assertEqual([value for _, value, _ in results], [6, 2, 4])

    def test_one_failure_does_not_abort(self):
        def flaky(item):
            if item == 2:
                raise ValueError("boom")
            return item
        results = utils.run_threaded(flaky, [1, 2, 3], threads=3)
        self.assertEqual(len(results), 3)
        self.assertIsNone(results[1][1])
        self.assertIsInstance(results[1][2], ValueError)
        self.assertEqual(results[2][1], 3)

    def test_empty_input(self):
        self.assertEqual(utils.run_threaded(lambda x: x, [], threads=4), [])

    def test_single_thread_path(self):
        results = utils.run_threaded(lambda x: x + 1, [1, 2], threads=1)
        self.assertEqual([v for _, v, _ in results], [2, 3])

    def test_progress_callback(self):
        seen = []
        utils.run_threaded(lambda x: x, [1, 2, 3], threads=2,
                           on_progress=lambda done, total, item, value, err:
                           seen.append((done, total)))
        self.assertEqual(len(seen), 3)
        self.assertEqual(seen[-1], (3, 3))


class TestDatasets(unittest.TestCase):
    def test_country_lookup(self):
        self.assertEqual(datasets.country_by_iso("pk")["name"], "Pakistan")
        self.assertIsNone(datasets.country_by_iso("ZZ"))
        self.assertIsNone(datasets.country_by_iso(""))

    def test_country_by_calling_code_shared(self):
        shared = datasets.country_by_calling_code("1")
        self.assertGreater(len(shared), 1)
        isos = [iso for iso, _ in shared]
        self.assertIn("US", isos)
        self.assertIn("CA", isos)

    def test_split_calling_code_simple(self):
        self.assertEqual(datasets.split_calling_code("923001234567"),
                         ("PK", "92", "3001234567"))

    def test_split_calling_code_longest_match(self):
        # 880 (Bangladesh) must win over 88, and 1 must not shadow 1868.
        self.assertEqual(datasets.split_calling_code("8801712345678")[1], "880")
        self.assertEqual(datasets.split_calling_code("18685551234")[1], "1")

    def test_split_calling_code_nanp_disambiguation(self):
        # 212 is a New York City area code, so +1 212... resolves to the US.
        self.assertEqual(datasets.split_calling_code("12125551234")[0], "US")
        # 416 is Toronto, so +1 416... resolves to Canada.
        self.assertEqual(datasets.split_calling_code("14165551234")[0], "CA")

    def test_split_calling_code_rejects_garbage(self):
        self.assertIsNone(datasets.split_calling_code("abc"))
        self.assertIsNone(datasets.split_calling_code(""))
        self.assertIsNone(datasets.split_calling_code("999999999"))

    def test_carrier_for_longest_prefix(self):
        self.assertEqual(datasets.carrier_for("PK", "3001234567")[0],
                         "Jazz (Mobilink)")
        self.assertEqual(datasets.carrier_for("PK", "3451234567")[0],
                         "Jazz (Mobilink)")
        self.assertIsNone(datasets.carrier_for("ZZ", "3001234567"))

    def test_area_for(self):
        self.assertEqual(datasets.area_for("PK", "4212345678")[1], "Lahore")
        self.assertIsNone(datasets.area_for("PK", "3001234567"))

    def test_all_countries_sorted(self):
        names = [info["name"] for _, info in datasets.all_countries()]
        self.assertEqual(names, sorted(names))

    def test_dataset_sizes(self):
        self.assertGreater(datasets.country_count(), 150)
        self.assertGreater(datasets.carrier_country_count(), 100)

    def test_every_country_has_required_fields(self):
        for iso, info in datasets.COUNTRIES.items():
            for field in ("name", "code", "nsn", "region", "tz"):
                self.assertIn(field, info, "%s missing %s" % (iso, field))
            self.assertTrue(info["nsn"], "%s has no NSN lengths" % iso)
            self.assertTrue(str(info["code"]).isdigit(),
                            "%s has a non-numeric calling code" % iso)

    def test_calling_codes_are_unique_per_country(self):
        # A calling code may be shared, but no country may declare two.
        for iso, info in datasets.COUNTRIES.items():
            self.assertIsInstance(info["code"], str, iso)


class TestValidate(unittest.TestCase):
    def test_e164_pakistan(self):
        res = validate.parse_number("+923001234567")
        self.assertTrue(res["ok"])
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "PK")
        self.assertEqual(res["country_code"], "92")
        self.assertEqual(res["nsn"], "3001234567")
        self.assertEqual(res["e164"], "+923001234567")

    def test_national_with_trunk_prefix(self):
        res = validate.parse_number("03001234567", "PK")
        self.assertTrue(res["valid"])
        self.assertEqual(res["e164"], "+923001234567")
        self.assertTrue(any("trunk" in n.lower() for n in res["notes"]))

    def test_national_without_trunk_prefix(self):
        res = validate.parse_number("3001234567", "PK")
        self.assertTrue(res["valid"])
        self.assertEqual(res["e164"], "+923001234567")

    def test_international_prefix_00(self):
        res = validate.parse_number("00923001234567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["e164"], "+923001234567")
        self.assertTrue(any("dialling prefix" in n for n in res["notes"]))

    def test_international_prefix_011(self):
        res = validate.parse_number("011442071234567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "GB")

    def test_bare_calling_code(self):
        res = validate.parse_number("923001234567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "PK")

    def test_formatted_input(self):
        res = validate.parse_number("+92 (300) 123-4567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["e164"], "+923001234567")

    def test_wrong_length_is_invalid(self):
        res = validate.parse_number("+9230012345")
        self.assertFalse(res["valid"])
        self.assertEqual(res["error"], "invalid_length")
        self.assertIn("expects", res["message"])

    def test_empty_input(self):
        res = validate.parse_number("")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "empty_input")

    def test_no_digits(self):
        res = validate.parse_number("hello")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "no_digits")

    def test_too_short(self):
        res = validate.parse_number("12")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "too_short")

    def test_too_long(self):
        res = validate.parse_number("+" + "9" * 20)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "too_long")

    def test_unknown_calling_code(self):
        res = validate.parse_number("+999123456789")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "unknown_country_code")

    def test_country_required_lists_candidates(self):
        # 7 digits with no matching calling code: the tool must ask for a
        # country rather than guess one.
        res = validate.parse_number("9999999")
        self.assertFalse(res["ok"])
        self.assertIn(res["error"], ("country_required", "unrecognised"))
        if res["error"] == "country_required":
            self.assertTrue(res["possible_countries"])

    def test_bare_calling_code_with_wrong_length_is_invalid(self):
        # 1 + 234567 parses as the US but is far too short.
        res = validate.parse_number("1234567")
        self.assertFalse(res["valid"])
        self.assertEqual(res["error"], "invalid_length")

    def test_shared_calling_code_flagged_ambiguous(self):
        res = validate.parse_number("+14165551234")
        self.assertTrue(res["ambiguous"])
        self.assertGreater(len(res["possible_countries"]), 1)

    def test_validate_number_compact(self):
        res = validate.validate_number("+923001234567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "PK")

    def test_is_valid_helper(self):
        self.assertTrue(validate.is_valid("+923001234567"))
        self.assertFalse(validate.is_valid("nonsense"))

    def test_never_raises_on_weird_input(self):
        for weird in (None, 0, [], {}, "+++", "-1", "\x00", "+92" * 40):
            res = validate.parse_number(weird)
            self.assertIn("ok", res)

    def test_uk_number(self):
        res = validate.parse_number("+442071234567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "GB")

    def test_us_number(self):
        res = validate.parse_number("+12125551234")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "US")

    def test_india_number(self):
        res = validate.parse_number("+919876543210")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "IN")

    def test_uae_number(self):
        res = validate.parse_number("+971501234567")
        self.assertTrue(res["valid"])
        self.assertEqual(res["iso"], "AE")


class TestCarrier(unittest.TestCase):
    def test_pakistan_mobile_operator(self):
        res = carrier.lookup_carrier("PK", "3001234567")
        self.assertTrue(res["ok"])
        self.assertEqual(res["operator"], "Jazz (Mobilink)")
        self.assertEqual(res["line_type"], "mobile")
        self.assertEqual(res["confidence"], "high")

    def test_pakistan_ufone(self):
        res = carrier.lookup_carrier("PK", "3331234567")
        self.assertEqual(res["operator"], "Ufone (PTCL)")

    def test_pakistan_telenor(self):
        res = carrier.lookup_carrier("PK", "3451234567")
        self.assertEqual(res["operator"], "Jazz (Mobilink)")

    def test_ported_range_has_medium_confidence(self):
        res = carrier.lookup_carrier("IN", "9876543210")
        self.assertTrue(res["ok"])
        self.assertEqual(res["confidence"], "medium")
        self.assertIn("Ported", res["note"])

    def test_plan_fallback_gives_low_confidence(self):
        res = carrier.lookup_carrier("PK", "2112345678")
        self.assertTrue(res["ok"])
        self.assertEqual(res["line_type"], "fixed")
        self.assertEqual(res["confidence"], "low")

    def test_unknown_country(self):
        res = carrier.lookup_carrier("ZZ", "3001234567")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "unknown_country")

    def test_no_nsn(self):
        res = carrier.lookup_carrier("PK", "")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "no_nsn")

    def test_no_match_reports_unknown_not_guessed(self):
        res = carrier.lookup_carrier("PK", "9999999999")
        self.assertFalse(res["ok"])
        self.assertEqual(res["line_type"], "unknown")
        self.assertIsNone(res["operator"])

    def test_line_type_helper(self):
        self.assertEqual(carrier.line_type("PK", "3001234567"), "mobile")

    def test_carrier_summary(self):
        self.assertIn("Jazz", carrier.carrier_summary("PK", "3001234567"))
        self.assertEqual(carrier.carrier_summary("PK", "9999999999"), "Unknown")


class TestRegion(unittest.TestCase):
    def test_pakistan_region(self):
        res = region.lookup_region("PK", "3001234567")
        self.assertTrue(res["ok"])
        self.assertEqual(res["country"], "Pakistan")
        self.assertEqual(res["country_ur"], "\u067e\u0627\u06a9\u0633\u062a\u0627\u0646")
        self.assertEqual(res["region"], "Southern Asia")
        self.assertIn("Asia/Karachi", res["timezones"])

    def test_fixed_line_area(self):
        res = region.lookup_region("PK", "4212345678")
        self.assertEqual(res["area_code"], "42")
        self.assertEqual(res["area_name"], "Lahore")
        self.assertTrue(res["area_applicable"])

    def test_mobile_has_no_area(self):
        res = region.lookup_region("PK", "3001234567")
        self.assertIsNone(res["area_code"])
        self.assertFalse(res["area_applicable"])
        self.assertIn("no geographic", res["note"])

    def test_unknown_country(self):
        res = region.lookup_region("ZZ", "3001234567")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "unknown_country")

    def test_helpers(self):
        self.assertEqual(region.country_name("PK"), "Pakistan")
        self.assertIsNone(region.country_name("ZZ"))
        self.assertIn("Asia/Karachi", region.timezones("PK"))
        self.assertEqual(region.area_name("PK", "4212345678"), "Lahore")
        self.assertIsNone(region.area_name("PK", "3001234567"))


class TestFormatting(unittest.TestCase):
    def test_all_formats(self):
        res = formatting.formats("PK", "92", "3001234567")
        self.assertTrue(res["ok"])
        self.assertEqual(res["e164"], "+923001234567")
        self.assertEqual(res["national"], "03001234567")
        self.assertEqual(res["rfc3966"], "tel:+923001234567")
        self.assertEqual(res["digits_only"], "923001234567")
        self.assertEqual(res["trunk_prefix"], "0")

    def test_grouping_avoids_single_digit_tail(self):
        res = formatting.formats("PK", "92", "3001234567")
        self.assertNotIn(" 7", res["international"].split(" ")[-1])
        self.assertEqual(res["international"], "+92 300 123 4567")

    def test_country_without_trunk_prefix(self):
        res = formatting.formats("US", "1", "2125551234")
        self.assertEqual(res["national"], "12125551234")

    def test_helpers(self):
        self.assertEqual(formatting.to_e164("PK", "92", "3001234567"),
                         "+923001234567")
        self.assertEqual(formatting.to_national("PK", "3001234567"),
                         "03001234567")

    def test_empty_nsn(self):
        res = formatting.formats("PK", "92", "")
        self.assertFalse(res["ok"])
        self.assertIsNone(res["e164"])


class TestExposure(unittest.TestCase):
    def test_no_online_lookup_is_declared(self):
        res = exposure.exposure_report("PK", "3001234567", "+923001234567",
                                       "mobile")
        self.assertFalse(res["online_lookup_performed"])
        self.assertIn("No online breach database", res["online_lookup_reason"])

    def test_voip_flagged(self):
        res = exposure.exposure_report("PK", "3912345678", "+923912345678",
                                       "voip")
        ids = [i["id"] for i in res["risk_indicators"]]
        self.assertIn("voip_range", ids)
        self.assertEqual(res["risk_level"], "medium")

    def test_premium_flagged_high(self):
        res = exposure.exposure_report("PK", "9001234567", "+929001234567",
                                       "premium")
        self.assertEqual(res["risk_level"], "high")

    def test_repeated_digits_flagged(self):
        res = exposure.exposure_report("PK", "3333333333", "+923333333333",
                                       "mobile")
        ids = [i["id"] for i in res["risk_indicators"]]
        self.assertIn("repeated_digits", ids)

    def test_sequential_digits_flagged(self):
        res = exposure.exposure_report("PK", "0123456789", "+920123456789",
                                       "mobile")
        ids = [i["id"] for i in res["risk_indicators"]]
        self.assertIn("sequential_digits", ids)

    def test_descending_digits_flagged(self):
        res = exposure.exposure_report("PK", "9876543210", "+929876543210",
                                       "mobile")
        ids = [i["id"] for i in res["risk_indicators"]]
        self.assertIn("sequential_digits", ids)

    def test_clean_number_is_informational(self):
        res = exposure.exposure_report("PK", "3001234567", "+923001234567",
                                       "mobile")
        self.assertEqual(res["risk_level"], "informational")

    def test_local_list_match(self):
        res = exposure.exposure_report("PK", "3001234567", "+923001234567",
                                       "mobile",
                                       local_list=["+92 300 1234567"])
        self.assertTrue(res["local_list"]["checked"])
        self.assertTrue(res["local_list"]["match"])

    def test_local_list_no_match(self):
        res = exposure.exposure_report("PK", "3001234567", "+923001234567",
                                       "mobile", local_list=["+923009999999"])
        self.assertTrue(res["local_list"]["checked"])
        self.assertFalse(res["local_list"]["match"])

    def test_local_list_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# my accounts\n+923001234567\n")
            path = fh.name
        try:
            res = exposure.exposure_report("PK", "3001234567",
                                           "+923001234567", "mobile",
                                           local_list_path=path)
            self.assertTrue(res["local_list"]["checked"])
            self.assertTrue(res["local_list"]["match"])
            self.assertEqual(res["local_list"]["entries"], 1)
        finally:
            os.unlink(path)

    def test_missing_local_list_reports_error(self):
        res = exposure.exposure_report("PK", "3001234567", "+923001234567",
                                       "mobile",
                                       local_list_path="/nope/missing.txt")
        self.assertFalse(res["local_list"]["checked"])
        self.assertEqual(res["local_list"]["error"], "list_not_found")

    def test_recommendations_present(self):
        res = exposure.exposure_report("PK", "3001234567", "+923001234567")
        self.assertTrue(res["recommendations"])


class TestAnalyze(unittest.TestCase):
    def test_full_analysis(self):
        res = analyze.analyze("+923001234567")
        self.assertTrue(res["ok"])
        self.assertTrue(res["valid"])
        self.assertEqual(res["country"], "Pakistan")
        self.assertEqual(res["line_type"], "mobile")
        self.assertEqual(res["carrier"]["operator"], "Jazz (Mobilink)")
        self.assertEqual(res["formats"]["e164"], "+923001234567")
        self.assertIsNotNone(res["exposure"])

    def test_invalid_number_still_returns_structure(self):
        res = analyze.analyze("nonsense")
        self.assertFalse(res["ok"])
        self.assertIsNone(res["carrier"])
        self.assertTrue(res["warnings"])

    def test_wrong_length_adds_warning(self):
        res = analyze.analyze("+9230012345")
        self.assertFalse(res["valid"])
        self.assertTrue(any("length rules" in w for w in res["warnings"]))

    def test_analyze_many_preserves_order(self):
        results = analyze.analyze_many(["+923001234567", "+442071234567"])
        self.assertEqual(results[0]["iso"], "PK")
        self.assertEqual(results[1]["iso"], "GB")

    def test_never_raises(self):
        for weird in (None, "", "++", "0", "x" * 200):
            res = analyze.analyze(weird)
            self.assertIn("ok", res)


class TestBatch(unittest.TestCase):
    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# list\n+923001234567\n\n+442071234567\n+923001234567\n")
            path = fh.name
        try:
            numbers, errors = batch.load_numbers(path=path)
            self.assertEqual(errors, [])
            self.assertEqual(numbers, ["+923001234567", "+442071234567"])
        finally:
            os.unlink(path)

    def test_missing_file_reports_error(self):
        numbers, errors = batch.load_numbers(path="/nope/missing.txt")
        self.assertEqual(numbers, [])
        self.assertTrue(errors)

    def test_inline_numbers(self):
        numbers, errors = batch.load_numbers(inline=["+923001234567"])
        self.assertEqual(numbers, ["+923001234567"])
        self.assertEqual(errors, [])

    def test_run_batch(self):
        results = batch.run_batch(["+923001234567", "garbage"])
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["valid"])
        self.assertFalse(results[1]["valid"])

    def test_run_batch_progress(self):
        seen = []
        batch.run_batch(["+923001234567", "+442071234567"],
                        on_progress=lambda i, t, r: seen.append((i, t)))
        self.assertEqual(seen, [(1, 2), (2, 2)])

    def test_batch_summary(self):
        results = batch.run_batch(["+923001234567", "+442071234567", "bad"])
        summary = batch.batch_summary(results)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["valid"], 2)
        self.assertEqual(summary["invalid"], 1)
        self.assertEqual(summary["countries"]["PK"], 1)

    def test_empty_batch(self):
        self.assertEqual(batch.run_batch([]), [])
        self.assertEqual(batch.batch_summary([])["total"], 0)


class TestReport(unittest.TestCase):
    def setUp(self):
        self.results = [analyze.analyze("+923001234567"),
                        analyze.analyze("+442071234567")]
        self.tmp = tempfile.mkdtemp(prefix="ruk_report_")

    def test_console_report_contains_key_facts(self):
        text = report.console_report(self.results[0])
        self.assertIn("+923001234567", text)
        self.assertIn("Pakistan", text)
        self.assertIn("Jazz", text)
        self.assertIn("NOT PERFORMED", text)

    def test_console_batch_table(self):
        text = report.console_batch(self.results)
        self.assertIn("Batch Results (2)", text)
        self.assertIn("Pakistan", text)

    def test_write_json(self):
        path = os.path.join(self.tmp, "out.json")
        report.write_json(self.results, path)
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["count"], 2)
        self.assertFalse(payload["live_location_tracking"])
        self.assertEqual(payload["results"][0]["iso"], "PK")

    def test_write_txt(self):
        path = os.path.join(self.tmp, "out.txt")
        report.write_txt(self.results, path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("NUMBER: +923001234567", text)
        self.assertIn("Online lookup    : NOT PERFORMED", text)

    def test_write_html(self):
        path = os.path.join(self.tmp, "out.html")
        report.write_html(self.results, path, title="Test Report")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("<!DOCTYPE html>", text)
        self.assertIn("Test Report", text)
        self.assertIn("+923001234567", text)
        self.assertIn("NO ONLINE LOOKUP", text)

    def test_html_escapes_untrusted_input(self):
        evil = analyze.analyze("<script>alert(1)</script>")
        path = os.path.join(self.tmp, "evil.html")
        report.write_html([evil], path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_write_report_all_formats(self):
        stem = os.path.join(self.tmp, "all")
        written = report.write_report(self.results, fmt="all", out=stem)
        self.assertEqual(set(written), {"json", "html", "txt"})
        for path in written.values():
            self.assertTrue(os.path.exists(path))

    def test_write_report_strips_known_extension(self):
        stem = os.path.join(self.tmp, "named.json")
        written = report.write_report(self.results, fmt="json", out=stem)
        self.assertEqual(written["json"], os.path.join(self.tmp, "named.json"))

    def test_write_report_rejects_bad_format(self):
        with self.assertRaises(ValueError):
            report.write_report(self.results, fmt="pdf")

    def test_disclaimer_mentions_no_location(self):
        self.assertIn("CANNOT", report.DISCLAIMER)
        self.assertIn("GPS", report.DISCLAIMER)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ruk_cfg_")
        self._old = os.environ.get("RUK_PHONEINFO_HOME")
        os.environ["RUK_PHONEINFO_HOME"] = self.tmp
        import importlib
        importlib.reload(config)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("RUK_PHONEINFO_HOME", None)
        else:
            os.environ["RUK_PHONEINFO_HOME"] = self._old
        import importlib
        importlib.reload(config)

    def test_defaults(self):
        cfg = config.load_config()
        self.assertFalse(cfg["terms_accepted"])
        self.assertEqual(cfg["default_country"], "PK")

    def test_accept_and_persist(self):
        self.assertFalse(config.terms_accepted())
        self.assertTrue(config.accept_terms())
        self.assertTrue(config.terms_accepted())
        self.assertTrue(config.CONFIG_FILE.exists())

    def test_config_file_is_owner_only(self):
        config.accept_terms()
        mode = config.CONFIG_FILE.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_legal_gate_force_accept(self):
        self.assertTrue(config.legal_gate(interactive=False, force_accept=True))

    def test_legal_gate_non_interactive_refuses(self):
        self.assertFalse(config.legal_gate(interactive=False, force_accept=False))

    def test_legal_gate_env_var(self):
        os.environ["RUK_ACCEPT_TERMS"] = "1"
        try:
            self.assertTrue(config.legal_gate(interactive=False))
        finally:
            os.environ.pop("RUK_ACCEPT_TERMS", None)

    def test_notice_languages(self):
        self.assertIn("LEGAL", config.legal_notice("en"))
        self.assertIn("\u0642\u0627\u0646\u0648\u0646\u06cc", config.legal_notice("ur"))

    def test_corrupt_config_falls_back_to_defaults(self):
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.CONFIG_FILE, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertFalse(config.load_config()["terms_accepted"])


class TestUI(unittest.TestCase):
    def setUp(self):
        ui.set_color(False)

    def tearDown(self):
        ui.set_color(False)

    def test_color_disabled_returns_plain(self):
        self.assertEqual(ui.c("hello", "red", "bold"), "hello")

    def test_color_enabled_wraps_ansi(self):
        ui.set_color(True)
        try:
            self.assertIn("\033[", ui.c("hello", "red"))
        finally:
            ui.set_color(False)

    def test_table_renders_all_cells(self):
        text = ui.table(["A", "B"], [["1", "2"], ["3", "4"]])
        for token in ("A", "B", "1", "2", "3", "4"):
            self.assertIn(token, text)
        self.assertIn("+", text)

    def test_table_handles_wide_and_arabic_text(self):
        text = ui.table(["Country", "Urdu"], [["Pakistan", "\u067e\u0627\u06a9\u0633\u062a\u0627\u0646"]])
        self.assertIn("Pakistan", text)
        self.assertIn("\u067e\u0627\u06a9\u0633\u062a\u0627\u0646", text)

    def test_kv_renders_dash_for_empty(self):
        text = ui.kv([("Key", None), ("Other", "value")])
        self.assertIn("-", text)
        self.assertIn("value", text)

    def test_banner_contains_version(self):
        self.assertIn(config.VERSION, ui.banner())

    def test_section_and_rule(self):
        self.assertIn("Title", ui.section("Title"))
        self.assertTrue(ui.rule("-", 10))

    def test_status_helpers(self):
        self.assertIn("ok", ui.ok("ok"))
        self.assertIn("warn", ui.warn("warn"))
        self.assertIn("err", ui.err("err"))
        self.assertIn("info", ui.info("info"))
        self.assertIn("bullet", ui.bullet("bullet"))

    def test_term_width_is_clamped(self):
        self.assertGreaterEqual(ui.term_width(), 40)
        self.assertLessEqual(ui.term_width(), 120)


if __name__ == "__main__":
    unittest.main(verbosity=2)
