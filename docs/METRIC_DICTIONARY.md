# Diccionario de metricas

## Principios

- La unidad de analisis es un video unico.
- La mediana es la medida principal de rendimiento porque TikTok suele tener distribuciones muy sesgadas.
- Cada tabla incluye `video_count`; no se interpreta un grupo sin revisar su muestra.
- Los resultados son asociaciones descriptivas. No prueban que un hashtag, una hora o una duracion causen mas views.
- Los contadores representan una fotografia acumulada en la fecha de descarga.

## Alcance

| Metrica | Formula | Interpretacion |
|---|---|---|
| `total_views` | Suma de views | Escala acumulada del contenido incluido. Aumenta mecanicamente al publicar mas. |
| `median_views` | Percentil 50 de views | Rendimiento tipico de un video; KPI principal. |
| `mean_views` | Suma de views / videos | Util, pero sensible a virales. |
| `p25_views`, `p75_views` | Percentiles 25 y 75 | Rango central del rendimiento. |
| `views_index` | Views del video / mediana global × 100 | 100 equivale a la mediana; 200 es el doble. |
| `viral_hit_rate` | Videos con views ≥ 2 × mediana / videos | Frecuencia de resultados claramente superiores al nivel tipico. |
| `top_10pct_view_share` | Views del 10% superior / views totales | Concentracion: cuanto depende la cuenta de pocos virales. |
| `views_per_day` | Views / max(dias desde publicacion, 1) | Aproximacion de velocidad; no sustituye una serie historica. |

## Engagement

Todas las tasas se calculan por 1.000 visualizaciones para comparar videos de distinto alcance:

```text
like_per_1000_views    = likes / views × 1.000
comment_per_1000_views = comentarios / views × 1.000
share_per_1000_views   = compartidos / views × 1.000
save_per_1000_views    = guardados / views × 1.000
```

`engagement_core` utiliza likes + comentarios + compartidos y exige los tres campos. `engagement_full` anade guardados y exige los cuatro. Si un campo falta, la tasa queda vacia; no se trata como cero.

Las tasas de la tabla resumen son ponderadas:

```text
comentarios totales / views totales × 1.000
```

Las tablas de segmentos muestran la mediana de la tasa individual de los videos del grupo. Son dos perspectivas distintas y ambas estan etiquetadas.

## Comentarios frente a views

`engagement_scaling.csv` estima por separado:

```text
log(1 + interaccion) = intercepto + elasticidad × log(1 + views)
```

- Elasticidad menor que `0,8`: la interaccion crece claramente mas despacio que las views.
- Entre `0,8` y `1,2`: crecimiento aproximadamente proporcional.
- Mayor que `1,2`: crecimiento mas rapido que las views.

La tabla incluye `r_squared`, videos usados y el cambio estimado de la interaccion asociado con un 10% mas de views. La regresion requiere al menos 10 videos y variacion suficiente. Es descriptiva y no causal.

## Cantidad de videos y visualizaciones

Se calculan dos relaciones diferentes:

1. `video_count` frente a `total_views` semanal: mide escala, pero es en parte mecanica porque mas videos ofrecen mas oportunidades de sumar views.
2. `video_count` frente a `median_views` semanal: mide si el rendimiento tipico por video cambia cuando aumenta la frecuencia.

`posting_frequency_relationship.csv` usa correlacion de Spearman, apropiada para relaciones monotonas y menos sensible a virales. Siempre incluye el numero de semanas.

## Hashtags

- `hashtag_performance.csv`: una fila por hashtag, explotando cada video una vez por hashtag unico.
- `hashtag_count_analysis.csv`: una fila por numero exacto de hashtags.
- `hashtag_count_bucket_analysis.csv`: rangos `0`, `1`, `2`, `3-4`, `5-7`, `8+`.
- `median_views_index`: mediana del grupo / mediana global × 100.

Un hashtag puede parecer mejor porque se usa en ciertos tipos de vivienda o formatos. No se interpreta como efecto causal.

## Musica

`music_type` distingue:

- `Sonido original`.
- `Musica no original`.
- `Desconocido`.

Se utiliza `musicOriginal` cuando esta disponible y el nombre del sonido como respaldo, porque algunos scrapers devuelven el indicador de forma inconsistente. `music_performance.csv` analiza sonidos concretos repetidos.

## Tiempo y frecuencia

- Dias y horas se convierten primero a la zona horaria elegida.
- `posting_gap_days` es la distancia desde la publicacion anterior.
- `posts_in_week` usa semanas de lunes a domingo.
- Las semanas incompletas del principio y final siguen apareciendo; deben revisarse antes de sacar conclusiones fuertes.

## Calidad de datos

La herramienta:

- Detecta los alias habituales de Clockworks y ApiDojo.
- Acepta JSON anidado y CSV con claves como `authorMeta.name`.
- Excluye objetos de perfil/seguidores mezclados con los posts.
- Deduplica por `video_id`, conservando la fila mas completa.
- Convierte contadores negativos en valores ausentes y los registra.
- No mezcla varias cuentas sin que el usuario seleccione una.
- Calcula cobertura de los campos principales.
- Conserva el hash SHA-256 del archivo de entrada para reproducibilidad.

## Limites importantes

- TikTok y Apify pueden modificar sus esquemas.
- El scraper puede devolver menos posts que los existentes.
- Los posts eliminados o privados no aparecen.
- Los seguidores suelen ser una fotografia actual, no el dato historico al publicar.
- No hay impresiones, retencion, visitas al perfil ni leads salvo que otra fuente los aporte.
- Diferentes edades de los videos hacen que las views acumuladas no sean directamente equivalentes.
