"""Interfaz de linea de comandos en espanol."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import traceback
import webbrowser

from .io import InputDataError, discover_input
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiktok-analyze",
        description=(
            "Analiza una exportacion JSON/JSONL/CSV de posts de TikTok obtenida con Apify "
            "y genera un informe HTML mas tablas para Power BI."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Ruta al archivo de Apify. Si se omite, usa el mas reciente de data/input.",
    )
    parser.add_argument(
        "--output-root",
        default="output",
        help="Carpeta donde crear cada analisis (por defecto: output).",
    )
    parser.add_argument(
        "--timezone",
        default="Europe/Madrid",
        help="Zona horaria IANA para dias y horas (por defecto: Europe/Madrid).",
    )
    parser.add_argument(
        "--as-of",
        help="Fecha de observacion YYYY-MM-DD; por defecto se usa el momento actual.",
    )
    parser.add_argument(
        "--min-group-size",
        type=int,
        default=2,
        help="Minimo de videos para mostrar hashtag/sonido/grupo (por defecto: 2).",
    )
    parser.add_argument(
        "--account",
        help="Cuenta concreta (sin @) si el archivo contiene posts de varias cuentas.",
    )
    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Abre report.html automaticamente al terminar.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Muestra el traceback completo si hay un error.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.min_group_size < 1:
        parser.error("--min-group-size debe ser 1 o mayor.")

    project_root = Path.cwd()
    try:
        if args.input:
            input_path = Path(args.input)
        else:
            input_path = discover_input(project_root / "data" / "input")
            print(f"Archivo detectado automaticamente: {input_path.name}")

        print("Leyendo y validando la exportacion de Apify...")
        result = run_pipeline(
            input_path,
            output_root=Path(args.output_root),
            timezone=args.timezone,
            as_of=args.as_of,
            min_group_size=args.min_group_size,
            account=args.account,
        )

        print("\nANALISIS COMPLETADO")
        print(f"Videos validos: {len(result.normalization.frame)}")
        print(f"Resultados: {result.output_dir}")
        print(f"Informe: {result.report_path}")
        print("\nConclusiones automaticas:")
        for finding in result.analysis.findings[:6]:
            print(f"- {finding}")

        if args.open_report:
            webbrowser.open(result.report_path.resolve().as_uri())
    except (FileNotFoundError, InputDataError, ValueError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover - red de seguridad para usuarios no tecnicos
        print(f"\nERROR INESPERADO: {exc}", file=sys.stderr)
        print("Vuelve a ejecutar con --debug para ver el detalle.", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        raise SystemExit(1) from exc
