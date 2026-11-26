import unittest

from front.__main__ import PlaneadorApp


class GraficaR11Tests(unittest.TestCase):
    def test_escala_regular_usa_proporcion_del_total(self):
        mediciones = [[10, 1.0], [20, 2.0], [40, 3.0]]

        coordenadas = PlaneadorApp._coordenadas_x_grafica_r11(
            mediciones, 0, 100, "regular"
        )

        self.assertEqual(coordenadas, [25, 50, 100])

    def test_escala_log2_separa_dobles_uniformemente(self):
        mediciones = [[10, 1.0], [20, 2.0], [40, 3.0]]

        coordenadas = PlaneadorApp._coordenadas_x_grafica_r11(
            mediciones, 0, 100, "log2"
        )

        self.assertEqual(coordenadas, [0, 50, 100])

    def test_una_medicion_se_centra_en_cualquier_escala(self):
        coordenadas = PlaneadorApp._coordenadas_x_grafica_r11(
            [[10, 1.0]], 20, 100, "regular"
        )

        self.assertEqual(coordenadas, [60])


if __name__ == "__main__":
    unittest.main()
