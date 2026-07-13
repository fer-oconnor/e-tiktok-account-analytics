from __future__ import annotations

import unittest

from tiktok_analytics.schema import normalize_records


class SchemaTests(unittest.TestCase):
    def test_clockworks_nested_and_flattened_fields(self) -> None:
        records = [
            {
                "id": "1",
                "text": "Casa #Madrid #Viajes",
                "createTimeISO": "2025-01-01T12:00:00Z",
                "playCount": 1000,
                "diggCount": 100,
                "commentCount": 10,
                "shareCount": 5,
                "collectCount": 20,
                "authorMeta": {"name": "demo"},
                "videoMeta": {"duration": 15},
                "musicMeta": {"musicName": "original sound", "musicOriginal": True},
                "hashtags": [{"name": "madrid"}, {"name": "viajes"}],
            },
            {
                "id": "2",
                "text": "Otra #Madrid",
                "createTimeISO": "2025-01-03T12:00:00Z",
                "playCount": "2,500",
                "diggCount": "250",
                "commentCount": 25,
                "shareCount": 12,
                "collectCount": 45,
                "authorMeta.name": "demo",
                "videoMeta.duration": 22,
                "musicMeta.musicName": "Cancion A",
                "musicMeta.musicOriginal": False,
                "hashtags": '[{"name":"madrid"}]',
            },
        ]
        result = normalize_records(records, as_of="2025-02-01")
        self.assertEqual(len(result.frame), 2)
        self.assertEqual(result.frame.loc[1, "views"], 2500)
        self.assertEqual(result.frame.loc[0, "hashtags"], ["madrid", "viajes"])
        self.assertEqual(result.frame.loc[0, "music_type"], "Sonido original")
        self.assertEqual(result.frame.loc[1, "posting_gap_days"], 2)

    def test_apidojo_schema(self) -> None:
        record = {
            "id": "99",
            "title": "Tutorial #python",
            "views": 10000,
            "likes": 800,
            "comments": 30,
            "shares": 20,
            "bookmarks": 120,
            "hashtags": ["python"],
            "channel": {"username": "demo", "followers": 4000},
            "uploadedAtFormatted": "2025-02-01T10:00:00Z",
            "video": {"duration": 42, "width": 576, "height": 1024},
            "song": {"id": "s1", "title": "Track", "artist": "Artist"},
            "postPage": "https://www.tiktok.com/@demo/video/99",
        }
        frame = normalize_records([record], as_of="2025-02-02").frame
        self.assertEqual(frame.loc[0, "views"], 10000)
        self.assertEqual(frame.loc[0, "saves"], 120)
        self.assertEqual(frame.loc[0, "author_username"], "demo")
        self.assertEqual(frame.loc[0, "duration_seconds"], 42)

    def test_excludes_non_video_and_deduplicates(self) -> None:
        video = {
            "id": "1",
            "playCount": 100,
            "createTime": 1_735_689_600,
            "authorMeta": {"name": "demo"},
        }
        follower = {"id": "user-1", "connectedTo": {"name": "demo"}}
        result = normalize_records([video, dict(video), follower], as_of="2025-02-01")
        self.assertEqual(len(result.frame), 1)
        self.assertEqual(result.quality["duplicate_video_rows_removed"], 1)
        self.assertEqual(result.quality["excluded_non_video_rows"], 1)

    def test_missing_dates_do_not_crash(self) -> None:
        record = {
            "id": "no-date",
            "playCount": 100,
            "authorMeta": {"name": "demo"},
        }
        result = normalize_records([record], as_of="2025-02-01")
        self.assertTrue(result.frame["created_at_utc"].isna().all())
        self.assertTrue(result.frame["week_start"].isna().all())

    def test_username_is_case_insensitive(self) -> None:
        records = [
            {"id": "1", "playCount": 100, "authorMeta": {"name": "Demo"}},
            {"id": "2", "playCount": 200, "authorMeta": {"name": "demo"}},
        ]
        result = normalize_records(records, account="DEMO", as_of="2025-02-01")
        self.assertEqual(result.quality["accounts_detected"], ["demo"])
        self.assertEqual(len(result.frame), 2)


if __name__ == "__main__":
    unittest.main()
