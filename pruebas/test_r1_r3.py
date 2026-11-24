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
            escritor.writerow(["B74-1", 1, "CALLE 26"])
            escritor.writerow(["B74-1", 2, "AVENIDA JIMENEZ"])
            escritor.writerow(["B74-1", 3, "CALLE 80"])
            escritor.writerow(["D10-1", 1, "CALLE 45"])
            escritor.writerow(["D10-1", 2, "AVENIDA JIMENEZ"])
            escritor.writerow(["D10-1", 3, "CALLE 80"])
            escritor.writerow(["B74-2", 1, "CALLE 80"])
            escritor.writerow(["B74-2", 2, "AVENIDA JIMENEZ"])
            escritor.writerow(["B74-2", 3, "CALLE 26"])
            escritor.writerow(["C20-1", 1, "CALLE 45"])
            escritor.writerow(["C20-1", 2, "CALLE 80"])
            escritor.writerow(["C20-1", 3, "AVENIDA JIMENEZ"])
            escritor.writerow(["C20-1", 4, "CALLE 26"])
            escritor.writerow(["1-Jan", 1, "CALLE 26"])
        ruta_horarios = Path(self.directorio_temporal.name) / "horarios.csv"
        with ruta_horarios.open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["ruta", "estacion", "hora"])
            escritor.writerow(["B74-1", "CALLE 26", "10:00"])
            escritor.writerow(["B74-1", "CALLE 26", "10:20"])
            escritor.writerow(["B74-1", "CALLE 80", "11:00"])
            escritor.writerow(["B74-2", "CALLE 26", "10:10"])
            escritor.writerow(["D10-1", "CALLE 45", "09:30"])
            escritor.writerow(["D10-1", "CALLE 80", "10:30"])
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
            self.red.proximo_bus("CALLE 26", "B74", "10:05"),
            "10:10",
        )
        self.assertEqual(
            self.red.proximo_bus("CALLE 26", "B74-1", "10:05"),
            "10:20",
        )
        self.assertIsNone(
            self.red.proximo_bus("CALLE 26", "B74", "23:00")
        )

    def test_viaje_encuentra_directo_y_transbordo(self):
        self.assertEqual(
            self.red.viaje("CALLE 26", "CALLE 80"),
            [["B74", "CALLE 26", "CALLE 80"]],
        )

    def test_viaje_elige_transbordo_con_menos_paradas_que_directo(self):
        self.assertEqual(
            self.red.viaje("CALLE 45", "CALLE 26"),
            [
                ["D10", "CALLE 45", "AVENIDA JIMENEZ"],
                ["B74", "AVENIDA JIMENEZ", "CALLE 26"],
            ],
        )

    def test_ranking_devuelve_k_estaciones_abiertas(self):
        self.assertEqual(
            self.red.ranking(3),
            ["CALLE 26", "CALLE 80", "CALLE 45"],
        )

    def test_r7_muestra_ambos_sentidos_y_agrega_solo_estacion_existente(self):
        self.assertEqual(self.red.servicios("B74"), ["B74-1", "B74-2"])
        self.assertEqual(self.red.servicios("1-Jan"), ["1-Jan"])
        self.assertEqual(
            self.red.recorrido("B74-1"),
            ["CALLE 26", "AVENIDA JIMENEZ", "CALLE 80"],
        )
        self.assertEqual(
            self.red.recorrido("B74-1", al_reves=True),
            ["CALLE 80", "AVENIDA JIMENEZ", "CALLE 26"],
        )

        self.red.agregar_parada("B74-1", "CALLE 45", "AVENIDA JIMENEZ")
        self.assertEqual(
            self.red.recorrido("B74-1"),
            ["CALLE 26", "AVENIDA JIMENEZ", "CALLE 45", "CALLE 80"],
        )
        self.assertEqual(
            self.red.recorrido("B74-2"),
            ["CALLE 80", "AVENIDA JIMENEZ", "CALLE 26"],
        )
        with self.assertRaises(ValueError):
            self.red.agregar_parada("B74-1", "ESTACION NUEVA", "CALLE 26")

    def test_r7_quita_parada_sin_borrar_estacion_de_la_red(self):
        self.red.quitar_parada("B74-1", "AVENIDA JIMENEZ")
        self.assertEqual(
            self.red.recorrido("B74-1"),
            ["CALLE 26", "CALLE 80"],
        )
        self.assertEqual(self.red.estado("AVENIDA JIMENEZ"), (True, True))

    def test_r8_y_r9_cierran_reabren_y_rehacen_cambios_en_orden(self):
        self.red.cerrar("CALLE 26")
        self.assertEqual(self.red.autocompletar("CALLE 26", 10), [])
        self.assertNotIn("CALLE 26", self.red.ranking(10))
        self.red.agregar_parada("B74-1", "CALLE 45", "AVENIDA JIMENEZ")
        self.assertEqual(self.red.estado("CALLE 26"), (True, False))

        self.assertTrue(self.red.deshacer())
        self.assertEqual(
            self.red.recorrido("B74-1"),
            ["CALLE 26", "AVENIDA JIMENEZ", "CALLE 80"],
        )
        self.assertTrue(self.red.deshacer())
        self.assertEqual(self.red.estado("CALLE 26"), (True, True))

        self.assertTrue(self.red.rehacer())
        self.assertEqual(self.red.estado("CALLE 26"), (True, False))
        self.assertTrue(self.red.rehacer())
        self.assertEqual(
            self.red.recorrido("B74-1"),
            ["CALLE 26", "AVENIDA JIMENEZ", "CALLE 45", "CALLE 80"],
        )
        self.assertFalse(self.red.rehacer())

        self.red.reabrir("CALLE 26")
        self.assertEqual(self.red.estado("CALLE 26"), (True, True))
        self.assertTrue(self.red.deshacer())
        self.assertEqual(self.red.estado("CALLE 26"), (True, False))

    def test_r9_un_cambio_nuevo_descarta_la_rama_de_rehacer(self):
        self.red.cerrar("CALLE 26")
        self.assertTrue(self.red.deshacer())
        self.red.cerrar("CALLE 80")
        self.assertFalse(self.red.rehacer())
        self.assertEqual(self.red.estado("CALLE 26"), (True, True))
        self.assertEqual(self.red.estado("CALLE 80"), (True, False))


if __name__ == "__main__":
    unittest.main()
