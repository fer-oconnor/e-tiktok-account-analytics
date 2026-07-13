from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from examples.generate_sample import build_sample_records
from tiktok_analytics.pipeline import run_pipeline


class PipelineTests(unittest.TestCase):
    def test_end_to_end_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "apify.json"
            source.write_text(json.dumps(build_sample_records(24)), encoding="utf-8")
            result = run_pipeline(
                source,
                output_root=root / "output",
                as_of="2025-06-01",
                timezone="Europe/Madrid",
                min_group_size=2,
            )
            self.assertTrue(result.report_path.exists())
            self.assertTrue(result.cleaned_data_path.exists())
            self.assertTrue((result.output_dir / "analysis_manifest.json").exists())
            self.assertTrue((result.output_dir / "tables" / "hashtag_performance.csv").exists())
            html = result.report_path.read_text(encoding="utf-8")
            self.assertIn("@demo_casas", html)
            self.assertIn("data:image/png;base64,", html)


if __name__ == "__main__":
    unittest.main()
