import csv
import tempfile
import unittest
from pathlib import Path

from motor import Red


class RedR1R3Tests(unittest.TestCase):
    def setUp(self):
        self.directorio_temporal = tempfile.TemporaryDirectory()
        ruta_estaciones = Path(self.directorio_temporal.name) / "estaciones.csv"
        with ruta_estaciones.open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["nombre"])
            escritor.writerow(["CALLE 80"])
            escritor.writerow(["AVENIDA JIMENEZ"])
            escritor.writerow(["CALLE 45"])
            escritor.writerow(["CALLE 26"])
        self.red = Red(self.directorio_temporal.name)

    def tearDown(self):
        self.directorio_temporal.cleanup()

    def test_estado_distingue_estacion_existente(self):
        self.assertEqual(self.red.estado(" calle 26 "), (True, True))
        self.assertEqual(self.red.estado("ESTACION FANTASMA"), (False, False))

    def test_autocompletar_respeta_prefijo_orden_y_limite(self):
        self.assertEqual(
            self.red.autocompletar("calle", 2),
            ["CALLE 26", "CALLE 45"],
        )
        self.assertEqual(self.red.autocompletar("calle", 0), [])

    def test_rango_incluye_extremos_y_esta_ordenado(self):
        self.assertEqual(
            self.red.rango("calle 26", "calle 80"),
            ["CALLE 26", "CALLE 45", "CALLE 80"],
        )
        self.assertEqual(
            self.red.rango("CALLE 80", "CALLE 26"),
            ["CALLE 80", "CALLE 45", "CALLE 26"],
        )

    def test_rango_inverso_admite_limites_que_no_existen(self):
        self.assertEqual(
            self.red.rango("CALLE 90", "CALLE 30"),
            ["CALLE 80", "CALLE 45"],
        )


if __name__ == "__main__":
    unittest.main()
