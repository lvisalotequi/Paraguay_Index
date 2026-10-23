"""Pruebas con Drive simulado de los cambios de la rama Pruebas-de-ajuste (no tocan Drive real)."""
import hashlib
import sys
from pathlib import Path
import unittest
from datetime import datetime, timezone
from unittest import mock

REPO = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO)


class DriveFalso:
    """Imita lo minimo de src.drive: carpeta -> {nombre: bytes}."""

    def __init__(self):
        self.archivos = {}
        self.llamadas = []

    def buscar(self, drive, nombre, carpeta_id, *a, **k):
        contenido = self.archivos.get((carpeta_id, nombre))
        if contenido is None:
            return None
        return {"id": f"{carpeta_id}/{nombre}", "name": nombre, "md5Checksum": hashlib.md5(contenido).hexdigest()}

    def subir(self, contenido, nombre, carpeta_id, mime_type=None):
        self.llamadas.append(("subir", nombre))
        self.archivos[(carpeta_id, nombre)] = contenido
        return "id"

    def reemplazar(self, drive, file_id, contenido, mime_type):
        carpeta, nombre = file_id.rsplit("/", 1)
        self.llamadas.append(("reemplazar", nombre))
        self.archivos[(carpeta, nombre)] = contenido
        return file_id


class PruebasDrive(unittest.TestCase):
    def test_subir_si_cambio(self):
        from src import drive

        f = DriveFalso()
        with mock.patch.object(drive, "_client", return_value=None), \
             mock.patch.object(drive, "_buscar_hijo_con_reintentos", f.buscar), \
             mock.patch.object(drive, "subir_archivo", f.subir), \
             mock.patch.object(drive, "_reemplazar_contenido", f.reemplazar):
            self.assertEqual(drive.subir_si_cambio(b"v1", "a.json", "C"), "nuevo")
            self.assertEqual(drive.subir_si_cambio(b"v1", "a.json", "C"), "sin_cambios")
            self.assertEqual(drive.subir_si_cambio(b"v2", "a.json", "C"), "actualizado")
            self.assertEqual(f.archivos[("C", "a.json")], b"v2")
            self.assertEqual([x[0] for x in f.llamadas], ["subir", "reemplazar"])

    def test_subir_variable_reemplaza_el_archivo_del_dia(self):
        from src import drive
        from src.processing import _common

        f = DriveFalso()
        with mock.patch.object(drive, "_client", return_value=None), \
             mock.patch.object(drive, "_buscar_hijo_con_reintentos", f.buscar), \
             mock.patch.object(drive, "subir_archivo", f.subir), \
             mock.patch.object(drive, "_reemplazar_contenido", f.reemplazar), \
             mock.patch.object(_common, "resolve_variable_folder", return_value="V"):
            self.assertTrue(_common.subir_variable("dim", "var", {(2025, 1): 1.0}, "USD"))
            self.assertFalse(_common.subir_variable("dim", "var", {(2025, 1): 1.0}, "USD"))  # mismo contenido
            self.assertTrue(_common.subir_variable("dim", "var", {(2025, 1): 1.0, (2025, 2): 2.0}, "USD"))  # crudos nuevos el mismo dia
            self.assertFalse(_common.subir_variable("dim", "var", {}, "USD"))  # sin datos
            nombres = {n for (_, n) in f.archivos}
            self.assertEqual(len(nombres), 1)  # un solo archivo del dia, no duplicados
            contenido = next(iter(f.archivos.values())).decode()
            self.assertIn("2025-Q2", contenido)


