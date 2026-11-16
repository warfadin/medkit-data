import copy
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import update_hospital_menu as menu


PDF_URL = f"https://{menu.HOSPITAL}/wp-content/uploads/2026/10/menu.pdf"
HTML = f'<a href="{PDF_URL}">Download</a>'
PDF = b"%PDF-1.4\n"


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "menu.json"
        self.old = {"year": 2026, "month": 10, "title": "Hospital", "source": "Form", "days": []}
        self.original = json.dumps(self.old)
        self.path.write_text(self.original)
        days = [
            {
                "date": day.isoformat(),
                "weekday": menu.WEEKDAYS[day.weekday()],
                "lunch": ["Soup", "Main", "Side", "Fruit"],
                "dinner": ["Soup", "Main", "Side", "Yogurt"],
            }
            for day in (date(2026, 11, n) for n in range(1, 31))
        ]
        self.result = {"days": days, "uncertainties": []}

    def run_mode(self, mode, result, *, day=16, env=None):
        with (
            patch.object(menu, "MENU_PATH", self.path),
            patch.object(menu, "datetime") as clock,
            patch.object(menu, "fetch", side_effect=[
                json.dumps({"content": {"rendered": HTML}}).encode(),
                PDF,
            ]) as fetch,
            patch.object(menu, "extract", return_value=result) as extract,
            patch.dict(menu.os.environ, {"OPENAI_API_KEY": "test"} if env is None else env, clear=True),
        ):
            clock.now.return_value = datetime(2026, 11, day)
            menu.run(mode)
            return fetch.call_count, extract.call_count

    def test_pdf_source_deduplicates_direct_link_and_viewer(self):
        iframe = f'<iframe src="//docs.google.com/viewer?url={PDF_URL}&amp;embedded=true"></iframe>'
        self.assertEqual(menu.find_pdf(HTML + iframe), PDF_URL)
        with self.assertRaises(ValueError):
            menu.find_pdf(HTML.replace(menu.HOSPITAL, "example.org"))
        with self.assertRaises(ValueError):
            menu.find_pdf(HTML + HTML.replace("menu.pdf", "other.pdf"))

    def test_source_checks_pdf_without_key_or_write(self):
        self.assertEqual(self.run_mode("source", None, env={}), (2, 0))
        self.assertEqual(self.path.read_text(), self.original)

    def test_preview_then_publish_preserves_schema_and_skips_repeat(self):
        self.run_mode("preview", self.result)
        self.assertEqual(self.path.read_text(), self.original)
        self.run_mode("publish", self.result)
        self.assertEqual(
            json.loads(self.path.read_text()),
            dict(self.old, month=11, days=self.result["days"]),
        )
        self.assertEqual(self.run_mode("scheduled", None, env={}), (0, 0))

    def test_rejects_uncertainty_missing_days_wrong_weekday_and_empty_meal(self):
        for defect in ("uncertainty", "missing", "weekday", "meal"):
            with self.subTest(defect=defect):
                result = copy.deepcopy(self.result)
                if defect == "uncertainty":
                    result["uncertainties"].append("Unreadable")
                elif defect == "missing":
                    result["days"].pop()
                elif defect == "weekday":
                    result["days"][0]["weekday"] = "Cuma"
                else:
                    result["days"][0]["dinner"][-1] = " "
                with self.assertRaises(ValueError):
                    self.run_mode("publish", result)
                self.assertEqual(self.path.read_text(), self.original)

    def test_prior_month_retries_then_fails_without_publishing(self):
        result = copy.deepcopy(self.result)
        for n, row in enumerate(result["days"], 1):
            day = date(2026, 9, n)
            row.update(date=day.isoformat(), weekday=menu.WEEKDAYS[day.weekday()])
        self.run_mode("scheduled", result, day=1)
        with self.assertRaisesRegex(ValueError, "expected 2026-11"):
            self.run_mode("scheduled", result, day=3)
        self.assertEqual(self.path.read_text(), self.original)


if __name__ == "__main__":
    unittest.main()
