#!/usr/bin/env python3
"""Tests for server/krow_config.py."""
from __future__ import annotations

import unittest

import client_preset
import krow_config


class KrowConfigTests(unittest.TestCase):
    def test_safe_fix_kinds(self):
        self.assertIn("low-contrast", krow_config.SAFE_FIX_KINDS)
        self.assertIn("junk-decimal", krow_config.SAFE_FIX_KINDS)
        self.assertIn("missing-thousands-separator", krow_config.SAFE_FIX_KINDS)
        self.assertIn("prefix-mismatch", krow_config.SAFE_FIX_KINDS)
        self.assertNotIn("zero-display-mismatch", krow_config.SAFE_FIX_KINDS)
        self.assertIn("year-automatic-coercion", krow_config.SAFE_FIX_KINDS)
        self.assertEqual(len(krow_config.SAFE_FIX_KINDS), 9)

    def test_service_config_acfr_preset(self):
        cfg = krow_config.service_config()
        self.assertEqual(
            cfg["presets"]["acfr"]["spreadsheetId"],
            client_preset.acfr_preset_ss_id(),
        )
        self.assertEqual(cfg["presets"]["acfr"]["label"], "ACFR preset")
        self.assertEqual(cfg["safe_fix_kinds"], list(krow_config.SAFE_FIX_KINDS))


if __name__ == "__main__":
    unittest.main()
