"""Pruebas de las claves del entorno (salto de linea final) y de la descarga del INE (no hacen red)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO)


class RespuestaFalsa:
    def __init__(self, status=200, contenido=b"datos", headers=None):
        self.status_code = status
        self.content = contenido
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            exc = RuntimeError(f"HTTP Error {self.status_code}")
            exc.response = self
            raise exc


class PruebasClaves(unittest.TestCase):
    def test_leer_clave_quita_saltos_de_linea_y_espacios(self):
        from src.entorno import leer_clave

        with mock.patch.dict(os.environ, {"CLAVE_X": "  abc123\n"}):
            self.assertEqual(leer_clave("CLAVE_X"), "abc123")

    def test_leer_clave_faltante_o_vacia_da_keyerror(self):
        from src.entorno import leer_clave

        with mock.patch.dict(os.environ, {"CLAVE_VACIA": "\n"}):
            with self.assertRaises(KeyError):
                leer_clave("CLAVE_VACIA")
        os.environ.pop("CLAVE_NO_EXISTE", None)
        with self.assertRaises(KeyError):
            leer_clave("CLAVE_NO_EXISTE")

    def test_congreso_no_manda_el_salto_de_linea_en_la_url(self):
        from src.ingestion import congreso_menciones_paraguay as congreso

        with mock.patch.dict(os.environ, {"CONGRESS_API_KEY": "clave-congreso\n"}):
            self.assertEqual(congreso._api_key(), "clave-congreso")

    def test_bea_no_manda_el_salto_de_linea_en_los_parametros(self):
        from src.ingestion import bea_inversion_directa as bea

        capturado = {}

        def falso_get(url, params=None, timeout=None):
            capturado.update(params)
            resp = mock.Mock()
            resp.json.return_value = {"BEAAPI": {"Results": {"Data": []}}}
            return resp

        with mock.patch.dict(os.environ, {"BEA_API_KEY": "clave-bea\n"}), \
             mock.patch.object(bea.requests, "get", falso_get):
            try:
                bea._pedir_datos()
            except Exception:  # noqa: BLE001 - solo interesa lo que se mando
                pass
        self.assertEqual(capturado["UserID"], "clave-bea")

    def test_sheet_id_sin_salto_de_linea(self):
        from src import sheets

        abierto = {}

        class ClienteFalso:
            def open_by_key(self, clave):
                abierto["clave"] = clave
                return "sheet"

        with mock.patch.dict(os.environ, {"SHEET_ID": "id-del-sheet\n"}), \
             mock.patch.object(sheets, "_client", return_value=ClienteFalso()):
            sheets._spreadsheet()
        self.assertEqual(abierto["clave"], "id-del-sheet")


class PruebasDescargaIne(unittest.TestCase):
    def setUp(self):
        from src.ingestion import ine_turismo_receptivo as ine

        self.ine = ine
        self.dormir = mock.patch.object(ine.time, "sleep").start()
        self.addCleanup(mock.patch.stopall)

    def test_usa_timeout_largo(self):
        self.assertGreaterEqual(self.ine.TIMEOUT_DESCARGA, 300)
        with mock.patch.object(self.ine.requests, "get", return_value=RespuestaFalsa()) as get:
            self.ine._descargar("https://x/a.xlsx")
        self.assertEqual(get.call_args.kwargs["timeout"], self.ine.TIMEOUT_DESCARGA)

    def test_reintenta_tras_un_timeout_y_devuelve_el_archivo_completo(self):
        respuestas = [TimeoutError("timeout"), RespuestaFalsa(contenido=b"completo")]
        with mock.patch.object(self.ine.requests, "get", side_effect=respuestas) as get:
            self.assertEqual(self.ine._descargar("https://x/a.xlsx"), b"completo")
        self.assertEqual(get.call_count, 2)

    def test_descarga_cortada_no_se_acepta(self):
        cortada = RespuestaFalsa(contenido=b"123", headers={"content-length": "10"})
        completa = RespuestaFalsa(contenido=b"0123456789", headers={"content-length": "10"})
        with mock.patch.object(self.ine.requests, "get", side_effect=[cortada, completa]):
            self.assertEqual(self.ine._descargar("https://x/a.xlsx"), b"0123456789")

    def test_si_siempre_falla_lanza_error_y_no_devuelve_parcial(self):
        with mock.patch.object(self.ine.requests, "get", side_effect=TimeoutError("timeout")) as get:
            with self.assertRaises(TimeoutError):
                self.ine._descargar("https://x/a.xlsx")
        self.assertEqual(get.call_count, self.ine.INTENTOS)

    def test_un_404_no_se_reintenta(self):
        with mock.patch.object(self.ine.requests, "get", return_value=RespuestaFalsa(status=404)) as get:
            with self.assertRaises(RuntimeError):
                self.ine._descargar("https://x/a.xlsx")
        self.assertEqual(get.call_count, 1)

    def test_un_503_si_se_reintenta(self):
        respuestas = [RespuestaFalsa(status=503), RespuestaFalsa(contenido=b"ok")]
        with mock.patch.object(self.ine.requests, "get", side_effect=respuestas) as get:
            self.assertEqual(self.ine._descargar("https://x/a.xlsx"), b"ok")
        self.assertEqual(get.call_count, 2)

    def test_run_no_sube_archivo_parcial_si_un_año_falla(self):
        ine = self.ine
        with mock.patch.object(ine, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(ine, "existe_archivo", return_value=False), \
             mock.patch.object(ine, "_descargar", side_effect=TimeoutError("timeout")), \
             mock.patch.object(ine, "subir_archivo") as subir:
            with self.assertRaises(RuntimeError):
                ine.run()
        subir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
