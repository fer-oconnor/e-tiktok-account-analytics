"""Orquestacion reproducible del analisis y escritura de resultados."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import __version__
from .io import load_records, safe_name
from .metrics import AnalysisResult, analyze
from .report import generate_report
from .schema import NormalizationResult, normalize_records


@dataclass
class PipelineResult:
    output_dir: Path
    report_path: Path
    cleaned_data_path: Path
    analysis: AnalysisResult
    normalization: NormalizationResult


TABLE_DESCRIPTIONS = {
    "summary_metrics": ("Una fila por KPI", "Resumen general y definiciones."),
    "weekly_performance": ("Una fila por semana", "Volumen y rendimiento semanal."),
    "posting_frequency_analysis": (
        "Una fila por rango de videos/semana",
        "Mediana de views segun frecuencia de publicacion.",
    ),
    "posting_frequency_relationship": (
        "Una fila por relacion",
        "Correlaciones entre cantidad semanal, views y engagement.",
    ),
    "posting_gap_analysis": (
        "Una fila por rango de dias",
        "Rendimiento segun dias desde el video anterior.",
    ),
    "hashtag_performance": ("Una fila por hashtag", "Rendimiento de hashtags repetidos."),
    "hashtag_count_analysis": (
        "Una fila por numero exacto de hashtags",
        "Cantidad de hashtags frente a views.",
    ),
    "hashtag_count_bucket_analysis": (
        "Una fila por rango de hashtags",
        "Version agrupada de cantidad de hashtags.",
    ),
    "music_type_performance": (
        "Una fila por tipo de sonido",
        "Original, no original o desconocido.",
    ),
    "music_performance": ("Una fila por sonido", "Rendimiento de sonidos reutilizados."),
    "duration_performance": ("Una fila por rango de segundos", "Duracion frente a rendimiento."),
    "caption_length_performance": (
        "Una fila por rango de caracteres",
        "Longitud del texto frente a rendimiento.",
    ),
    "content_type_performance": ("Una fila por formato", "Video frente a carrusel/fotos."),
    "weekday_performance": ("Una fila por dia", "Rendimiento por dia de la semana."),
    "hour_performance": ("Una fila por hora", "Rendimiento por hora local."),
    "weekday_hour_performance": ("Una fila por dia y hora", "Cruce de momento de publicacion."),
    "monthly_performance": ("Una fila por mes", "Evolucion mensual."),
    "location_performance": ("Una fila por ubicacion", "Ubicacion si el scraper la devuelve."),
    "language_performance": ("Una fila por idioma", "Idioma detectado en el texto."),
    "engagement_scaling": (
        "Una fila por interaccion",
        "Elasticidad de likes, comentarios, shares y saves respecto a views.",
    ),
    "correlations": ("Una fila por pareja de variables", "Correlaciones Spearman descriptivas."),
    "top_videos": ("Una fila por video", "Top 25 videos por views."),
    "data_dictionary": ("Una fila por columna", "Diccionario del dataset limpio."),
    "data_quality_fields": ("Una fila por campo", "Cobertura de campos relevantes."),
    "data_quality_warnings": ("Una fila por aviso", "Problemas y cautelas detectados."),
}


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Tipo no serializable: {type(value)!r}")


def _csv_ready(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = result[column].map(
                lambda value: value.isoformat() if pd.notna(value) else None
            )
        elif result[column].dtype == "object":
            result[column] = result[column].map(
                lambda value: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (list, dict))
                else value
            )
    return result


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    _csv_ready(frame).to_csv(path, index=False, encoding="utf-8-sig")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_output_dir(root: Path, account: str) -> Path:
    timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
    base = root / f"{safe_name(account)}_{timestamp}"
    candidate = base
    counter = 2
    while candidate.exists():
        candidate = Path(str(base) + f"_{counter}")
        counter += 1
    return candidate


def run_pipeline(
    input_path: Path,
    *,
    output_root: Path,
    timezone: str = "Europe/Madrid",
    as_of: str | None = None,
    min_group_size: int = 2,
    account: str | None = None,
) -> PipelineResult:
    input_path = input_path.expanduser().resolve()
    records = load_records(input_path)
    normalization = normalize_records(
        records,
        timezone=timezone,
        as_of=as_of,
        account=account,
    )
    analysis = analyze(
        normalization.frame,
        normalization.quality,
        min_group_size=min_group_size,
    )

    accounts = normalization.quality.get("accounts_detected", [])
    account_name = accounts[0] if accounts else account or input_path.stem
    output_dir = _unique_output_dir(output_root.expanduser().resolve(), account_name)
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=False)

    cleaned_path = output_dir / "cleaned_videos.csv"
    _write_csv(normalization.frame, cleaned_path)
    for name, table in analysis.tables.items():
        _write_csv(table, tables_dir / f"{name}.csv")

    manifest_rows = []
    for name, table in analysis.tables.items():
        grain, description = TABLE_DESCRIPTIONS.get(name, ("Consultar tabla", "Tabla analitica."))
        manifest_rows.append(
            {
                "table": name,
                "file": f"tables/{name}.csv",
                "rows": len(table),
                "grain": grain,
                "description": description,
            }
        )
    _write_csv(pd.DataFrame(manifest_rows), output_dir / "power_bi_manifest.csv")

    quality_path = output_dir / "data_quality.json"
    quality_path.write_text(
        json.dumps(normalization.quality, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    manifest = {
        "tool": "tiktok-account-analytics",
        "version": __version__,
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "input": {
            "filename": input_path.name,
            "sha256": _sha256(input_path),
            "rows_read": len(records),
        },
        "parameters": {
            "timezone": timezone,
            "as_of": normalization.quality.get("as_of_utc"),
            "min_group_size": min_group_size,
            "account_filter": account,
        },
        "output": {
            "account": account_name,
            "valid_unique_videos": len(normalization.frame),
            "table_rows": {name: len(table) for name, table in analysis.tables.items()},
        },
    }
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    report_path = output_dir / "report.html"
    generate_report(
        normalization.frame,
        analysis,
        normalization.quality,
        report_path,
    )
    return PipelineResult(
        output_dir=output_dir,
        report_path=report_path,
        cleaned_data_path=cleaned_path,
        analysis=analysis,
        normalization=normalization,
    )

