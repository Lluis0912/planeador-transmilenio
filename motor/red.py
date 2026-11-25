import csv
import random


def simular_fila(llegadas, frecuencia, capacidad):
    """
    R10: simula una fila FIFO durante el periodo indicado por `llegadas`.

    Cada posicion de llegadas representa pasajeros que llegan en ese minuto.
    Un bus aparece en el minuto 0 y luego cada `frecuencia` minutos; lleva
    hasta `capacidad` personas. Devuelve:
    [abordados, espera_promedio, espera_maxima, cola_maxima, no_abordados].

    Los tiempos son minutos y la espera promedio se pondera por pasajero.
    Los que siguen esperando al terminar cuentan como no_abordados, y su
    espera hasta el fin del periodo se incluye en las métricas.

    Complejidad: O(t + p), donde t es la duración en minutos y p los
    pasajeros en cola. Los grupos con el mismo minuto se almacenan juntos
    para evitar crear un objeto por pasajero.
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
    Red en memoria de las estaciones disponibles.

    Estructura principal: dos listas paralelas ordenadas alfabéticamente.
    - _estaciones guarda los nombres sin repetir.
    - _abiertas guarda el estado correspondiente a cada nombre.

    Mantener las listas ordenadas permite buscar estaciones con búsqueda binaria.
    Es mas eficiente que recorrer todas las estaciones para cada consulta:
    O(log n) para buscar, frente a O(n) para una busqueda lineal.

    Las listas son una estructura permitida por las reglas del proyecto.
    La clase no usa diccionarios ni conjuntos dentro de motor/.
    """
    def __init__(self, carpeta):
        # Complejidad: O(n log n), por ordenar n nombres con merge sort,
        # mas O(n) para leer y consolidar el archivo.
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

        # R4-R6 cargan las otras dos tablas permitidas por el proyecto.
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
        """Configura la tasa base que genera demanda en todas las estaciones."""
        self._validar_cantidad(pasajeros_por_minuto, "El flujo")
        self._flujo_global = pasajeros_por_minuto
        self._resultado_r10 = []

    def aplicar_flujo_global_a_estaciones(self, pasajeros_por_minuto):
        """
        Aplica la tasa global a todas las estaciones y limpia tasas locales.

        Recorre S configuraciones de estación: O(S) tiempo y O(1) espacio
        adicional. Los destinos se eligen aleatoriamente por lote al simular.
        """
        self.configurar_demanda_global(pasajeros_por_minuto)
        for configuracion in self._flujos_estaciones:
            configuracion[1] = -1

    def configurar_demanda_estacion(self, estacion, pasajeros_por_minuto=None):
        """
        Configura el flujo local de una estación, sin fijar destinos.

        Si no se entrega tasa local, la estación usa el flujo global.
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
        """Quita la tasa local para volver a usar el flujo global."""
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
        """Asigna una única capacidad para todos los buses en O(1)."""
        self._validar_cantidad(capacidad, "La capacidad")
        if capacidad == 0:
            raise ValueError("La capacidad debe ser mayor que cero.")
        self._capacidad_universal = capacidad
        self._resultado_r10 = []

    def agregar_hora_pico(self, desde, hasta, pasajeros_extra):
        """
        Añade demanda por minuto a todas las estaciones abiertas en un intervalo.

        Acepta HH:MM; si `hasta` es menor que `desde`, el intervalo cruza
        medianoche. En el caso habitual [14:00, 17:00), incluye las 14:00 y no
        incluye las 17:00.
        """
        self._validar_cantidad(pasajeros_extra, "El incremento")
        minuto_desde = self._convertir_hora(desde)
        minuto_hasta = self._convertir_hora(hasta)
        if minuto_desde is None or minuto_hasta is None:
            raise ValueError("Las horas deben tener el formato HH:MM.")
        self._horas_pico.append([minuto_desde, minuto_hasta, pasajeros_extra])
        self._resultado_r10 = []

    def limpiar_horas_pico(self):
        """Quita todos los incrementos de demanda personalizados."""
        self._horas_pico = []
        self._resultado_r10 = []

    def _construir_eventos_horario(self):
        """
        Agrupa las llegadas programadas por servicio, parada y viaje indexado.

        Los CSV no tienen identificador de vehículo; por ello, el evento numero
        i de cada parada de un servicio se asocia al viaje i. Es una
        aproximación de los datos disponibles, y se documenta en README.

        Si H son las filas de horario y P el máximo de paradas de un servicio,
        ubicar estaciones cuesta O(H*P) y ordenar los eventos O(H log H).
        Las listas agrupadas requieren O(H) espacio.
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
        """Marca el índice R10 para reconstruirlo tras cambios R7."""
        self._eventos_horario_desactualizados = True

    def _asegurar_eventos_horario_actualizados(self):
        """Reconstruye una sola vez el índice R10 cuando cambian recorridos."""
        if self._eventos_horario_desactualizados:
            self._eventos_horario, self._viajes_horario = (
                self._construir_eventos_horario()
            )
            self._eventos_horario_desactualizados = False

    @classmethod
    def _ordenar_eventos_horario(cls, eventos):
        """Ordena llegadas por minuto con merge sort: O(H log H), espacio O(H)."""
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

    def _simular_dia_por_frecuencia(self, frecuencia):
        """
        Prototipo privado anterior de R10; no lo usa el frontend.

        La simulación activa con destinos aleatorios y horarios reales es
        `simular_dia()`, más abajo. No es parte del contrato de la interfaz;
        solo documenta el modelo inicial basado en frecuencia.

        Demanda: una tasa global y un destino, con excepciones por estación;
        los incrementos horarios se suman a la tasa aplicable. Servicio:
        recorridos direccionales de rutas.csv, un bus por servicio cada
        `frecuencia` minutos, capacidad global o sobrescrita por bus.
        Al transferir, cada pasajero vuelve a la cola FIFO de la estación.

        Retorna [resumen, estaciones]. El resumen es
        [generados, abordajes, no_abordados, espera_promedio, espera_maxima,
        cola_maxima, pasajeros_en_red_al_final]. Cada fila por estación es
        [nombre, generados, esperando_al_final, cola_maxima, espera_promedio,
        espera_maxima, no_abordados].

        Complejidad: O(M*R^2*P^2 + D*(N + A + E + Q)), donde M es la cantidad
        de estaciones con flujo, R servicios direccionales, P paradas máximas,
        D=1440 minutos, N estaciones, A buses activos por minuto, E eventos de
        parada y Q grupos FIFO revisados. Se guardan grupos equivalentes, no
        objetos individuales; espacio O(N + E + G), G grupos diarios.
        """
        self._validar_cantidad(frecuencia, "La frecuencia")
        if frecuencia == 0:
            raise ValueError("La frecuencia debe ser mayor que cero.")

        colas = []
        metricas = []
        demandas = []
        for estacion in self._estaciones:
            colas.append([])
            metricas.append([0, 0, 0, 0, 0, 0])

        indice_estacion = 0
        while indice_estacion < len(self._estaciones):
            estacion = self._estaciones[indice_estacion]
            config = self._buscar_flujo_estacion(estacion)
            if config == -1:
                flujo = self._flujo_global
                destino = ""
            else:
                flujo = self._flujos_estaciones[config][1]
                destino = ""
            plan = []
            if destino != "":
                if flujo > 0 or len(self._horas_pico) > 0:
                    plan = self._plan_servicios(estacion, destino)
            demandas.append([flujo, destino, plan])
            indice_estacion += 1

        buses_activos = []
        total_generados = 0
        total_abordajes = 0
        total_completados = 0
        espera_total = 0
        espera_maxima = 0
        cola_maxima_red = 0

        minuto = 0
        while minuto < 1440:
            indice_estacion = 0
            while indice_estacion < len(self._estaciones):
                estacion = self._estaciones[indice_estacion]
                if self._abiertas[indice_estacion]:
                    demanda = demandas[indice_estacion]
                    flujo = demanda[0]
                    destino = demanda[1]
                    flujo_minuto = flujo + self._incremento_hora(minuto)
                    if destino != estacion and flujo_minuto > 0:
                        total_generados += flujo_minuto
                        metricas[indice_estacion][0] += flujo_minuto
                        plan = demanda[2]
                        if len(plan) > 0:
                            primer_tramo = plan[0]
                            servicio_siguiente = ""
                            if len(plan) > 1:
                                servicio_siguiente = plan[1][0]
                            cola = colas[indice_estacion]
                            cola.append(
                                [
                                    minuto,
                                    destino,
                                    primer_tramo[0],
                                    primer_tramo[1],
                                    servicio_siguiente,
                                    flujo_minuto,
                                ]
                            )
                            total_esperando = self._contar_cola(cola)
                            if total_esperando > metricas[indice_estacion][1]:
                                metricas[indice_estacion][1] = total_esperando
                            if total_esperando > cola_maxima_red:
                                cola_maxima_red = total_esperando
                        else:
                            cola = colas[indice_estacion]
                            cola.append(
                                [
                                    minuto,
                                    destino,
                                    "",
                                    destino,
                                    "",
                                    flujo_minuto,
                                ]
                            )
                            total_esperando = self._contar_cola(cola)
                            if total_esperando > metricas[indice_estacion][1]:
                                metricas[indice_estacion][1] = total_esperando
                            if total_esperando > cola_maxima_red:
                                cola_maxima_red = total_esperando
                indice_estacion += 1

            if minuto % frecuencia == 0:
                indice_ruta = 0
                while indice_ruta < len(self._rutas_info):
                    capacidad = self._capacidad_universal
                    if len(self._rutas_info[indice_ruta][1]) > 0:
                        buses_activos.append(
                            [
                                indice_ruta,
                                0,
                                minuto,
                                [],
                                0,
                                capacidad,
                            ]
                        )
                    indice_ruta += 1

            buses_pendientes = []
            for bus_activo in buses_activos:
                indice_ruta = bus_activo[0]
                identificador = self._rutas_info[indice_ruta][0]
                indice_parada = bus_activo[1]
                llegada = bus_activo[2]
                pasajeros_bus = bus_activo[3]
                ocupacion = bus_activo[4]
                capacidad = bus_activo[5]

                if llegada != minuto:
                    buses_pendientes.append(bus_activo)
                    continue

                paradas = self._rutas_info[indice_ruta][1]
                estacion_bus = paradas[indice_parada]
                indice_actual = self._posicion_estacion(estacion_bus)
                pasajeros_restantes = []
                for pasajero in pasajeros_bus:
                    if pasajero[2] == estacion_bus:
                        ocupacion -= pasajero[4]
                        if pasajero[3] != "":
                            indice_transbordo = self._posicion_estacion(estacion_bus)
                            if indice_transbordo != -1:
                                colas[indice_transbordo].append(
                                    [
                                        minuto,
                                        pasajero[1],
                                        pasajero[3],
                                        pasajero[1],
                                        "",
                                        pasajero[4],
                                    ]
                                )
                                cola_actual = self._contar_cola(
                                    colas[indice_transbordo]
                                )
                                if cola_actual > metricas[indice_transbordo][1]:
                                    metricas[indice_transbordo][1] = cola_actual
                                if cola_actual > cola_maxima_red:
                                    cola_maxima_red = cola_actual
                        else:
                            total_completados += pasajero[4]
                    else:
                        pasajeros_restantes.append(pasajero)
                pasajeros_bus = pasajeros_restantes

                if indice_actual != -1 and self._abiertas[indice_actual]:
                    cola = colas[indice_actual]
                    nueva_cola = []
                    for pasajero in cola:
                        if (
                            pasajero[2] == identificador
                            and pasajero[3] != estacion_bus
                            and ocupacion < capacidad
                        ):
                            cupo = capacidad - ocupacion
                            abordados = pasajero[5]
                            if abordados > cupo:
                                abordados = cupo
                            espera = minuto - pasajero[0]
                            espera_total += espera * abordados
                            total_abordajes += abordados
                            metricas[indice_actual][2] += espera * abordados
                            metricas[indice_actual][3] += abordados
                            if espera > espera_maxima:
                                espera_maxima = espera
                            if espera > metricas[indice_actual][4]:
                                metricas[indice_actual][4] = espera
                            ocupacion += abordados
                            pasajeros_bus.append(
                                [
                                    minuto,
                                    pasajero[1],
                                    pasajero[3],
                                    pasajero[4],
                                    abordados,
                                ]
                            )
                            pasajero[5] -= abordados
                        if pasajero[5] > 0:
                            nueva_cola.append(pasajero)
                    colas[indice_actual] = nueva_cola

                bus_activo[3] = pasajeros_bus
                bus_activo[4] = ocupacion
                bus_activo[1] += 1
                if bus_activo[1] < len(paradas):
                    bus_activo[2] = minuto + 3
                    buses_pendientes.append(bus_activo)

            buses_activos = buses_pendientes
            minuto += 1

        total_no_abordados = 0
        maximo_espera_red_final = espera_maxima
        suma_esperas_metricas = espera_total
        cantidad_esperas_metricas = total_abordajes
        indice_estacion = 0
        while indice_estacion < len(colas):
            cola = colas[indice_estacion]
            metricas_estacion = metricas[indice_estacion]
            esperando = 0
            for pasajero in cola:
                cantidad = pasajero[5]
                esperando += cantidad
                total_no_abordados += cantidad
                espera = 1439 - pasajero[0]
                suma_esperas_metricas += espera * cantidad
                cantidad_esperas_metricas += cantidad
                if espera > maximo_espera_red_final:
                    maximo_espera_red_final = espera
                if espera > metricas_estacion[4]:
                    metricas_estacion[4] = espera
                metricas_estacion[2] += espera * cantidad
                metricas_estacion[3] += cantidad

            metricas_estacion[5] = esperando
            indice_estacion += 1

        pasajeros_a_bordo = 0
        for bus_activo in buses_activos:
            for pasajero in bus_activo[3]:
                pasajeros_a_bordo += pasajero[4]

        if cantidad_esperas_metricas > 0:
            promedio_red = (
                suma_esperas_metricas / cantidad_esperas_metricas
            )
        else:
            promedio_red = 0
        pasajeros_en_red = total_generados - total_completados
        if pasajeros_en_red < total_no_abordados + pasajeros_a_bordo:
            pasajeros_en_red = total_no_abordados + pasajeros_a_bordo

        resumen = [
            total_generados,
            total_abordajes,
            total_no_abordados,
            promedio_red,
            maximo_espera_red_final,
            cola_maxima_red,
            pasajeros_en_red,
        ]
        filas_estaciones = []
        indice_estacion = 0
        while indice_estacion < len(self._estaciones):
            metricas_estacion = metricas[indice_estacion]
            if metricas_estacion[3] > 0:
                promedio = metricas_estacion[2] / metricas_estacion[3]
            else:
                promedio = 0
            filas_estaciones.append(
                [
                    self._estaciones[indice_estacion],
                    metricas_estacion[0],
                    metricas_estacion[5],
                    metricas_estacion[1],
                    promedio,
                    metricas_estacion[4],
                    metricas_estacion[5],
                ]
            )
            indice_estacion += 1

        self._resultado_r10 = [resumen, filas_estaciones]
        return self._resultado_r10

    def _guardar_itinerario(
        self, destinos, indice_destino, servicio, parada, siguiente, pasos
    ):
        """Conserva para cada destino el recorrido conocido con menos paradas."""
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
        Precalcula destinos alcanzables directos o con un transbordo.

        Indexar los recorridos por estación evita volver a escanear todas las
        rutas al asignar cada lote aleatorio. El coste es proporcional a las
        combinaciones de tramos válidas examinadas para este origen.
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
        """Busca la primera salida en o después del minuto con búsqueda binaria."""
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
        """
        Filtra rutas conocidas por salidas reales dentro de la ventana.

        Los itinerarios topológicos se agrupan por servicio y transbordo una
        vez por origen. Aquí se comprueban las salidas programadas del grupo y
        sus máscaras de paradas posteriores, sin reconstruir combinaciones de
        rutas para cada destino en cada minuto.
        """
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

    def simular_dia(self, semilla=None):
        """
        Simula 24 horas con las llegadas reales registradas en horarios.csv.

        Cada viaje se crea a partir de las secuencias de horarios por parada.
        Las colas se guardan como matriz estación x servicio; cada celda es una
        lista FIFO de lotes. En cada llegada se recorre y reconstruye esa cola
        conservando, en orden, los grupos que no puede abordar ese bus.
        El evento de horario identifica minuto, viaje, estación y orden de parada.

        Cada lote elige uniformemente un destino distinto del origen entre los
        que tienen un itinerario con salidas utilizables en la ventana de 30
        minutos. Se valida el viaje real al abordar y también la salida de
        transbordo. La tasa global aplica a todas las estaciones y la demanda
        pico se suma.

        Retorna [resumen, estaciones]. El resumen termina con pasajeros_en_red
        y llegadas a destino; cada fila de estación termina con su total de
        llegadas a destino, sin contar transbordos.

        La semilla opcional permite repetir una simulación para pruebas.
        Los índices de salidas por minuto cuestan O(1440*S + H), donde S es
        el número de pares estación-servicio con horarios y H los eventos.
        La simulación cuesta O(1440*N + W + B + Q): W cuenta las salidas
        examinadas por itinerario, B los destinos validados con máscaras y Q
        los grupos de pasajeros procesados. Espacio O(H + V*N + N*R +
        1440*S + D + G), con V viajes, D opciones de destino y G grupos.
        """
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
            if flujos[indice_origen] > 0 or len(self._horas_pico) > 0:
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
        minuto = 0

        while minuto < 1440:
            indice_estacion = 0
            while indice_estacion < numero_estaciones:
                flujo = flujos[indice_estacion]
                if flujo >= 0 and self._abiertas[indice_estacion]:
                    llegadas = flujo + self._incremento_hora(minuto)
                    if llegadas > 0:
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
        """Devuelve una copia superficial de los resultados R10 para el front."""
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

    def _plan_servicios(self, origen, destino):
        """Helper del prototipo R10 por frecuencia; R5 usa `viaje()`."""
        if origen == destino:
            return []
        posicion_origen = self._posicion_estacion(origen)
        posicion_destino = self._posicion_estacion(destino)
        if posicion_origen == -1 or posicion_destino == -1:
            return []
        if not self._abiertas[posicion_origen] or not self._abiertas[posicion_destino]:
            return []

        mejor = []
        mejor_cantidad = -1
        for servicio_a in self._rutas_info:
            paradas_a = servicio_a[1]
            inicio_a = self._buscar_en_lista(paradas_a, origen)
            fin_directo = self._buscar_en_lista(paradas_a, destino)
            if inicio_a != -1 and fin_directo > inicio_a:
                cantidad = fin_directo - inicio_a
                if mejor_cantidad == -1 or cantidad < mejor_cantidad:
                    mejor_cantidad = cantidad
                    mejor = [[servicio_a[0], destino]]

        indice_a = 0
        while indice_a < len(self._rutas_info):
            servicio_a = self._rutas_info[indice_a]
            paradas_a = servicio_a[1]
            inicio_a = self._buscar_en_lista(paradas_a, origen)
            if inicio_a != -1:
                indice_b = 0
                while indice_b < len(self._rutas_info):
                    if indice_b != indice_a:
                        servicio_b = self._rutas_info[indice_b]
                        paradas_b = servicio_b[1]
                        fin_b = self._buscar_en_lista(paradas_b, destino)
                        if fin_b != -1:
                            indice_parada = inicio_a + 1
                            while indice_parada < len(paradas_a):
                                transbordo = paradas_a[indice_parada]
                                inicio_b = self._buscar_en_lista(
                                    paradas_b, transbordo
                                )
                                posicion_transbordo = self._posicion_estacion(
                                    transbordo
                                )
                                if (
                                    inicio_b != -1
                                    and fin_b > inicio_b
                                    and posicion_transbordo != -1
                                    and self._abiertas[posicion_transbordo]
                                ):
                                    cantidad = (
                                        indice_parada - inicio_a
                                        + fin_b - inicio_b
                                    )
                                    if mejor_cantidad == -1 or cantidad < mejor_cantidad:
                                        mejor_cantidad = cantidad
                                        mejor = [
                                            [servicio_a[0], transbordo],
                                            [servicio_b[0], destino],
                                        ]
                                indice_parada += 1
                    indice_b += 1
            indice_a += 1
        return mejor

    def _buscar_flujo_estacion(self, estacion):
        """Búsqueda lineal del prototipo R10 antiguo; no la usa la app."""
        posicion = 0
        while posicion < len(self._flujos_estaciones):
            if self._flujos_estaciones[posicion][0] == estacion:
                return posicion
            posicion += 1
        return -1

    @staticmethod
    def _contar_cola(cola):
        """Conteo auxiliar del prototipo R10 antiguo, no del simulador activo."""
        cantidad = 0
        for pasajero in cola:
            cantidad += pasajero[5]
        return cantidad

    def _incremento_hora(self, minuto):
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
        nombre = self._normalizar(estacion)
        if self._posicion_estacion(nombre) == -1:
            raise ValueError("La estación indicada no existe.")
        return nombre

    @staticmethod
    def _validar_cantidad(cantidad, nombre):
        if not isinstance(cantidad, int) or cantidad < 0:
            raise ValueError(nombre + " debe ser un entero no negativo.")

    def buses_rutas(self):
        """Devuelve los buses de las rutas ordenadas en O(R)."""
        buses = []
        for informacion in self._rutas_info:
            bus = self._nombre_bus(informacion[0])
            if len(buses) == 0 or buses[-1] != bus:
                buses.append(bus)
        return buses

    def servicios(self, bus):
        """
        Devuelve los identificadores direccionales de un bus en O(R).

        El front usa esta lista para que las modificaciones se apliquen a un
        recorrido concreto; así se pueden mostrar ambos sentidos y editar el
        servicio elegido sin ambigüedad.
        """
        bus_normalizado = self._normalizar(bus)
        encontrados = []
        for informacion in self._rutas_info:
            nombre_bus = self._normalizar(self._nombre_bus(informacion[0]))
            if nombre_bus == bus_normalizado:
                encontrados.append(informacion[0])
        return encontrados

    def estaciones(self):
        """Devuelve los nombres existentes para los selectores del front: O(n)."""
        nombres = []
        for nombre in self._estaciones:
            nombres.append(nombre)
        return nombres

    def recorrido(self, ruta, al_reves=False):
        """
        R7: obtiene una copia del recorrido en el orden solicitado.

        `ruta` es el identificador direccional, por ejemplo B74-1. El front
        consulta el mismo servicio con al_reves=False y True para mostrar ambos
        sentidos. Complejidad O(R + P); la copia evita que el front modifique
        directamente las estructuras internas.
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
        R7: inserta una estación existente entre dos paradas de un servicio.

        `despues_de` debe tener una parada siguiente para que la inserción quede
        entre dos paradas que ya estaban en el recorrido. Buscar servicio,
        validar estación y reconstruir la lista cuesta O(R + P + log N).
        El historial guarda referencias a las listas anterior y nueva, sin
        copiar toda la red (R9). La edición invalida las cachés R6 y R10.
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
        R7: elimina una estación de un recorrido sin eliminarla de la red.

        Complejidad O(R + P): se localiza el servicio y la parada y se reconstruye
        la lista. R9 conserva referencias a la lista antes y después del cambio.
        El resto de servicios y la lista maestra de estaciones quedan intactos.
        La edición invalida las cachés R6 y R10.
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
        """R8: cierra una estación existente y registra el cambio para R9."""
        self._cambiar_estado_estacion(nombre, False)

    def reabrir(self, nombre):
        """R8: reabre una estación existente y registra el cambio para R9."""
        self._cambiar_estado_estacion(nombre, True)

    def deshacer(self):
        """
        R9: aplica la acción inversa más reciente usando una pila LIFO.

        Sacar y mover la acción cuesta O(1) amortizado. Reemplazar un booleano
        o una referencia a lista también cuesta O(1); R10 invalida sus eventos
        al cambiar una ruta y los reconstruye al iniciar la siguiente simulación.
        """
        if len(self._historial_deshacer) == 0:
            return False

        anterior = self._historial_deshacer.pop()
        self._aplicar_cambio_historial(anterior, False)
        self._historial_rehacer.append(anterior)
        return True

    def rehacer(self):
        """R9: reaplica la acción más reciente en O(1) amortizado."""
        if len(self._historial_rehacer) == 0:
            return False

        siguiente = self._historial_rehacer.pop()
        self._aplicar_cambio_historial(siguiente, True)
        self._historial_deshacer.append(siguiente)
        return True

    def proximo_bus(self, estacion, bus, hora):
        """
        R4: busca la siguiente llegada del bus indicado en una estacion.

        El archivo usa identificadores con sentido, como B74-1 y B74-2,
        mientras que el usuario puede buscar por el bus base "B74". Se incluyen
        tanto la coincidencia exacta como sus variantes que terminan en "-...".
        Los horarios ordenados permiten buscar el primer tiempo >= hora actual.

        Complejidad: O(log b + v*log h), donde b es la cantidad de buses
        unicos, v las variantes del bus indicado y h las filas de horario.
        Para cada variante, una busqueda binaria devuelve directamente su
        primera llegada posible, sin recorrer sus horarios anteriores.
        Retorna una cadena "HH:MM" o None si no existen buses posteriores.
        El front llama esta funcion con estacion, bus y hora actual; no busca
        llegadas por su cuenta.
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
        R5: busca el viaje directo o con un solo transbordo con menos paradas.

        _rutas_info usa una lista por servicio direccional:
        [id_servicio, [estacion_1, estacion_2, ...]]
        La funcion compara recorridos directos y pares de servicios que
        comparten una estacion. El CSV usa id_servicio para separar sentidos;
        la respuesta convierte ese id en el bus que debe abordar el usuario.

        El resultado, preparado para el front, es una lista de segmentos:
        [bus, estacion_subida, estacion_bajada]. Los CSV distinguen variantes
        direccionales como B74-1 y B74-2; el pasajero toma el bus B74, asi que
        _nombre_bus elimina el sufijo numerico solo al preparar la respuesta.
        Un viaje directo tiene un segmento y un transbordo tiene dos.
        Si no hay recorrido posible devuelve [].

        Se comparan todas las opciones directas y con un transbordo, guardando
        la de menor cantidad total de paradas recorridas. Solo se permite
        avanzar en el orden de cada servicio direccional.

        Complejidad: O(log n + R^2*P^2 + R^2*P*log n), donde n es el numero
        de estaciones, R los servicios direccionales y P las paradas maximas
        por servicio. El ultimo termino corresponde a verificar estaciones de
        transbordo con estado(), que usa busqueda binaria. Se usan listas
        simples porque dict/set estan prohibidos; estas conservan el orden del
        recorrido sin indices auxiliares.
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
        Convierte un servicio direccional como B74-1 en el bus B74.

        Los sufijos no numéricos, como los de identificadores existentes
        "1-Jan", se conservan completos. Complejidad O(L), donde L es la
        longitud del identificador.
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
        R6: devuelve las k estaciones abiertas con mas buses diarios.

        _ranking guarda [nombre, cantidad, indice_estacion], en orden por
        cantidad descendente y nombre ascendente. El indice permite consultar
        si la estacion sigue abierta en O(1), sin otra busqueda binaria.

        La reconstruccion cuesta         O(H + R + J log J + U log U + U log N);
        la consulta revisa M filas hasta reunir k estaciones abiertas: O(M),
        con O(k) espacio de respuesta. Rechazar k <= 0 cuesta O(1).

        La frecuencia del servicio se estima por su mayor cantidad de horarios
        en una parada y se asigna a sus paradas actuales, incluidas las nuevas
        de R7. Cerrar/reabrir filtra el cache en vivo; editar recorridos lo
        invalida. R10 no lo modifica.         Merge sort ordena las J paradas porque
        mapas y conjuntos estan prohibidos en el motor.
        Retorna solamente nombres: [nombre1, nombre2, ...], como espera el
        front para R6. Los conteos internos siguen disponibles en _ranking.
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
        Convierte rutas.csv en [nombre, [paradas ordenadas]].

        Lee O(q) filas, ordena por ruta y orden con merge sort O(q log q)
        y agrupa O(q). Es mas simple y rapido que buscar rutas desordenadas
        durante cada viaje.
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
        Convierte horarios.csv en filas ordenadas por ruta y estacion.

        Cada fila queda como [ruta, estacion, minuto, HH:MM].
        ordenar por ruta, estacion y minuto permite buscar con binaria O(log h).
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
        """Crea una lista ordenada de identificadores únicos: O(h)."""
        buses = []
        for fila in self._horarios:
            if len(buses) == 0 or buses[-1] != fila[0]:
                buses.append(fila[0])
        return buses

    def _construir_ranking(self):
        """
        Estima los buses diarios de cada servicio y los asigna a sus paradas.

        El máximo de horarios por parada representa los viajes diarios del
        servicio; así, una parada agregada en R7 también hereda su frecuencia.
        Los servicios y horarios están ordenados, por lo que agruparlos cuesta
        O(H). Emparejar rutas cuesta O(R); ordenar las J paradas actuales y
        agruparlas cuesta O(J log J); ordenar el ranking cuesta O(U log U).
        Esta caché solo se invalida con ediciones de recorrido: R10 no cambia
        datos ni conteos de R6.
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
        """Ordena [estacion, frecuencia] por nombre en O(J log J)."""
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

    @classmethod
    def _ordenar_nombres(cls, nombres):
        """Ordena nombres para agrupar frecuencias en O(h log h), O(h) espacio."""
        if len(nombres) < 2:
            return nombres

        mitad = len(nombres) // 2
        izquierda = cls._ordenar_nombres(nombres[:mitad])
        derecha = cls._ordenar_nombres(nombres[mitad:])
        resultado = []
        i = 0
        j = 0
        while i < len(izquierda) and j < len(derecha):
            if izquierda[i] <= derecha[j]:
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
        """Busca un valor en una secuencia ordenada de ruta en O(P) peor caso."""
        posicion = 0
        while posicion < len(valores):
            if valores[posicion] == valor:
                return posicion
            posicion += 1
        return -1

    def _indice_ruta(self, ruta):
        identificador = str(ruta).strip()
        posicion = 0
        while posicion < len(self._rutas_info):
            if self._rutas_info[posicion][0] == identificador:
                return posicion
            posicion += 1
        return -1

    def _cambiar_estado_estacion(self, nombre, abierta):
        """R8: busca en O(log N); el registro delta de R9 cuesta O(1)."""
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
        """Guarda una acción delta en la pila y descarta la rama de rehacer."""
        self._historial_deshacer.append(cambio)
        self._historial_rehacer = []

    def _aplicar_cambio_historial(self, cambio, rehacer):
        """Aplica una acción delta de R9 en O(1), sin copiar la red."""
        posicion_valor = 3 if rehacer else 2
        if cambio[0] == "ruta":
            self._rutas_info[cambio[1]][1] = cambio[posicion_valor]
            self._invalidar_ranking()
            self._invalidar_eventos_horario()
        else:
            self._abiertas[cambio[1]] = cambio[posicion_valor]
        self._resultado_r10 = []

    def _invalidar_ranking(self):
        """Marca R6 para reconstrucción diferida tras una edición de recorrido."""
        self._ranking_desactualizado = True

    def _posicion_estacion(self, estacion):
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
        """Busca el inicio del identificador o sus variantes en O(log b)."""
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
        # Primera fila que no precede a (ruta, estacion, minuto).
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
        Convierte una hora texto a minutos desde 00:00.

        Complejidad O(L), siendo L la longitud del texto. Soporta "9:05",
        "09:05" y horas con segundos; usa solo metodos str permitidos.
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
        Ordena rutas por nombre y luego por numero de orden.
        Complejidad O(q log q), memoria auxiliar O(q).
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
        Ordena horarios por ruta, estacion y minuto.
        Complejidad O(h log h), necesaria antes de usar busqueda binaria.
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
        """Ordena [estacion, conteo, indice] en O(u log u), espacio O(u)."""
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
        R1: consulta si una estacion existe y si esta abierta.

        Retorna (False, False) si no existe y (True, abierta) si existe.
        El front usa esta tupla para mostrar el resultado al usuario.

        Complejidad: O(log n), usando busqueda binaria sobre _estaciones.
        Es mas eficiente que recorrer la lista completa, que seria O(n).
        """
        nombre_normalizado = self._normalizar(nombre)
        posicion = self._posicion_insercion(nombre_normalizado)

        if posicion < len(self._estaciones):
            if self._estaciones[posicion] == nombre_normalizado:
                return (True, self._abiertas[posicion])

        return (False, False)

    def autocompletar(self, prefijo, k):
        """
        R2: devuelve hasta k estaciones abiertas que comienzan por prefijo.

        Primero ubica el prefijo con busqueda binaria y luego recorre solamente
        el tramo que puede coincidir. La lista ya esta en orden alfabetico.
        El front recibe una lista simple y la muestra como opciones de una barra
        de busqueda y seleccion.

        Complejidad: O(log n + m), donde m es el numero de estaciones revisadas
        hasta obtener k resultados o terminar el prefijo. En el mejor caso es
        O(log n); como maximo puede revisar O(n) cuando casi todas coinciden.
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
        R3: devuelve las estaciones abiertas dentro de un rango alfabetico.

        Si desde <= hasta, el recorrido es ascendente e inclusivo.
        Si desde > hasta, la direccion se invierte y el recorrido es descendente
        e inclusivo. Los extremos pueden ser nombres parciales o inexistentes.

        Complejidad: O(log n + r), donde r es el numero de estaciones ubicadas
        dentro del rango. La busqueda binaria evita recorrer desde el inicio.
        Construir la lista de resultados necesariamente cuesta O(r).

        El front llama este metodo y coloca el resultado recibido en el Listbox.
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
        # Respecto a n, el numero de estaciones, es O(1): solo procesa un
        # nombre. Si L es la longitud de ese nombre, trim y upper costean O(L).
        # Permite que R1, R2 y R3 sean insensibles a mayusculas y espacios.
        return str(nombre).strip().upper()

    def _posicion_insercion(self, nombre):
        """
        Ubica el primer elemento que no es menor que nombre.

        Implementacion de insertion point con busqueda binaria.
        Complejidad: O(log n); evita una busqueda lineal en _estaciones.
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
        Ordena una lista mediante merge sort.

        Se uso merge sort en vez de sorted(), list.sort(), min() o max()
        porque las reglas de motor/ prohiben esas operaciones sobre colecciones.
        El algoritmo divide la lista y combina cada mitad ordenada.

        Complejidad: O(n log n) en todos los casos, con O(n) de memoria auxiliar
        durante las combinaciones. Es mas eficiente que un metodo de burbuja,
        que seria O(n^2), y permite que todas las consultas posteriores sean
        mas eficientes.
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
