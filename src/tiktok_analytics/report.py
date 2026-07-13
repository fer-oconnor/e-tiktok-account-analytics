"""Generacion de un informe HTML autocontenido con graficos."""

from __future__ import annotations

import base64
from html import escape
from io import BytesIO
import os
from pathlib import Path
import tempfile
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tiktok-analytics-mpl"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .constants import WEEKDAY_ORDER
from .metrics import AnalysisResult

COLORS = {
    "navy": "#111827",
    "blue": "#2563EB",
    "cyan": "#06B6D4",
    "purple": "#7C3AED",
    "pink": "#EC4899",
    "green": "#10B981",
    "amber": "#F59E0B",
    "slate": "#64748B",
    "grid": "#E2E8F0",
}


def _human_number(value: Any, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    absolute = abs(number)
    if absolute >= 1_000_000_000:
        return f"{number / 1_000_000_000:.{digits}f}B".replace(".", ",")
    if absolute >= 1_000_000:
        return f"{number / 1_000_000:.{digits}f}M".replace(".", ",")
    if absolute >= 1_000:
        return f"{number / 1_000:.{digits}f}K".replace(".", ",")
    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")
    return f"{number:.{digits}f}".replace(".", ",")


def _pct(value: Any, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f}%".replace(".", ",")


def _style_axis(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(COLORS["grid"])
    axis.grid(axis="y", color=COLORS["grid"], linewidth=0.8, alpha=0.75)
    axis.tick_params(colors=COLORS["slate"], labelsize=9)
    axis.set_axisbelow(True)


def _number_formatter(value: float, _position: int) -> str:
    return _human_number(value)


def _to_data_uri(fig: plt.Figure) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _placeholder(message: str) -> str:
    fig, axis = plt.subplots(figsize=(8, 3.6))
    axis.axis("off")
    axis.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        color=COLORS["slate"],
        fontsize=11,
        wrap=True,
    )
    return _to_data_uri(fig)


def _bar_chart(
    table: pd.DataFrame,
    label: str,
    value: str,
    title: str,
    *,
    limit: int = 12,
    color: str = "blue",
    sort_desc: bool = True,
) -> str:
    if table.empty or label not in table or value not in table:
        return _placeholder("No hay datos suficientes para este grafico.")
    work = table[[label, value] + (["video_count"] if "video_count" in table else [])].dropna(
        subset=[label, value]
    )
    if work.empty:
        return _placeholder("No hay datos suficientes para este grafico.")
    work = work.sort_values(value, ascending=not sort_desc).head(limit)
    work = work.sort_values(value, ascending=True)
    height = max(3.4, 0.38 * len(work) + 1.3)
    fig, axis = plt.subplots(figsize=(8.2, height))
    bars = axis.barh(work[label].astype(str), work[value], color=COLORS[color], alpha=0.9)
    axis.set_title(title, loc="left", fontsize=13, weight="bold", color=COLORS["navy"], pad=12)
    axis.xaxis.set_major_formatter(FuncFormatter(_number_formatter))
    axis.set_xlabel("Mediana de visualizaciones", color=COLORS["slate"], fontsize=9)
    _style_axis(axis)
    for index, bar in enumerate(bars):
        count = (
            f" · n={int(work.iloc[index]['video_count'])}"
            if "video_count" in work and pd.notna(work.iloc[index]["video_count"])
            else ""
        )
        axis.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f"  {_human_number(bar.get_width())}{count}",
            va="center",
            fontsize=8.5,
            color=COLORS["navy"],
        )
    axis.margins(x=0.22)
    fig.tight_layout()
    return _to_data_uri(fig)


