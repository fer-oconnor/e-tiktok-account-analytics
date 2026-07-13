"""Genera un dataset sintetico compatible con Clockworks para probar la herramienta."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def build_sample_records(count: int = 36) -> list[dict]:
    start = datetime(2025, 1, 2, 17, 0, tzinfo=timezone.utc)
    base_views = [
        12_000,
        18_500,
        84_000,
        14_500,
        25_000,
        128_000,
        31_000,
        43_000,
        215_000,
        36_000,
        57_000,
        305_000,
    ]
    hashtag_sets = [
        ["casas", "viajes"],
        ["airbnb", "escapada", "espana"],
        ["casas", "lujo", "inspiracion"],
        ["viajes"],
        ["airbnb", "casas"],
        ["lujo", "espana", "viajes", "viral"],
    ]
    records = []
    day = 0
    for index in range(count):
        # Alterna semanas de baja y alta frecuencia para probar la relacion de cadencia.
        if index:
            day += [1, 2, 4, 1, 1, 6][index % 6]
        created = start + timedelta(days=day, hours=(index * 3) % 8)
        cycle = index // len(base_views)
        views = int(base_views[index % len(base_views)] * (1 + 0.12 * cycle))
        likes = int(views * (0.055 + 0.004 * (index % 4)))
        comments = int(1.7 * (views**0.52) * (1 + 0.03 * (index % 3)))
        shares = int(0.7 * (views**0.68))
        saves = int(views * (0.009 + 0.002 * (index % 3)))
        tags = hashtag_sets[index % len(hashtag_sets)]
        original = index % 3 != 1
        slideshow = index % 8 == 0
        records.append(
            {
                "id": str(7400000000000000000 + index),
                "text": f"Alojamiento numero {index + 1} "
                + " ".join(f"#{tag}" for tag in tags),
                "createTime": int(created.timestamp()),
                "createTimeISO": created.isoformat().replace("+00:00", "Z"),
                "isAd": False,
                "authorMeta": {
                    "id": "7000000000000000001",
                    "name": "demo_casas",
                    "nickName": "Demo Casas",
                    "fans": 50_000,
                },
                "musicMeta": {
                    "musicId": "original-demo" if original else f"song-{index % 4}",
                    "musicName": "original sound - demo_casas"
                    if original
                    else f"Cancion tendencia {index % 4}",
                    "musicAuthor": "demo_casas" if original else f"Artista {index % 4}",
                    "musicOriginal": original,
                },
                "webVideoUrl": f"https://www.tiktok.com/@demo_casas/video/{7400000000000000000 + index}",
                "videoMeta": {
                    "height": 1024,
                    "width": 576,
                    "duration": 0 if slideshow else [8, 15, 24, 42, 75][index % 5],
                    "format": "mp4",
                },
                "diggCount": likes,
                "shareCount": shares,
                "playCount": views,
                "collectCount": saves,
                "commentCount": comments,
                "hashtags": [{"name": tag} for tag in tags],
                "mentions": [],
                "isSlideshow": slideshow,
                "isPinned": index in {0, 2},
            }
        )
    return records


def main() -> None:
    destination = Path(__file__).with_name("sample_clockworks.json")
    destination.write_text(
        json.dumps(build_sample_records(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Dataset sintetico creado: {destination}")


if __name__ == "__main__":
    main()

