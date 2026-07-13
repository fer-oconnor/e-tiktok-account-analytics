from __future__ import annotations

import unittest

from examples.generate_sample import build_sample_records
from tiktok_analytics.metrics import analyze
from tiktok_analytics.schema import normalize_records


class MetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalized = normalize_records(
            build_sample_records(36), as_of="2025-06-01", timezone="Europe/Madrid"
        )
        cls.analysis = analyze(cls.normalized.frame, cls.normalized.quality, min_group_size=2)

    def test_required_tables_exist(self) -> None:
        required = {
            "hashtag_count_analysis",
            "posting_frequency_analysis",
            "music_type_performance",
            "engagement_scaling",
            "data_quality_fields",
        }
        self.assertTrue(required.issubset(self.analysis.tables))

    def test_comment_elasticity_is_sublinear(self) -> None:
        scaling = self.analysis.tables["engagement_scaling"]
        elasticity = float(scaling.loc[scaling["metric"].eq("comments"), "elasticity"].iloc[0])
        self.assertGreater(elasticity, 0.35)
        self.assertLess(elasticity, 0.75)

    def test_frequency_keeps_week_sample_size(self) -> None:
        frequency = self.analysis.tables["posting_frequency_analysis"]
        self.assertIn("number_of_weeks", frequency.columns)
        self.assertGreater(frequency["number_of_weeks"].sum(), 1)

    def test_rates_are_per_thousand(self) -> None:
        first = self.normalized.frame.iloc[0]
        expected = first["comments"] / first["views"] * 1000
        self.assertAlmostEqual(first["comment_per_1000_views"], expected)

    def test_weighted_rate_uses_only_rows_with_metric(self) -> None:
        frame = self.normalized.frame.head(2).copy()
        frame.loc[frame.index[1], "saves"] = float("nan")
        result = analyze(frame, {**self.normalized.quality, "accounts_detected": ["demo_casas"]})
        summary = result.tables["summary_metrics"].set_index("metric")
        expected = frame.iloc[0]["saves"] / frame.iloc[0]["views"] * 1000
        actual = float(summary.loc["weighted_save_per_1000_views", "value"])
        self.assertAlmostEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
