"""Lectura de exportaciones de Apify y utilidades de archivos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

SUPPORTED_SUFFIXES = {".json", ".jsonl", ".ndjson", ".csv"}


class InputDataError(ValueError):
    """El archivo existe, pero no contiene un dataset utilizable."""


def discover_input(input_dir: Path) -> Path:
    """Devuelve el archivo compatible mas reciente de ``input_dir``."""
    if not input_dir.exists():
        raise FileNotFoundError(
            f"No existe la carpeta de entrada: {input_dir}. "
            "Creala o ejecuta el comando desde la raiz del proyecto."
        )
    files = [
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    if not files:
        raise FileNotFoundError(
            f"No hay ningun JSON, JSONL o CSV dentro de {input_dir}. "
            "Descarga el dataset de Apify y copialo ahi."
        )
    return max(files, key=lambda path: path.stat().st_mtime)


def _unwrap_json(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = None
        for key in ("items", "data", "results", "posts", "datasetItems"):
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
        if records is None:
            # Algunos exports contienen un unico video como objeto raiz.
            records = [payload]
    else:
        raise InputDataError("El JSON debe contener una lista u objeto de videos.")

    clean = [record for record in records if isinstance(record, dict)]
    if not clean:
        raise InputDataError("No se han encontrado objetos de video en el archivo.")
    return clean


def load_records(path: Path) -> list[dict[str, Any]]:
    """Carga JSON, JSONL o CSV y devuelve una lista de diccionarios."""
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise InputDataError(
            f"Formato {suffix or '(sin extension)'} no compatible. "
            "Usa JSON (recomendado), JSONL o CSV."
        )

    if suffix == ".json":
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                return _unwrap_json(json.load(handle))
        except json.JSONDecodeError as exc:
            raise InputDataError(f"JSON invalido: {exc}") from exc

    if suffix in {".jsonl", ".ndjson"}:
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InputDataError(
                        f"JSONL invalido en la linea {line_number}: {exc}"
                    ) from exc
                if isinstance(item, dict):
                    records.append(item)
        if not records:
            raise InputDataError("El JSONL no contiene objetos.")
        return records

    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        frame = pd.read_csv(path, encoding="latin-1", low_memory=False)
    if frame.empty:
        raise InputDataError("El CSV esta vacio.")
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def safe_name(value: str, default: str = "cuenta") -> str:
    """Convierte texto libre en un nombre de carpeta seguro y legible."""
    keep = []
    for char in str(value).strip().lower():
        if char.isalnum() or char in {"-", "_"}:
            keep.append(char)
        elif char in {" ", ".", "/", "\\", "@"}:
            keep.append("-")
    result = "".join(keep).strip("-_")
    while "--" in result:
        result = result.replace("--", "-")
    return result or default

