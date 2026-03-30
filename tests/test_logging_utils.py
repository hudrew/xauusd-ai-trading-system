from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.logging_utils import JsonFormatter


class JsonFormatterTests(unittest.TestCase):
    def test_format_includes_exception_details(self) -> None:
        formatter = JsonFormatter()

        try:
            raise RuntimeError("boom")
        except RuntimeError:
            record = logging.getLogger("xauusd.test").makeRecord(
                name="xauusd.test",
                level=logging.ERROR,
                fn=__file__,
                lno=20,
                msg="live_cycle_failed",
                args=(),
                exc_info=sys.exc_info(),
                extra={
                    "extra_payload": {
                        "symbol": "XAUUSD",
                    }
                },
            )

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload["message"], "live_cycle_failed")
        self.assertEqual(payload["symbol"], "XAUUSD")
        self.assertEqual(payload["exception_type"], "RuntimeError")
        self.assertEqual(payload["exception_message"], "boom")
        self.assertIn("RuntimeError: boom", payload["exception"])


if __name__ == "__main__":
    unittest.main()
