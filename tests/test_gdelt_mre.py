"""Pruebas con BigQuery/Drive/Sheets simulados de la automatizacion de GDELT y MRE."""
import io
import sys
from pathlib import Path
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest import mock

REPO = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO)

from src.ingestion import _gdelt_auto as g  # noqa: E402

GIB = 1024**3


class PruebasCalendario(unittest.TestCase):
    def test_meses_cubiertos_expande_rangos(self):
        c = g.meses_cubiertos(["monthly_2015-02_2015-04.csv", "monthly_2026-01_2026-01.csv",
                               "historical_processed_2015-02_2026-01.csv", "monthly_2025-01_2025-01_pilot4d.csv", "otro.csv"])
        self.assertEqual(c, {"2015-02", "2015-03", "2015-04", "2026-01"})

    def test_ultimo_mes_extraible_respeta_el_margen(self):
        self.assertEqual(g.ultimo_mes_extraible(date(2026, 10, 23)), date(2026, 9, 1))
        self.assertEqual(g.ultimo_mes_extraible(date(2026, 10, 2)), date(2026, 8, 1))  # 1-2 de octubre: septiembre aun no
        self.assertEqual(g.ultimo_mes_extraible(date(2026, 10, 4)), date(2026, 9, 1))
        self.assertEqual(g.ultimo_mes_extraible(date(2026, 1, 2)), date(2025, 11, 1))  # cruce de año

    def test_meses_faltantes_de_hoy(self):
        # lo que realmente hay en Drive: feb-2015 a ene-2026
        nombres = ["monthly_2015-02_2025-12.csv", "monthly_2026-01_2026-01.csv"]
        falt = g.meses_faltantes(g.meses_cubiertos(nombres), date(2026, 10, 23))
        self.assertEqual([m.strftime("%Y-%m") for m in falt], [f"2026-{m:02d}" for m in range(2, 10)])

    def test_sin_faltantes(self):
        self.assertEqual(g.meses_faltantes(g.meses_cubiertos(["monthly_2015-02_2026-09.csv"]), date(2026, 10, 23)), [])

    def test_hueco_en_el_medio_tambien_se_detecta(self):
        falt = g.meses_faltantes(g.meses_cubiertos(["monthly_2015-02_2015-05.csv", "monthly_2015-07_2015-08.csv"]), date(2015, 9, 20))
        self.assertEqual([m.strftime("%Y-%m") for m in falt], ["2015-06"])