class PruebasIngestion(unittest.TestCase):
    def test_fa_gov_refresca_los_dos_ultimos_anios(self):
        from src.ingestion import fa_gov_asistencia_oficial as m

        f = DriveFalso()
        anio = datetime.now(timezone.utc).year
        # todo lo anterior a los 2 ultimos años ya existe en Drive
        for a in range(m.ANIO_MINIMO, anio - 1):
            for medida in m.MEDIDAS:
                f.archivos[("C", f"PRY_{medida}_{a}.json")] = b"[]"
        pedidos = []

        def pedir(a, medida):
            pedidos.append((a, medida))
            return [{"x": a}]

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "existe_archivo", lambda n, c: (c, n) in f.archivos), \
             mock.patch.object(m, "_pedir_medida", pedir), \
             mock.patch.object(m, "subir_si_cambio", lambda c, n, k, mime_type=None: (
                 "sin_cambios" if f.archivos.get((k, n)) == c else
                 ("actualizado" if (k, n) in f.archivos else "nuevo"))):
            m.run()
        self.assertEqual(sorted({a for a, _ in pedidos}), [anio - 1, anio])
        self.assertEqual(len(pedidos), 4)  # 2 años x 2 medidas, ninguno mas

    def test_fa_gov_falla_en_rojo_si_un_archivo_falla(self):
        from src.ingestion import fa_gov_asistencia_oficial as m

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "existe_archivo", return_value=True), \
             mock.patch.object(m, "_pedir_medida", side_effect=RuntimeError("api caida")):
            with self.assertRaises(RuntimeError):
                m.run()

    def test_cuota_bancomundial_suma_el_año_en_vivo_y_nombra_por_corte(self):
        from src.ingestion import cuota_capital_bancomundial as m

        subidos = {}
        vivo = {"anio_fiscal": 2026, "porcentaje_voto": 15.98, "cierre_anio_fiscal": "2026-06-30",
                "url_fuente": "u", "origen": "tabla_vigente_en_vivo"}
        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "_filas_previas_en_drive", return_value=[]), \
             mock.patch.object(m, "_leer_tabla_vigente", return_value=vivo), \
             mock.patch.object(m, "existe_archivo", return_value=False), \
             mock.patch.object(m, "subir_archivo", lambda c, n, k, mime_type=None: subidos.update({n: c})):
            m.run()
        (nombre, contenido), = subidos.items()
        self.assertTrue(nombre.startswith("cuota_capital_bancomundial_verificado_"))
        self.assertTrue(nombre.endswith("_corte_2026-06-30.csv"))
        self.assertGreater(nombre, f"cuota_capital_bancomundial_verificado_{m.FECHA_VERIFICACION}.csv")  # processing lo ve como el mas reciente
        import io
        import pandas as pd
        df = pd.read_csv(io.BytesIO(contenido))
        self.assertIn(2026, df["anio_fiscal"].tolist())
        self.assertEqual(len(df), len(m.HISTORICO) + 1)

    def test_cuota_bancomundial_el_historico_manda_sobre_lo_vivo(self):
        from src.ingestion import cuota_capital_bancomundial as m

        subidos = {}
        vivo = {"anio_fiscal": 2025, "porcentaje_voto": 99.0, "cierre_anio_fiscal": "2025-06-30",
                "url_fuente": "u", "origen": "tabla_vigente_en_vivo"}
        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "_filas_previas_en_drive", return_value=[]), \
             mock.patch.object(m, "_leer_tabla_vigente", return_value=vivo), \
             mock.patch.object(m, "existe_archivo", return_value=False), \
             mock.patch.object(m, "subir_archivo", lambda c, n, k, mime_type=None: subidos.update({n: c})):
            m.run()
        import io
        import pandas as pd
        df = pd.read_csv(io.BytesIO(next(iter(subidos.values()))))
        self.assertEqual(float(df.loc[df["anio_fiscal"] == 2025, "porcentaje_voto"].iloc[0]), 15.79)

    def test_ine_turismo_no_sube_archivo_parcial(self):
        from src.ingestion import ine_turismo_receptivo as m

        class R:
            status_code = 500
            content = b""

            def raise_for_status(self):
                raise RuntimeError("500")

        with mock.patch.object(m, "resolve_ingestion_folder", return_value="C"), \
             mock.patch.object(m, "existe_archivo", return_value=False), \
             mock.patch.object(m.requests, "get", return_value=R()), \
             mock.patch.object(m, "subir_archivo") as sube:
            with self.assertRaises(RuntimeError):
                m.run()
            sube.assert_not_called()


