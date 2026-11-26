import csv
import random
import time


def simular_fila(llegadas, frecuencia, capacidad):
    """
    R10: simula una cola FIFO usando grupos de llegadas.

    Devuelve abordados, espera promedio y máxima, cola máxima y no abordados.
    Cuesta O(T + G): recorre los minutos y los grupos, no cada pasajero.
    """
    if frecuencia <= 0 or capacidad <= 0:
        raise ValueError("La frecuencia y la capacidad deben ser mayores que cero.")

    cola = []
    cabeza = 0
    abordados = 0
    espera_total = 0
    espera_maxima = 0
    cola_maxima = 0
    pasajeros_en_cola = 0

    minuto = 0
    while minuto < len(llegadas):
        cantidad = llegadas[minuto]
        if cantidad < 0:
            raise ValueError("Las llegadas no pueden ser negativas.")
        if cantidad > 0:
            cola.append([minuto, cantidad])
            pasajeros_en_cola += cantidad
        if pasajeros_en_cola > cola_maxima:
            cola_maxima = pasajeros_en_cola

        if minuto % frecuencia == 0:
            cupo = capacidad
            while cupo > 0 and cabeza < len(cola):
                grupo = cola[cabeza]
                suben = grupo[1]
                if suben > cupo:
                    suben = cupo
                espera = minuto - grupo[0]
                espera_total += espera * suben
                if espera > espera_maxima:
                    espera_maxima = espera
                abordados += suben
                pasajeros_en_cola -= suben
                cupo -= suben
                grupo[1] -= suben
                if grupo[1] == 0:
                    cabeza += 1
        minuto += 1

    no_abordados = 0
    fin_periodo = len(llegadas) - 1
    for grupo in cola[cabeza:]:
        no_abordados += grupo[1]
        espera = fin_periodo - grupo[0]
        espera_total += espera * grupo[1]
        if espera > espera_maxima:
            espera_maxima = espera

    total_esperas = abordados + no_abordados
    if total_esperas > 0:
        espera_promedio = espera_total / total_esperas
    else:
        espera_promedio = 0

    return [
        abordados,
        espera_promedio,
        espera_maxima,
        cola_maxima,
        no_abordados,
    ]


