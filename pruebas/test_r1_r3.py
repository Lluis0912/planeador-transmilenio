import csv
import tempfile
import unittest
from pathlib import Path

from motor import Red, simular_fila


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
            escritor.writerow(["B74-1", "AVENIDA JIMENEZ", "10:10"])
            escritor.writerow(["B74-1", "AVENIDA JIMENEZ", "10:30"])
            escritor.writerow(["B74-1", "CALLE 80", "10:20"])
            escritor.writerow(["B74-1", "CALLE 80", "11:00"])
            escritor.writerow(["B74-2", "CALLE 80", "10:00"])
            escritor.writerow(["B74-2", "AVENIDA JIMENEZ", "10:05"])
            escritor.writerow(["B74-2", "CALLE 26", "10:10"])
            escritor.writerow(["D10-1", "CALLE 45", "09:30"])
            escritor.writerow(["D10-1", "AVENIDA JIMENEZ", "09:40"])
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
            ["AVENIDA JIMENEZ", "CALLE 80", "CALLE 26"],
        )

    def test_ranking_se_actualiza_con_ediciones_y_no_con_r10(self):
        ranking_inicial = self.red.ranking(4)
        self.red.configurar_demanda_global(1)
        self.red.simular_dia(semilla=17)
        self.assertEqual(self.red.ranking(4), ranking_inicial)

        self.red.quitar_parada("B74-1", "AVENIDA JIMENEZ")
        self.assertNotEqual(self.red.ranking(4), ranking_inicial)
        self.assertTrue(self.red.deshacer())
        self.assertEqual(self.red.ranking(4), ranking_inicial)
        self.assertTrue(self.red.rehacer())
        self.assertNotEqual(self.red.ranking(4), ranking_inicial)

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

    def test_r7_y_r9_actualizan_eventos_r10_al_editar_y_deshacer(self):
        indice_servicio = self.red._indice_ruta("B74-1")
        indice_estacion = self.red._posicion_estacion("CALLE 80")

        def ordenes_parada_final():
            ordenes = []
            for evento in self.red._eventos_horario:
                indice_viaje = evento[1]
                if (
                    self.red._viajes_horario[indice_viaje][0]
                    == indice_servicio
                    and evento[2] == indice_estacion
                ):
                    ordenes.append(evento[3])
            return ordenes

        self.assertEqual(ordenes_parada_final(), [2, 2])
        self.red.agregar_parada("B74-1", "CALLE 45", "AVENIDA JIMENEZ")
        self.assertTrue(self.red._eventos_horario_desactualizados)
        self.red._asegurar_eventos_horario_actualizados()
        self.assertEqual(ordenes_parada_final(), [3, 3])
        self.assertTrue(self.red.deshacer())
        self.assertTrue(self.red._eventos_horario_desactualizados)
        self.red._asegurar_eventos_horario_actualizados()
        self.assertEqual(ordenes_parada_final(), [2, 2])

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
        self.assertIn("CALLE 26", self.red.ranking(10))
        self.assertTrue(self.red.deshacer())
        self.assertEqual(self.red.estado("CALLE 26"), (True, False))
        self.assertNotIn("CALLE 26", self.red.ranking(10))

    def test_r9_un_cambio_nuevo_descarta_la_rama_de_rehacer(self):
        self.red.cerrar("CALLE 26")
        self.assertTrue(self.red.deshacer())
        self.red.cerrar("CALLE 80")
        self.assertFalse(self.red.rehacer())
        self.assertEqual(self.red.estado("CALLE 26"), (True, True))
        self.assertEqual(self.red.estado("CALLE 80"), (True, False))

    def test_simular_fila_respeta_fifo_capacidad_y_mide_espera(self):
        resultado = simular_fila([2, 0, 0], frecuencia=10, capacidad=1)
        self.assertEqual(resultado, [1, 1.0, 2, 2, 1])

    def test_r10_demanda_se_genera_cerca_de_servicios_programados(self):
        self.red.configurar_demanda_global(0)
        self.red.configurar_demanda_estacion(
            "CALLE 26", pasajeros_por_minuto=2
        )
        self.red.configurar_capacidad_universal(1)

        resumen, estaciones = self.red.simular_dia(semilla=17)
        self.assertEqual(resumen[0], 102)
        self.assertLessEqual(resumen[1], 2)
        self.assertGreater(resumen[4], 30)
        self.assertEqual(resumen[6], resumen[0] - resumen[7])

        fila_origen = None
        for fila in estaciones:
            if fila[0] == "CALLE 26":
                fila_origen = fila
        self.assertIsNotNone(fila_origen)
        self.assertEqual(fila_origen[1], 102)
        self.assertEqual(
            resumen[7],
            sum(fila[7] for fila in estaciones),
        )

    def test_r10_demanda_global_y_hora_pico_se_suman(self):
        self.red.configurar_demanda_global(0)
        self.red.agregar_hora_pico("00:00", "00:01", 1)
        resumen, estaciones = self.red.simular_dia()
        self.assertEqual(resumen[0], 0)

        self.red.limpiar_horas_pico()
        resumen_sin_pico, estaciones_sin_pico = self.red.simular_dia()
        self.assertEqual(resumen_sin_pico[0], 0)

        self.red.agregar_hora_pico("09:30", "09:32", 1)
        self.red.configurar_capacidad_universal(1000000)
        resumen_con_servicio, estaciones_con_servicio = (
            self.red.simular_dia(semilla=42)
        )
        self.assertGreater(resumen_con_servicio[0], 0)
        self.assertLessEqual(resumen_con_servicio[4], 30)
        self.assertEqual(
            resumen_con_servicio[0],
            resumen_con_servicio[7],
        )

    def test_r10_flujo_global_genera_pasajeros_en_todas_las_estaciones(self):
        self.red.configurar_demanda_global(5)
        self.red.configurar_capacidad_universal(1000000)

        resumen, estaciones = self.red.simular_dia(semilla=42)

        self.assertGreater(resumen[0], 0)
        self.assertLess(resumen[0], 4 * 5 * 1440)
        self.assertEqual(
            resumen[0],
            sum(fila[1] for fila in estaciones),
        )
        self.assertEqual(resumen[0], resumen[7])
        for fila in estaciones:
            self.assertGreater(fila[1], 0)

    def test_r11_total_fijo_es_exacto_y_se_reparte_desde_hora_elegida(self):
        self.red.configurar_demanda_global(99)
        self.red.agregar_hora_pico("10:00", "12:00", 100)
        self.red.configurar_capacidad_universal(1000000)

        resumen, estaciones = self.red.simular_dia(
            semilla=42,
            total_pasajeros=103,
            hora_inicio="10:00",
        )

        self.assertEqual(resumen[0], 103)
        self.assertEqual(sum(fila[1] for fila in estaciones), 103)

    def test_r11_total_fijo_se_asigna_aunque_no_haya_bus_inmediato(self):
        resumen, _ = self.red.simular_dia(
            total_pasajeros=1, hora_inicio="23:59"
        )
        self.assertEqual(resumen[0], 1)
        self.assertEqual(resumen[1], 0)

        for estacion in self.red.estaciones():
            self.red.cerrar(estacion)
        with self.assertRaisesRegex(ValueError, "No hay estaciones abiertas"):
            self.red.simular_dia(total_pasajeros=1, hora_inicio="23:59")

    def test_r11_mide_tamaños_duplicados_y_genera_totales_exactos(self):
        tiempo_base, mediciones = self.red.medir_rendimiento_r10(
            [10, 20], hora_inicio="10:00"
        )

        self.assertGreater(tiempo_base, 0)
        self.assertEqual([fila[0] for fila in mediciones], [10, 20])
        self.assertTrue(all(fila[1] > 0 for fila in mediciones))
        self.assertEqual(self.red.resultado_simulacion()[0][0], 20)

    def test_r10_flujo_global_reemplaza_todas_las_tasas_locales(self):
        self.red.configurar_demanda_estacion(
            "CALLE 26", pasajeros_por_minuto=1
        )
        self.red.configurar_demanda_estacion(
            "CALLE 45", pasajeros_por_minuto=2
        )

        self.red.aplicar_flujo_global_a_estaciones(3)
        self.red.configurar_capacidad_universal(1000000)
        resumen, estaciones = self.red.simular_dia(semilla=42)

        self.assertGreater(resumen[0], 0)
        self.assertLess(resumen[0], 4 * 3 * 1440)
        self.assertEqual(
            resumen[0],
            sum(fila[1] for fila in estaciones),
        )
        self.assertEqual(resumen[0], resumen[7])
        for fila in estaciones:
            self.assertGreaterEqual(fila[1], 0)

    def test_r10_destinos_aleatorios_son_repetibles_y_miden_llegadas(self):
        self.red.configurar_demanda_global(0)
        self.red.configurar_demanda_estacion("CALLE 45", pasajeros_por_minuto=1)
        self.red.configurar_capacidad_universal(1000000)

        resumen, estaciones = self.red.simular_dia(semilla=42)
        resumen_repetido, estaciones_repetidas = self.red.simular_dia(semilla=42)
        _, estaciones_otro_sorteo = self.red.simular_dia(
            semilla=43
        )

        self.assertGreater(resumen[0], 0)
        self.assertLess(resumen[0], 1440)
        self.assertEqual(resumen, resumen_repetido)
        self.assertEqual(estaciones, estaciones_repetidas)
        self.assertLessEqual(resumen[4], 30)
        self.assertEqual(resumen[0], resumen[7])
        self.assertNotEqual(
            [fila[7] for fila in estaciones],
            [fila[7] for fila in estaciones_otro_sorteo],
        )
        self.assertEqual(
            resumen[7],
            sum(fila[7] for fila in estaciones),
        )
        self.assertGreater(resumen[7], 0)


if __name__ == "__main__":
    unittest.main()
