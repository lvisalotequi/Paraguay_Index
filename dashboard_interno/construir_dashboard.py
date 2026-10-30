#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# RESPONSABLE DEL CODIGO:                                                      #
#   EQUILIBRIUM BDC - EQUIPO DEL PROYECTO                                      #
#                                                                              #
# FECHA DE CREACION: 29/10/2026                                                #
# NOMBRE: construir_dashboard                                                  #
# DETALLE: Arma una copia AUTOSUFICIENTE del dashboard (un solo HTML, sin      #
#          archivos hermanos) y la sube a Drive, para que el web app de        #
#          Apps Script (dashboard_interno/apps_script/Codigo.gs) la sirva en   #
#          el enlace interno. No modifica nada de dashboard/: lee esos mismos  #
#          archivos y les aplica parches puntuales y verificados, asi el       #
#          enlace interno y el de GitHub Pages muestran siempre el mismo       #
#          dashboard. El HTML sale SIN datos (lleva un marcador): el web app   #
#          los inyecta en cada visita leyendo el Sheet us_py_engagement_index. #
# CORRE DESPUES DE: dashboard/US-PY Engagement Index.dc.html (el diseno)       #
# SALIDA: dashboard_interno/salida/dashboard.html (local) y, en Drive,         #
#         04_final/dashboard_interno/dashboard.html (siempre el mismo archivo) #
# USO: python dashboard_interno/construir_dashboard.py [--sin-subir]           #
#-----------------------------------------------------------------------------.#


# 0. SETUP -----

## 0.1. Entorno ---------------------------------------------------------------------

import base64
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # en GitHub Actions las variables ya vienen puestas
    pass


## 0.2. Rutas y credenciales --------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]

# para poder importar src.drive igual que lo hacen los tests
sys.path.insert(0, str(REPO))

CARPETA_DASHBOARD = REPO / "dashboard"

PAGINA = CARPETA_DASHBOARD / "US-PY Engagement Index.dc.html"

SOPORTE_JS = CARPETA_DASHBOARD / "support.js"

CARPETA_SALIDA = REPO / "dashboard_interno" / "salida"

# la cuenta de servicio (GOOGLE_APPLICATION_CREDENTIALS) solo se usa al subir; ver src/drive.py


## 0.3. Parametros configurables ----------------------------------------------------

# --sin-subir arma el archivo local y no toca Drive (para revisar antes de publicar)
SUBIR_A_DRIVE = "--sin-subir" not in sys.argv

# carpeta de Drive (dentro de 04_final) y nombre fijo del archivo: el web app lo busca por ese nombre
CARPETA_DRIVE = "dashboard_interno"

NOMBRE_ARCHIVO = "dashboard.html"

# solo para avisar el id que va en las propiedades del Apps Script
NOMBRE_SHEET = "us_py_engagement_index"

# donde el web app inyecta los datos de cada visita (ver Codigo.gs, MARCA_DATOS)
MARCA_DATOS = "<!--USPY_DATOS-->"

# sin esta tipografia el dashboard cae a la del sistema de diseno (Geologica), cuyas fuentes NO se incrustan
FUENTE_ESPERADA = '--font-sans:"Barlow"'


#=============================================================================.#
# 1. LEER EL DISENO -----
#=============================================================================.#

def leer(ruta):

    return ruta.read_text(encoding="utf-8")


pagina_raw = leer(PAGINA)

soporte_js_raw = leer(SOPORTE_JS)

print(f"  {PAGINA.name}: {len(pagina_raw):,} caracteres")


#=============================================================================.#
# 2. ARMAR EL HTML AUTOSUFICIENTE -----
#=============================================================================.#

# Cada parche se ancla a un texto exacto del dashboard y exige que aparezca las veces esperadas:
# si el diseno cambia y el ancla ya no calza, se corta aca en vez de publicar una pagina rota.