class Red:
    """
    Datos y operaciones del motor R1–R11.

    `_estaciones` y `_abiertas` son listas paralelas; las demás listas guardan
    rutas, horarios, cachés, historial y resultados de cada requisito.
    """
    def __init__(self, carpeta):
        """Carga las listas base compartidas por R1–R11."""
        # R1: ordena y consolida estaciones para las búsquedas posteriores.
        ruta_archivo = str(carpeta).rstrip("/\\") + "/estaciones.csv"
        estaciones = []

        with open(ruta_archivo, "r", encoding="utf-8-sig", newline="") as archivo:
            lector = csv.reader(archivo)
            encabezado = next(lector, None)
            posicion_nombre = -1
            if encabezado is not None:
                indice = 0
                while indice < len(encabezado):
                    if encabezado[indice].strip().lower() == "nombre":
                        posicion_nombre = indice
                        break
                    indice += 1

            if posicion_nombre == -1:
                raise ValueError("estaciones.csv debe tener una columna 'nombre'")

            for fila in lector:
                nombre = fila[posicion_nombre] if posicion_nombre < len(fila) else ""
                if nombre is not None and nombre.strip() != "":
                    estaciones.append([nombre.strip().upper(), True])

        estaciones = self._ordenar(estaciones)
        self._estaciones = []
        self._abiertas = []

        for estacion in estaciones:
            if len(self._estaciones) == 0 or self._estaciones[-1] != estacion[0]:
                self._estaciones.append(estacion[0])
                self._abiertas.append(estacion[1])

        # R4–R11 comparten las tablas de rutas y horarios.
        base = str(carpeta).rstrip("/\\")
        self._rutas_info = self._cargar_rutas(base + "/rutas.csv")
        self._horarios = self._cargar_horarios(base + "/horarios.csv")
        self._buses = self._obtener_buses()
        self._ranking = self._construir_ranking()
        self._ranking_desactualizado = False
        self._historial_deshacer = []
        self._historial_rehacer = []
        self._flujo_global = 0
        self._flujos_estaciones = []
        self._capacidad_universal = 80
        self._horas_pico = []
        self._resultado_r10 = []
        self._eventos_horario, self._viajes_horario = (
            self._construir_eventos_horario()
        )
        self._eventos_horario_desactualizados = False

    def configurar_demanda_global(self, pasajeros_por_minuto):
        """R10: establece el flujo base de pasajeros por estación y minuto."""
        self._validar_cantidad(pasajeros_por_minuto, "El flujo")
        self._flujo_global = pasajeros_por_minuto
        self._resultado_r10 = []

    def aplicar_flujo_global_a_estaciones(self, pasajeros_por_minuto):
        """
        R10: aplica el flujo global y elimina las tasas locales.

        Recorre las configuraciones locales en O(S).
        """
        self.configurar_demanda_global(pasajeros_por_minuto)
        for configuracion in self._flujos_estaciones:
            configuracion[1] = -1

    def configurar_demanda_estacion(self, estacion, pasajeros_por_minuto=None):
        """
        R10: establece o quita el flujo local de una estación.
        """
        if pasajeros_por_minuto is not None:
            self._validar_cantidad(pasajeros_por_minuto, "El flujo")
        origen_normalizado = self._validar_estacion_configurable(estacion)
        flujo_local = -1 if pasajeros_por_minuto is None else pasajeros_por_minuto
        posicion = 0
        while posicion < len(self._flujos_estaciones):
            if self._flujos_estaciones[posicion][0] == origen_normalizado:
                self._flujos_estaciones[posicion] = [
                    origen_normalizado,
                    flujo_local,
                ]
                self._resultado_r10 = []
                return
            posicion += 1
        self._flujos_estaciones.append([origen_normalizado, flujo_local])
        self._resultado_r10 = []

    def quitar_demanda_estacion(self, estacion):
        """R10: quita el flujo local y vuelve a usar el global."""
        origen_normalizado = self._normalizar(estacion)
        posicion = 0
        while posicion < len(self._flujos_estaciones):
            if self._flujos_estaciones[posicion][0] == origen_normalizado:
                self._flujos_estaciones.pop(posicion)
                self._resultado_r10 = []
                return True
            posicion += 1
        return False

    def configurar_capacidad_universal(self, capacidad):
        """R10: establece la capacidad común de los buses en O(1)."""
        self._validar_cantidad(capacidad, "La capacidad")
        if capacidad == 0:
            raise ValueError("La capacidad debe ser mayor que cero.")
        self._capacidad_universal = capacidad
        self._resultado_r10 = []

    def agregar_hora_pico(self, desde, hasta, pasajeros_extra):
        """
        R10: agrega pasajeros por minuto dentro del intervalo indicado.

        El inicio se incluye y el final se excluye; admite cruzar medianoche.
        """
        self._validar_cantidad(pasajeros_extra, "El incremento")
        minuto_desde = self._convertir_hora(desde)
        minuto_hasta = self._convertir_hora(hasta)
        if minuto_desde is None or minuto_hasta is None:
            raise ValueError("Las horas deben tener el formato HH:MM.")
        self._horas_pico.append([minuto_desde, minuto_hasta, pasajeros_extra])
        self._resultado_r10 = []

    def limpiar_horas_pico(self):
        """R10: elimina los incrementos de demanda por hora pico."""
        self._horas_pico = []
        self._resultado_r10 = []

    def _construir_eventos_horario(self):
        """
        R10: construye eventos de viaje a partir de los horarios.

        Como el CSV no identifica vehículos, alinea las filas de cada parada
        por posición. Cuesta O(H·P + H log N + H log H) y usa O(H + P) espacio.
        """
        eventos = []
        viajes = []
        indice_horario = 0

        for indice_servicio in range(len(self._rutas_info)):
            servicio = self._rutas_info[indice_servicio]
            identificador = servicio[0]
            paradas = servicio[1]
            horarios_por_parada = []
            for parada in paradas:
                horarios_por_parada.append([])

            while (
                indice_horario < len(self._horarios)
                and self._horarios[indice_horario][0] < identificador
            ):
                indice_horario += 1

            while (
                indice_horario < len(self._horarios)
                and self._horarios[indice_horario][0] == identificador
            ):
                fila = self._horarios[indice_horario]
                indice_parada = self._buscar_en_lista(paradas, fila[1])
                if indice_parada != -1:
                    horarios_por_parada[indice_parada].append(fila[2])
                indice_horario += 1

            cantidad_viajes = 0
            for horarios_parada in horarios_por_parada:
                if len(horarios_parada) > cantidad_viajes:
                    cantidad_viajes = len(horarios_parada)

            for indice_viaje in range(cantidad_viajes):
                viaje_id = len(viajes)
                viajes.append(
                    [indice_servicio, self._capacidad_universal, [], 0]
                )
                minuto_anterior = -1
                for indice_parada in range(len(paradas)):
                    horas = horarios_por_parada[indice_parada]
                    if indice_viaje < len(horas):
                        minuto = horas[indice_viaje]
                        while minuto < minuto_anterior:
                            minuto += 1440
                        minuto_anterior = minuto
                        if minuto < 1440:
                            indice_estacion = self._posicion_estacion(
                                paradas[indice_parada]
                            )
                            if indice_estacion != -1:
                                eventos.append(
                                    [
                                        minuto,
                                        viaje_id,
                                        indice_estacion,
                                        indice_parada,
                                    ]
                                )

        return self._ordenar_eventos_horario(eventos), viajes

    def _invalidar_eventos_horario(self):
        """R7/R9: marca el índice de horarios R10 para reconstruirlo."""
        self._eventos_horario_desactualizados = True

    def _asegurar_eventos_horario_actualizados(self):
        """R10/R11: reconstruye el índice si R7/R9 cambiaron un recorrido."""
        if self._eventos_horario_desactualizados:
            self._eventos_horario, self._viajes_horario = (
                self._construir_eventos_horario()
            )
            self._eventos_horario_desactualizados = False

    @classmethod
    def _ordenar_eventos_horario(cls, eventos):
        """R10: ordena eventos por hora con merge sort, O(H log H)."""
        if len(eventos) < 2:
            return eventos

        mitad = len(eventos) // 2
        izquierda = cls._ordenar_eventos_horario(eventos[:mitad])
        derecha = cls._ordenar_eventos_horario(eventos[mitad:])
        resultado = []
        i = 0
        j = 0
        while i < len(izquierda) and j < len(derecha):
            clave_izquierda = (
                izquierda[i][0],
                izquierda[i][1],
                izquierda[i][3],
            )
            clave_derecha = (
                derecha[j][0],
                derecha[j][1],
                derecha[j][3],
            )
            if clave_izquierda <= clave_derecha:
                resultado.append(izquierda[i])
                i += 1
            else:
                resultado.append(derecha[j])
                j += 1
        while i < len(izquierda):
            resultado.append(izquierda[i])
            i += 1
        while j < len(derecha):
            resultado.append(derecha[j])
            j += 1
        return resultado

    def _guardar_itinerario(
        self, destinos, indice_destino, servicio, parada, siguiente, pasos
    ):
        """R10: conserva el itinerario con menos paradas para un destino."""
        if not self._abiertas[indice_destino]:
            return
        actual = destinos[indice_destino]
        if pasos < actual[4]:
            destinos[indice_destino] = [
                servicio,
                parada,
                siguiente,
                indice_destino,
                pasos,
            ]

    def _agregar_itinerarios_desde(
        self, indice_origen, servicios_por_estacion, destinos
    ):
        """
        R10: prepara destinos directos o con un transbordo para un origen.
        """
        for servicio_a, inicio_a in servicios_por_estacion[indice_origen]:
            paradas_a = self._rutas_info[servicio_a][1]
            for parada_a in range(inicio_a + 1, len(paradas_a)):
                nombre_parada = paradas_a[parada_a]
                indice_parada = self._posicion_estacion(nombre_parada)
                if indice_parada == -1 or not self._abiertas[indice_parada]:
                    continue

                self._guardar_itinerario(
                    destinos,
                    indice_parada,
                    servicio_a,
                    indice_parada,
                    -1,
                    parada_a - inicio_a,
                )

                for servicio_b, inicio_b in servicios_por_estacion[indice_parada]:
                    if servicio_b == servicio_a:
                        continue
                    paradas_b = self._rutas_info[servicio_b][1]
                    for parada_b in range(inicio_b + 1, len(paradas_b)):
                        indice_destino = self._posicion_estacion(
                            paradas_b[parada_b]
                        )
                        if indice_destino == -1 or indice_destino == indice_origen:
                            continue
                        pasos = (
                            parada_a - inicio_a + parada_b - inicio_b
                        )
                        self._guardar_itinerario(
                            destinos,
                            indice_destino,
                            servicio_a,
                            indice_parada,
                            servicio_b,
                            pasos,
                        )

    @staticmethod
    def _primera_salida_desde(salidas, minuto):
        """R10: busca con binaria la primera salida desde ese minuto."""
        izquierda = 0
        derecha = len(salidas)
        while izquierda < derecha:
            medio = (izquierda + derecha) // 2
            if salidas[medio][0] < minuto:
                izquierda = medio + 1
            else:
                derecha = medio
        return izquierda

    def _itinerarios_con_salida_futura(
        self,
        indice_origen,
        minuto,
        opciones,
        salidas,
        posiciones_por_minuto,
        eventos_viaje,
        mascara_posterior,
    ):
        """R10: filtra itinerarios por salidas reales dentro de 30 minutos."""
        ventana_maxima_espera = 30
        destinos = []
        limite_salida = minuto + ventana_maxima_espera
        for grupo_itinerario in opciones:
            servicio = grupo_itinerario[0]
            indice_transbordo = grupo_itinerario[1]
            servicio_siguiente = grupo_itinerario[2]
            salidas_servicio = salidas[indice_origen][servicio]
            indices_minuto = posiciones_por_minuto[indice_origen][servicio]
            if indices_minuto is None:
                posicion = len(salidas_servicio)
            else:
                posicion = indices_minuto[minuto]
            destinos_posibles = 0
            destinos_requeridos = grupo_itinerario[4]

            while (
                posicion < len(salidas_servicio)
                and salidas_servicio[posicion][0] <= limite_salida
            ):
                salida = salidas_servicio[posicion]
                indice_evento = salida[3]
                if servicio_siguiente == -1:
                    destinos_posibles |= mascara_posterior[indice_evento]
                else:
                    evento_conexion = eventos_viaje[salida[1]][
                        indice_transbordo
                    ]
                    if (
                        evento_conexion is not None
                        and evento_conexion[1] > salida[2]
                    ):
                        minuto_siguiente = evento_conexion[0] + 1
                        salidas_siguientes = salidas[indice_transbordo][
                            servicio_siguiente
                        ]
                        indices_siguiente = posiciones_por_minuto[
                            indice_transbordo
                        ][servicio_siguiente]
                        if indices_siguiente is None:
                            posicion_siguiente = len(salidas_siguientes)
                        elif minuto_siguiente <= 1440:
                            posicion_siguiente = indices_siguiente[
                                minuto_siguiente
                            ]
                        else:
                            posicion_siguiente = len(salidas_siguientes)
                        limite_transbordo = (
                            evento_conexion[0] + ventana_maxima_espera
                        )
                        while (
                            posicion_siguiente < len(salidas_siguientes)
                            and salidas_siguientes[posicion_siguiente][0]
                            <= limite_transbordo
                        ):
                            evento_siguiente = salidas_siguientes[
                                posicion_siguiente
                            ]
                            destinos_posibles |= mascara_posterior[
                                evento_siguiente[3]
                            ]
                            if (
                                destinos_posibles & destinos_requeridos
                                == destinos_requeridos
                            ):
                                break
                            posicion_siguiente += 1
                posicion += 1
                if (
                    destinos_posibles & destinos_requeridos
                    == destinos_requeridos
                ):
                    break

            for indice_destino, itinerario in grupo_itinerario[3]:
                if destinos_posibles & (1 << indice_destino):
                    destinos.append([indice_destino, itinerario])
        return destinos

    def simular_dia(
        self, semilla=None, total_pasajeros=None, hora_inicio="00:00"
    ):
        """
        R10: simula hasta medianoche con horarios y colas FIFO de grupos.

        Acepta flujo configurado o un total fijo. Cuesta
        O(NR + H + 1440A + VN + N(C + DK) + TN + W + B + Q) y usa
        O(H + VN + NR + 1440A + ND + G) espacio.
        """
        minuto_inicio = self._convertir_hora(hora_inicio)
        if minuto_inicio is None:
            raise ValueError("La hora de inicio debe tener formato HH:MM.")
        if total_pasajeros is not None:
            self._validar_cantidad(total_pasajeros, "El total de pasajeros")

        self._asegurar_eventos_horario_actualizados()
        numero_estaciones = len(self._estaciones)
        numero_servicios = len(self._rutas_info)
        colas = []
        metricas = []
        esperando_estacion = []
        cola_sin_ruta = []
        flujos = []

        indice_estacion = 0
        while indice_estacion < numero_estaciones:
            colas_estacion = []
            indice_servicio = 0
            while indice_servicio < numero_servicios:
                colas_estacion.append([])
                indice_servicio += 1
            colas.append(colas_estacion)
            metricas.append([0, 0, 0, 0, 0, 0, 0])
            esperando_estacion.append(0)
            cola_sin_ruta.append([])
            flujos.append(self._flujo_global)
            indice_estacion += 1

        for configuracion in self._flujos_estaciones:
            indice_origen = self._posicion_estacion(configuracion[0])
            if indice_origen == -1:
                continue
            flujo = configuracion[1]
            if flujo < 0:
                flujo = self._flujo_global
            flujos[indice_origen] = flujo

        servicios_por_estacion = []
        indice_estacion = 0
        while indice_estacion < numero_estaciones:
            servicios_por_estacion.append([])
            indice_estacion += 1
        for indice_servicio in range(numero_servicios):
            paradas = self._rutas_info[indice_servicio][1]
            for indice_parada in range(len(paradas)):
                indice = self._posicion_estacion(paradas[indice_parada])
                if indice != -1:
                    servicios = servicios_por_estacion[indice]
                    servicio_encontrado = False
                    for servicio_existente, _ in servicios:
                        if servicio_existente == indice_servicio:
                            servicio_encontrado = True
                            break
                    if not servicio_encontrado:
                        servicios.append([indice_servicio, indice_parada])

        salidas = []
        for indice_estacion in range(numero_estaciones):
            salidas_estacion = []
            for indice_servicio in range(numero_servicios):
                salidas_estacion.append([])
            salidas.append(salidas_estacion)
        eventos_por_viaje = []
        eventos_ordenados_por_viaje = []
        for viaje in self._viajes_horario:
            eventos_por_viaje.append([None] * numero_estaciones)
            eventos_ordenados_por_viaje.append([])
        mascara_posterior = [0] * len(self._eventos_horario)
        for indice_evento_horario in range(len(self._eventos_horario)):
            evento = self._eventos_horario[indice_evento_horario]
            indice_viaje = evento[1]
            indice_estacion = evento[2]
            indice_servicio = self._viajes_horario[indice_viaje][0]
            referencia_evento = [evento[0], evento[3], indice_evento_horario]
            eventos_por_viaje[indice_viaje][indice_estacion] = (
                referencia_evento
            )
            eventos_ordenados_por_viaje[indice_viaje].append(
                [
                    evento[0],
                    indice_estacion,
                    evento[3],
                    indice_evento_horario,
                ]
            )
            salidas[indice_estacion][indice_servicio].append(
                [
                    evento[0],
                    indice_viaje,
                    evento[3],
                    indice_evento_horario,
                ]
            )

        posiciones_por_minuto = []
        for indice_estacion in range(numero_estaciones):
            posiciones_estacion = []
            for indice_servicio in range(numero_servicios):
                salidas_servicio = salidas[indice_estacion][indice_servicio]
                if len(salidas_servicio) == 0:
                    posiciones_estacion.append(None)
                    continue
                posiciones_minuto = []
                posicion = 0
                for minuto_consulta in range(1441):
                    while (
                        posicion < len(salidas_servicio)
                        and salidas_servicio[posicion][0] < minuto_consulta
                    ):
                        posicion += 1
                    posiciones_minuto.append(posicion)
                posiciones_estacion.append(posiciones_minuto)
            posiciones_por_minuto.append(posiciones_estacion)

        for eventos_viaje in eventos_ordenados_por_viaje:
            estaciones_posteriores = 0
            indice_evento_viaje = len(eventos_viaje) - 1
            while indice_evento_viaje >= 0:
                evento_viaje = eventos_viaje[indice_evento_viaje]
                mascara_posterior[evento_viaje[3]] = estaciones_posteriores
                estaciones_posteriores |= 1 << evento_viaje[1]
                indice_evento_viaje -= 1

        opciones_por_estacion = []
        for indice_origen in range(numero_estaciones):
            opciones = []
            if (
                flujos[indice_origen] > 0
                or len(self._horas_pico) > 0
                or total_pasajeros is not None
            ):
                itinerarios_estacion = []
                for indice_destino in range(numero_estaciones):
                    itinerarios_estacion.append(
                        [-1, -1, -1, -1, numero_estaciones + 1]
                    )
                self._agregar_itinerarios_desde(
                    indice_origen,
                    servicios_por_estacion,
                    itinerarios_estacion,
                )
                for indice_destino in range(numero_estaciones):
                    if itinerarios_estacion[indice_destino][0] != -1:
                        itinerario = itinerarios_estacion[indice_destino]
                        if itinerario[2] == -1:
                            indice_transbordo = -1
                        else:
                            indice_transbordo = itinerario[1]
                        grupo_encontrado = False
                        for grupo_itinerario in opciones:
                            if (
                                grupo_itinerario[0] == itinerario[0]
                                and grupo_itinerario[1] == indice_transbordo
                                and grupo_itinerario[2] == itinerario[2]
                            ):
                                grupo_encontrado = True
                                break
                        if not grupo_encontrado:
                            grupo_itinerario = [
                                itinerario[0],
                                indice_transbordo,
                                itinerario[2],
                                [],
                                0,
                            ]
                            opciones.append(grupo_itinerario)
                        grupo_itinerario[3].append(
                            [indice_destino, itinerario]
                        )
                        grupo_itinerario[4] |= 1 << indice_destino
            opciones_por_estacion.append(opciones)

        numero_slots_fijos = 0
        if total_pasajeros is not None:
            estaciones_con_ruta = 0
            for indice_origen in range(numero_estaciones):
                if (
                    self._abiertas[indice_origen]
                    and len(opciones_por_estacion[indice_origen]) > 0
                ):
                    estaciones_con_ruta += 1
            numero_slots_fijos = (
                estaciones_con_ruta * (1440 - minuto_inicio)
            )
            if total_pasajeros > 0 and numero_slots_fijos == 0:
                raise ValueError(
                    "No hay estaciones abiertas con rutas para generar pasajeros."
                )
        self._slots_simulacion_r10 = numero_slots_fijos

        generador = random.Random(semilla)
        marcas_evento_transbordo = [-1] * (
            numero_estaciones * numero_servicios
        )
        destinos_evento_transbordo = [0] * (
            numero_estaciones * numero_servicios
        )

        viajes = []
        for viaje in self._viajes_horario:
            viajes.append(
                [viaje[0], self._capacidad_universal, [], 0]
            )

        total_generados = 0
        total_abordajes = 0
        total_completados = 0
        total_destinos_alcanzados = 0
        espera_total = 0
        cantidad_esperas = 0
        espera_maxima = 0
        cola_maxima_red = 0
        indice_evento = 0
        while (
            indice_evento < len(self._eventos_horario)
            and self._eventos_horario[indice_evento][0] < minuto_inicio
        ):
            indice_evento += 1
        minuto = minuto_inicio
        indice_slot_fijo = 0

        while minuto < 1440:
            indice_estacion = 0
            while indice_estacion < numero_estaciones:
                llegadas = 0
                itinerarios_disponibles = []
                opciones_origen = opciones_por_estacion[indice_estacion]
                if self._abiertas[indice_estacion]:
                    if total_pasajeros is None:
                        flujo = flujos[indice_estacion]
                        if flujo >= 0:
                            llegadas = flujo + self._incremento_hora(minuto)
                    elif total_pasajeros > 0:
                        if len(opciones_origen) > 0:
                            llegadas = (
                                ((indice_slot_fijo + 1) * total_pasajeros)
                                // numero_slots_fijos
                                - (indice_slot_fijo * total_pasajeros)
                                // numero_slots_fijos
                            )
                            indice_slot_fijo += 1

                    if llegadas > 0:
                        if total_pasajeros is None:
                            if numero_estaciones < 2:
                                raise ValueError(
                                    "Se necesitan al menos dos estaciones para asignar destinos."
                                )
                            itinerarios_disponibles = (
                                self._itinerarios_con_salida_futura(
                                    indice_estacion,
                                    minuto,
                                    opciones_por_estacion[indice_estacion],
                                    salidas,
                                    posiciones_por_minuto,
                                    eventos_por_viaje,
                                    mascara_posterior,
                                )
                            )
                            if len(itinerarios_disponibles) == 0:
                                indice_estacion += 1
                                continue
                            itinerario_disponible = itinerarios_disponibles[
                                generador.randrange(len(itinerarios_disponibles))
                            ]
                            indice_destino = itinerario_disponible[0]
                            itinerario = itinerario_disponible[1]
                        else:
                            opcion = opciones_origen[
                                generador.randrange(len(opciones_origen))
                            ]
                            destino_elegido = opcion[3][
                                generador.randrange(len(opcion[3]))
                            ]
                            indice_destino = destino_elegido[0]
                            itinerario = destino_elegido[1]
                        total_generados += llegadas
                        metricas[indice_estacion][0] += llegadas
                        servicio = itinerario[0]
                        if servicio == -1:
                            cola_sin_ruta[indice_estacion].append(
                                [minuto, indice_destino, llegadas]
                            )
                        else:
                            colas[indice_estacion][servicio].append(
                                [
                                    minuto,
                                    indice_destino,
                                    itinerario[1],
                                    itinerario[2],
                                    llegadas,
                                ]
                            )
                        esperando_estacion[indice_estacion] += llegadas
                        cantidad_espera = esperando_estacion[indice_estacion]
                        if cantidad_espera > metricas[indice_estacion][1]:
                            metricas[indice_estacion][1] = cantidad_espera
                        if cantidad_espera > cola_maxima_red:
                            cola_maxima_red = cantidad_espera
                indice_estacion += 1

            while (
                indice_evento < len(self._eventos_horario)
                and self._eventos_horario[indice_evento][0] == minuto
            ):
                evento = self._eventos_horario[indice_evento]
                indice_viaje = evento[1]
                indice_estacion = evento[2]
                viaje = viajes[indice_viaje]
                indice_servicio = viaje[0]
                if self._abiertas[indice_estacion]:
                    manifiesto = viaje[2]
                    restantes = []
                    for pasajero in manifiesto:
                        if pasajero[1] == indice_estacion:
                            viaje[3] -= pasajero[3]
                            siguiente_servicio = pasajero[2]
                            if siguiente_servicio == -1:
                                total_completados += pasajero[3]
                                total_destinos_alcanzados += pasajero[3]
                                metricas[indice_estacion][6] += pasajero[3]
                            else:
                                destino = pasajero[0]
                                colas[indice_estacion][siguiente_servicio].append(
                                    [
                                        minuto,
                                        destino,
                                        destino,
                                        -1,
                                        pasajero[3],
                                    ]
                                )
                                esperando_estacion[indice_estacion] += pasajero[3]
                                cantidad_espera = esperando_estacion[indice_estacion]
                                if cantidad_espera > metricas[indice_estacion][1]:
                                    metricas[indice_estacion][1] = cantidad_espera
                                if cantidad_espera > cola_maxima_red:
                                    cola_maxima_red = cantidad_espera
                        else:
                            restantes.append(pasajero)
                    viaje[2] = restantes

                    cola = colas[indice_estacion][indice_servicio]
                    cabeza = 0
                    grupos_restantes = []
                    while cabeza < len(cola):
                        grupo = cola[cabeza]
                        puede_abordar = False
                        if viaje[3] < viaje[1]:
                            if grupo[3] == -1:
                                puede_abordar = (
                                    mascara_posterior[indice_evento]
                                    & (1 << grupo[1])
                                ) != 0
                            else:
                                indice_transbordo = grupo[2]
                                servicio_siguiente = grupo[3]
                                indice_cache = (
                                    indice_transbordo
                                    * numero_servicios
                                    + servicio_siguiente
                                )
                                marca_evento = indice_evento + 1
                                if (
                                    marcas_evento_transbordo[indice_cache]
                                    != marca_evento
                                ):
                                    destinos_posibles = 0
                                    evento_conexion = eventos_por_viaje[
                                        indice_viaje
                                    ][indice_transbordo]
                                    if (
                                        evento_conexion is not None
                                        and evento_conexion[1] > evento[3]
                                    ):
                                        minuto_siguiente = (
                                            evento_conexion[0] + 1
                                        )
                                        salidas_siguientes = salidas[
                                            indice_transbordo
                                        ][servicio_siguiente]
                                        posicion_siguiente = (
                                            self._primera_salida_desde(
                                                salidas_siguientes,
                                                minuto_siguiente,
                                            )
                                        )
                                        limite_transbordo = (
                                            evento_conexion[0] + 30
                                        )
                                        while (
                                            posicion_siguiente
                                            < len(salidas_siguientes)
                                            and salidas_siguientes[
                                                posicion_siguiente
                                            ][0]
                                            <= limite_transbordo
                                        ):
                                            evento_siguiente = (
                                                salidas_siguientes[
                                                    posicion_siguiente
                                                ]
                                            )
                                            destinos_posibles |= (
                                                mascara_posterior[
                                                    evento_siguiente[3]
                                                ]
                                            )
                                            posicion_siguiente += 1
                                    destinos_evento_transbordo[
                                        indice_cache
                                    ] = destinos_posibles
                                    marcas_evento_transbordo[
                                        indice_cache
                                    ] = marca_evento
                                puede_abordar = (
                                    destinos_evento_transbordo[indice_cache]
                                    & (1 << grupo[1])
                                ) != 0

                        if puede_abordar:
                            espacio = viaje[1] - viaje[3]
                            abordados = grupo[4]
                            if abordados > espacio:
                                abordados = espacio
                            espera = minuto - grupo[0]
                            espera_total += espera * abordados
                            cantidad_esperas += abordados
                            total_abordajes += abordados
                            metricas[indice_estacion][2] += espera * abordados
                            metricas[indice_estacion][3] += abordados
                            if espera > espera_maxima:
                                espera_maxima = espera
                            if espera > metricas[indice_estacion][4]:
                                metricas[indice_estacion][4] = espera
                            viaje[3] += abordados
                            viaje[2].append(
                                [
                                    grupo[1],
                                    grupo[2],
                                    grupo[3],
                                    abordados,
                                ]
                            )
                            grupo[4] -= abordados
                            esperando_estacion[indice_estacion] -= abordados
                        if grupo[4] > 0:
                            grupos_restantes.append(grupo)
                        cabeza += 1
                    colas[indice_estacion][indice_servicio] = (
                        grupos_restantes
                    )
                indice_evento += 1
            minuto += 1

        no_abordados = 0
        pasajeros_a_bordo = 0
        for viaje in viajes:
            for pasajero in viaje[2]:
                pasajeros_a_bordo += pasajero[3]

        filas_estaciones = []
        indice_estacion = 0
        while indice_estacion < numero_estaciones:
            total_en_cola = 0
            indice_servicio = 0
            while indice_servicio < numero_servicios:
                cola = colas[indice_estacion][indice_servicio]
                cabeza = 0
                while cabeza < len(cola):
                    grupo = cola[cabeza]
                    cantidad = grupo[4]
                    total_en_cola += cantidad
                    no_abordados += cantidad
                    espera = 1439 - grupo[0]
                    espera_total += espera * cantidad
                    cantidad_esperas += cantidad
                    metricas[indice_estacion][2] += espera * cantidad
                    metricas[indice_estacion][3] += cantidad
                    if espera > espera_maxima:
                        espera_maxima = espera
                    if espera > metricas[indice_estacion][4]:
                        metricas[indice_estacion][4] = espera
                    cabeza += 1
                indice_servicio += 1

            for grupo in cola_sin_ruta[indice_estacion]:
                cantidad = grupo[2]
                total_en_cola += cantidad
                no_abordados += cantidad
                espera = 1439 - grupo[0]
                espera_total += espera * cantidad
                cantidad_esperas += cantidad
                metricas[indice_estacion][2] += espera * cantidad
                metricas[indice_estacion][3] += cantidad
                if espera > espera_maxima:
                    espera_maxima = espera
                if espera > metricas[indice_estacion][4]:
                    metricas[indice_estacion][4] = espera

            metricas[indice_estacion][5] = total_en_cola
            if metricas[indice_estacion][3] > 0:
                promedio = (
                    metricas[indice_estacion][2]
                    / metricas[indice_estacion][3]
                )
            else:
                promedio = 0
            filas_estaciones.append(
                [
                    self._estaciones[indice_estacion],
                    metricas[indice_estacion][0],
                    total_en_cola,
                    metricas[indice_estacion][1],
                    promedio,
                    metricas[indice_estacion][4],
                    total_en_cola,
                    metricas[indice_estacion][6],
                ]
            )
            indice_estacion += 1

        if cantidad_esperas > 0:
            espera_promedio = espera_total / cantidad_esperas
        else:
            espera_promedio = 0
        pasajeros_en_red = total_generados - total_completados
        resumen = [
            total_generados,
            total_abordajes,
            no_abordados,
            espera_promedio,
            espera_maxima,
            cola_maxima_red,
            pasajeros_en_red,
            total_destinos_alcanzados,
        ]
        self._resultado_r10 = [resumen, filas_estaciones]
        return self._resultado_r10

    def resultado_simulacion(self):
        """R10: devuelve una copia del resultado para mostrar en el front."""
        resultado = []
        if len(self._resultado_r10) == 0:
            return resultado
        resumen = []
        for valor in self._resultado_r10[0]:
            resumen.append(valor)
        estaciones = []
        for fila in self._resultado_r10[1]:
            copia_fila = []
            for valor in fila:
                copia_fila.append(valor)
            estaciones.append(copia_fila)
        resultado.append(resumen)
        resultado.append(estaciones)
        return resultado

    def medir_rendimiento_r10(self, cantidades, hora_inicio="00:00"):
        """
        R11: mide R10 tres veces por tamaño y devuelve los promedios.

        Retorna tiempo base, mediciones por tamaño y E.
        """
        if not isinstance(cantidades, list) or len(cantidades) == 0:
            raise ValueError("Se requiere una lista de tamaños de prueba.")
        for cantidad in cantidades:
            self._validar_cantidad(cantidad, "Cada tamaño")
            if cantidad == 0:
                raise ValueError("Los tamaños del benchmark deben ser mayores que cero.")
        if self._convertir_hora(hora_inicio) is None:
            raise ValueError("La hora de inicio debe tener formato HH:MM.")

        self._asegurar_eventos_horario_actualizados()
        repeticiones = 3
        tiempo_base_total = 0
        for _ in range(repeticiones):
            inicio_base = time.perf_counter()
            self.simular_dia(
                semilla=42,
                total_pasajeros=0,
                hora_inicio=hora_inicio,
            )
            tiempo_base_total += time.perf_counter() - inicio_base
        segundos_base = tiempo_base_total / repeticiones
        numero_slots = self._slots_simulacion_r10
        mediciones = []
        for cantidad in cantidades:
            mediciones.append([cantidad, 0])

        repeticion = 0
        while repeticion < repeticiones:
            if repeticion % 2 == 0:
                indice = 0
                paso = 1
                limite = len(cantidades)
            else:
                indice = len(cantidades) - 1
                paso = -1
                limite = -1
            while indice != limite:
                cantidad = cantidades[indice]
                inicio = time.perf_counter()
                resultado = self.simular_dia(
                    semilla=42,
                    total_pasajeros=cantidad,
                    hora_inicio=hora_inicio,
                )
                segundos = time.perf_counter() - inicio
                if resultado[0][0] != cantidad:
                    raise RuntimeError(
                        "La simulación no generó el total exacto solicitado."
                    )
                mediciones[indice][1] += segundos
                indice += paso
            repeticion += 1

        for medicion in mediciones:
            medicion[1] /= repeticiones
        return [segundos_base, mediciones, numero_slots]

    def _incremento_hora(self, minuto):
        """R10: suma los incrementos de demanda activos en el minuto."""
        incremento = 0
        for periodo in self._horas_pico:
            desde = periodo[0]
            hasta = periodo[1]
            if desde <= hasta:
                if desde <= minuto < hasta:
                    incremento += periodo[2]
            elif minuto >= desde or minuto < hasta:
                incremento += periodo[2]
        return incremento

    def _validar_estacion_configurable(self, estacion):
        """R10: valida y normaliza una estación de demanda."""
        nombre = self._normalizar(estacion)
        if self._posicion_estacion(nombre) == -1:
            raise ValueError("La estación indicada no existe.")
        return nombre

    @staticmethod
    def _validar_cantidad(cantidad, nombre):
        """R10/R11: exige una cantidad entera no negativa."""
        if not isinstance(cantidad, int) or cantidad < 0:
            raise ValueError(nombre + " debe ser un entero no negativo.")

    def buses_rutas(self):
        """R7: devuelve los buses disponibles para seleccionar una ruta."""
        buses = []
        for informacion in self._rutas_info:
            bus = self._nombre_bus(informacion[0])
            if len(buses) == 0 or buses[-1] != bus:
                buses.append(bus)
        return buses

    def servicios(self, bus):
        """
        R7: devuelve los servicios direccionales de un bus en O(R).
        """
        bus_normalizado = self._normalizar(bus)
        encontrados = []
        for informacion in self._rutas_info:
            nombre_bus = self._normalizar(self._nombre_bus(informacion[0]))
            if nombre_bus == bus_normalizado:
                encontrados.append(informacion[0])
        return encontrados

    def estaciones(self):
        """R7/R8/R10: devuelve los nombres usados en los selectores."""
        nombres = []
        for nombre in self._estaciones:
            nombres.append(nombre)
        return nombres

    def recorrido(self, ruta, al_reves=False):
        """
        R7: devuelve una copia del recorrido, en orden normal o inverso.

        Cuesta O(R + P); la copia protege la lista interna.
        """
        indice_ruta = self._indice_ruta(ruta)
        if indice_ruta == -1:
            return []

        paradas = self._rutas_info[indice_ruta][1]
        resultado = []
        if al_reves:
            posicion = len(paradas) - 1
            while posicion >= 0:
                resultado.append(paradas[posicion])
                posicion -= 1
        else:
            for parada in paradas:
                resultado.append(parada)
        return resultado

    def agregar_parada(self, ruta, nueva, despues_de):
        """
        R7: inserta una estación existente dentro de un servicio.

        Cuesta O(R + P + log N). R9 guarda las listas anterior y nueva;
        invalida las cachés de R6 y el índice horario de R10.
        """
        indice_ruta = self._indice_ruta(ruta)
        if indice_ruta == -1:
            raise ValueError("El recorrido seleccionado no existe.")

        nombre_nuevo = self._normalizar(nueva)
        posicion_estacion = self._posicion_estacion(nombre_nuevo)
        if posicion_estacion == -1:
            raise ValueError("Solo se pueden agregar estaciones existentes.")

        paradas = self._rutas_info[indice_ruta][1]
        posicion_nueva = self._buscar_en_lista(paradas, nombre_nuevo)
        if posicion_nueva != -1:
            raise ValueError("La estación ya está en este recorrido.")

        posicion_anterior = self._buscar_en_lista(
            paradas, self._normalizar(despues_de)
        )
        if posicion_anterior == -1 or posicion_anterior >= len(paradas) - 1:
            raise ValueError("Seleccione una parada con otra parada después.")

        nuevas_paradas = []
        posicion = 0
        while posicion < len(paradas):
            nuevas_paradas.append(paradas[posicion])
            if posicion == posicion_anterior:
                nuevas_paradas.append(nombre_nuevo)
            posicion += 1
        self._guardar_cambio(
            ["ruta", indice_ruta, paradas, nuevas_paradas]
        )
        self._rutas_info[indice_ruta][1] = nuevas_paradas
        self._invalidar_ranking()
        self._invalidar_eventos_horario()
        self._resultado_r10 = []

    def quitar_parada(self, ruta, estacion):
        """
        R7: quita una estación del recorrido, no de la red.

        Cuesta O(R + P). R9 conserva las listas anterior y nueva; invalida
        las cachés de R6 y el índice horario de R10.
        """
        indice_ruta = self._indice_ruta(ruta)
        if indice_ruta == -1:
            raise ValueError("El recorrido seleccionado no existe.")

        paradas = self._rutas_info[indice_ruta][1]
        nombre = self._normalizar(estacion)
        posicion_eliminar = self._buscar_en_lista(paradas, nombre)
        if posicion_eliminar == -1:
            raise ValueError("La estación no pertenece a este recorrido.")

        nuevas_paradas = []
        posicion = 0
        while posicion < len(paradas):
            if posicion != posicion_eliminar:
                nuevas_paradas.append(paradas[posicion])
            posicion += 1
        self._guardar_cambio(
            ["ruta", indice_ruta, paradas, nuevas_paradas]
        )
        self._rutas_info[indice_ruta][1] = nuevas_paradas
        self._invalidar_ranking()
        self._invalidar_eventos_horario()
        self._resultado_r10 = []

    def cerrar(self, nombre):
        """R8/R9: cierra una estación y guarda el cambio para deshacerlo."""
        self._cambiar_estado_estacion(nombre, False)

    def reabrir(self, nombre):
        """R8/R9: reabre una estación y guarda el cambio para deshacerlo."""
        self._cambiar_estado_estacion(nombre, True)

    def deshacer(self):
        """
        R9: aplica la última acción de la pila en O(1) amortizado.
        """
        if len(self._historial_deshacer) == 0:
            return False

        anterior = self._historial_deshacer.pop()
        self._aplicar_cambio_historial(anterior, False)
        self._historial_rehacer.append(anterior)
        return True

    def rehacer(self):
        """R9: reaplica la última acción de la pila en O(1) amortizado."""
        if len(self._historial_rehacer) == 0:
            return False

        siguiente = self._historial_rehacer.pop()
        self._aplicar_cambio_historial(siguiente, True)
        self._historial_deshacer.append(siguiente)
        return True

    def proximo_bus(self, estacion, bus, hora):
        """
        R4: devuelve la próxima llegada del bus a una estación.

        Busca en las listas ordenadas de buses y horarios: O(log B + V log H).
        Acepta el bus base y sus variantes direccionales.
        """
        estacion_normalizada = self._normalizar(estacion)
        bus_normalizado = self._normalizar(bus)
        minuto_objetivo = self._convertir_hora(hora)
        if minuto_objetivo is None or bus_normalizado == "":
            return None

        posicion_bus = self._posicion_bus(bus_normalizado)
        siguiente_minuto = -1
        siguiente_hora = None

        while posicion_bus < len(self._buses):
            nombre_bus = self._buses[posicion_bus]
            if nombre_bus != bus_normalizado and not nombre_bus.startswith(
                bus_normalizado + "-"
            ):
                break

            posicion_horario = self._posicion_horario(
                nombre_bus, estacion_normalizada, minuto_objetivo
            )
            if posicion_horario < len(self._horarios):
                fila = self._horarios[posicion_horario]
                if fila[0] == nombre_bus and fila[1] == estacion_normalizada:
                    if siguiente_minuto == -1 or fila[2] < siguiente_minuto:
                        siguiente_minuto = fila[2]
                        siguiente_hora = fila[3]
            posicion_bus += 1

        return siguiente_hora

    def viaje(self, origen, destino):
        """
        R5: encuentra el viaje directo o con un transbordo de menos paradas.

        Usa listas de paradas en orden de recorrido. Cuesta
        O(log N + R²P² + R²P log N) y devuelve segmentos para el front.
        """
        origen_normalizado = self._normalizar(origen)
        destino_normalizado = self._normalizar(destino)

        existe_origen, abierta_origen = self.estado(origen_normalizado)
        existe_destino, abierta_destino = self.estado(destino_normalizado)
        if not existe_origen or not existe_destino:
            return []
        if not abierta_origen or not abierta_destino:
            return []
        if origen_normalizado == destino_normalizado:
            return []

        mejor_segmentos = []
        mejor_paradas = -1

        # Considera cada servicio directo; la diferencia de indices cuenta
        # cuantas paradas se recorren desde el origen hasta el destino.
        for informacion in self._rutas_info:
            servicio = informacion[0]
            paradas = informacion[1]
            indice_origen = self._buscar_en_lista(paradas, origen_normalizado)
            indice_destino = self._buscar_en_lista(paradas, destino_normalizado)
            if indice_origen != -1 and indice_destino > indice_origen:
                cantidad = indice_destino - indice_origen
                if mejor_paradas == -1 or cantidad < mejor_paradas:
                    mejor_paradas = cantidad
                    mejor_segmentos = [
                        [
                            self._nombre_bus(servicio),
                            origen_normalizado,
                            destino_normalizado,
                        ]
                    ]

        indice_ruta_a = 0
        while indice_ruta_a < len(self._rutas_info):
            servicio_a = self._rutas_info[indice_ruta_a][0]
            paradas_a = self._rutas_info[indice_ruta_a][1]
            indice_origen = self._buscar_en_lista(paradas_a, origen_normalizado)
            if indice_origen != -1:
                indice_ruta_b = 0
                while indice_ruta_b < len(self._rutas_info):
                    if indice_ruta_b != indice_ruta_a:
                        servicio_b = self._rutas_info[indice_ruta_b][0]
                        paradas_b = self._rutas_info[indice_ruta_b][1]
                        indice_destino = self._buscar_en_lista(paradas_b, destino_normalizado)
                        if indice_destino != -1:
                            indice_parada = 0
                            while indice_parada < len(paradas_a):
                                transbordo = paradas_a[indice_parada]
                                indice_b = self._buscar_en_lista(paradas_b, transbordo)
                                if (
                                    transbordo != origen_normalizado
                                    and transbordo != destino_normalizado
                                    and indice_parada > indice_origen
                                    and indice_b != -1
                                    and indice_destino > indice_b
                                ):
                                    existe_transbordo, abierta_transbordo = self.estado(transbordo)
                                    if existe_transbordo and abierta_transbordo:
                                        cantidad = (
                                            indice_parada - indice_origen
                                            + indice_destino - indice_b
                                        )
                                        if mejor_paradas == -1 or cantidad < mejor_paradas:
                                            mejor_paradas = cantidad
                                            mejor_segmentos = [
                                                [
                                                    self._nombre_bus(servicio_a),
                                                    origen_normalizado,
                                                    transbordo,
                                                ],
                                                [
                                                    self._nombre_bus(servicio_b),
                                                    transbordo,
                                                    destino_normalizado,
                                                ],
                                            ]
                                indice_parada += 1
                    indice_ruta_b += 1
            indice_ruta_a += 1

        return mejor_segmentos

    @staticmethod
    def _nombre_bus(identificador_servicio):
        """
        R5/R7: quita el sufijo direccional numérico del identificador.
        """
        separador = identificador_servicio.rfind("-")
        if separador == -1:
            return identificador_servicio

        sufijo = identificador_servicio[separador + 1:]
        if sufijo.isdigit():
            return identificador_servicio[:separador]
        return identificador_servicio

    def ranking(self, k):
        """
        R6: devuelve las k estaciones abiertas con más buses diarios.

        Usa una lista cacheada y ordenada por frecuencia y nombre. Construirla
        cuesta O(H + R + J log J + U log U + U log N); consultar cuesta O(M).
        """
        if k <= 0:
            return []

        if self._ranking_desactualizado:
            self._ranking = self._construir_ranking()
            self._ranking_desactualizado = False

        resultados = []
        posicion = 0
        while posicion < len(self._ranking) and len(resultados) < k:
            estacion = self._ranking[posicion]
            indice_estacion = estacion[2]
            if (
                indice_estacion != -1
                and self._abiertas[indice_estacion]
            ):
                resultados.append(estacion[0])
            posicion += 1

        return resultados

    def _cargar_rutas(self, ruta_archivo):
        """
        R5–R7/R10: carga las rutas como listas ordenadas de paradas.

        Ordenar q filas cuesta O(q log q); agruparlas, O(q).
        """
        filas = []
        with open(ruta_archivo, "r", encoding="utf-8-sig", newline="") as archivo:
            lector = csv.reader(archivo)
            encabezado = next(lector, None)
            if encabezado is None:
                return []

            indice_ruta = -1
            indice_orden = -1
            indice_estacion = -1
            indice = 0
            while indice < len(encabezado):
                nombre = encabezado[indice].strip().lower()
                if nombre == "ruta":
                    indice_ruta = indice
                elif nombre == "orden":
                    indice_orden = indice
                elif nombre == "estacion":
                    indice_estacion = indice
                indice += 1

            if indice_ruta == -1 or indice_orden == -1 or indice_estacion == -1:
                raise ValueError("rutas.csv debe tener ruta, orden y estacion")

            for fila in lector:
                if indice_ruta >= len(fila) or indice_orden >= len(fila) or indice_estacion >= len(fila):
                    continue
                try:
                    orden = int(fila[indice_orden].strip())
                except ValueError:
                    continue
                ruta = fila[indice_ruta].strip()
                estacion = fila[indice_estacion].strip().upper()
                filas.append([ruta, orden, estacion])

        filas = self._ordenar_rutas(filas)
        resultado = []
        indice_fila = 0
        while indice_fila < len(filas):
            ruta = filas[indice_fila][0]
            paradas = []
            while indice_fila < len(filas) and filas[indice_fila][0] == ruta:
                estacion = filas[indice_fila][2]
                if len(paradas) == 0 or paradas[-1] != estacion:
                    paradas.append(estacion)
                indice_fila += 1
            resultado.append([ruta, paradas])
        return resultado

    def _cargar_horarios(self, ruta_archivo):
        """
        R4/R6/R10: carga horarios ordenados por ruta, estación y minuto.
        """
        filas = []
        with open(ruta_archivo, "r", encoding="utf-8-sig", newline="") as archivo:
            lector = csv.reader(archivo)
            encabezado = next(lector, None)
            if encabezado is None:
                return []

            indice_ruta = -1
            indice_estacion = -1
            indice_hora = -1
            indice = 0
            while indice < len(encabezado):
                nombre = encabezado[indice].strip().lower()
                if nombre == "ruta":
                    indice_ruta = indice
                elif nombre == "estacion":
                    indice_estacion = indice
                elif nombre == "hora":
                    indice_hora = indice
                indice += 1

            if indice_ruta == -1 or indice_estacion == -1 or indice_hora == -1:
                raise ValueError("horarios.csv debe tener ruta, estacion y hora")

            for fila in lector:
                if indice_ruta >= len(fila) or indice_estacion >= len(fila) or indice_hora >= len(fila):
                    continue
                texto_hora = fila[indice_hora].strip()
                minuto = self._convertir_hora(texto_hora)
                if minuto is None:
                    continue
                ruta = fila[indice_ruta].strip()
                estacion = fila[indice_estacion].strip().upper()
                filas.append([ruta, estacion, minuto, texto_hora])

        return self._ordenar_horarios(filas)

    def _obtener_buses(self):
        """R4/R7: crea la lista ordenada de servicios del archivo horario."""
        buses = []
        for fila in self._horarios:
            if len(buses) == 0 or buses[-1] != fila[0]:
                buses.append(fila[0])
        return buses

    def _construir_ranking(self):
        """
        R6: estima frecuencias por servicio y las agrupa por estación.

        Las listas ordenadas permiten agrupar en O(H + R); ordenar y ubicar
        las paradas cuesta O(J log J + U log N), y ordenar el ranking O(U log U).
        """
        frecuencias_servicio = []
        posicion_horario = 0
        while posicion_horario < len(self._horarios):
            servicio = self._horarios[posicion_horario][0]
            frecuencia_maxima = 0
            while (
                posicion_horario < len(self._horarios)
                and self._horarios[posicion_horario][0] == servicio
            ):
                estacion = self._horarios[posicion_horario][1]
                cantidad = 0
                while (
                    posicion_horario < len(self._horarios)
                    and self._horarios[posicion_horario][0] == servicio
                    and self._horarios[posicion_horario][1] == estacion
                ):
                    cantidad += 1
                    posicion_horario += 1
                if cantidad > frecuencia_maxima:
                    frecuencia_maxima = cantidad
            frecuencias_servicio.append([servicio, frecuencia_maxima])

        conteos_parada = []
        posicion_frecuencia = 0
        for ruta in self._rutas_info:
            while (
                posicion_frecuencia < len(frecuencias_servicio)
                and frecuencias_servicio[posicion_frecuencia][0] < ruta[0]
            ):
                posicion_frecuencia += 1

            frecuencia = 0
            if (
                posicion_frecuencia < len(frecuencias_servicio)
                and frecuencias_servicio[posicion_frecuencia][0] == ruta[0]
            ):
                frecuencia = frecuencias_servicio[posicion_frecuencia][1]

            for estacion in ruta[1]:
                conteos_parada.append([estacion, frecuencia])

        conteos_parada = self._ordenar_conteos_parada(conteos_parada)
        conteos = []
        posicion = 0
        while posicion < len(conteos_parada):
            estacion = conteos_parada[posicion][0]
            cantidad = 0
            while (
                posicion < len(conteos_parada)
                and conteos_parada[posicion][0] == estacion
            ):
                cantidad += conteos_parada[posicion][1]
                posicion += 1
            if cantidad > 0:
                conteos.append(
                    [estacion, cantidad, self._posicion_estacion(estacion)]
                )
        return self._ordenar_ranking(conteos)

    @classmethod
    def _ordenar_conteos_parada(cls, filas):
        """R6: ordena frecuencias por estación con merge sort, O(J log J)."""
        if len(filas) < 2:
            return filas

        medio = len(filas) // 2
        izquierda = cls._ordenar_conteos_parada(filas[:medio])
        derecha = cls._ordenar_conteos_parada(filas[medio:])
        resultado = []
        i = 0
        j = 0
        while i < len(izquierda) and j < len(derecha):
            if izquierda[i][0] <= derecha[j][0]:
                resultado.append(izquierda[i])
                i += 1
            else:
                resultado.append(derecha[j])
                j += 1
        while i < len(izquierda):
            resultado.append(izquierda[i])
            i += 1
        while j < len(derecha):
            resultado.append(derecha[j])
            j += 1
        return resultado

    def _buscar_en_lista(self, valores, valor):
        """R5/R7/R10: busca una parada en una ruta en O(P)."""
        posicion = 0
        while posicion < len(valores):
            if valores[posicion] == valor:
                return posicion
            posicion += 1
        return -1

    def _indice_ruta(self, ruta):
        """R7: obtiene el índice de un servicio direccional en O(R)."""
        identificador = str(ruta).strip()
        posicion = 0
        while posicion < len(self._rutas_info):
            if self._rutas_info[posicion][0] == identificador:
                return posicion
            posicion += 1
        return -1

    def _cambiar_estado_estacion(self, nombre, abierta):
        """R8/R9: cambia el estado con búsqueda O(log N) y registro O(1)."""
        estacion = self._normalizar(nombre)
        posicion = self._posicion_estacion(estacion)
        if posicion == -1:
            raise ValueError("La estación no existe.")
        if self._abiertas[posicion] == abierta:
            return False

        estado_anterior = self._abiertas[posicion]
        self._guardar_cambio(
            ["estado", posicion, estado_anterior, abierta]
        )
        self._abiertas[posicion] = abierta
        self._resultado_r10 = []
        return True

    def _guardar_cambio(self, cambio):
        """R9: guarda una acción y descarta la rama de rehacer."""
        self._historial_deshacer.append(cambio)
        self._historial_rehacer = []

    def _aplicar_cambio_historial(self, cambio, rehacer):
        """R9: aplica una acción guardada sin copiar la red."""
        posicion_valor = 3 if rehacer else 2
        if cambio[0] == "ruta":
            self._rutas_info[cambio[1]][1] = cambio[posicion_valor]
            self._invalidar_ranking()
            self._invalidar_eventos_horario()
        else:
            self._abiertas[cambio[1]] = cambio[posicion_valor]
        self._resultado_r10 = []

    def _invalidar_ranking(self):
        """R6/R7/R9: marca el ranking para reconstruirlo tras editar una ruta."""
        self._ranking_desactualizado = True

    def _posicion_estacion(self, estacion):
        """R4/R6–R8/R10: busca una estación ordenada en O(log N)."""
        inicio = 0
        fin = len(self._estaciones)
        while inicio < fin:
            medio = (inicio + fin) // 2
            if self._estaciones[medio] < estacion:
                inicio = medio + 1
            else:
                fin = medio
        if inicio < len(self._estaciones) and self._estaciones[inicio] == estacion:
            return inicio
        return -1

    def _posicion_bus(self, bus):
        """R4: busca un bus y el inicio de sus variantes en O(log B)."""
        inicio = 0
        fin = len(self._buses)
        while inicio < fin:
            medio = (inicio + fin) // 2
            if self._buses[medio] < bus:
                inicio = medio + 1
            else:
                fin = medio
        return inicio

    def _posicion_horario(self, ruta, estacion, minuto):
        """R4: busca con binaria la primera fila desde la hora solicitada."""
        inicio = 0
        fin = len(self._horarios)
        while inicio < fin:
            medio = (inicio + fin) // 2
            fila = self._horarios[medio]
            anterior = (
                fila[0] < ruta
                or (
                    fila[0] == ruta
                    and (
                        fila[1] < estacion
                        or (fila[1] == estacion and fila[2] < minuto)
                    )
                )
            )
            if anterior:
                inicio = medio + 1
            else:
                fin = medio
        return inicio

    @staticmethod
    def _convertir_hora(hora):
        """
        R4/R10: convierte HH:MM a minutos desde medianoche en O(L).
        """
        texto = str(hora).strip()
        partes = texto.split(":")
        if len(partes) < 2:
            return None
        try:
            horas = int(partes[0])
            minutos = int(partes[1])
        except ValueError:
            return None
        if horas < 0 or horas > 23 or minutos < 0 or minutos > 59:
            return None
        return horas * 60 + minutos

    @classmethod
    def _ordenar_rutas(cls, filas):
        """
        R5–R7/R10: ordena filas de ruta con merge sort, O(X log X).
        """
        if len(filas) < 2:
            return filas

        medio = len(filas) // 2
        izquierda = cls._ordenar_rutas(filas[:medio])
        derecha = cls._ordenar_rutas(filas[medio:])
        resultado = []
        indice_izquierda = 0
        indice_derecha = 0

        while indice_izquierda < len(izquierda) and indice_derecha < len(derecha):
            fila_izquierda = izquierda[indice_izquierda]
            fila_derecha = derecha[indice_derecha]
            izquierda_antes = (
                fila_izquierda[0] < fila_derecha[0]
                or (
                    fila_izquierda[0] == fila_derecha[0]
                    and fila_izquierda[1] <= fila_derecha[1]
                )
            )
            if izquierda_antes:
                resultado.append(fila_izquierda)
                indice_izquierda += 1
            else:
                resultado.append(fila_derecha)
                indice_derecha += 1

        while indice_izquierda < len(izquierda):
            resultado.append(izquierda[indice_izquierda])
            indice_izquierda += 1
        while indice_derecha < len(derecha):
            resultado.append(derecha[indice_derecha])
            indice_derecha += 1
        return resultado

    @classmethod
    def _ordenar_horarios(cls, filas):
        """
        R4/R6/R10: ordena horarios para búsquedas binarias, O(H log H).
        """
        if len(filas) < 2:
            return filas

        medio = len(filas) // 2
        izquierda = cls._ordenar_horarios(filas[:medio])
        derecha = cls._ordenar_horarios(filas[medio:])
        resultado = []
        indice_izquierda = 0
        indice_derecha = 0

        while indice_izquierda < len(izquierda) and indice_derecha < len(derecha):
            fila_izquierda = izquierda[indice_izquierda]
            fila_derecha = derecha[indice_derecha]
            clave_izquierda = (
                fila_izquierda[0],
                fila_izquierda[1],
                fila_izquierda[2],
            )
            clave_derecha = (
                fila_derecha[0],
                fila_derecha[1],
                fila_derecha[2],
            )
            if clave_izquierda <= clave_derecha:
                resultado.append(fila_izquierda)
                indice_izquierda += 1
            else:
                resultado.append(fila_derecha)
                indice_derecha += 1

        while indice_izquierda < len(izquierda):
            resultado.append(izquierda[indice_izquierda])
            indice_izquierda += 1
        while indice_derecha < len(derecha):
            resultado.append(derecha[indice_derecha])
            indice_derecha += 1
        return resultado

    @classmethod
    def _ordenar_ranking(cls, filas):
        """R6: ordena estaciones por conteo y nombre, O(U log U)."""
        if len(filas) < 2:
            return filas

        medio = len(filas) // 2
        izquierda = cls._ordenar_ranking(filas[:medio])
        derecha = cls._ordenar_ranking(filas[medio:])
        resultado = []
        indice_izquierda = 0
        indice_derecha = 0

        while indice_izquierda < len(izquierda) and indice_derecha < len(derecha):
            fila_izquierda = izquierda[indice_izquierda]
            fila_derecha = derecha[indice_derecha]
            izquierda_antes = (
                fila_izquierda[1] > fila_derecha[1]
                or (
                    fila_izquierda[1] == fila_derecha[1]
                    and fila_izquierda[0] < fila_derecha[0]
                )
            )
            if izquierda_antes:
                resultado.append(fila_izquierda)
                indice_izquierda += 1
            else:
                resultado.append(fila_derecha)
                indice_derecha += 1

        while indice_izquierda < len(izquierda):
            resultado.append(izquierda[indice_izquierda])
            indice_izquierda += 1
        while indice_derecha < len(derecha):
            resultado.append(derecha[indice_derecha])
            indice_derecha += 1
        return resultado

    def estado(self, nombre):
        """
        R1: devuelve si una estación existe y está abierta.

        Busca en `_estaciones` por binaria: O(log N).
        """
        nombre_normalizado = self._normalizar(nombre)
        posicion = self._posicion_insercion(nombre_normalizado)

        if posicion < len(self._estaciones):
            if self._estaciones[posicion] == nombre_normalizado:
                return (True, self._abiertas[posicion])

        return (False, False)

    def autocompletar(self, prefijo, k):
        """
        R2: devuelve hasta k estaciones abiertas con el prefijo indicado.

        Binaria más recorrido de coincidencias: O(log N + M).
        """
        if k <= 0:
            return []

        prefijo_normalizado = self._normalizar(prefijo)
        posicion = self._posicion_insercion(prefijo_normalizado)
        resultados = []

        while posicion < len(self._estaciones) and len(resultados) < k:
            nombre = self._estaciones[posicion]
            if not nombre.startswith(prefijo_normalizado):
                break
            if self._abiertas[posicion]:
                resultados.append(nombre)
            posicion += 1

        return resultados

    def rango(self, desde, hasta):
        """
        R3: devuelve las estaciones abiertas dentro del rango inclusivo.

        Busca el límite por binaria y recorre el rango: O(log N + K_r).
        """
        limite_inferior = self._normalizar(desde)
        limite_superior = self._normalizar(hasta)
        resultados = []

        if limite_inferior <= limite_superior:
            posicion = self._posicion_insercion(limite_inferior)
            while posicion < len(self._estaciones):
                nombre = self._estaciones[posicion]
                if nombre > limite_superior:
                    break
                if self._abiertas[posicion]:
                    resultados.append(nombre)
                posicion += 1
        else:
            posicion = self._posicion_insercion(limite_inferior)
            if posicion < len(self._estaciones):
                if self._estaciones[posicion] == limite_inferior:
                    posicion += 1
            posicion -= 1

            while posicion >= 0:
                nombre = self._estaciones[posicion]
                if nombre < limite_superior:
                    break
                if self._abiertas[posicion]:
                    resultados.append(nombre)
                posicion -= 1

        return resultados

    @staticmethod
    def _normalizar(nombre):
        """Compartida: normaliza nombres en O(L) para búsquedas R1–R10."""
        return str(nombre).strip().upper()

    def _posicion_insercion(self, nombre):
        """
        R1–R3: ubica el límite inferior en la lista en O(log N).
        """
        inicio = 0
        fin = len(self._estaciones)

        while inicio < fin:
            medio = (inicio + fin) // 2
            if self._estaciones[medio] < nombre:
                inicio = medio + 1
            else:
                fin = medio

        return inicio

    @classmethod
    def _ordenar(cls, estaciones):
        """
        R1: ordena estaciones con merge sort en O(N log N) y O(N) espacio.
        """
        if len(estaciones) < 2:
            return estaciones

        medio = len(estaciones) // 2
        izquierda = cls._ordenar(estaciones[:medio])
        derecha = cls._ordenar(estaciones[medio:])
        resultado = []
        indice_izquierda = 0
        indice_derecha = 0

        while indice_izquierda < len(izquierda) and indice_derecha < len(derecha):
            if izquierda[indice_izquierda][0] <= derecha[indice_derecha][0]:
                resultado.append(izquierda[indice_izquierda])
                indice_izquierda += 1
            else:
                resultado.append(derecha[indice_derecha])
                indice_derecha += 1

        while indice_izquierda < len(izquierda):
            resultado.append(izquierda[indice_izquierda])
            indice_izquierda += 1

        while indice_derecha < len(derecha):
            resultado.append(derecha[indice_derecha])
            indice_derecha += 1

        return resultado
