import json
import tempfile
import unittest
from pathlib import Path

from scraper_mre import Candidate, canonical_url, count_mentions, extract_article, load_patterns, parse_date


class ScraperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = load_patterns(Path(__file__).with_name("terminos_eeuu.json"))

    def test_fechas_espanol(self):
        self.assertEqual(parse_date("Asunción, 18 de octubre de 2018"), "2018-10-18")
        self.assertEqual(parse_date("3 de setiembre de 2021"), "2021-09-03")

    def test_menciones_sin_solapamiento(self):
        count, labels = count_mentions(
            "Estados Unidos y EE.UU. dialogaron con funcionarios estadounidenses.", self.patterns
        )
        self.assertEqual(count, 3)
        self.assertTrue(labels)

    def test_no_confunde_emiratos(self):
        count, _ = count_mentions("Emiratos Árabes Unidos cooperó con Paraguay.", self.patterns)
        self.assertEqual(count, 0)

    def test_canonicaliza_paginacion(self):
        value = canonical_url("http://mre.gov.py/index.php/noticias/nota?ccm_paging_p=7&utm_source=x")
        self.assertEqual(value, "https://www.mre.gov.py/index.php/noticias/nota")

    def test_extrae_articulo_actual(self):
        raw = """
        <html><head><meta name="description" content="Descripción de prueba suficientemente clara."></head>
        <body><header>Menú</header><main><article><h1>Reunión bilateral</h1>
        <p>Paraguay y Estados Unidos mantuvieron una reunión de trabajo.</p>
        <p>Asunción, 18 de octubre de 2018</p></article></main><footer>Pie</footer></body></html>
        """
        item = Candidate("actual", "https://x", "https://x")
        title, description, text, published = extract_article(raw, item)
        self.assertEqual(title, "Reunión bilateral")
        self.assertEqual(published, "2018-10-18")
        self.assertIn("Estados Unidos", text)
        self.assertNotIn("Pie", text)

    def test_portal_historico_excluye_ultimas_noticias(self):
        raw = """
        <html><head><title>Portal MRE :: Reunión en Brasil</title></head><body>
        <h5 class="page-title">Reunión en Brasil</h5>
        <div class="section contenido_principal">
          <p>Autoridades paraguayas mantuvieron una reunión de trabajo en Brasil.</p>
          <p>01 de agosto de 2018</p><hr>
          <h5>Últimas Noticias Publicadas</h5>
          <div>El presidente de Estados Unidos recibió a una delegación.</div>
        </div></body></html>
        """
        item = Candidate("wayback", "https://x", "https://x")
        title, _, text, published = extract_article(raw, item)
        self.assertEqual(title, "Reunión en Brasil")
        self.assertEqual(published, "2018-08-01")
        self.assertNotIn("Estados Unidos", text)


if __name__ == "__main__":
    unittest.main()
