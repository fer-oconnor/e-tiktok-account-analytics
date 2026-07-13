"""Definiciones compartidas por el pipeline."""

from __future__ import annotations

WEEKDAY_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miercoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sabado",
    6: "Domingo",
}

WEEKDAY_ORDER = list(WEEKDAY_ES.values())

# Se prueban de izquierda a derecha. Las rutas con puntos funcionan tanto con
# JSON anidado como con CSV de Apify, que suele aplanarlas como "videoMeta.duration".
FIELD_ALIASES: dict[str, list[str]] = {
    "video_id": ["id", "videoId", "video_id", "awemeId", "aweme_id"],
    "caption": ["text", "title", "desc", "description", "caption"],
    "created_at": [
        "createTimeISO",
        "uploadedAtFormatted",
        "create_time_iso",
        "createTime",
        "uploadedAt",
        "create_time",
        "timestamp",
    ],
    "views": [
        "playCount",
        "views",
        "viewCount",
        "stats.playCount",
        "stats.viewCount",
        "statistics.playCount",
        "statistics.viewCount",
    ],
    "likes": [
        "diggCount",
        "likes",
        "likeCount",
        "stats.diggCount",
        "stats.likeCount",
        "statistics.diggCount",
        "statistics.likeCount",
    ],
    "comments": [
        "commentCount",
        "comments",
        "stats.commentCount",
        "statistics.commentCount",
    ],
    "shares": [
        "shareCount",
        "shares",
        "stats.shareCount",
        "statistics.shareCount",
    ],
    "saves": [
        "collectCount",
        "bookmarks",
        "saveCount",
        "saves",
        "stats.collectCount",
        "stats.saveCount",
        "statistics.collectCount",
    ],
    "video_url": ["webVideoUrl", "postPage", "videoUrl", "shareUrl", "url"],
    "author_username": [
        "authorMeta.name",
        "authorMeta.uniqueId",
        "channel.username",
        "author.uniqueId",
        "author.username",
        "username",
    ],
    "author_name": [
        "authorMeta.nickName",
        "channel.name",
        "author.nickname",
        "author.name",
    ],
    "author_followers": [
        "authorMeta.fans",
        "authorMeta.followers",
        "channel.followers",
        "author.stats.followerCount",
        "author.followerCount",
    ],
    "duration_seconds": [
        "videoMeta.duration",
        "video.duration",
        "video.durationSeconds",
        "duration",
    ],
    "video_width": ["videoMeta.width", "video.width", "width"],
    "video_height": ["videoMeta.height", "video.height", "height"],
    "video_format": ["videoMeta.format", "video.format", "format"],
    "music_id": ["musicMeta.musicId", "song.id", "music.id", "musicId"],
    "music_name": [
        "musicMeta.musicName",
        "song.title",
        "music.title",
        "musicName",
    ],
    "music_author": [
        "musicMeta.musicAuthor",
        "song.artist",
        "music.authorName",
        "musicAuthor",
    ],
    "music_original": [
        "musicMeta.musicOriginal",
        "song.original",
        "music.original",
        "musicOriginal",
    ],
    "hashtags": ["hashtags", "challenges", "textExtra"],
    "mentions": ["mentions", "detailedMentions"],
    "language": ["textLanguage", "language", "text_language"],
    "location": ["locationCreated", "location", "region"],
    "is_slideshow": ["isSlideshow", "isPhoto", "photoMode"],
    "is_pinned": ["isPinned", "pinned"],
    "is_ad": ["isAd", "isSponsored", "sponsored"],
}

COUNT_FIELDS = ["views", "likes", "comments", "shares", "saves"]

REQUIRED_FOR_CORE = ["video_id", "views", "created_at_utc"]

DATA_DICTIONARY: dict[str, str] = {
    "video_id": "Identificador unico del video.",
    "caption": "Texto o descripcion del video.",
    "created_at_utc": "Fecha y hora de publicacion en UTC.",
    "created_at_local": "Fecha y hora convertida a la zona horaria elegida.",
    "views": "Visualizaciones acumuladas observadas al descargar el dataset.",
    "likes": "Me gusta acumulados.",
    "comments": "Comentarios acumulados.",
    "shares": "Compartidos acumulados.",
    "saves": "Guardados o favoritos acumulados.",
    "engagement_core_per_1000_views": "Likes + comentarios + compartidos por cada 1.000 views.",
    "engagement_full_per_1000_views": "Likes + comentarios + compartidos + guardados por cada 1.000 views.",
    "like_per_1000_views": "Likes por cada 1.000 views.",
    "comment_per_1000_views": "Comentarios por cada 1.000 views.",
    "share_per_1000_views": "Compartidos por cada 1.000 views.",
    "save_per_1000_views": "Guardados por cada 1.000 views.",
    "views_per_day": "Views acumuladas divididas por los dias desde publicacion (aproximacion).",
    "hashtag_count": "Numero de hashtags unicos detectados.",
    "music_type": "Sonido original, musica no original o desconocido.",
    "posting_gap_days": "Dias transcurridos desde la publicacion anterior de la cuenta.",
    "views_index": "Views del video respecto a la mediana de la cuenta; 100 equivale a la mediana.",
}
