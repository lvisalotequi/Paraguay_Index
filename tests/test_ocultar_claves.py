"""Pruebas del ocultamiento de claves (consola y pipeline_log) y del estado "OK con omitidos" (sin red ni Sheets)."""
import io
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

REPO = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO)

CLAVE = "AbCdEf0123456789ZzYyXxWwVvUu"  # clave de mentira, con la forma de las reales


class PruebasOcultar(unittest.TestCase):
    def test_tapa_api_key_en_la_url_de_un_httperror(self):
        from src.entorno import ocultar_claves

        texto = f"HTTPError('401 Client Error: Unauthorized for url: https://api.govinfo.gov/search?api_key={CLAVE}%0A')"
        salida = ocultar_claves(texto)
        self.assertNotIn(CLAVE, salida)
        self.assertIn("api_key=***", salida)
        self.assertIn("https://api.govinfo.gov/search", salida)  # el resto del mensaje se conserva

    def test_tapa_la_clave_dentro_del_repr_escapado_de_un_diccionario(self):
        from src.entorno import ocultar_claves

        errores = {"congreso": f"HTTPError('401 for url: https://x.gov/search?api_key={CLAVE}&page=1')",
                   "fa": "RuntimeError('4 archivos fallaron: [(\\'a\\', \"HTTPError(\\\\\\'403 for url: https://x?userid=" + CLAVE + "\\\\\\')\")]')"}
        salida = ocultar_claves(errores)
        self.assertNotIn(CLAVE, salida)
        self.assertIn("&page=1", salida)  # lo que viene despues de la clave no se come

    def test_tapa_userid_de_bea(self):
        from src.entorno import ocultar_claves

        url = f"https://apps.bea.gov/api/data?UserID={CLAVE}&method=GETDATA&DatasetName=MNE"
        salida = ocultar_claves(url)
        self.assertNotIn(CLAVE, salida)
        self.assertIn("UserID=***&method=GETDATA", salida)

    def test_tapa_el_valor_exacto_de_los_secrets_aunque_no_vaya_en_una_url(self):
        from urllib.parse import quote

        from src.entorno import ocultar_claves

        with mock.patch.dict(os.environ, {"CONGRESS_API_KEY": CLAVE + "\n", "BEA_API_KEY": "clave con espacio/1234"}):
            self.assertNotIn(CLAVE, ocultar_claves(f"la clave es {CLAVE}"))
            self.assertNotIn("clave con espacio/1234", ocultar_claves("x clave con espacio/1234 y"))
            self.assertNotIn(quote("clave con espacio/1234", safe=""), ocultar_claves(quote("clave con espacio/1234", safe="")))

    def test_no_tapa_valores_cortos_ni_texto_comun(self):
        from src.entorno import ocultar_claves

        with mock.patch.dict(os.environ, {"CONGRESS_API_KEY": "abc"}):
            self.assertEqual(ocultar_claves("abc de abecedario"), "abc de abecedario")
        self.assertEqual(ocultar_claves("monkey=banana, page=2"), "monkey=banana, page=2")

    def test_tapa_bearer_y_clave_privada(self):
        from src.entorno import ocultar_claves

        self.assertNotIn("tok3n.abc-123", ocultar_claves("Authorization: Bearer tok3n.abc-123"))
        pem = "-----BEGIN PRIVATE KEY-----\nMIIEvQ\nxyz\n-----END PRIVATE KEY-----"
        salida = ocultar_claves(f"credenciales: {pem} fin")
        self.assertNotIn("MIIEvQ", salida)
        self.assertIn("fin", salida)


class PruebasFiltroDeConsola(unittest.TestCase):
    def test_lo_impreso_sale_sin_la_clave_y_el_filtro_no_se_apila(self):
        from src.entorno import _FiltroDeClaves, instalar_filtro_en_consola

        original_out, original_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        try:
            instalar_filtro_en_consola()
            instalar_filtro_en_consola()
            self.assertIsInstance(sys.stdout, _FiltroDeClaves)
            self.assertNotIsInstance(sys.stdout._destino, _FiltroDeClaves)  # no se envuelve dos veces
            print(f"url: https://x.gov?api_key={CLAVE}&z=1")
            print(f"error: UserID={CLAVE}", file=sys.stderr)
            sys.stdout.flush()  # los atributos del flujo original siguen disponibles
            salida, error = sys.stdout._destino.getvalue(), sys.stderr._destino.getvalue()
        finally:
            sys.stdout, sys.stderr = original_out, original_err
        self.assertNotIn(CLAVE, salida + error)
        self.assertIn("api_key=***&z=1", salida)


class WsFalso:
    def __init__(self):
        self.filas = []

    def append_row(self, fila):
        self.filas.append(fila)


class PruebasLogDelSheet(unittest.TestCase):
    def _registrar(self, modules_run, errors):
        from src import sheets

        ws = WsFalso()
        hoja = mock.Mock()
        hoja.worksheet.return_value = ws
        ahora = datetime.now(timezone.utc)
        with mock.patch.object(sheets, "_spreadsheet", return_value=hoja):
            sheets.append_log_row(started=ahora, finished=ahora, modules_run=modules_run, errors=errors)
        return ws.filas[0]

    def test_estado_ok_ok_con_omitidos_y_error(self):
        self.assertEqual(self._registrar(["a", "b"], {})[4], "OK")
        self.assertEqual(self._registrar(["a", "b (omitido)"], {})[4], "OK con omitidos")
        self.assertEqual(self._registrar(["a (reintento) (omitido)"], {})[4], "OK con omitidos")
        self.assertEqual(self._registrar(["a", "b (omitido)"], {"c": "boom"})[4], "ERROR")  # el error manda

    def test_la_clave_no_llega_al_sheet_aunque_el_llamador_no_la_tape(self):
        fila = self._registrar(["a"], {"congreso": f"HTTPError('401 for url: https://x.gov?api_key={CLAVE}%0A')"})
        self.assertNotIn(CLAVE, " ".join(str(c) for c in fila))
        self.assertIn("api_key=***", fila[3])


class PruebasPipeline(unittest.TestCase):
    def test_run_pipeline_registra_el_error_sin_la_clave(self):
        import run_pipeline

        class Roto:
            DIMENSION = "d"

            def run(self):
                raise RuntimeError(f"401 Client Error: Unauthorized for url: https://x.gov/search?api_key={CLAVE}%0A")

        registro = {}
        salida, error = io.StringIO(), io.StringIO()
        original = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = salida, error  # lo que imprime run() con el error, sin el filtro global
        try:
            with mock.patch.object(run_pipeline, "discover_ingestion_modules", return_value=["roto"]), \
                 mock.patch.object(run_pipeline.importlib, "import_module", lambda n: Roto()), \
                 mock.patch.object(run_pipeline, "write_dataframe", lambda t, df: None), \
                 mock.patch.object(run_pipeline, "append_log_row", lambda **k: registro.update(log=k)), \
                 mock.patch.dict(os.environ, {"GITHUB_OUTPUT": os.devnull}):
                with self.assertRaises(SystemExit):
                    run_pipeline.run()
        finally:
            sys.stdout, sys.stderr = original
        self.assertNotIn(CLAVE, str(registro["log"]["errors"]))
        self.assertIn("api_key=***", str(registro["log"]["errors"]))
        self.assertNotIn(CLAVE, error.getvalue())


if __name__ == "__main__":
    unittest.main()
