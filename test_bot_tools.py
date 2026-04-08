"""Тесты инструментов файловой системы (replace_in_file и др.)."""

import json
import tempfile
import unittest
from pathlib import Path

from bot_tools import execute_tool, replace_in_file


class TestReplaceInFile(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_replaces_unique_match(self) -> None:
        p = self.root / "a.txt"
        p.write_text("hello world\n", encoding="utf-8")
        r = replace_in_file("a.txt", "world", "there", self.root)
        self.assertTrue(r.get("replaced"))
        self.assertEqual(p.read_text(encoding="utf-8"), "hello there\n")

    def test_rejects_empty_old_text(self) -> None:
        p = self.root / "b.txt"
        p.write_text("x", encoding="utf-8")
        r = replace_in_file("b.txt", "", "y", self.root)
        self.assertIn("error", r)

    def test_rejects_ambiguous(self) -> None:
        p = self.root / "c.txt"
        p.write_text("foo foo\n", encoding="utf-8")
        r = replace_in_file("c.txt", "foo", "bar", self.root)
        self.assertIn("error", r)
        self.assertIn("2", r["error"])

    def test_execute_tool_json(self) -> None:
        p = self.root / "d.txt"
        p.write_text("one two\n", encoding="utf-8")
        out = execute_tool(
            "replace_in_file",
            {"path": "d.txt", "old_text": "two", "new_text": "2"},
            self.root,
        )
        data = json.loads(out)
        self.assertTrue(data.get("replaced"))
        self.assertEqual(p.read_text(encoding="utf-8"), "one 2\n")


if __name__ == "__main__":
    unittest.main()