class PruebasPipeline(unittest.TestCase):
    def test_run_pipeline_distingue_omitido_de_ok(self):
        import run_pipeline

        class Mod:
            DIMENSION = "d"
            DESCRIPCION = "x"
            URL_FUENTE = "u"

            def __init__(self, ret):
                self._ret = ret

            def run(self):
                return self._ret

        modulos = {"src.ingestion.a": Mod(None), "src.ingestion.b": Mod("omitido: sin extraccion local")}
        registro = {}
        with mock.patch.object(run_pipeline, "discover_ingestion_modules", return_value=["a", "b"]), \
             mock.patch.object(run_pipeline.importlib, "import_module", lambda n: modulos[n]), \
             mock.patch.object(run_pipeline, "write_dataframe", lambda t, df: registro.update(df=df)), \
             mock.patch.object(run_pipeline, "append_log_row", lambda **k: registro.update(log=k)):
            run_pipeline.run()
        estados = dict(zip(registro["df"]["fuente"], registro["df"]["estado_ultima_corrida"]))
        self.assertEqual(estados, {"a": "OK", "b": "OMITIDO"})
        self.assertIn("b (omitido)", registro["log"]["modules_run"])
        self.assertEqual(registro["log"]["errors"], {})

    def test_run_pipeline_con_error_sale_con_codigo_1(self):
        import run_pipeline

        class Roto:
            DIMENSION = "d"

            def run(self):
                raise RuntimeError("fallo")

        with mock.patch.object(run_pipeline, "discover_ingestion_modules", return_value=["a"]), \
             mock.patch.object(run_pipeline.importlib, "import_module", lambda n: Roto()), \
             mock.patch.object(run_pipeline, "write_dataframe"), \
             mock.patch.object(run_pipeline, "append_log_row"):
            with self.assertRaises(SystemExit) as cm:
                run_pipeline.run()
        self.assertEqual(cm.exception.code, 1)


class PruebasProcessing(unittest.TestCase):
    def test_clave_boletin_ordena_cronologicamente(self):
        from src.processing import compromiso_economico_privado as m

        nombres = [
            "Boletin_Comercio_Exterior_1961_al_4_Trim_2025.xlsx",
            "Boletin_Comercio_Exterior_1961_al_1_Trim_2026.xlsx",
            "Boletin_Comercio_Exterior_1961_al_2_Trim_2026.xlsx",
            "Boletin_Comercio_Exterior_1961_al_3_Trim_2025.xlsx",
        ]
        orden = sorted(({"name": n} for n in nombres), key=m._clave_boletin)
        self.assertEqual(orden[-1]["name"], "Boletin_Comercio_Exterior_1961_al_2_Trim_2026.xlsx")
        # el orden alfabetico (el bug anterior) elegia 4_Trim_2025
        self.assertEqual(sorted(nombres)[-1], "Boletin_Comercio_Exterior_1961_al_4_Trim_2025.xlsx")

    def test_dimension_1_sube_lo_que_pudo_y_avisa_el_error(self):
        from src.processing import compromiso_financiero_oficial as m

        subidas = []
        with mock.patch.object(m, "_extraer_fa_gov", return_value=({(2025, 1): 1}, {(2025, 1): 2})), \
             mock.patch.object(m, "_extraer_exim", side_effect=RuntimeError("sin archivo")), \
             mock.patch.object(m, "_extraer_dfc", return_value=({(2025, 1): 1}, {(2025, 1): 1})), \
             mock.patch.object(m, "_extraer_bid", return_value=({(2025, 1): 1}, {(2025, 1): 1})), \
             mock.patch.object(m, "_extraer_bancomundial", return_value=({(2025, 1): 1}, {(2025, 1): 1})), \
             mock.patch.object(m, "_extraer_usaspending", return_value={(2025, 1): 1}), \
             mock.patch.object(m, "subir_variable", lambda d, v, val, u: subidas.append(v)):
            with self.assertRaises(RuntimeError) as cm:
                m.run()
        self.assertIn("exim_autorizaciones", str(cm.exception))
        self.assertIn("fa_gov_obligaciones", subidas)
        self.assertIn("usaspending_obligaciones", subidas)
        self.assertNotIn("exim_autorizado", subidas)

    def test_poblacion_maxima_es_el_anio_en_curso(self):
        from src.processing import insumos_indice as m

        self.assertEqual(m.ANIO_MAXIMO_POBLACION, datetime.now(timezone.utc).year)


if __name__ == "__main__":
    unittest.main(verbosity=2)
