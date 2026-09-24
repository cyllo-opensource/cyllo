# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
"""Tests for core/result_cap.py — tool-result cap-and-spill (pure functions)."""
import json

from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.result_cap import cap_result

# Small, generous caps for readable fixtures.
MAX = 500
PREVIEW_ROWS = 3
PREVIEW_CHARS = 200


class TestResultCap(TransactionCase):

    def _cap(self, out):
        return cap_result(out, MAX, PREVIEW_ROWS, PREVIEW_CHARS)

    def test_small_result_passthrough(self):
        out = {"message": "ok", "records": [1, 2]}
        content, capped = self._cap(out)
        self.assertFalse(capped)
        self.assertEqual(json.loads(content), out)

    def test_small_string_passthrough(self):
        content, capped = self._cap("a short answer")
        self.assertFalse(capped)
        self.assertEqual(content, "a short answer")

    def test_long_list_truncated_with_total(self):
        out = {"result": [{"id": i, "name": f"row-{i}"} for i in range(500)]}
        content, capped = self._cap(out)
        self.assertTrue(capped)
        data = json.loads(content)
        self.assertEqual(len(data["result"]), PREVIEW_ROWS)   # trimmed
        self.assertEqual(data["_result_total"], 500)          # true total kept
        self.assertEqual(data["_result_shown"], PREVIEW_ROWS)
        self.assertTrue(data["_truncated"])
        self.assertIn("_hint", data)

    def test_pre_serialized_json_string_is_structured(self):
        # analytic_record returns a JSON *string*; it must still truncate by row.
        out = json.dumps({"result": [{"id": i} for i in range(500)],
                          "entities": []})
        content, capped = self._cap(out)
        self.assertTrue(capped)
        data = json.loads(content)
        self.assertEqual(len(data["result"]), PREVIEW_ROWS)
        self.assertEqual(data["_result_total"], 500)

    def test_oversized_after_row_trim_falls_back_to_char_preview(self):
        # A few rows, but each so large the trimmed dict still exceeds MAX.
        out = {"result": [{"blob": "x" * 400} for _ in range(5)]}
        content, capped = self._cap(out)
        self.assertTrue(capped)
        data = json.loads(content)
        self.assertTrue(data["_truncated"])
        self.assertIn("_preview", data)
        self.assertLessEqual(len(data["_preview"]), PREVIEW_CHARS)

    def test_long_plain_string_char_preview(self):
        content, capped = self._cap("y" * 5000)
        self.assertTrue(capped)
        data = json.loads(content)
        self.assertIn("_preview", data)
        self.assertEqual(data["_total_chars"], 5000)
        self.assertLessEqual(len(data["_preview"]), PREVIEW_CHARS)

    def test_short_list_not_truncated(self):
        out = {"result": [1, 2]}  # under preview_rows
        content, capped = self._cap(out)
        self.assertFalse(capped)
        self.assertEqual(json.loads(content), out)