def reemplazar(texto, patron, nuevo, que, veces=1, banderas=0):

    resultado, n = re.subn(patron, nuevo, texto, flags=banderas)

    if veces is not None and n != veces:

        raise SystemExit(
            f"Parche '{que}': se esperaban {veces} coincidencia(s) y hay {n}. "
            "El dashboard cambio; hay que revisar este parche en construir_dashboard.py."
        )

    print(f"  parche '{que}': {n}")

    return resultado


def js_en_linea(js, que):

    # un </script o un <!-- dentro del JS cortaria o cambiaria el modo de lectura de la etiqueta
    if "</script" in js.lower() or "<!--" in js:

        raise SystemExit(f"{que} contiene '</script' o '<!--': no se puede incrustar tal cual.")

    return js


fuentes_locales_omitidas = []


def css_en_linea(ruta_relativa):

    ruta = Path(ruta_relativa)

    css = leer(CARPETA_DASHBOARD / ruta)

    # styles.css solo importa los tokens: se resuelven en linea
    css = re.sub(
        r'@import url\("([^"]+)"\);?',
        lambda m: css_en_linea((ruta.parent / m.group(1)).as_posix()),
        css,
    )

    # @font-face de archivos locales (Geologica): se omiten. El dashboard usa Barlow desde Google Fonts
    # (ver FUENTE_ESPERADA) y en el sitio original el navegador nunca pidio un .ttf
    css, n = re.subn(r'@font-face\{[^}]*url\("(?!https?:|data:)[^"]+"\)[^}]*\}', "", css)

    fuentes_locales_omitidas.append(n)

    return css


# tipos de imagen que se incrustan (el diseno ya uso SVG y, desde 2026-10-30, tambien PNG para los logos de los socios)
TIPOS_IMAGEN = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def imagen_en_linea(ruta_relativa):

    ruta = CARPETA_DASHBOARD / ruta_relativa

    contenido = ruta.read_bytes()

    return f"data:{TIPOS_IMAGEN[ruta.suffix.lower()]};base64," + base64.b64encode(contenido).decode("ascii")


# Script de descargas: los enlaces "indice_ancho.csv" / "diccionario.csv" de la nota tecnica apuntan a
# datos/*.csv, que en Apps Script no existe. Se atiende el clic con los mismos datos que dibujan la pagina.
SCRIPT_DESCARGAS = """<script>
(function(){
  var CLAVES={'datos/indice_ancho.csv':'ancho','datos/diccionario.csv':'diccionario'};
  document.addEventListener('click',function(e){
    var a=e.target&&e.target.closest?e.target.closest('a[download]'):null;
    if(!a)return;
    var ruta=a.getAttribute('href'),clave=CLAVES[ruta],datos=window.__USPY_DATOS;
    if(!clave||!datos||!datos[clave])return;
    e.preventDefault();
    var url=URL.createObjectURL(new Blob([datos[clave]],{type:'text/csv;charset=utf-8'}));
    var enlace=document.createElement('a');
    enlace.href=url;enlace.download=ruta.split('/').pop();
    document.body.appendChild(enlace);enlace.click();enlace.remove();
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
  },true);
})();
</script>"""


# 1. Cabecera: marcador de datos, atajo del runtime, descargas y el runtime en linea
# window.__resources = {} evita que el runtime vuelva a pedir su propia pagina para releer la plantilla:
# con support.js en linea, ese texto contiene "<x-dc>" (un mensaje de error) y la plantilla saldria corrupta
cabecera = (
    MARCA_DATOS + "\n"
    "<script>window.__resources={};</script>\n"
    + SCRIPT_DESCARGAS + "\n"
    "<script>" + js_en_linea(soporte_js_raw, "support.js") + "</script>"
)

pagina_limpiando = reemplazar(
    pagina_raw,
    r'<script src="\./support\.js"></script>',
    lambda m: cabecera,
    "support.js y cabecera",
)


