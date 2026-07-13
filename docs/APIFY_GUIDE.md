# Guia exacta: descargar una cuenta de TikTok con Apify

## Opcion recomendada: Clockworks TikTok Scraper

1. Abre [TikTok Scraper de Clockworks](https://apify.com/clockworks/tiktok-scraper).
2. Pulsa **Try for free** e inicia sesion en Apify.
3. En la seccion **Usernames**, escribe el usuario de TikTok sin `@`.
4. En **Number of videos per hashtag, profile or search**, escribe cuantos posts quieres obtener. Recomendacion inicial: `500`.
5. En **Profile sections to scrape**, deja unicamente **Videos**.
6. En **Profile video sorting**, selecciona **Latest**.
7. Deja **Exclude pinned posts** desactivado. El codigo deduplica los posts fijados.
8. No rellenes hashtags, busquedas ni URLs de videos: este analisis debe contener una sola cuenta.
9. Deja **Scrape related videos** desactivado para no mezclar otros autores.
10. Deja `commentsPerPost`, seguidores y seguidos en `0`. El contador total de comentarios del post ya se obtiene; no necesitamos descargar el texto de cada comentario.
11. Deja desactivadas las descargas de videos, portadas, carruseles, avatares, sonidos y subtitulos. No hacen falta para este analisis y pueden aumentar el coste.
12. Pulsa **Start** y espera a que el estado de la ejecucion sea **Succeeded**.
13. Abre la pestana **Output** o el dataset de la ejecucion.
14. Pulsa **Export** o **Download results**.
15. Selecciona **JSON**. Es el formato recomendado porque conserva hashtags y metadatos anidados. Tambien se admite CSV y JSONL.
16. Exporta todos los campos y todos los items; no descargues solo las filas visibles de la previsualizacion.
17. Guarda el archivo y copialo en `data/input`.
18. Ejecuta `run_analysis.bat`.

La [documentacion oficial de datasets de Apify](https://docs.apify.com/storage/dataset) confirma que cada objeto es una fila del dataset y que puede exportarse desde **Export** en JSON, CSV, JSONL y otros formatos.

## Configuracion mediante JSON

Si prefieres el editor JSON de Apify, usa:

```json
{
  "profiles": ["nombre_de_la_cuenta"],
  "resultsPerPage": 500,
  "profileScrapeSections": ["videos"],
  "profileSorting": "latest",
  "excludePinnedPosts": false,
  "scrapeRelatedVideos": false,
  "commentsPerPost": 0,
  "maxFollowersPerProfile": 0,
  "maxFollowingPerProfile": 0,
  "shouldDownloadVideos": false,
  "shouldDownloadCovers": false,
  "shouldDownloadSlideshowImages": false,
  "shouldDownloadAvatars": false,
  "shouldDownloadMusicCovers": false
}
```

## Como saber si la descarga esta completa

- Compara el numero de items del dataset con `resultsPerPage`.
- Si ambos son exactamente iguales, es posible que hayas alcanzado el limite. Repite con un numero mayor si quieres mas historia.
- En el informe, revisa `data_quality.json` y el periodo mostrado en la cabecera.
- Apify devuelve contadores acumulados en el momento de la descarga, no el historial diario de un mismo video.

## Errores frecuentes

### El informe dice que hay varias cuentas

Probablemente activaste videos relacionados, utilizaste una busqueda o exportaste varios perfiles. Repite el scrape con una cuenta o ejecuta:

```powershell
python analyze.py data\input\archivo.json --account usuario
```

### Solo aparece un video

Clockworks usa `resultsPerPage` como numero de videos por perfil y su valor predeterminado puede ser muy bajo. Escribe expresamente `100`, `500` o el limite que necesites.

### Faltan guardados o musica

Algunos scrapers o posts no devuelven todos los campos. El informe mide su cobertura y deja en blanco las metricas no calculables; no convierte silenciosamente los datos ausentes en cero.

### El CSV pierde hashtags

Usa JSON. El lector admite campos aplanados de CSV, pero JSON conserva mejor listas y objetos anidados.

