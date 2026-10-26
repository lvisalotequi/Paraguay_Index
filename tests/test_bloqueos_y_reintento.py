"""Pruebas del diagnostico de bloqueos (403/Cloudflare), del "omitido" de BCP y MRE, de la ruta nueva de
fa_gov y del reintento de run_pipeline.py (no hacen red ni tocan Drive/Sheets)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO)
sys.path.insert(0, str(Path(REPO) / "mre_scraping"))


class Resp:
    def __init__(self, status=200, url="https://sitio.test/x", headers=None, content=b"ok", text="ok"):
        self.status_code = status
        self.url = url
        self.headers = headers or {}
        self.content = content
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP Error {self.status_code}")

    def json(self):
        return {"data": [], "totalCount": 0}


BLOQUEO = dict(status=403, headers={"server": "cloudflare", "cf-mitigated": "challenge", "cf-ray": "abc123",
                                    "content-type": "text/html"}, text="<html><title>Just a moment...</title></html>")


class PruebasDiagnostico(unittest.TestCase):
    def test_diagnostico_trae_url_y_encabezados_de_cloudflare(self):
        from src.ingestion._bloqueo import diagnostico

        texto = diagnostico(Resp(url="https://www.bcp.gov.py/web/x", **BLOQUEO))
        for esperado in ("HTTP 403", "https://www.bcp.gov.py/web/x", "server=cloudflare", "cf-mitigated=challenge",
                         "cf-ray=abc123", "Just a moment"):
            self.assertIn(esperado, texto)

    def test_comprobar_distingue_bloqueo_de_otros_errores(self):
        from src.ingestion._bloqueo import SitioBloqueado, comprobar

        comprobar(Resp(200))  # no lanza
        for status in (403, 429):
            with self.assertRaises(SitioBloqueado):
                comprobar(Resp(status))
        with self.assertRaises(SitioBloqueado):
            comprobar(Resp(200, headers={"cf-mitigated": "challenge"}))
        with self.assertRaises(RuntimeError) as ctx:  # un 404 sigue siendo un error normal
            comprobar(Resp(404))
        self.assertNotIsInstance(ctx.exception, SitioBloqueado)

    def test_comprobar_tolera_respuestas_sin_headers(self):
        from src.ingestion._bloqueo import comprobar

        class Minima:
            status_code = 500
            content = b""

            def raise_for_status(self):
                raise RuntimeError("500")

        with self.assertRaises(RuntimeError):
            comprobar(Minima())

    def test_omitido_por_bloqueo_usa_el_prefijo_que_reintenta_run_pipeline(self):
        from src.ingestion._bloqueo import PREFIJO_OMITIDO_REINTENTABLE, omitido_por_bloqueo

        motivo = omitido_por_bloqueo("bcp_x", "bcp.gov.py", RuntimeError("HTTP 403"))
        self.assertTrue(motivo.startswith(PREFIJO_OMITIDO_REINTENTABLE))
        self.assertIn("sigue vigente", motivo)


class PruebasBcp(unittest.TestCase):
    def setUp(self):
        from src.ingestion import _bcp_common

        self.common = _bcp_common
        mock.patch.object(_bcp_common.time, "sleep").start()
        self.addCleanup(mock.patch.stopall)

    def test_reintenta_si_el_primer_intento_esta_bloqueado(self):
        respuestas = [Resp(**BLOQUEO), Resp(200, content=b"archivo")]
        with mock.patch.object(self.common.requests, "get", side_effect=respuestas) as get:
            self.assertEqual(self.common.descargar_bytes("https://x/a.xlsx"), b"archivo")
        self.assertEqual(get.call_count, 2)

    def test_si_el_bloqueo_sigue_lanza_sitio_bloqueado_con_diagnostico(self):
        from src.ingestion._bloqueo import SitioBloqueado

        with mock.patch.object(self.common.requests, "get", side_effect=lambda *a, **k: Resp(**BLOQUEO)) as get:
            with self.assertRaises(SitioBloqueado) as ctx:
                self.common.obtener_html("https://www.bcp.gov.py/pagina")
        self.assertEqual(get.call_count, self.common.INTENTOS_BLOQUEO)
        self.assertIn("cf-mitigated=challenge", str(ctx.exception))

    def test_los_tres_modulos_devuelven_omitido_y_no_suben_nada(self):
        from src.ingestion import bcp_comercio_exterior, bcp_inversion_directa, bcp_remesas_familiares
        from src.ingestion._bloqueo import PREFIJO_OMITIDO_REINTENTABLE, SitioBloqueado

        for modulo in (bcp_comercio_exterior, bcp_inversion_directa, bcp_remesas_familiares):
            with self.subTest(modulo=modulo.FUENTE):
                # bloqueo al pedir la pagina
                with mock.patch.object(modulo, "resolve_ingestion_folder", return_value="C"), \
                     mock.patch.object(modulo, "_obtener_archivo", side_effect=SitioBloqueado("HTTP 403 | x")), \
                     mock.patch.object(modulo, "subir_si_cambio") as subir:
                    resultado = modulo.run()
                self.assertTrue(resultado.startswith(PREFIJO_OMITIDO_REINTENTABLE))
                subir.assert_not_called()
                # bloqueo al descargar el archivo
                with mock.patch.object(modulo, "resolve_ingestion_folder", return_value="C"), \
                     mock.patch.object(modulo, "_obtener_archivo", return_value=("a.xlsx", "https://x/a.xlsx")), \
                     mock.patch.object(modulo, "descargar_bytes", side_effect=SitioBloqueado("HTTP 403 | x")), \
                     mock.patch.object(modulo, "subir_si_cambio") as subir:
                    resultado = modulo.run()
                self.assertTrue(resultado.startswith(PREFIJO_OMITIDO_REINTENTABLE))
                subir.assert_not_called()

    def test_un_error_que_no_es_bloqueo_sigue_siendo_error(self):
        from src.ingestion import bcp_remesas_familiares as m

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "_obtener_archivo", side_effect=RuntimeError("No se encontro ningun link")):
            with self.assertRaises(RuntimeError):
                m.run()


class PruebasFaGov(unittest.TestCase):
    def test_usa_la_ruta_nueva_de_la_api(self):
        from src.ingestion import fa_gov_asistencia_oficial as m

        self.assertIn("/api/country_dashboard/activities", m.URL_BASE)
        with mock.patch.object(m.requests, "get", return_value=Resp(200)) as get:
            m._pedir_medida(2025, "Obligations")
        self.assertEqual(get.call_args.args[0],
                         "https://foreignassistance.gov/api/country_dashboard/activities/PRY/0/2025/Obligations")

    def test_un_403_sale_como_error_con_diagnostico(self):
        from src.ingestion import fa_gov_asistencia_oficial as m

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "existe_archivo", return_value=True), \
             mock.patch.object(m.requests, "get", side_effect=lambda *a, **k: Resp(**BLOQUEO)):
            with self.assertRaises(RuntimeError) as ctx:
                m.run()
        self.assertIn("cf-mitigated=challenge", str(ctx.exception))


class PruebasMre(unittest.TestCase):
    def test_el_error_del_fetcher_trae_estado_y_cf_mitigated(self):
        import scraper_mre

        sesion = mock.Mock()
        sesion.get.return_value = Resp(url="https://www.mre.gov.py/archivo-de-noticias/", **BLOQUEO)
        with tempfile.TemporaryDirectory() as tmp:
            fetcher = scraper_mre.Fetcher(Path(tmp), 0, 5.0, 0)
            with mock.patch.object(fetcher, "_session", return_value=sesion):
                with self.assertRaises(RuntimeError) as ctx:
                    fetcher.get("https://www.mre.gov.py/archivo-de-noticias/")
        self.assertIn("HTTP 403", str(ctx.exception))
        self.assertIn("cf-mitigated=challenge", str(ctx.exception))

    def test_modulo_mre_devuelve_omitido_reintentable(self):
        from src.ingestion import mre_menciones_eeuu as m
        from src.ingestion._bloqueo import PREFIJO_OMITIDO_REINTENTABLE

        incremental = mock.Mock()

        class SitioNoAccesible(Exception):
            pass

        incremental.SitioNoAccesible = SitioNoAccesible
        incremental.actualizar.side_effect = SitioNoAccesible("HTTP 403 | https://www.mre.gov.py/")
        with mock.patch.object(m, "_base_en_drive", return_value=("noticias_clasificadas_x.csv", [{"a": 1}])), \
             mock.patch.dict(sys.modules, {"actualizar_incremental": incremental}):
            motivo = m._actualizar_incremental("C", "2026-10-26")
        self.assertTrue(motivo.startswith(PREFIJO_OMITIDO_REINTENTABLE))


class PruebasReintentoDelPipeline(unittest.TestCase):
    class Mod:
        DIMENSION = "d"
        DESCRIPCION = "x"
        URL_FUENTE = "u"

        def __init__(self, accion):
            self.accion = accion

        def run(self):
            if isinstance(self.accion, Exception):
                raise self.accion
            return self.accion

    def _correr(self, modulos, entorno=None, previas=None):
        import run_pipeline

        registro = {}
        salida = tempfile.NamedTemporaryFile("w+", suffix=".out", delete=False)
        salida.close()
        env = {"GITHUB_OUTPUT": salida.name}
        env.update(entorno or {})
        codigo = None
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(run_pipeline, "discover_ingestion_modules", return_value=sorted(modulos)), \
             mock.patch.object(run_pipeline.importlib, "import_module", lambda n: modulos[n.rsplit(".", 1)[1]]), \
             mock.patch.object(run_pipeline, "leer_pestana", return_value=previas or []), \
             mock.patch.object(run_pipeline, "write_dataframe", lambda t, df: registro.update(df=df)), \
             mock.patch.object(run_pipeline, "append_log_row", lambda **k: registro.update(log=k)):
            try:
                run_pipeline.run()
            except SystemExit as exc:
                codigo = exc.code
        with open(salida.name, encoding="utf-8") as f:
            registro["salida"] = f.read()
        os.unlink(salida.name)
        registro["codigo"] = codigo
        return registro

    def test_deja_en_la_salida_los_errores_y_los_omitidos_por_bloqueo(self):
        from src.ingestion._bloqueo import PREFIJO_OMITIDO_REINTENTABLE

        modulos = {
            "a_ok": self.Mod(None),
            "b_bloqueado": self.Mod(f"{PREFIJO_OMITIDO_REINTENTABLE} (x): HTTP 403"),
            "c_roto": self.Mod(RuntimeError("boom")),
            "d_omitido_normal": self.Mod("omitido: sin extraccion local"),
        }
        r = self._correr({f"{k}": v for k, v in modulos.items()})
        self.assertEqual(r["salida"].strip(), "modulos_fallidos=b_bloqueado,c_roto")
        self.assertEqual(r["codigo"], 1)  # c_roto es un error real

    def test_sin_fallidos_la_salida_queda_vacia(self):
        r = self._correr({"a": self.Mod(None), "b": self.Mod("omitido: sin extraccion local")})
        self.assertEqual(r["salida"].strip(), "modulos_fallidos=")
        self.assertIsNone(r["codigo"])

    def test_bloqueo_persistente_no_pone_la_corrida_en_rojo(self):
        from src.ingestion._bloqueo import PREFIJO_OMITIDO_REINTENTABLE

        r = self._correr({"bcp": self.Mod(f"{PREFIJO_OMITIDO_REINTENTABLE} (bcp.gov.py): HTTP 403")},
                         entorno={"SOLO_MODULOS": "bcp"})
        self.assertIsNone(r["codigo"])
        self.assertEqual(r["log"]["errors"], {})

    def test_solo_modulos_corre_solo_esos_y_los_marca_como_reintento(self):
        corridos = []

        class Registra(self.Mod):
            def __init__(self, nombre):
                super().__init__(None)
                self.nombre = nombre

            def run(self):
                corridos.append(self.nombre)

        modulos = {n: Registra(n) for n in ("a", "b", "c")}
        r = self._correr(modulos, entorno={"SOLO_MODULOS": "b, c"})
        self.assertEqual(corridos, ["b", "c"])
        self.assertEqual(r["log"]["modules_run"], ["b (reintento)", "c (reintento)"])

    def test_solo_modulos_con_nombre_inexistente_aborta(self):
        r = self._correr({"a": self.Mod(None)}, entorno={"SOLO_MODULOS": "zzz"})
        self.assertIn("no existen", str(r["codigo"]))  # SystemExit con el motivo, antes de correr nada
        self.assertNotIn("log", r)

    def test_el_reintento_conserva_las_filas_del_catalogo_de_los_demas_modulos(self):
        previas = [
            {"fuente": "otro", "dimension": "d", "descripcion": "", "url_fuente": "", "estado_ultima_corrida": "OK",
             "ultima_corrida_utc": "t"},
            {"fuente": "bcp", "dimension": "d", "descripcion": "", "url_fuente": "", "estado_ultima_corrida": "OMITIDO",
             "ultima_corrida_utc": "t"},
        ]
        r = self._correr({"bcp": self.Mod(None)}, entorno={"SOLO_MODULOS": "bcp"}, previas=previas)
        estados = dict(zip(r["df"]["fuente"], r["df"]["estado_ultima_corrida"]))
        self.assertEqual(estados, {"bcp": "OK", "otro": "OK"})  # 'bcp' actualizado, 'otro' intacto


class PruebasWorkflow(unittest.TestCase):
    def test_el_workflow_encadena_ingestion_reintento_y_processing(self):
        import yaml

        wf = yaml.safe_load(Path(REPO, ".github", "workflows", "run_pipeline.yml").read_text(encoding="utf-8"))
        jobs = wf["jobs"]
        self.assertEqual(set(jobs), {"ingestion", "reintento", "processing"})
        self.assertEqual(jobs["reintento"]["needs"], "ingestion")
        self.assertEqual(set(jobs["processing"]["needs"]), {"ingestion", "reintento"})
        paso = next(p for p in jobs["ingestion"]["steps"] if p.get("id") == "ingestion")
        self.assertTrue(paso["continue-on-error"])
        self.assertEqual(jobs["reintento"]["steps"][-1]["env"]["SOLO_MODULOS"],
                         "${{ needs.ingestion.outputs.modulos_fallidos }}")


if __name__ == "__main__":
    unittest.main()
