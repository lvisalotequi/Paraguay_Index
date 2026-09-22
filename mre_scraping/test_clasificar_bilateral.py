import unittest
from pathlib import Path
from clasificar_bilateral import classify, compile_rules
from scraper_mre import load_patterns

class BilateralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parent
        cls.config, cls.rules = compile_rules(root / "reglas_bilaterales.json")
        cls.us = load_patterns(root / "terminos_eeuu.json")

    def run_case(self, title, text):
        return classify({"titulo": title, "texto": text}, self.us, self.config, self.rules)

    def test_reunion_bilateral_de_peso(self):
        result = self.run_case("Canciller se reúne con secretario de Estado de EE.UU.",
          "Paraguay y Estados Unidos abordaron cooperación bilateral en seguridad y firmaron un acuerdo.")
        self.assertEqual(result["es_bilateral"], 1)
        self.assertEqual(result["nivel_relevancia"], "bilateral de peso")

    def test_mencion_incidental_no_es_bilateral(self):
        result = self.run_case("Concierto en Boston", "Una artista paraguaya actuó en Estados Unidos.")
        self.assertEqual(result["es_bilateral"], 0)
        self.assertEqual(result["nivel_relevancia"], "mención simple")

    def test_multilateral_sin_interaccion_no_es_bilateral(self):
        result = self.run_case("Asamblea de Naciones Unidas", "Paraguay y Estados Unidos participaron del debate de la ONU.")
        self.assertEqual(result["es_bilateral"], 0)

    def test_mencion_lejana_no_es_bilateral(self):
        text = "El canciller de Paraguay recibió a la embajadora de España. " + ("Contexto general. " * 40) + "Estados Unidos participó en otra actividad."
        self.assertEqual(self.run_case("Embajadora de España presenta credenciales", text)["es_bilateral"], 0)

if __name__ == "__main__": unittest.main()