def _views_over_time(frame: pd.DataFrame) -> str:
    work = frame.dropna(subset=["created_at_local", "views"]).sort_values("created_at_local")
    if work.empty:
        return _placeholder("Faltan fechas o visualizaciones.")
    fig, axis = plt.subplots(figsize=(9, 4.2))
    axis.scatter(
        work["created_at_local"],
        work["views"],
        s=32,
        alpha=0.72,
        color=COLORS["blue"],
        edgecolor="white",
        linewidth=0.4,
    )
    rolling = work.set_index("created_at_local")["views"].rolling("45D", min_periods=3).median()
    if rolling.notna().any():
        axis.plot(rolling.index, rolling, color=COLORS["pink"], linewidth=2.2, label="Mediana movil 45 dias")
        axis.legend(frameon=False, fontsize=9)
    axis.set_yscale("symlog", linthresh=100)
    axis.yaxis.set_major_formatter(FuncFormatter(_number_formatter))
    axis.set_title("Rendimiento de los videos a lo largo del tiempo", loc="left", fontsize=13, weight="bold")
    axis.set_ylabel("Views (escala logaritmica)", color=COLORS["slate"], fontsize=9)
    _style_axis(axis)
    fig.autofmt_xdate(rotation=25)
    fig.tight_layout()
    return _to_data_uri(fig)


def _frequency_scatter(weekly: pd.DataFrame) -> str:
    work = weekly.dropna(subset=["video_count", "median_views"])
    if len(work) < 2:
        return _placeholder("Se necesitan al menos dos semanas con datos.")
    fig, axis = plt.subplots(figsize=(7.8, 4.2))
    sizes = 35 + 130 * (work["total_views"] / work["total_views"].max()).fillna(0)
    axis.scatter(
        work["video_count"],
        work["median_views"],
        s=sizes,
        color=COLORS["purple"],
        alpha=0.68,
        edgecolor="white",
    )
    axis.set_title("Cantidad publicada vs. rendimiento por video", loc="left", fontsize=13, weight="bold")
    axis.set_xlabel("Videos publicados esa semana", color=COLORS["slate"], fontsize=9)
    axis.set_ylabel("Mediana de views de la semana", color=COLORS["slate"], fontsize=9)
    axis.yaxis.set_major_formatter(FuncFormatter(_number_formatter))
    axis.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    _style_axis(axis)
    fig.tight_layout()
    return _to_data_uri(fig)


def _engagement_rates(headline: dict[str, Any]) -> str:
    labels = ["Likes", "Comentarios", "Compartidos", "Guardados"]
    values = [
        headline.get("weighted_like_per_1000_views"),
        headline.get("weighted_comment_per_1000_views"),
        headline.get("weighted_share_per_1000_views"),
        headline.get("weighted_save_per_1000_views"),
    ]
    if all(pd.isna(value) for value in values):
        return _placeholder("No hay interacciones suficientes.")
    fig, axis = plt.subplots(figsize=(7.8, 4.2))
    bars = axis.bar(labels, values, color=[COLORS["blue"], COLORS["pink"], COLORS["cyan"], COLORS["green"]])
    axis.set_title("Interacciones por cada 1.000 visualizaciones", loc="left", fontsize=13, weight="bold")
    axis.set_ylabel("Interacciones / 1.000 views", color=COLORS["slate"], fontsize=9)
    _style_axis(axis)
    for bar, value in zip(bars, values):
        if pd.notna(value):
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1f}", ha="center", va="bottom", fontsize=9)
    axis.margins(y=0.18)
    fig.tight_layout()
    return _to_data_uri(fig)