# 2. Hojas de estilo del sistema de diseno, en linea
pagina_limpiando = reemplazar(
    pagina_limpiando,
    r'<link rel="stylesheet" href="(_ds/[^"]+\.css)">',
    lambda m: f'<style data-origen="{m.group(1)}">{css_en_linea(m.group(1))}</style>',
    "hojas de estilo del sistema de diseno",
    veces=7,
)


# 3. Componentes del sistema de diseno (botones, selectores, pestanas), en linea
pagina_limpiando = reemplazar(
    pagina_limpiando,
    r'<script src="(_ds/[^"]+\.js)"></script>',
    lambda m: "<script>" + js_en_linea(leer(CARPETA_DASHBOARD / m.group(1)), m.group(1)) + "</script>",
    "componentes del sistema de diseno",
)


# 4. Imagenes (logos) en linea, de cualquier tipo y en cualquier cantidad: el diseno puede sumar logos sin que este
#    parche cambie. Lo que quede sin incrustar lo detecta la validacion de abajo ("quedan rutas relativas")
extensiones = "|".join(re.escape(e[1:]) for e in TIPOS_IMAGEN)

pagina_limpiando = reemplazar(
    pagina_limpiando,
    r'src="(assets/[^"]+\.(?:' + extensiones + r'))"',
    lambda m: f'src="{imagen_en_linea(m.group(1))}"',
    "imagenes",
    veces=None,
)


# 5. Datos: leerCSV() lee lo que inyecta el web app en vez de pedir datos/*.csv por XMLHttpRequest
pagina_limpiando = reemplazar(
    pagina_limpiando,
    r"^function leerCSV\(t\)\{.*$",
    lambda m: (
        "function leerCSV(t){const d=window.__USPY_DATOS;"
        "if(!d||typeof d[t]!=='string'||!d[t])"
        "throw new Error('El dashboard no recibio los datos de la pestana '+t+'.');"
        "return parseCSV(d[t]);}"
    ),
    "lectura de datos",
    banderas=re.M,
)


# 6. Parametros de la direccion (?lang=en): dentro de Apps Script la pagina vive en un marco y su
#    location.search va vacio, asi que el web app los entrega en window.__USPY_BUSQUEDA
pagina_limpiando = reemplazar(
    pagina_limpiando,
    r"new URLSearchParams\(location\.search\)",
    lambda m: "new URLSearchParams(window.__USPY_BUSQUEDA!==undefined?window.__USPY_BUSQUEDA:location.search)",
    "parametros de la direccion",
    veces=2,
)

pagina_clean = pagina_limpiando


#=============================================================================.#
# 3. VALIDAR -----
#=============================================================================.#

problemas = []

# 1. El marcador de datos esta una sola vez (el web app lo reemplaza)
if pagina_clean.count(MARCA_DATOS) != 1:

    problemas.append(f"el marcador {MARCA_DATOS} aparece {pagina_clean.count(MARCA_DATOS)} veces, debe ser 1")


# 2. No quedan archivos hermanos por pedir (en Apps Script ninguna ruta relativa existe).
#    Se mira el HTML y el CSS, no el cuerpo de los scripts: el runtime y los componentes traen cadenas
#    con "url(" y rutas de componentes que esta pagina no usa
sin_scripts = re.sub(r"<script\b[^>]*>.*?</script>", "<script></script>", pagina_clean, flags=re.S)

relativas = re.findall(r'(?:src|href)="(?!https?:|data:|#|\{\{|datos/)[^"]*"', sin_scripts)

if relativas:

    problemas.append(f"quedan rutas relativas: {sorted(set(relativas))[:5]}")

# (%23 es "#": el filtro de grano del sistema de diseno apunta a un id dentro de su propio SVG en linea)
locales = re.findall(r'url\((?!["\']?(?:https?:|data:|#|%23))[^)]*\)', sin_scripts)

if locales:

    problemas.append(f"quedan url() locales en el CSS: {sorted(set(locales))[:5]}")

