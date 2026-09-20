"""Run with: python -m unittest -v   (no network, no credits, no dependencies beyond the app's)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("HUMANSTANDARD_API_KEY", "test-key")

import detect  # noqa: E402
import extract_audio  # noqa: E402
import outreach  # noqa: E402
import requests  # noqa: E402

DEFAULT_LOG_FILE = detect.LOG_FILE  # captured before any test patches it


class RoutingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(detect, "LOG_FILE", Path(tmp.name) / "log.jsonl")
        patcher.start()
        self.addCleanup(patcher.stop)

    def route(self, result, sender="artist"):
        with mock.patch("builtins.print"):
            return detect.handle_result("x", result, sender=sender)

    def test_only_a_clear_ai_verdict_produces_outreach(self):
        self.assertEqual(self.route({"verdict": "human", "confidence": 0.97})[0], "certificate")
        self.assertEqual(self.route({"verdict": "ai", "confidence": 0.98})[0], "outreach")
        for verdict in ("suspicious", "uncertain", "no_vocal", "something_new", None):
            with self.subTest(verdict=verdict):
                self.assertEqual(self.route({"verdict": verdict, "confidence": 0.61})[0], "review")

    def test_low_confidence_ai_goes_to_review_not_outreach(self):
        # The real case from the demo: verdict "ai" at 7.2% confidence.
        kind, text = self.route({"verdict": "ai", "confidence": 0.072, "origin": "unknown"})
        self.assertEqual(kind, "review")
        self.assertIn("LOW CONFIDENCE", text)
        self.assertNotIn("Subject:", text)

    def test_outreach_threshold_boundary(self):
        floor = detect.AI_OUTREACH_MIN_CONFIDENCE
        self.assertEqual(self.route({"verdict": "ai", "confidence": floor})[0], "outreach")
        self.assertEqual(self.route({"verdict": "ai", "confidence": floor - 0.01})[0], "review")
        self.assertEqual(self.route({"verdict": "ai", "confidence": None})[0], "review")

    def test_log_records_job_id_and_extra_fields(self):
        with mock.patch("builtins.print"):
            detect.handle_result("x", {"verdict": "human", "confidence": 0.9, "ai_probability": 0.1}, job_id="job-1")
        entry = json.loads(detect.LOG_FILE.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["job_id"], "job-1")
        self.assertEqual(entry["ai_probability"], 0.1)

    def test_missing_or_null_fields_never_crash_any_route(self):
        for verdict in ("human", "ai", "suspicious", None):
            for result in (
                {"verdict": verdict},
                {"verdict": verdict, "confidence": None, "origin": None, "origin_map": None},
            ):
                with self.subTest(result=result):
                    self.route(result)

    def test_review_text_never_calls_it_confirmed_ai(self):
        _, text = self.route({"verdict": "suspicious", "confidence": 0.61})
        self.assertIn("not a confirmed AI claim", text)
        self.assertNotIn("Subject:", text)

    def test_certificate_states_its_basis_without_reference_evidence(self):
        _, text = self.route({"verdict": "human", "confidence": 0.97})
        self.assertIn("full-mix analysis only", text)

    def test_log_path_does_not_depend_on_the_working_directory(self):
        self.assertTrue(DEFAULT_LOG_FILE.is_absolute())
        self.assertEqual(DEFAULT_LOG_FILE.parent, Path(detect.__file__).resolve().parent)


class OutreachTests(unittest.TestCase):
    def test_both_voices_are_drafts_with_placeholders(self):
        for sender in outreach.SENDERS:
            with self.subTest(sender=sender):
                text = outreach.generate_outreach_email({"confidence": 0.98, "origin": "suno"}, sender)
                self.assertIn("[Track title]", text)
                self.assertIn("[Your name]", text)
                self.assertIn("possible origin: suno", text)

    def test_label_voice_is_distinct(self):
        text = outreach.generate_outreach_email({"confidence": 0.9}, "label")
        self.assertIn("on behalf of our artist", text)
        self.assertNotIn("independent artist", text)

    def test_no_none_when_origin_missing(self):
        for origin in (None, "", "unknown", "Unknown", "none", "human"):
            text = outreach.generate_outreach_email({"confidence": 0.61, "origin": origin})
            self.assertNotIn("None", text)
            self.assertNotIn("possible origin", text)

    def test_unknown_sender_is_rejected(self):
        with self.assertRaises(ValueError):
            outreach.generate_outreach_email({"confidence": 0.5}, "bogus")


class PollingTests(unittest.TestCase):
    @staticmethod
    def reply(status_code=200, body=None):
        r = mock.Mock(status_code=status_code)
        r.json.return_value = body or {}
        r.raise_for_status.side_effect = (
            requests.HTTPError(f"{status_code}") if status_code >= 400 else None
        )
        return r

    def poll(self, replies, **kwargs):
        with mock.patch("requests.get", side_effect=replies), mock.patch("time.sleep"), mock.patch("builtins.print"):
            return detect.poll_job("job", **kwargs)

    def test_survives_network_blips_and_server_errors(self):
        done = {"status": "complete", "result": {"verdict": "human"}}
        result = self.poll([
            requests.ConnectionError("blip"),
            self.reply(503),
            self.reply(200, {"status": "processing"}),
            self.reply(200, done),
        ])
        self.assertEqual(result["verdict"], "human")

    def test_bad_key_fails_immediately(self):
        with self.assertRaises(requests.HTTPError):
            self.poll([self.reply(401)])

    def test_failed_job_raises(self):
        with self.assertRaises(RuntimeError):
            self.poll([self.reply(200, {"status": "failed"})])

    def test_times_out(self):
        with mock.patch("time.time", side_effect=[0, 1, 500]):
            with self.assertRaises(TimeoutError):
                self.poll([self.reply(200, {"status": "processing"})] * 3)


class ExtractTests(unittest.TestCase):
    def test_video_detection(self):
        for name in ("a.mp4", "B.MOV", "c.webm"):
            self.assertTrue(extract_audio.is_video(name), name)
        for name in ("a.mp3", "b.wav", "c.m4a"):
            self.assertFalse(extract_audio.is_video(name), name)

    def test_missing_ffmpeg_gives_a_clear_error(self):
        with mock.patch.dict(os.environ, {"FFMPEG_PATH": ""}), mock.patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg not found"):
                extract_audio.extract_audio("clip.mp4", "out.wav")


if __name__ == "__main__":
    unittest.main()