def _comments_scaling(frame: pd.DataFrame, scaling: pd.DataFrame) -> str:
    work = frame[["views", "comments"]].dropna()
    work = work[(work["views"] >= 0) & (work["comments"] >= 0)]
    if len(work) < 3:
        return _placeholder("No hay suficientes videos con views y comentarios.")
    x = np.log10(work["views"] + 1)
    y = np.log10(work["comments"] + 1)
    fig, axis = plt.subplots(figsize=(7.8, 4.5))
    axis.scatter(x, y, s=34, color=COLORS["pink"], alpha=0.65, edgecolor="white")
    row = scaling[scaling["metric"].eq("comments")] if not scaling.empty else pd.DataFrame()
    if not row.empty and pd.notna(row.iloc[0]["elasticity"]):
        slope = float(row.iloc[0]["elasticity"])
        intercept = float(np.polyfit(np.log1p(work["views"]), np.log1p(work["comments"]), 1)[1])
        x_raw = np.linspace(work["views"].min(), work["views"].max(), 100)
        y_raw = np.expm1(intercept + slope * np.log1p(x_raw)).clip(0, None)
        axis.plot(np.log10(x_raw + 1), np.log10(y_raw + 1), color=COLORS["navy"], linewidth=2)
        subtitle = f"Elasticidad {slope:.2f} · {row.iloc[0]['scaling_type']}"
    else:
        subtitle = "Muestra insuficiente para calcular elasticidad fiable"
    axis.set_title(
        "¿Crecen los comentarios al mismo ritmo que las views?",
        loc="left",
        fontsize=13,
        weight="bold",
        pad=28,
    )
    axis.text(0, 1.01, subtitle, transform=axis.transAxes, color=COLORS["slate"], fontsize=9)
    axis.set_xlabel("log10(views + 1)", color=COLORS["slate"], fontsize=9)
    axis.set_ylabel("log10(comentarios + 1)", color=COLORS["slate"], fontsize=9)
    _style_axis(axis)
    fig.tight_layout()
    return _to_data_uri(fig)


def _weekday_hour_heatmap(frame: pd.DataFrame) -> str:
    work = frame.dropna(subset=["publish_weekday", "publish_hour", "views"])
    if len(work) < 5:
        return _placeholder("Se necesitan mas publicaciones con fecha y hora.")
    pivot = work.pivot_table(
        index="publish_weekday",
        columns="publish_hour",
        values="views",
        aggfunc="median",
    ).reindex(WEEKDAY_ORDER)
    if pivot.dropna(how="all").empty:
        return _placeholder("No se pudo construir el mapa horario.")
    fig, axis = plt.subplots(figsize=(9, 4.4))
    masked = np.ma.masked_invalid(pivot.to_numpy(dtype=float))
    image = axis.imshow(masked, aspect="auto", cmap="Blues")
    axis.set_yticks(range(len(pivot.index)), pivot.index)
    axis.set_xticks(range(len(pivot.columns)), [f"{int(hour):02d}" for hour in pivot.columns])
    axis.set_xlabel("Hora local de publicacion", color=COLORS["slate"], fontsize=9)
    axis.set_title("Mediana de views por dia y hora", loc="left", fontsize=13, weight="bold")
    colorbar = fig.colorbar(image, ax=axis, pad=0.02)
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(_number_formatter))
    axis.tick_params(labelsize=8)
    fig.tight_layout()
    return _to_data_uri(fig)


