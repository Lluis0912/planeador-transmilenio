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
        ruta_rutas = Path(self.directorio_temporal.name) / "rutas.csv"
        with ruta_rutas.open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["ruta", "orden", "estacion"])
            escritor.writerow(["A", 1, "CALLE 26"])
            escritor.writerow(["A", 2, "AVENIDA JIMENEZ"])
            escritor.writerow(["A", 3, "CALLE 80"])
            escritor.writerow(["B", 1, "CALLE 45"])
            escritor.writerow(["B", 2, "AVENIDA JIMENEZ"])
            escritor.writerow(["B", 3, "CALLE 80"])
        ruta_horarios = Path(self.directorio_temporal.name) / "horarios.csv"
        with ruta_horarios.open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["ruta", "estacion", "hora"])
            escritor.writerow(["A-1", "CALLE 26", "10:00"])
            escritor.writerow(["A-1", "CALLE 26", "10:20"])
            escritor.writerow(["A-1", "CALLE 80", "11:00"])
            escritor.writerow(["A-2", "CALLE 26", "10:10"])
            escritor.writerow(["B", "CALLE 45", "09:30"])
            escritor.writerow(["B", "CALLE 80", "10:30"])
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

    def test_proximo_bus_usa_siguiente_horario(self):
        self.assertEqual(
            self.red.proximo_bus("CALLE 26", "A", "10:05"),
            "10:10",
        )
        self.assertEqual(
            self.red.proximo_bus("CALLE 26", "A-1", "10:05"),
            "10:20",
        )
        self.assertIsNone(
            self.red.proximo_bus("CALLE 26", "A", "23:00")
        )

    def test_viaje_encuentra_directo_y_transbordo(self):
        self.assertEqual(
            self.red.viaje("CALLE 26", "CALLE 80"),
            [["A", "CALLE 26", "CALLE 80"]],
        )
        self.assertEqual(
            self.red.viaje("CALLE 45", "CALLE 26"),
            [
                ["B", "CALLE 45", "AVENIDA JIMENEZ"],
                ["A", "AVENIDA JIMENEZ", "CALLE 26"],
            ],
        )

    def test_ranking_devuelve_k_estaciones_abiertas(self):
        self.assertEqual(
            self.red.ranking(3),
            ["CALLE 26", "CALLE 80", "CALLE 45"],
        )


if __name__ == "__main__":
    unittest.main()
