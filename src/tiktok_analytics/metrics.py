"""Metricas y tablas analiticas a partir del dataset canonico."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .constants import DATA_DICTIONARY, REQUIRED_FOR_CORE, WEEKDAY_ORDER


@dataclass
class AnalysisResult:
    tables: dict[str, pd.DataFrame]
    findings: list[str]
    quality_warnings: list[dict[str, str]]
    headline: dict[str, Any]


def _safe_divide(numerator: float, denominator: float, multiplier: float = 1.0) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return np.nan
    return float(numerator) / float(denominator) * multiplier


def _spearman(left: pd.Series, right: pd.Series) -> float:
    pair = pd.concat([left, right], axis=1).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan
    return float(pair.iloc[:, 0].rank().corr(pair.iloc[:, 1].rank()))


def _format_int(value: float | int) -> str:
    if pd.isna(value):
        return "No disponible"
    return f"{int(round(value)):,}".replace(",", ".")


def _format_float(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "No disponible"
    return f"{value:.{digits}f}".replace(".", ",")


def performance_by_dimension(
    frame: pd.DataFrame,
    dimension: str,
    *,
    min_group_size: int = 1,
    include_missing: bool = False,
) -> pd.DataFrame:
    """Agrega rendimiento con mediana, volumen, tasas y tamano muestral."""
    work = frame.copy()
    if include_missing:
        work[dimension] = work[dimension].fillna("Desconocido").replace("", "Desconocido")
    else:
        work = work[work[dimension].notna() & work[dimension].astype(str).ne("")]
    if work.empty:
        return pd.DataFrame(
            columns=[dimension, "video_count", "total_views", "median_views"]
        )

    aggregations: dict[str, tuple[str, str]] = {
        "video_count": ("video_id", "nunique"),
        "total_views": ("views", "sum"),
        "median_views": ("views", "median"),
        "mean_views": ("views", "mean"),
        "p25_views": ("views", lambda series: series.quantile(0.25)),
        "p75_views": ("views", lambda series: series.quantile(0.75)),
        "max_views": ("views", "max"),
        "median_views_per_day": ("views_per_day", "median"),
        "median_like_per_1000_views": ("like_per_1000_views", "median"),
        "median_comment_per_1000_views": ("comment_per_1000_views", "median"),
        "median_share_per_1000_views": ("share_per_1000_views", "median"),
        "median_save_per_1000_views": ("save_per_1000_views", "median"),
        "median_engagement_per_1000_views": (
            "engagement_full_per_1000_views",
            "median",
        ),
        "viral_hit_rate": ("is_viral_2x_median", "mean"),
    }
    result = work.groupby(dimension, dropna=False, observed=True).agg(**aggregations).reset_index()
    overall_median = frame["views"].median()
    total_views = frame["views"].sum(min_count=1)
    result["median_views_index"] = (
        result["median_views"] / overall_median * 100 if overall_median > 0 else np.nan
    )
    result["share_of_total_views"] = result["total_views"] / total_views
    result["viral_hit_rate"] = result["viral_hit_rate"] * 100
    result["sample_sufficient"] = result["video_count"] >= min_group_size
    result = result[result["video_count"] >= min_group_size]
    return result.sort_values(
        ["median_views", "video_count"], ascending=[False, False], na_position="last"
    ).reset_index(drop=True)


def build_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    valid_views = frame["views"].dropna()
    total_views = valid_views.sum(min_count=1)
    def weighted_rate(metric: str) -> float:
        subset = frame[["views", metric]].dropna()
        subset = subset[subset["views"] > 0]
        return _safe_divide(
            subset[metric].sum(min_count=1),
            subset["views"].sum(min_count=1),
            1_000,
        )

    top_n = max(1, int(np.ceil(len(frame) * 0.10)))
    top_share = _safe_divide(
        frame.nlargest(top_n, "views")["views"].sum(min_count=1), total_views, 100
    )
    median_views = valid_views.median()
    viral_rate = (
        float((valid_views >= 2 * median_views).mean() * 100)
        if len(valid_views) and median_views > 0
        else np.nan
    )
    weeks_span = (
        max((frame["created_at_utc"].max() - frame["created_at_utc"].min()).days / 7, 1)
        if frame["created_at_utc"].notna().sum() >= 2
        else np.nan
    )

    headline = {
        "video_count": int(frame["video_id"].nunique()),
        "total_views": float(total_views) if pd.notna(total_views) else np.nan,
        "median_views": float(median_views) if pd.notna(median_views) else np.nan,
        "mean_views": float(valid_views.mean()) if len(valid_views) else np.nan,
        "p25_views": float(valid_views.quantile(0.25)) if len(valid_views) else np.nan,
        "p75_views": float(valid_views.quantile(0.75)) if len(valid_views) else np.nan,
        "max_views": float(valid_views.max()) if len(valid_views) else np.nan,
        "top_10pct_view_share": top_share,
        "viral_hit_rate_2x_median": viral_rate,
        "posts_per_week": _safe_divide(len(frame), weeks_span),
        "weighted_like_per_1000_views": weighted_rate("likes"),
        "weighted_comment_per_1000_views": weighted_rate("comments"),
        "weighted_share_per_1000_views": weighted_rate("shares"),
        "weighted_save_per_1000_views": weighted_rate("saves"),
        "date_start": frame["created_at_local"].min(),
        "date_end": frame["created_at_local"].max(),
    }
    definitions = {
        "video_count": "Videos unicos analizados.",
        "total_views": "Suma de views acumuladas de todos los videos.",
        "median_views": "Mediana de views por video; medida principal robusta ante virales.",
        "mean_views": "Media de views por video; sensible a videos virales.",
        "p25_views": "Percentil 25 de views.",
        "p75_views": "Percentil 75 de views.",
        "max_views": "Mayor numero de views observado.",
        "top_10pct_view_share": "Porcentaje de views concentrado en el 10% de videos con mas views.",
        "viral_hit_rate_2x_median": "Porcentaje de videos con al menos el doble de la mediana de views.",
        "posts_per_week": "Ritmo medio de publicacion durante el periodo observado.",
        "weighted_like_per_1000_views": "Likes totales por cada 1.000 views totales.",
        "weighted_comment_per_1000_views": "Comentarios totales por cada 1.000 views totales.",
        "weighted_share_per_1000_views": "Compartidos totales por cada 1.000 views totales.",
        "weighted_save_per_1000_views": "Guardados totales por cada 1.000 views totales.",
        "date_start": "Primera publicacion incluida.",
        "date_end": "Ultima publicacion incluida.",
    }
    rows = []
    for metric, value in headline.items():
        if metric in {"date_start", "date_end"}:
            display = value.strftime("%Y-%m-%d %H:%M") if pd.notna(value) else "No disponible"
            raw_value = value.isoformat() if pd.notna(value) else None
        elif metric in {
            "top_10pct_view_share",
            "viral_hit_rate_2x_median",
            "posts_per_week",
            "weighted_like_per_1000_views",
            "weighted_comment_per_1000_views",
            "weighted_share_per_1000_views",
            "weighted_save_per_1000_views",
        }:
            display = _format_float(value)
            raw_value = value
        else:
            display = _format_int(value)
            raw_value = value
        rows.append(
            {
                "metric": metric,
                "value": raw_value,
                "display_value": display,
                "definition": definitions[metric],
            }
        )
    return pd.DataFrame(rows), headline


def build_weekly(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame[frame["week_start"].notna()].copy()
    if work.empty:
        return pd.DataFrame()
    result = (
        work.groupby("week_start", observed=True)
        .agg(
            video_count=("video_id", "nunique"),
            total_views=("views", "sum"),
            median_views=("views", "median"),
            mean_views=("views", "mean"),
            median_views_per_day=("views_per_day", "median"),
            median_engagement_per_1000_views=(
                "engagement_full_per_1000_views",
                "median",
            ),
        )
        .reset_index()
    )
    result["posting_frequency_bucket"] = result["video_count"].map(
        lambda value: (
            "1 video/semana"
            if value <= 1
            else "2 videos/semana"
            if value == 2
            else "3-4 videos/semana"
            if value <= 4
            else "5-7 videos/semana"
            if value <= 7
            else "8+ videos/semana"
        )
    )
    return result.sort_values("week_start").reset_index(drop=True)


def build_frequency(frame: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    if weekly.empty:
        return pd.DataFrame()
    rows = []
    for bucket, week_subset in weekly.groupby("posting_frequency_bucket", observed=True):
        week_names = set(week_subset["week_start"])
        videos = frame[frame["week_start"].isin(week_names)]
        rows.append(
            {
                "posting_frequency_bucket": bucket,
                "number_of_weeks": int(len(week_subset)),
                "video_count": int(videos["video_id"].nunique()),
                "total_views": videos["views"].sum(min_count=1),
                "median_views_per_video": videos["views"].median(),
                "mean_views_per_video": videos["views"].mean(),
                "median_weekly_total_views": week_subset["total_views"].median(),
                "median_views_per_day": videos["views_per_day"].median(),
                "median_engagement_per_1000_views": videos[
                    "engagement_full_per_1000_views"
                ].median(),
            }
        )
    order = {
        "1 video/semana": 1,
        "2 videos/semana": 2,
        "3-4 videos/semana": 3,
        "5-7 videos/semana": 4,
        "8+ videos/semana": 5,
    }
    result = pd.DataFrame(rows)
    result["_order"] = result["posting_frequency_bucket"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def build_frequency_relationship(weekly: pd.DataFrame) -> pd.DataFrame:
    if weekly.empty:
        return pd.DataFrame()
    rows = []
    for metric, description in [
        ("median_views", "Calidad por video: videos semanales frente a mediana de views."),
        ("total_views", "Escala: videos semanales frente a views totales de la semana."),
        (
            "median_engagement_per_1000_views",
            "Eficiencia: videos semanales frente a engagement mediano por 1.000 views.",
        ),
    ]:
        correlation = _spearman(weekly["video_count"], weekly[metric])
        rows.append(
            {
                "relationship": f"video_count_vs_{metric}",
                "weeks": len(weekly),
                "spearman_correlation": correlation,
                "interpretation": _correlation_label(correlation),
                "description": description,
            }
        )
    return pd.DataFrame(rows)


def _correlation_label(value: float) -> str:
    if pd.isna(value):
        return "No calculable"
    absolute = abs(value)
    strength = "debil" if absolute < 0.3 else "moderada" if absolute < 0.6 else "fuerte"
    direction = "positiva" if value > 0 else "negativa" if value < 0 else "nula"
    return f"{strength} {direction}"


def build_posting_gap(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame[frame["posting_gap_days"].notna()].copy()
    if work.empty:
        return pd.DataFrame()

    def bucket(value: float) -> str:
        if value <= 1:
            return "<=1 dia"
        if value <= 3:
            return "1-3 dias"
        if value <= 7:
            return "3-7 dias"
        return ">7 dias"

    work["posting_gap_bucket"] = work["posting_gap_days"].map(bucket)
    return performance_by_dimension(work, "posting_gap_bucket", min_group_size=1)


def build_hashtag_performance(frame: pd.DataFrame, min_group_size: int) -> pd.DataFrame:
    columns = [
        "video_id",
        "hashtags",
        "views",
        "views_per_day",
        "like_per_1000_views",
        "comment_per_1000_views",
        "share_per_1000_views",
        "save_per_1000_views",
        "engagement_full_per_1000_views",
        "is_viral_2x_median",
    ]
    exploded = frame[columns].explode("hashtags").rename(columns={"hashtags": "hashtag"})
    exploded = exploded[exploded["hashtag"].notna() & exploded["hashtag"].astype(str).ne("")]
    if exploded.empty:
        return pd.DataFrame()
    return performance_by_dimension(
        exploded, "hashtag", min_group_size=min_group_size
    )


def build_music_performance(frame: pd.DataFrame, min_group_size: int) -> pd.DataFrame:
    work = frame.copy()
    work["music_label"] = work.apply(
        lambda row: (
            f"{row['music_name']} — {row['music_author']}"
            if row.get("music_name") and row.get("music_author")
            else row.get("music_name") or "Desconocido"
        ),
        axis=1,
    )
    return performance_by_dimension(
        work, "music_label", min_group_size=min_group_size, include_missing=True
    )


def build_scaling(frame: pd.DataFrame) -> pd.DataFrame:
    """Elasticidad log-log: cuanto crece cada interaccion al crecer las views."""
    rows = []
    for metric in ["likes", "comments", "shares", "saves"]:
        pair = frame[["views", metric]].dropna()
        pair = pair[(pair["views"] >= 0) & (pair[metric] >= 0)]
        if len(pair) < 10 or pair["views"].nunique() < 3 or pair[metric].nunique() < 3:
            rows.append(
                {
                    "metric": metric,
                    "videos_used": len(pair),
                    "elasticity": np.nan,
                    "r_squared": np.nan,
                    "estimated_change_for_10pct_more_views_pct": np.nan,
                    "scaling_type": "Muestra insuficiente",
                }
            )
            continue
        x = np.log1p(pair["views"].astype(float).to_numpy())
        y = np.log1p(pair[metric].astype(float).to_numpy())
        slope, intercept = np.polyfit(x, y, 1)
        predicted = intercept + slope * x
        residual = np.sum((y - predicted) ** 2)
        total = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - residual / total if total > 0 else np.nan
        if slope < 0:
            label = "Relacion inversa/no estable"
        elif slope < 0.8:
            label = "Sublineal: crece mas despacio que las views"
        elif slope <= 1.2:
            label = "Aproximadamente proporcional a las views"
        else:
            label = "Superlineal: crece mas rapido que las views"
        rows.append(
            {
                "metric": metric,
                "videos_used": len(pair),
                "elasticity": float(slope),
                "r_squared": float(r_squared),
                "estimated_change_for_10pct_more_views_pct": float(
                    (1.1**slope - 1) * 100
                ),
                "scaling_type": label,
            }
        )
    return pd.DataFrame(rows)


def build_correlations(frame: pd.DataFrame) -> pd.DataFrame:
    variables = [
        "views",
        "likes",
        "comments",
        "shares",
        "saves",
        "duration_seconds",
        "hashtag_count",
        "caption_length",
        "posting_gap_days",
    ]
    rows = []
    for index, left in enumerate(variables):
        for right in variables[index + 1 :]:
            raw = _spearman(frame[left], frame[right])
            positive = frame[[left, right]].dropna()
            log_corr = _spearman(np.log1p(positive[left].clip(lower=0)), np.log1p(positive[right].clip(lower=0)))
            rows.append(
                {
                    "metric_x": left,
                    "metric_y": right,
                    "spearman_raw": raw,
                    "spearman_log1p": log_corr,
                }
            )
    return pd.DataFrame(rows)


def build_top_videos(frame: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    columns = [
        "video_id",
        "created_at_local",
        "video_url",
        "caption",
        "views",
        "views_index",
        "views_per_day",
        "likes",
        "comments",
        "shares",
        "saves",
        "engagement_full_per_1000_views",
        "duration_seconds",
        "hashtag_count",
        "hashtags_text",
        "music_name",
        "music_type",
        "is_pinned",
    ]
    result = frame.nlargest(min(limit, len(frame)), "views")[columns].copy()
    result.insert(0, "views_rank", range(1, len(result) + 1))
    return result


def build_quality_tables(
    frame: pd.DataFrame, quality: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, str]]]:
    core_fields = [
        "video_id",
        "views",
        "created_at_utc",
        "likes",
        "comments",
        "shares",
        "saves",
        "duration_seconds",
        "hashtags",
        "music_name",
        "author_username",
        "video_url",
    ]
    field_rows = []
    for field in core_fields:
        populated = frame[field].notna()
        if field in {"video_id", "author_username", "video_url", "music_name"}:
            populated &= frame[field].astype(str).ne("")
        elif field == "hashtags":
            populated &= frame[field].map(
                lambda value: isinstance(value, list) and len(value) > 0
            )
        field_rows.append(
            {
                "field": field,
                "populated_rows": int(populated.sum()),
                "total_rows": len(frame),
                "coverage_pct": float(populated.mean() * 100) if len(frame) else 0.0,
                "importance": "Necesario" if field in REQUIRED_FOR_CORE else "Complementario",
            }
        )
    fields = pd.DataFrame(field_rows)
    warnings: list[dict[str, str]] = []

    def add(severity: str, code: str, message: str) -> None:
        warnings.append({"severity": severity, "code": code, "message": message})

    if len(frame) < 10:
        add("Alta", "SMALL_SAMPLE", "Menos de 10 videos: no conviene comparar grupos.")
    elif len(frame) < 30:
        add("Media", "LIMITED_SAMPLE", "Menos de 30 videos: interpreta segmentos pequenos con cautela.")
    if frame["views"].isna().mean() > 0:
        add("Alta", "MISSING_VIEWS", "Hay videos sin views; se excluyen de varias metricas.")
    if frame["created_at_utc"].isna().mean() > 0.10:
        add("Alta", "MISSING_DATES", "Mas del 10% de videos no tiene fecha valida.")
    if frame["saves"].notna().mean() < 0.80:
        add(
            "Media",
            "LOW_SAVE_COVERAGE",
            "Guardados disponibles en menos del 80%: usa engagement core cuando falten.",
        )
    accounts = quality.get("accounts_detected", [])
    if len(accounts) > 1:
        add(
            "Alta",
            "MULTIPLE_ACCOUNTS",
            "El archivo contiene varias cuentas; filtra una con --account para no mezclarlas.",
        )
    if quality.get("duplicate_video_rows_removed", 0):
        add(
            "Baja",
            "DUPLICATES_REMOVED",
            f"Se eliminaron {quality['duplicate_video_rows_removed']} duplicados por video_id.",
        )
    if quality.get("synthetic_video_ids_created", 0):
        add(
            "Media",
            "SYNTHETIC_IDS",
            f"Se crearon {quality['synthetic_video_ids_created']} IDs porque faltaba video_id.",
        )
    if not warnings:
        add("Baja", "NO_MAJOR_ISSUES", "No se detectaron problemas materiales automaticos.")
    return fields, pd.DataFrame(warnings), warnings


def build_data_dictionary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in frame.columns:
        rows.append(
            {
                "column": column,
                "dtype": str(frame[column].dtype),
                "definition": DATA_DICTIONARY.get(column, "Campo normalizado o derivado; consulta METRIC_DICTIONARY.md."),
            }
        )
    return pd.DataFrame(rows)


def _best_group(table: pd.DataFrame, label_column: str) -> str | None:
    if table.empty or "median_views" not in table:
        return None
    usable = table[table["video_count"] >= 2]
    if usable.empty:
        return None
    row = usable.sort_values("median_views", ascending=False).iloc[0]
    return f"{row[label_column]} ({int(row['video_count'])} videos; mediana {_format_int(row['median_views'])} views)"


def _generate_findings(
    frame: pd.DataFrame,
    headline: dict[str, Any],
    tables: dict[str, pd.DataFrame],
) -> list[str]:
    findings = [
        f"Se analizaron {headline['video_count']} videos con {_format_int(headline['total_views'])} views acumuladas; la mediana fue {_format_int(headline['median_views'])} views por video.",
        f"El 10% de videos con mas alcance concentra {_format_float(headline['top_10pct_view_share'], 1)}% de todas las views. Esto mide cuanto depende la cuenta de unos pocos virales.",
    ]
    scaling = tables.get("engagement_scaling", pd.DataFrame())
    comments = scaling[scaling.get("metric", pd.Series(dtype=str)).eq("comments")]
    if not comments.empty and pd.notna(comments.iloc[0]["elasticity"]):
        row = comments.iloc[0]
        findings.append(
            "La elasticidad comentarios-views es "
            f"{_format_float(row['elasticity'])}: {row['scaling_type'].lower()}. "
            f"Un 10% mas de views se asocia aproximadamente con {_format_float(row['estimated_change_for_10pct_more_views_pct'], 1)}% mas comentarios; es asociacion, no causalidad."
        )
    frequency_rel = tables.get("posting_frequency_relationship", pd.DataFrame())
    quality_rel = frequency_rel[
        frequency_rel.get("relationship", pd.Series(dtype=str)).eq(
            "video_count_vs_median_views"
        )
    ]
    if not quality_rel.empty and pd.notna(quality_rel.iloc[0]["spearman_correlation"]):
        row = quality_rel.iloc[0]
        findings.append(
            "La relacion semanal entre cantidad publicada y mediana de views es "
            f"{row['interpretation']} (Spearman {_format_float(row['spearman_correlation'])}; {int(row['weeks'])} semanas)."
        )

    candidates = [
        ("hashtag_count_analysis", "hashtag_count", "cantidad de hashtags"),
        ("hashtag_performance", "hashtag", "hashtag"),
        ("music_type_performance", "music_type", "tipo de musica"),
        ("duration_performance", "duration_bucket", "duracion"),
    ]
    for table_name, label_column, description in candidates:
        table = tables.get(table_name, pd.DataFrame())
        best = _best_group(table, label_column) if label_column in table.columns else None
        if best:
            findings.append(f"Mejor grupo observado por {description}: {best}.")
    return findings


def analyze(
    frame: pd.DataFrame,
    quality: dict[str, Any],
    *,
    min_group_size: int = 2,
) -> AnalysisResult:
    if len(quality.get("accounts_detected", [])) > 1:
        raise ValueError(
            "El dataset contiene varias cuentas: "
            + ", ".join(quality["accounts_detected"])
            + ". Vuelve a ejecutar indicando --account NOMBRE."
        )

    summary, headline = build_summary(frame)
    weekly = build_weekly(frame)
    tables: dict[str, pd.DataFrame] = {
        "summary_metrics": summary,
        "weekly_performance": weekly,
        "posting_frequency_analysis": build_frequency(frame, weekly),
        "posting_frequency_relationship": build_frequency_relationship(weekly),
        "posting_gap_analysis": build_posting_gap(frame),
        "hashtag_performance": build_hashtag_performance(frame, min_group_size),
        "hashtag_count_analysis": performance_by_dimension(
            frame, "hashtag_count", min_group_size=min_group_size
        ),
        "hashtag_count_bucket_analysis": performance_by_dimension(
            frame, "hashtag_count_bucket", min_group_size=min_group_size
        ),
        "music_type_performance": performance_by_dimension(
            frame, "music_type", min_group_size=min_group_size, include_missing=True
        ),
        "music_performance": build_music_performance(frame, min_group_size),
        "duration_performance": performance_by_dimension(
            frame, "duration_bucket", min_group_size=min_group_size, include_missing=True
        ),
        "caption_length_performance": performance_by_dimension(
            frame, "caption_length_bucket", min_group_size=min_group_size
        ),
        "content_type_performance": performance_by_dimension(
            frame, "content_type", min_group_size=min_group_size
        ),
        "weekday_performance": performance_by_dimension(
            frame, "publish_weekday", min_group_size=min_group_size
        ),
        "hour_performance": performance_by_dimension(
            frame, "publish_hour", min_group_size=min_group_size
        ),
        "weekday_hour_performance": performance_by_dimension(
            frame.assign(
                weekday_hour=np.where(
                    frame["publish_weekday"].notna() & frame["publish_hour"].notna(),
                    frame["publish_weekday"].astype(str)
                    + " "
                    + frame["publish_hour"].astype("Int64").astype(str)
                    + ":00",
                    None,
                )
            ),
            "weekday_hour",
            min_group_size=min_group_size,
        ),
        "monthly_performance": performance_by_dimension(
            frame, "publish_year_month", min_group_size=1
        ),
        "location_performance": performance_by_dimension(
            frame, "location", min_group_size=min_group_size
        ),
        "language_performance": performance_by_dimension(
            frame, "language", min_group_size=min_group_size
        ),
        "engagement_scaling": build_scaling(frame),
        "correlations": build_correlations(frame),
        "top_videos": build_top_videos(frame),
        "data_dictionary": build_data_dictionary(frame),
    }
    fields, warnings_table, warnings = build_quality_tables(frame, quality)
    tables["data_quality_fields"] = fields
    tables["data_quality_warnings"] = warnings_table
    findings = _generate_findings(frame, headline, tables)
    return AnalysisResult(
        tables=tables,
        findings=findings,
        quality_warnings=warnings,
        headline=headline,
    )