def _top_videos_html(table: pd.DataFrame) -> str:
    if table.empty:
        return "<p>No hay videos disponibles.</p>"
    rows = []
    for _, row in table.head(15).iterrows():
        caption = str(row.get("caption") or "")
        if len(caption) > 90:
            caption = caption[:87] + "…"
        url = str(row.get("video_url") or "")
        video_label = f"#{int(row['views_rank'])}"
        if url.startswith("http"):
            video_label = f'<a href="{escape(url)}" target="_blank" rel="noopener">{video_label}</a>'
        rows.append(
            "<tr>"
            f"<td>{video_label}</td>"
            f"<td>{escape(caption) or '—'}</td>"
            f"<td>{_human_number(row.get('views'))}</td>"
            f"<td>{_human_number(row.get('comments'))}</td>"
            f"<td>{_human_number(row.get('shares'))}</td>"
            f"<td>{_human_number(row.get('saves'))}</td>"
            f"<td>{_human_number(row.get('engagement_full_per_1000_views'))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Rank</th><th>Video</th><th>Views</th><th>Comentarios</th>"
        "<th>Compartidos</th><th>Guardados</th><th>Eng./1.000</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _warnings_html(warnings: list[dict[str, str]]) -> str:
    parts = []
    for warning in warnings:
        severity = warning.get("severity", "Baja")
        css = "warning-high" if severity == "Alta" else "warning-medium" if severity == "Media" else "warning-low"
        parts.append(
            f'<li class="{css}"><strong>{escape(severity)}</strong> · {escape(warning.get("message", ""))}</li>'
        )
    return "<ul class=\"warnings\">" + "".join(parts) + "</ul>"


def generate_report(
    frame: pd.DataFrame,
    analysis: AnalysisResult,
    quality: dict[str, Any],
    output_path: Path,
) -> None:
    """Escribe el informe HTML sin depender de internet para abrirlo."""
    tables = analysis.tables
    headline = analysis.headline
    account = quality.get("accounts_detected", [])
    account_name = "@" + account[0] if account else "Cuenta de TikTok"
    generated = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")

    charts = {
        "timeline": _views_over_time(frame),
        "engagement": _engagement_rates(headline),
        "frequency": _frequency_scatter(tables["weekly_performance"]),
        "hashtags": _bar_chart(
            tables["hashtag_performance"],
            "hashtag",
            "median_views",
            "Hashtags con mejor mediana de views",
            color="cyan",
        ),
        "hashtag_count": _bar_chart(
            tables["hashtag_count_analysis"],
            "hashtag_count",
            "median_views",
            "Numero de hashtags vs. mediana de views",
            color="purple",
            sort_desc=False,
        ),
        "music": _bar_chart(
            tables["music_type_performance"],
            "music_type",
            "median_views",
            "Tipo de musica vs. mediana de views",
            color="pink",
        ),
        "duration": _bar_chart(
            tables["duration_performance"],
            "duration_bucket",
            "median_views",
            "Duracion vs. mediana de views",
            color="green",
        ),
        "comments": _comments_scaling(frame, tables["engagement_scaling"]),
        "heatmap": _weekday_hour_heatmap(frame),
    }

    findings_html = "".join(f"<li>{escape(finding)}</li>" for finding in analysis.findings)
    start = headline.get("date_start")
    end = headline.get("date_end")
    period = (
        f"{start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}"
        if pd.notna(start) and pd.notna(end)
        else "Periodo no disponible"
    )

    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Informe TikTok · {escape(account_name)}</title>
  <style>
    :root {{ --navy:#111827; --slate:#64748B; --blue:#2563EB; --cyan:#06B6D4; --purple:#7C3AED; --pink:#EC4899; --green:#10B981; --amber:#F59E0B; --line:#E2E8F0; --paper:#F8FAFC; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; color:var(--navy); background:var(--paper); line-height:1.55; }}
    .hero {{ background:linear-gradient(120deg,#0F172A,#1E3A8A 60%,#6D28D9); color:white; padding:54px 24px; }}
    .container {{ max-width:1180px; margin:0 auto; }}
    .eyebrow {{ text-transform:uppercase; letter-spacing:.12em; font-size:12px; opacity:.75; font-weight:700; }}
    h1 {{ font-size:clamp(34px,6vw,62px); line-height:1.04; margin:8px 0 14px; }}
    h2 {{ font-size:28px; margin:0 0 20px; }} h3 {{ font-size:18px; margin:0 0 8px; }}
    .hero p {{ max-width:760px; color:#DBEAFE; margin:0; }}
    .meta {{ margin-top:22px; display:flex; gap:22px; flex-wrap:wrap; font-size:13px; color:#BFDBFE; }}
    main {{ padding:34px 22px 70px; }}
    section {{ margin:28px 0 48px; }}
    .kpis {{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-top:-58px; position:relative; }}
    .card,.panel {{ background:white; border:1px solid var(--line); border-radius:16px; box-shadow:0 10px 28px rgba(15,23,42,.06); }}
    .card {{ padding:18px; min-height:112px; }} .card .label {{ color:var(--slate); font-size:12px; }} .card .value {{ display:block; font-size:26px; font-weight:800; margin-top:7px; }}
    .panel {{ padding:24px; }}
    .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .chart img {{ width:100%; display:block; }}
    .caption {{ font-size:12px; color:var(--slate); margin:4px 4px 0; }}
    .findings {{ padding-left:22px; margin:0; }} .findings li {{ margin:10px 0; }}
    .warnings {{ list-style:none; padding:0; margin:0; display:grid; gap:8px; }} .warnings li {{ border-left:4px solid var(--line); background:#F8FAFC; border-radius:8px; padding:10px 12px; font-size:13px; }}
    .warnings .warning-high {{ border-color:#EF4444; }} .warnings .warning-medium {{ border-color:var(--amber); }} .warnings .warning-low {{ border-color:var(--green); }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:12px; }} table {{ width:100%; border-collapse:collapse; min-width:820px; background:white; }} th,td {{ padding:12px 14px; text-align:left; border-bottom:1px solid var(--line); font-size:13px; }} th {{ background:#F1F5F9; color:#334155; position:sticky; top:0; }} td:nth-child(n+3) {{ white-space:nowrap; }} a {{ color:var(--blue); font-weight:700; }}
    .note {{ border-left:4px solid var(--blue); background:#EFF6FF; border-radius:10px; padding:14px 16px; color:#1E3A8A; font-size:13px; }}
    .method {{ color:#475569; font-size:14px; }} .method li {{ margin:8px 0; }}
    footer {{ color:var(--slate); font-size:12px; padding-top:22px; border-top:1px solid var(--line); }}
    @media (max-width:950px) {{ .kpis {{ grid-template-columns:repeat(3,1fr); }} .grid-2 {{ grid-template-columns:1fr; }} }}
    @media (max-width:560px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); margin-top:-32px; }} .card .value {{ font-size:21px; }} .panel {{ padding:16px; }} }}
    @media print {{ body {{ background:white; }} .card,.panel {{ box-shadow:none; break-inside:avoid; }} .hero {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
  </style>
</head>
<body>
  <header class="hero"><div class="container">
    <div class="eyebrow">TikTok Account Analytics · Apify</div>
    <h1>{escape(account_name)}</h1>
    <p>Informe automatico de alcance, engagement, contenido, frecuencia y consistencia. Prioriza medianas y tasas normalizadas para que unos pocos virales no distorsionen toda la lectura.</p>
    <div class="meta"><span>Periodo: {escape(period)}</span><span>Zona horaria: {escape(str(quality.get('timezone','—')))}</span><span>Generado: {generated}</span></div>
  </div></header>
  <main class="container">
    <div class="kpis">
      <div class="card"><span class="label">Videos</span><span class="value">{_human_number(headline.get('video_count'))}</span></div>
      <div class="card"><span class="label">Views totales</span><span class="value">{_human_number(headline.get('total_views'))}</span></div>
      <div class="card"><span class="label">Mediana de views</span><span class="value">{_human_number(headline.get('median_views'))}</span></div>
      <div class="card"><span class="label">Publicaciones/semana</span><span class="value">{_human_number(headline.get('posts_per_week'))}</span></div>
      <div class="card"><span class="label">Virales ≥2× mediana</span><span class="value">{_pct(headline.get('viral_hit_rate_2x_median'))}</span></div>
      <div class="card"><span class="label">Views en top 10%</span><span class="value">{_pct(headline.get('top_10pct_view_share'))}</span></div>
    </div>

    <section>
      <div class="grid-2">
        <div class="panel"><h2>Lectura ejecutiva</h2><ol class="findings">{findings_html}</ol></div>
        <div class="panel"><h2>Calidad de los datos</h2>{_warnings_html(analysis.quality_warnings)}</div>
      </div>
    </section>

    <section><h2>1. Alcance y consistencia</h2>
      <div class="grid-2">
        <div class="panel chart"><img src="{charts['timeline']}" alt="Views a lo largo del tiempo"><p class="caption">Cada punto es un video. La escala logaritmica permite ver simultaneamente videos normales y virales.</p></div>
        <div class="panel chart"><img src="{charts['engagement']}" alt="Tasas de engagement"><p class="caption">Tasas ponderadas: interacciones totales divididas por views totales. Sirven para comparar cuentas de distinto tamano.</p></div>
      </div>
    </section>

    <section><h2>2. Cantidad publicada y rendimiento</h2>
      <div class="grid-2">
        <div class="panel chart"><img src="{charts['frequency']}" alt="Frecuencia frente a views"><p class="caption">La comparacion importante es frecuencia frente a mediana por video; total de views por semana aumenta mecanicamente al publicar mas.</p></div>
        <div class="panel chart"><img src="{charts['heatmap']}" alt="Mapa de dia y hora"><p class="caption">Mediana de views por hora local. Las celdas con pocos videos deben tomarse como hipotesis, no como regla.</p></div>
      </div>
    </section>

    <section><h2>3. Hashtags, musica y formato</h2>
      <div class="grid-2">
        <div class="panel chart"><img src="{charts['hashtags']}" alt="Hashtags"><p class="caption">Solo se muestran hashtags con el minimo de videos configurado. n indica el tamano de muestra.</p></div>
        <div class="panel chart"><img src="{charts['hashtag_count']}" alt="Cantidad de hashtags"><p class="caption">Relacion entre cantidad exacta de hashtags y mediana de views.</p></div>
        <div class="panel chart"><img src="{charts['music']}" alt="Tipo de musica"><p class="caption">Clasificacion basada en musicOriginal y, cuando falta o es inconsistente, en el nombre del sonido.</p></div>
        <div class="panel chart"><img src="{charts['duration']}" alt="Duracion"><p class="caption">Compara rangos de duracion con mediana de views; no demuestra que la duracion cause el resultado.</p></div>
      </div>
    </section>

    <section><h2>4. Views frente a comentarios</h2>
      <div class="panel chart"><img src="{charts['comments']}" alt="Elasticidad comentarios views"><p class="caption">La elasticidad se estima con una regresion log-log. Menor que 1 significa que los comentarios crecen proporcionalmente menos que las views. R² y muestra estan en engagement_scaling.csv.</p></div>
    </section>

    <section><h2>5. Videos con mayor alcance</h2>{_top_videos_html(tables['top_videos'])}</section>

    <section><h2>Metodologia y limites</h2>
      <div class="panel method">
        <ul>
          <li><strong>Unidad de analisis:</strong> un video unico, deduplicado mediante video_id.</li>
          <li><strong>Metrica principal:</strong> mediana de views. La media y el total se conservan, pero pueden estar dominados por virales.</li>
          <li><strong>Engagement:</strong> se expresa por cada 1.000 views. El engagement core usa likes + comentarios + compartidos; el completo anade guardados cuando existen.</li>
          <li><strong>Comentarios vs. views:</strong> elasticidad de log(1+comentarios) frente a log(1+views). Es una asociacion descriptiva, no una estimacion causal.</li>
          <li><strong>Fecha de observacion:</strong> los contadores son acumulados en el momento de descargar Apify. Videos antiguos han tenido mas tiempo para crecer; views/dia es solo una aproximacion.</li>
          <li><strong>Seguidores:</strong> Apify suele devolver una fotografia actual, no los seguidores historicos de cada publicacion. Por eso no se usa como KPI causal por video.</li>
          <li><strong>Grupos pequenos:</strong> se muestra siempre n. Las diferencias con pocos videos sirven para formular hipotesis que deben comprobarse con nuevas publicaciones.</li>
          <li><strong>Privacidad:</strong> el archivo original y los resultados estan ignorados por Git para evitar que se publiquen accidentalmente.</li>
        </ul>
        <div class="note">Para Power BI utiliza los CSV de la carpeta <strong>tables</strong>. Cada tabla incluye el tamano de muestra y usa nombres de columnas estables entre ejecuciones.</div>
      </div>
    </section>

    <footer>Generado por TikTok Account Analytics v1.0 · Archivo autocontenido: puede abrirse sin conexion.</footer>
  </main>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
