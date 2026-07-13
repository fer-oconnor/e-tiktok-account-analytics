"""Normalizacion tolerante a distintos esquemas de scrapers de TikTok."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

from .constants import COUNT_FIELDS, FIELD_ALIASES, WEEKDAY_ES

_MISSING = object()
_HASHTAG_RE = re.compile(r"#([^\s#.,!?;:()\[\]{}]+)", flags=re.UNICODE)
_VIDEO_ID_RE = re.compile(r"/video/(\d+)")


@dataclass
class NormalizationResult:
    frame: pd.DataFrame
    quality: dict[str, Any]


def _is_missing(value: Any) -> bool:
    if value is None or value is _MISSING:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _get_path(record: dict[str, Any], path: str) -> Any:
    # CSV de Apify: la clave completa puede ser literalmente "authorMeta.name".
    if path in record:
        return record[path]
    current: Any = record
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _resolve(record: dict[str, Any], field: str) -> tuple[Any, str | None]:
    for alias in FIELD_ALIASES[field]:
        value = _get_path(record, alias)
        if not _is_missing(value) and value != "":
            return value, alias
    return None, None


def _to_number(value: Any) -> float:
    if _is_missing(value) or isinstance(value, (list, dict)):
        return np.nan
    if isinstance(value, str):
        cleaned = value.strip().replace("\u00a0", "").replace(" ", "")
        if not cleaned:
            return np.nan
        # Acepta 1,234 y 1234; no interpreta comas decimales en contadores.
        if cleaned.count(",") == 1 and "." not in cleaned:
            right = cleaned.split(",", 1)[1]
            cleaned = cleaned.replace(",", "") if len(right) == 3 else cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        suffix = cleaned[-1:].lower()
        multiplier = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix)
        if multiplier:
            cleaned = cleaned[:-1]
        try:
            number = float(cleaned)
        except ValueError:
            return np.nan
        return number * multiplier if multiplier else number
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _to_bool(value: Any) -> bool | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "si", "sí", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def _maybe_parse_collection(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return []
    if stripped[0] not in "[{(":
        return value
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(stripped)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
    return value


def _normalise_tag(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("name", "hashtagName", "challengeName", "title"):
            candidate = value.get(key)
            if candidate:
                value = candidate
                break
        else:
            return None
    text = str(value).strip().lstrip("#").casefold()
    text = re.sub(r"\s+", "", text)
    return text or None


def _extract_hashtags(raw: Any, caption: str) -> list[str]:
    raw = _maybe_parse_collection(raw)
    candidates: list[Any]
    if isinstance(raw, list):
        candidates = raw
    elif isinstance(raw, dict):
        candidates = list(raw.values())
    elif isinstance(raw, str):
        if "#" in raw:
            candidates = _HASHTAG_RE.findall(raw)
        elif "," in raw:
            candidates = raw.split(",")
        else:
            candidates = [raw]
    else:
        candidates = []

    tags = [_normalise_tag(item) for item in candidates]
    tags.extend(_normalise_tag(item) for item in _HASHTAG_RE.findall(caption or ""))
    return list(dict.fromkeys(tag for tag in tags if tag))


def _count_mentions(raw: Any, caption: str) -> int:
    raw = _maybe_parse_collection(raw)
    if isinstance(raw, list):
        return len(raw)
    if isinstance(raw, dict):
        return len(raw)
    if isinstance(raw, str) and raw.strip():
        if raw.strip().startswith("@"):
            return len(re.findall(r"@[\w.]+", raw))
        return len([part for part in raw.split(",") if part.strip()])
    return len(re.findall(r"(?<!\w)@[\w.]+", caption or ""))


def _parse_datetime(value: Any) -> pd.Timestamp:
    if _is_missing(value):
        return pd.NaT
    numeric = _to_number(value)
    if not np.isnan(numeric) and not isinstance(value, str):
        unit = "ms" if abs(numeric) >= 10_000_000_000 else "s"
        return pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
    if isinstance(value, str) and value.strip().replace(".", "", 1).isdigit():
        numeric = float(value)
        unit = "ms" if abs(numeric) >= 10_000_000_000 else "s"
        return pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(value, utc=True, errors="coerce")


def _synthetic_id(video_url: str, row_number: int) -> str:
    match = _VIDEO_ID_RE.search(video_url or "")
    if match:
        return match.group(1)
    seed = f"{video_url}|{row_number}".encode("utf-8")
    return "missing-" + hashlib.sha1(seed).hexdigest()[:12]


def _music_type(row: pd.Series) -> tuple[str, str]:
    explicit = row.get("music_original")
    name = str(row.get("music_name") or "").casefold()
    original_words = ("original sound", "sonido original", "som original", "originalton")
    if explicit is True:
        return "Sonido original", "campo musicOriginal"
    if any(word in name for word in original_words):
        return "Sonido original", "nombre del sonido"
    if name:
        return "Musica no original", "nombre del sonido"
    return "Desconocido", "sin datos"


def _bucket_duration(value: float) -> str:
    if pd.isna(value):
        return "Desconocida"
    if value <= 10:
        return "0-10 s"
    if value <= 20:
        return "11-20 s"
    if value <= 30:
        return "21-30 s"
    if value <= 60:
        return "31-60 s"
    if value <= 120:
        return "61-120 s"
    return ">120 s"


def _bucket_caption(value: int) -> str:
    if value <= 50:
        return "0-50"
    if value <= 100:
        return "51-100"
    if value <= 150:
        return "101-150"
    return ">150"


def _bucket_hashtags(value: int) -> str:
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    if value <= 4:
        return "3-4"
    if value <= 7:
        return "5-7"
    return "8+"


def _bucket_frequency(value: int) -> str:
    if value <= 1:
        return "1 video/semana"
    if value == 2:
        return "2 videos/semana"
    if value <= 4:
        return "3-4 videos/semana"
    if value <= 7:
        return "5-7 videos/semana"
    return "8+ videos/semana"


def normalize_records(
    records: list[dict[str, Any]],
    *,
    timezone: str = "Europe/Madrid",
    as_of: str | datetime | pd.Timestamp | None = None,
    account: str | None = None,
) -> NormalizationResult:
    """Convierte diferentes outputs de Apify a una fila canonica por video."""
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Zona horaria no reconocida: {timezone}") from exc

    aliases_used: dict[str, Counter[str]] = {
        field: Counter() for field in FIELD_ALIASES
    }
    rows: list[dict[str, Any]] = []
    excluded_non_video = 0
    synthetic_ids = 0

    for row_number, record in enumerate(records, start=1):
        values: dict[str, Any] = {}
        for field in FIELD_ALIASES:
            value, alias = _resolve(record, field)
            values[field] = value
            if alias:
                aliases_used[field][alias] += 1

        values["caption"] = str(values.get("caption") or "").strip()
        for field in COUNT_FIELDS + [
            "author_followers",
            "duration_seconds",
            "video_width",
            "video_height",
        ]:
            values[field] = _to_number(values.get(field))
        values["created_at_utc"] = _parse_datetime(values.pop("created_at", None))
        values["music_original"] = _to_bool(values.get("music_original"))
        values["is_slideshow"] = _to_bool(values.get("is_slideshow"))
        values["is_pinned"] = _to_bool(values.get("is_pinned"))
        values["is_ad"] = _to_bool(values.get("is_ad"))
        values["video_url"] = str(values.get("video_url") or "").strip()
        values["author_username"] = str(values.get("author_username") or "").strip().lstrip("@")
        values["author_name"] = str(values.get("author_name") or "").strip()
        values["music_id"] = str(values.get("music_id") or "").strip()
        values["music_name"] = str(values.get("music_name") or "").strip()
        values["music_author"] = str(values.get("music_author") or "").strip()
        values["hashtags"] = _extract_hashtags(values.get("hashtags"), values["caption"])
        values["mention_count"] = _count_mentions(values.pop("mentions", None), values["caption"])

        video_id = str(values.get("video_id") or "").strip()
        used_synthetic_id = False
        if not video_id:
            video_id = _synthetic_id(values["video_url"], row_number)
            used_synthetic_id = True
        values["video_id"] = video_id

        # Excluye perfiles, seguidores y otros objetos mezclados en el dataset.
        has_video_signal = (
            not pd.isna(values["views"])
            or "/video/" in values["video_url"]
            or not pd.isna(values["duration_seconds"])
        )
        if not has_video_signal:
            excluded_non_video += 1
            continue
        if used_synthetic_id:
            synthetic_ids += 1
        rows.append(values)

    if not rows:
        raise ValueError(
            "No se ha encontrado ninguna fila de video. Comprueba que exportaste "
            "los posts del perfil y no solo los datos generales de la cuenta."
        )

    frame = pd.DataFrame(rows)
    input_video_rows = len(frame)
    negative_replaced: dict[str, int] = {}
    for field in COUNT_FIELDS + ["author_followers", "duration_seconds"]:
        negative_mask = frame[field].notna() & (frame[field] < 0)
        negative_replaced[field] = int(negative_mask.sum())
        frame.loc[negative_mask, field] = np.nan

    frame["_completeness"] = frame.notna().sum(axis=1)
    frame = frame.sort_values(
        ["video_id", "_completeness", "views"],
        ascending=[True, False, False],
        na_position="last",
    )
    duplicate_rows = int(frame.duplicated("video_id", keep="first").sum())
    frame = frame.drop_duplicates("video_id", keep="first").drop(columns="_completeness")
    frame["created_at_utc"] = pd.to_datetime(
        frame["created_at_utc"], utc=True, errors="coerce"
    )
    frame["author_username"] = (
        frame["author_username"].fillna("").astype(str).str.strip().str.lstrip("@").str.casefold()
    )

    if account:
        wanted = account.strip().lstrip("@").casefold()
        available = sorted(
            value for value in frame["author_username"].dropna().astype(str).unique() if value
        )
        frame = frame[
            frame["author_username"].astype(str).str.casefold().eq(wanted)
        ].copy()
        if frame.empty:
            raise ValueError(
                f"La cuenta '{account}' no aparece en el dataset. "
                f"Cuentas detectadas: {', '.join(available) or 'ninguna'}."
            )

    frame["created_at_local"] = frame["created_at_utc"].dt.tz_convert(timezone)
    frame["publish_date"] = frame["created_at_local"].dt.date.astype("string")
    frame["publish_year_month"] = frame["created_at_local"].dt.strftime("%Y-%m")
    frame["publish_hour"] = frame["created_at_local"].dt.hour.astype("Int64")
    frame["publish_weekday_number"] = frame["created_at_local"].dt.weekday.astype("Int64")
    frame["publish_weekday"] = frame["publish_weekday_number"].map(WEEKDAY_ES)
    local_naive = frame["created_at_local"].dt.tz_localize(None)
    frame["week_start"] = (
        local_naive.dt.normalize() - pd.to_timedelta(local_naive.dt.weekday, unit="D")
    ).dt.strftime("%Y-%m-%d")

    if as_of is None:
        as_of_ts = pd.Timestamp.now(tz="UTC")
    else:
        as_of_ts = pd.to_datetime(as_of, utc=True, errors="raise")
    age_days = (as_of_ts - frame["created_at_utc"]).dt.total_seconds() / 86_400
    frame["days_since_post"] = age_days.where(age_days >= 0).clip(lower=1)
    frame["views_per_day"] = frame["views"] / frame["days_since_post"]

    frame["caption_length"] = frame["caption"].str.len().astype("Int64")
    frame["caption_word_count"] = frame["caption"].str.split().str.len().fillna(0).astype("Int64")
    frame["caption_length_bucket"] = frame["caption_length"].map(_bucket_caption)
    frame["hashtag_count"] = frame["hashtags"].map(len).astype("Int64")
    frame["hashtags_text"] = frame["hashtags"].map(lambda tags: "|".join(tags))
    frame["hashtag_count_bucket"] = frame["hashtag_count"].map(_bucket_hashtags)
    frame["duration_bucket"] = frame["duration_seconds"].map(_bucket_duration)
    frame["content_type"] = np.where(frame["is_slideshow"].eq(True), "Carrusel/fotos", "Video")

    music = frame.apply(_music_type, axis=1, result_type="expand")
    frame["music_type"] = music[0]
    frame["music_type_source"] = music[1]

    valid_views = frame["views"].where(frame["views"] > 0)
    for metric in ["likes", "comments", "shares", "saves"]:
        label = {
            "likes": "like",
            "comments": "comment",
            "shares": "share",
            "saves": "save",
        }[metric]
        frame[f"{label}_per_1000_views"] = frame[metric] / valid_views * 1_000

    core_fields = ["likes", "comments", "shares"]
    full_fields = core_fields + ["saves"]
    frame["engagement_core"] = frame[core_fields].sum(axis=1, min_count=len(core_fields))
    frame["engagement_full"] = frame[full_fields].sum(axis=1, min_count=len(full_fields))
    frame["engagement_core_per_1000_views"] = frame["engagement_core"] / valid_views * 1_000
    frame["engagement_full_per_1000_views"] = frame["engagement_full"] / valid_views * 1_000

    account_group = frame["author_username"].replace("", "cuenta_desconocida")
    frame = frame.assign(_account_group=account_group).sort_values(
        ["_account_group", "created_at_utc", "video_id"]
    )
    frame["posting_gap_days"] = (
        frame.groupby("_account_group", dropna=False)["created_at_utc"]
        .diff()
        .dt.total_seconds()
        .div(86_400)
    )
    frame["posts_in_week"] = (
        frame.groupby(["_account_group", "week_start"], dropna=False)["video_id"]
        .transform("count")
        .astype("Int64")
    )
    frame["posting_frequency_bucket"] = frame["posts_in_week"].map(_bucket_frequency)

    median_views = frame["views"].median()
    frame["views_index"] = frame["views"] / median_views * 100 if median_views > 0 else np.nan
    frame["is_viral_2x_median"] = frame["views"] >= 2 * median_views if median_views > 0 else False

    log_views = np.log1p(frame["views"].clip(lower=0))
    log_median = float(log_views.median())
    mad = float((log_views - log_median).abs().median())
    frame["robust_views_z"] = (
        0.6745 * (log_views - log_median) / mad if mad > 0 else 0.0
    )
    frame["is_views_outlier"] = frame["robust_views_z"].abs() > 3.5
    frame = frame.drop(columns="_account_group").sort_values(
        ["created_at_utc", "video_id"], na_position="last"
    )

    accounts = sorted(
        value for value in frame["author_username"].fillna("").astype(str).unique() if value
    )
    source_aliases = {
        field: dict(counter.most_common()) for field, counter in aliases_used.items() if counter
    }
    quality = {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "as_of_utc": as_of_ts.isoformat(),
        "timezone": timezone,
        "input_rows": len(records),
        "video_like_rows_before_deduplication": input_video_rows,
        "valid_unique_videos": len(frame),
        "excluded_non_video_rows": excluded_non_video,
        "duplicate_video_rows_removed": duplicate_rows,
        "synthetic_video_ids_created": synthetic_ids,
        "negative_values_replaced_with_null": negative_replaced,
        "accounts_detected": accounts,
        "source_aliases_used": source_aliases,
    }
    return NormalizationResult(frame=frame.reset_index(drop=True), quality=quality)