class PruebasRegistro(unittest.TestCase):
    def test_uso_del_mes(self):
        reg = [{"mes_calendario": "2026-10", "gib_facturados": "7.5"}, {"mes_calendario": "2026-10", "gib_facturados": 2},
               {"mes_calendario": "2026-09", "gib_facturados": 100}, {"mes_calendario": "2026-10", "gib_facturados": ""}]
        self.assertAlmostEqual(g.gib_usados_en_el_mes(reg, "2026-10"), 9.5)

    def test_fila_de_registro(self):
        f = g.fila_de_registro("2026-02", "job1", 8 * GIB, 8 * GIB + 1024, "abc", "github_actions", "completado",
                               ahora=datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(len(f), len(g.ENCABEZADO_REGISTRO))
        self.assertEqual(f[6], "2026-10")
        self.assertEqual(f[1], "2026-02")

    def test_tope_de_la_consulta(self):
        self.assertEqual(g.tope_de_la_consulta(1, 20 * GIB), 10 * 1024**2)
        self.assertEqual(g.tope_de_la_consulta(7 * GIB + 5, 20 * GIB), 7 * GIB + 1024**2)
        self.assertEqual(g.tope_de_la_consulta(50 * GIB, 20 * GIB), 20 * GIB)


class JobFalso:
    def __init__(self, bytes_):
        self.total_bytes_processed = bytes_
        self.total_bytes_billed = bytes_

    def result(self):
        import pandas as pd

        class R:
            def to_dataframe(self, create_bqstorage_client=False):
                return pd.DataFrame({"month": ["2026-02-01", "2026-02-01"], "source_country": ["PY", "BOTH"], "proxy_articles": [3, 5]})

        return R()


class ClienteFalso:
    def __init__(self, estimado=8 * GIB):
        self.estimado = estimado
        self.enviados = []
        self.dry_runs = 0

    def query(self, sql, job_config=None, job_id=None, job_retry=None):
        if job_config is not None and job_config.dry_run:
            self.dry_runs += 1
            return SimpleNamespace(total_bytes_processed=self.estimado)
        if job_id in [j for j, _ in self.enviados]:
            from google.api_core.exceptions import Conflict

            raise Conflict("ya existe")
        self.enviados.append((job_id, job_config.maximum_bytes_billed))
        return JobFalso(self.estimado)

    def get_job(self, job_id, location=None):
        return JobFalso(self.estimado)


class PruebasActualizar(unittest.TestCase):
    NOMBRES = ["monthly_2015-02_2025-12.csv", "monthly_2026-01_2026-01.csv"]
    HOY = date(2026, 10, 23)

    def correr(self, cliente, registro=None, nombres=None, config_extra=None):
        subidos, filas = {}, []
        config = dict(g.cargar_config(), **(config_extra or {}))
        with mock.patch.object(g, "leer_pestana", return_value=registro or []), \
             mock.patch.object(g, "agregar_filas", lambda tab, enc, f: filas.extend(f)), \
             mock.patch.object(g, "verificar_sin_facturacion"), \
             mock.patch.object(g, "cargar_config", return_value=config):
            res = g.actualizar(lambda n, c: subidos.update({n: c}), nombres or self.NOMBRES, hoy=self.HOY, client=cliente)
        return res, subidos, filas

    def test_extrae_los_8_meses_y_los_registra(self):
        cliente = ClienteFalso()
        (subidos, pendientes), archivos, filas = self.correr(cliente)
        self.assertEqual(subidos, [f"2026-{m:02d}" for m in range(2, 10)])
        self.assertEqual(pendientes, [])
        self.assertEqual(sorted(archivos), [f"monthly_2026-{m:02d}_2026-{m:02d}.csv" for m in range(2, 10)])
        self.assertEqual(len(filas), 8)
        self.assertEqual(cliente.dry_runs, 8)
        # cada archivo es un CSV valido con las columnas del extractor manual
        primero = next(iter(archivos.values())).decode("utf-8-sig")
        self.assertIn("query_bytes_billed", primero.splitlines()[0])
        # el job id es deterministico: mismo mes + mismo sql => mismo id
        self.assertEqual(len({j for j, _ in cliente.enviados}), 8)

    def test_tope_por_corrida_deja_pendientes(self):
        cliente = ClienteFalso()
        (subidos, pendientes), _, _ = self.correr(cliente, config_extra={"per_run_gib": 20})
        self.assertEqual(len(subidos), 2)  # 8 GiB + 8 GiB ; el tercero (24 > 20) ya no entra
        self.assertEqual(pendientes[0], "2026-04")
        self.assertEqual(pendientes[-1], "2026-09")

    def test_tope_mensual_usa_el_registro(self):
        cliente = ClienteFalso()
        mes = datetime.now(timezone.utc).strftime("%Y-%m")
        registro = [{"mes_calendario": mes, "gib_facturados": 845}]
        (subidos, pendientes), _, _ = self.correr(cliente, registro=registro)
        self.assertEqual(subidos, [])
        self.assertEqual(len(pendientes), 8)

    def test_estimacion_sobre_el_tope_por_consulta_falla(self):
        with self.assertRaises(RuntimeError):
            self.correr(ClienteFalso(estimado=25 * GIB))

    def test_sin_pendientes_no_toca_bigquery(self):
        cliente = ClienteFalso()
        (subidos, pendientes), archivos, filas = self.correr(cliente, nombres=["monthly_2015-02_2026-09.csv"])
        self.assertEqual((subidos, pendientes, archivos, filas, cliente.dry_runs), ([], [], {}, [], 0))

    def test_job_ya_enviado_se_recupera_sin_reenviar(self):
        cliente = ClienteFalso()
        cliente.enviados.append(("gdelt_regla_b_2026_09_" + __import__("hashlib").sha256(b"x").hexdigest()[:12], 1))
        # se fuerza el Conflict para el id real del primer mes
        original = cliente.query

        def query(sql, job_config=None, job_id=None, job_retry=None):
            if job_config is not None and not job_config.dry_run and job_id.startswith("gdelt_regla_b_2026_02_"):
                from google.api_core.exceptions import Conflict

                raise Conflict("ya existe")
            return original(sql, job_config=job_config, job_id=job_id, job_retry=job_retry)

        cliente.query = query
        (subidos, _), _, filas = self.correr(cliente)
        self.assertIn("2026-02", subidos)
        self.assertEqual([f[9] for f in filas if f[1] == "2026-02"], ["recuperado"])

    def test_sin_confirmar_facturacion_no_consulta_nada(self):
        cliente = ClienteFalso()
        config = g.cargar_config()
        with mock.patch.object(g, "leer_pestana", return_value=[]), \
             mock.patch.object(g, "agregar_filas"), \
             mock.patch.object(g, "cargar_config", return_value=config), \
             mock.patch.object(g, "verificar_sin_facturacion", side_effect=RuntimeError("no se pudo confirmar")):
            with self.assertRaises(RuntimeError):
                g.actualizar(lambda n, c: None, self.NOMBRES, hoy=self.HOY, client=cliente)
        self.assertEqual((cliente.enviados, cliente.dry_runs), ([], 0))


class PruebasMre(unittest.TestCase):
    def test_modulo_sube_incremental_y_manifiesto(self):
        from src.ingestion import mre_menciones_eeuu as m

        previas_csv = (
            "fecha,mes,titulo,descripcion,texto,url_original,url_consulta,fuente,captura_wayback,menciona_eeuu,"
            "numero_menciones_eeuu,terminos_encontrados,estado,es_bilateral,puntaje_bilateral,nivel_relevancia,tipo_relacion,"
            "actores_detectados,acciones_detectadas,evidencia_clasificacion\n"
            "2026-01-05,2026-01,t,d,texto largo,https://www.mre.gov.py/a,https://www.mre.gov.py/a,actual,,0,0,,fuera_periodo,0,0,sin mención,,,,\n"
        ).encode("utf-8-sig")
        subidas = {}

        def actualizar(previas, cache, *a, **k):
            fila = dict(previas[0], estado="ok")
            return [fila], {"previas": 1, "candidatas_nuevas": 0, "reintentos_de_errores": 0, "errores_resueltos": 0,
                            "reevaluadas_por_periodo": 1, "agregadas": 0, "total": 1}

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "listar_archivos", return_value=[{"id": "1", "name": "noticias_clasificadas_2026-09-22.csv"},
                                                                    {"id": "2", "name": "manifiesto_2026-09-22.json"}]), \
             mock.patch.object(m, "descargar_archivo", return_value=previas_csv), \
             mock.patch.object(m, "subir_si_cambio", lambda c, n, k, mime_type=None: subidas.update({n: c}) or "nuevo"), \
             mock.patch.object(m, "LOCAL_OUTPUT_DIR", m.Path("/no/existe")), \
             mock.patch.dict(sys.modules, {}):
            sys.path.insert(0, str(m.CARPETA_SCRAPER))
            import actualizar_incremental as inc

            with mock.patch.object(inc, "actualizar", actualizar):
                resultado = m.run()
        self.assertIsNone(resultado)
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertEqual(sorted(subidas), [f"manifiesto_{hoy}.json", f"noticias_clasificadas_{hoy}.csv"])
        self.assertIn("ok", subidas[f"noticias_clasificadas_{hoy}.csv"].decode("utf-8-sig"))

    def test_sin_base_en_drive_se_omite(self):
        from src.ingestion import mre_menciones_eeuu as m

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "listar_archivos", return_value=[]), \
             mock.patch.object(m, "LOCAL_OUTPUT_DIR", m.Path("/no/existe")):
            self.assertTrue(m.run().startswith("omitido"))

    def test_sitio_caido_se_omite(self):
        from src.ingestion import mre_menciones_eeuu as m

        sys.path.insert(0, str(m.CARPETA_SCRAPER))
        import actualizar_incremental as inc

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "listar_archivos", return_value=[{"id": "1", "name": "noticias_clasificadas_2026-09-22.csv"}]), \
             mock.patch.object(m, "descargar_archivo", return_value="fecha,url_original,estado\n2026-01-01,https://x/a,ok\n".encode("utf-8-sig")), \
             mock.patch.object(m, "LOCAL_OUTPUT_DIR", m.Path("/no/existe")), \
             mock.patch.object(inc, "actualizar", side_effect=inc.SitioNoAccesible("403")):
            self.assertTrue(m.run().startswith("omitido"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