# los unicos datos/ permitidos son los dos enlaces de descarga, que atiende SCRIPT_DESCARGAS
pedidos_datos = set(re.findall(r'["\'](datos/[^"\']+)["\']', pagina_clean))

esperados = {"datos/indice_ancho.csv", "datos/diccionario.csv"}

if not pedidos_datos <= esperados:

    problemas.append(f"hay referencias a datos/ que nadie atiende: {sorted(pedidos_datos - esperados)}")

if "XMLHttpRequest" in re.findall(r"^function leerCSV.*$", pagina_clean, flags=re.M)[0]:

    problemas.append("leerCSV sigue pidiendo los datos por red")


# 3. La tipografia que se usa es la que NO se incrusta (Barlow), no la del sistema de diseno
if FUENTE_ESPERADA not in pagina_clean:

    problemas.append(f"el dashboard ya no declara {FUENTE_ESPERADA}: las fuentes Geologica se omitieron y harian falta")


# 4. Cada </script> cierra un <script> (el JS incrustado puede nombrar "<script" en un texto, eso no cuenta)
pares = len(re.findall(r"<script\b[^>]*>.*?</script>", pagina_clean, flags=re.S))

cerradas = pagina_clean.count("</script>")

if pares != cerradas:

    problemas.append(f"hay {cerradas} </script> y solo {pares} <script> que los abren")


if problemas:

    raise SystemExit("El HTML no es autosuficiente:\n  - " + "\n  - ".join(problemas))


print(f"  fuentes locales omitidas (@font-face): {sum(fuentes_locales_omitidas)}")

print(f"  HTML autosuficiente: {len(pagina_clean.encode('utf-8')) / 1024:,.0f} KB, sin rutas relativas")


#=============================================================================.#
# 4. GUARDAR EN LOCAL -----
#=============================================================================.#

CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

ruta_salida = CARPETA_SALIDA / NOMBRE_ARCHIVO

contenido_bytes = pagina_clean.encode("utf-8")

ruta_salida.write_bytes(contenido_bytes)

# ruta relativa: la de la Unidad compartida lleva emojis y la consola de Windows (cp1252) no los imprime
print(f"  guardado: {ruta_salida.relative_to(REPO).as_posix()}")


#=============================================================================.#
# 5. SUBIR A DRIVE -----
#=============================================================================.#

if not SUBIR_A_DRIVE:

    print("  --sin-subir: no se toca Drive.")

else:

    from src import drive

    # 1. 04_final se busca por nombre y se compara con el id conocido: si no coinciden, se corta
    #    antes de crear nada en una carpeta equivocada
    carpeta_final_id = drive.resolve_etapa_folder(drive.CARPETA_FINAL)

    if drive.resolve_folder(drive.CARPETA_FINAL) != carpeta_final_id:

        raise SystemExit("04_final no coincide con el id guardado en src/drive.py (ETAPA_FOLDER_IDS).")

    # 2. Subcarpeta del dashboard (se crea solo la primera vez) y archivo de nombre fijo (se reemplaza)
    carpeta_dashboard_id = drive.resolve_folder(drive.CARPETA_FINAL, CARPETA_DRIVE)

    archivo_id = drive.subir_o_reemplazar(
        contenido_bytes,
        NOMBRE_ARCHIVO,
        carpeta_dashboard_id,
        mime_type="text/html",
    )

    # 3. Id del Sheet que lee el web app (solo se busca, nunca se crea)
    sheet = next(
        (a for a in drive.listar_archivos(carpeta_final_id) if a["name"] == NOMBRE_SHEET),
        None,
    )

    print(f"  Drive: 04_final/{CARPETA_DRIVE}/{NOMBRE_ARCHIVO} (archivo {archivo_id})")

    print("  Propiedades del script de Apps Script:")

    print(f"    DASHBOARD_CARPETA_ID = {carpeta_dashboard_id}")

    print(f"    INDICE_SHEET_ID      = {sheet['id'] if sheet else '(no se encontro ' + NOMBRE_SHEET + ' en 04_final)'}")
