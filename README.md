# TikTok Account Analytics

Analiza cualquier cuenta publica de TikTok a partir de los posts descargados con Apify. No necesitas modificar el codigo: deja el JSON o CSV en `data/input`, ejecuta el analisis y obtendras un informe HTML autocontenido y tablas listas para Power BI.

El proyecto esta pensado para Windows y para usuarios sin experiencia previa en Python.

## Que genera

- `report.html`: informe visual que se abre en el navegador y funciona sin internet.
- `cleaned_videos.csv`: una fila limpia y deduplicada por video.
- `power_bi_manifest.csv`: indice de todas las tablas y su nivel de detalle.
- `tables/*.csv`: tablas independientes para hashtags, musica, frecuencia, duracion, horarios, engagement y calidad.
- `data_quality.json`: campos detectados, duplicados, filas excluidas y esquema de origen.
- `analysis_manifest.json`: archivo de entrada, hash, parametros y version para poder reproducir el resultado.

## Inicio rapido en Windows

### 1. Descarga el proyecto

En GitHub, pulsa **Code → Download ZIP** y descomprime el archivo. No ejecutes los `.bat` dentro del ZIP sin descomprimirlo.

### 2. Instala Python

Instala [Python 3.11 o superior](https://www.python.org/downloads/). En la primera pantalla del instalador marca **Add python.exe to PATH**.

### 3. Prepara la herramienta una sola vez

Abre la carpeta descomprimida y haz doble clic en:

```text
setup_windows.bat
```

Se creara un entorno aislado en `.venv` y se instalaran las dependencias. Cuando aparezca `INSTALACION COMPLETADA`, puedes cerrar la ventana.

### 4. Descarga los posts de Apify

Sigue la guia exacta de [docs/APIFY_GUIDE.md](docs/APIFY_GUIDE.md). Descarga **JSON** si puedes; CSV tambien funciona.

### 5. Copia el archivo

Copia el archivo descargado, sin cambiar su contenido, dentro de:

```text
data\input
```

### 6. Ejecuta el analisis

Haz doble clic en:

```text
run_analysis.bat
```

La herramienta usa automaticamente el JSON/JSONL/CSV mas reciente de `data/input`. Al terminar abrira `report.html` y mostrara la carpeta exacta de resultados.

### 7. Encuentra los resultados

Cada ejecucion crea una carpeta independiente:

```text
output\nombre-cuenta_YYYYMMDD_HHMMSS\
```

Esto evita borrar analisis anteriores.

## Configuracion recomendada en Apify

Este proyecto se ha validado con:

- [Clockworks TikTok Scraper](https://apify.com/clockworks/tiktok-scraper), tanto JSON anidado como CSV aplanado.
- El esquema de [ApiDojo TikTok Scraper](https://apify.com/apidojo/tiktok-scraper).

Configuracion recomendada para Clockworks:

```json
{
  "profiles": ["nombre_de_la_cuenta"],
  "resultsPerPage": 500,
  "profileScrapeSections": ["videos"],
  "profileSorting": "latest",
  "excludePinnedPosts": false,
  "scrapeRelatedVideos": false,
  "commentsPerPost": 0,
  "shouldDownloadVideos": false,
  "shouldDownloadCovers": false,
  "shouldDownloadSlideshowImages": false,
  "shouldDownloadAvatars": false,
  "shouldDownloadMusicCovers": false
}
```

Cambia `nombre_de_la_cuenta` por el usuario sin `@`. `resultsPerPage` es el numero maximo de posts que quieres descargar por perfil. Apify admite hasta 1.000.000, pero el coste y el tiempo aumentan con los resultados. Para un primer analisis suelen bastar entre 100 y 500; para estudiar toda la historia, usa un limite que cubra todos los posts.

## Metricas principales

Incluye todo lo que se analizo inicialmente en HomesForYou y varias metricas adicionales:

- Cantidad de videos por semana frente a views totales y mediana de views por video.
- Mediana de views por numero exacto de hashtags y por rangos.
- Rendimiento de cada hashtag, exigiendo un minimo de videos.
- Mediana de views por tipo de musica y por sonido concreto.
- Elasticidad de comentarios frente a views para comprobar si los comentarios crecen mas despacio.
- Likes, comentarios, compartidos y guardados por cada 1.000 views.
- Duracion, formato, longitud del caption, dia y hora de publicacion.
- Tiempo desde la publicacion anterior y frecuencia semanal.
- Tendencia mensual y views por dia desde la publicacion.
- Tasa de videos que duplican la mediana.
- Porcentaje de views concentrado en el 10% de mejores videos.
- Deteccion de duplicados, campos ausentes, valores invalidos y mezcla de cuentas.

Las formulas y cautelas estan documentadas en [docs/METRIC_DICTIONARY.md](docs/METRIC_DICTIONARY.md).

## Usar una ruta concreta o varias cuentas

Desde PowerShell, situado en la carpeta del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
python analyze.py "C:\Users\TU_USUARIO\Downloads\dataset.json" --open-report
```

Si el archivo incluye varias cuentas, la herramienta se detiene para evitar mezclarlas. Elige una:

```powershell
python analyze.py "data\input\dataset.json" --account nombre_de_la_cuenta --open-report
```

Otras opciones utiles:

```powershell
python analyze.py --timezone Europe/Madrid --min-group-size 3 --as-of 2026-07-13
```

- `--timezone`: convierte las fechas antes de calcular dia y hora.
- `--min-group-size`: minimo de videos para mostrar hashtags, sonidos y grupos.
- `--as-of`: fija la fecha de observacion para reproducir `views_per_day`.
- `--debug`: muestra el detalle tecnico si ocurre un error.

## Probar sin datos reales

```powershell
.\.venv\Scripts\Activate.ps1
python examples\generate_sample.py
python analyze.py examples\sample_clockworks.json --as-of 2025-06-01 --open-report
```

El ejemplo es completamente sintetico.

## Llevar los resultados a Power BI

1. Abre Power BI Desktop.
2. Selecciona **Obtener datos → Texto/CSV**.
3. Empieza por `cleaned_videos.csv` para graficos a nivel de video.
4. Usa `power_bi_manifest.csv` para saber que contiene cada tabla.
5. Para los analisis ya agregados, importa los CSV de `tables`.
6. No sumes de nuevo `median_views`: ya es una medida agregada. En Power BI usa **No resumir** cuando muestres ese campo por categoria.

## Privacidad y seguridad

`data/input` y `output` estan incluidos en `.gitignore`. Los datos reales y los informes no se suben a GitHub con un commit normal. No uses `git add -f` sobre esas carpetas.

Apify obtiene datos publicos, pero el resultado puede contener informacion personal. Utilizalo con una finalidad legitima y respetando la normativa y las condiciones aplicables.

## Verificacion

Ejecuta las pruebas automaticas desde la raiz:

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

Las pruebas cubren Clockworks anidado, CSV con campos aplanados, ApiDojo, deduplicacion, elasticidad, frecuencia y una ejecucion completa con informe.

