"""Pruebas del dashboard interno (HTML autosuficiente + web app de Apps Script), sin red ni Drive.

Fijan los errores que aparecieron al armarlo:
  - el HTML no debe pedir archivos hermanos (en Apps Script ninguna ruta relativa existe),
  - el runtime necesita window.__resources (si no, relee su propia pagina y corrompe la plantilla),
  - Codigo.gs no puede llevar los separadores U+2028/U+2029 como caracter real (rompen el literal de regex),
  - lo que Codigo.gs y construir_dashboard.py acuerdan (nombre del archivo, marcador, columnas) debe coincidir.
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CARPETA = REPO / "dashboard_interno"
CONSTRUCTOR = CARPETA / "construir_dashboard.py"
CODIGO_GS = CARPETA / "apps_script" / "Codigo.gs"
MANIFIESTO = CARPETA / "apps_script" / "appsscript.json"
SALIDA = CARPETA / "salida" / "dashboard.html"
FUENTES = [
    REPO / "dashboard" / "US-PY Engagement Index.dc.html",
    REPO / "dashboard" / "support.js",
    REPO / "dashboard" / "exportar_datos.py",
]

COMILLA = "[" + chr(34) + chr(39) + "]"  # comilla simple o doble, sin barras invertidas


def valor_de(texto, nombre):
    """Valor de una constante de texto (NOMBRE = 'valor' en JS o NOMBRE = "valor" en Python)."""
    m = re.search(nombre + " = " + COMILLA + "([^" + chr(34) + chr(39) + "]+)" + COMILLA, texto)
    assert m, f"no encuentro {nombre}"
    return m.group(1)


def lista_de(texto, nombre):
    """Textos entre comillas de la lista NOMBRE = [ ... ]."""
    m = re.search(nombre + r" = \[(.*?)\]", texto, flags=re.S)
    assert m, f"no encuentro {nombre}"
    return re.findall(COMILLA + "([^" + chr(34) + chr(39) + "]+)" + COMILLA, m.group(1))


class PruebasHtmlAutosuficiente(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.antes = [f.read_bytes() for f in FUENTES]
        cls.corrida = subprocess.run(
            [sys.executable, str(CONSTRUCTOR), "--sin-subir"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        cls.html = SALIDA.read_text(encoding="utf-8") if cls.corrida.returncode == 0 else ""

    def test_el_constructor_termina_bien(self):
        self.assertEqual(self.corrida.returncode, 0, self.corrida.stdout + self.corrida.stderr)

    def test_no_modifica_el_dashboard_original(self):
        self.assertEqual([f.read_bytes() for f in FUENTES], self.antes)

    def test_el_marcador_de_datos_esta_una_sola_vez(self):
        marca = valor_de(CONSTRUCTOR.read_text(encoding="utf-8"), "MARCA_DATOS")
        self.assertEqual(self.html.count(marca), 1)

    def test_no_pide_archivos_hermanos(self):
        sin_scripts = re.sub(r"<script\b[^>]*>.*?</script>", "", self.html, flags=re.S)
        self.assertNotRegex(sin_scripts, r'(?:src|href)="(?:\./|_ds/|assets/)')
        self.assertNotIn("support.js", sin_scripts)

    def test_lee_los_datos_inyectados_y_no_por_red(self):
        linea = re.search(r"^function leerCSV.*$", self.html, flags=re.M).group(0)
        self.assertIn("window.__USPY_DATOS", linea)
        self.assertNotIn("XMLHttpRequest", linea)

    def test_el_runtime_no_relee_su_propia_pagina(self):
        # sin esto, el "<x-dc>" que hay dentro de support.js se tomaria como inicio de la plantilla
        self.assertLess(self.html.index("window.__resources={}"), self.html.index('"use strict"'))

    def test_los_parametros_de_la_direccion_salen_de_la_variable_inyectada(self):
        # dentro de Apps Script location.search va vacio: el idioma (?lang=) llega por la variable que inyecta el web app
        self.assertNotIn("new URLSearchParams(location.search)", self.html)
        parcheada = "new URLSearchParams(window.__USPY_BUSQUEDA!==undefined?window.__USPY_BUSQUEDA:location.search)"
        self.assertEqual(self.html.count(parcheada), 2)  # urlDe() y la eleccion del idioma

    def test_no_incrusta_las_fuentes_del_sistema_de_diseno(self):
        # el dashboard usa Barlow (Google Fonts); incrustar Geologica sumaria ~3 MB sin que se vea
        self.assertNotIn("@font-face{font-family:" + chr(34) + "Geologica", self.html)
        self.assertIn('--font-sans:"Barlow"', self.html)


class PruebasWebApp(unittest.TestCase):
    def test_codigo_gs_sin_separadores_unicode_reales(self):
        texto = CODIGO_GS.read_text(encoding="utf-8")
        self.assertNotIn(chr(0x2028), texto)
        self.assertNotIn(chr(0x2029), texto)

    def test_el_nombre_del_archivo_y_el_marcador_coinciden_con_el_constructor(self):
        gs = CODIGO_GS.read_text(encoding="utf-8")
        py = CONSTRUCTOR.read_text(encoding="utf-8")
        self.assertEqual(valor_de(gs, "NOMBRE_ARCHIVO"), valor_de(py, "NOMBRE_ARCHIVO"))
        self.assertEqual(valor_de(gs, "MARCA_DATOS"), valor_de(py, "MARCA_DATOS"))

    def test_las_columnas_obligatorias_coinciden_con_exportar_datos(self):
        gs = lista_de(CODIGO_GS.read_text(encoding="utf-8"), "const COLUMNAS_OBLIGATORIAS")
        py = lista_de((REPO / "dashboard" / "exportar_datos.py").read_text(encoding="utf-8"), "COLUMNAS_OBLIGATORIAS")
        self.assertEqual(gs, py)

    def test_las_pestanas_coinciden_con_exportar_datos(self):
        gs = CODIGO_GS.read_text(encoding="utf-8")
        py = (REPO / "dashboard" / "exportar_datos.py").read_text(encoding="utf-8")
        for pestana in lista_de(py, "PESTANAS"):
            self.assertIn(pestana, gs)

    def test_el_manifiesto_es_valido(self):
        m = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
        self.assertEqual(m["webapp"], {"executeAs": "USER_DEPLOYING", "access": "DOMAIN"})
        self.assertEqual(m["runtimeVersion"], "V8")

    def test_los_permisos_alcanzan_para_lo_que_usa_codigo_gs(self):
        # SpreadsheetApp exige el permiso completo "spreadsheets": con "spreadsheets.readonly" falla
        # («Los permisos especificados no son suficientes para llamar a SpreadsheetApp.openById»)
        gs = CODIGO_GS.read_text(encoding="utf-8")
        permisos = set(json.loads(MANIFIESTO.read_text(encoding="utf-8"))["oauthScopes"])
        base = "https://www.googleapis.com/auth/"
        self.assertIn("SpreadsheetApp.", gs)
        self.assertIn(base + "spreadsheets", permisos)
        self.assertNotIn(base + "spreadsheets.readonly", permisos)  # sobra: el completo ya lo incluye
        self.assertIn("DriveApp.", gs)
        self.assertIn(base + "drive.readonly", permisos)
        self.assertIn("Session.getActiveUser", gs)
        self.assertIn(base + "userinfo.email", permisos)

    def test_codigo_gs_solo_lee_el_sheet(self):
        # el permiso "spreadsheets" tambien permite escribir: Codigo.gs no debe hacerlo nunca
        gs = CODIGO_GS.read_text(encoding="utf-8")
        for escritura in (".setValue", ".setValues", ".appendRow", ".clear(", ".deleteRow", ".insertRow",
                          ".setFormula", ".insertSheet", ".deleteSheet", ".setFrozen"):
            self.assertNotIn(escritura, gs, escritura)


class PruebasAcceso(unittest.TestCase):
    """Contraseña y código de acceso: lo que hace que la pantalla de acceso proteja de verdad y no solo lo parezca."""

    @classmethod
    def setUpClass(cls):
        cls.gs = CODIGO_GS.read_text(encoding="utf-8")

    def funcion(self, nombre):
        return re.search(r"^function " + nombre + r".*?^}", self.gs, flags=re.S | re.M).group(0)

    def test_doget_solo_entrega_la_pantalla_de_acceso(self):
        # si doGet sirviera el dashboard, la pantalla de acceso se podria saltar
        cuerpo = self.funcion("doGet")
        for prohibido in ("leerDatos_", "inyectarDatos_", "armarDashboard_", "SpreadsheetApp", "DriveApp", "getBlob"):
            self.assertNotIn(prohibido, cuerpo, prohibido)
        self.assertIn("paginaAcceso_", cuerpo)

    def test_solo_doget_y_entrar_son_llamables_desde_el_navegador(self):
        # google.script.run no puede llamar a las funciones que terminan en guion bajo
        nombres = re.findall(r"^function ([A-Za-z0-9_]+)", self.gs, flags=re.M)
        self.assertEqual(sorted(n for n in nombres if not n.endswith("_")), ["doGet", "entrar"])

    def test_entrar_valida_antes_de_armar_el_dashboard_y_es_el_unico_que_lo_arma(self):
        # entrar() es publica: no puede confiar en que doGet() ya comprobo algo
        cuerpo = self.funcion("entrar")
        orden = [cuerpo.index(x) for x in ("problemaConfiguracion_", "comprobarPersona_", "verificar_", "armarDashboard_")]
        self.assertEqual(orden, sorted(orden))
        self.assertEqual(self.gs.count("armarDashboard_("), 2)  # su definicion y la llamada de entrar()

    def test_el_formulario_no_envia_la_contrasena_por_la_direccion(self):
        self.assertIn('onsubmit="return false"', self.gs)
        for campo in re.findall(r"<input [^>]*>", self.gs):
            self.assertNotIn(" name=", campo)

    def test_no_registra_la_contrasena(self):
        self.assertNotIn("Logger.", self.gs)
        self.assertNotIn("console.", self.gs)

    def test_los_limites_son_razonables(self):
        def numero(nombre):
            return int(re.search(r"const " + nombre + r" = (\d+);", self.gs).group(1))

        self.assertGreaterEqual(numero("MIN_CLAVE"), 8)
        self.assertGreaterEqual(numero("MIN_CODIGO"), 4)
        self.assertLessEqual(numero("MAX_INTENTOS"), 10)
        # CacheService no acepta mas de 21600 s (6 h) de vencimiento
        self.assertTrue(300 <= numero("BLOQUEO_SEGUNDOS") <= 21600)


if __name__ == "__main__":
    unittest.main()
