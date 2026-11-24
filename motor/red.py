import csv


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

        La lista _ranking contiene [nombre, cantidad] y se mantiene ordenada
        por cantidad descendente y nombre ascendente. El ranking se calcula una
        sola vez al cargar los archivos, por lo que cambios futuros pueden
        recalcularlo en O(h log h).

        Complejidad: construir el ranking O(h + n log n), consultar ranking(k)
        O(k), y rechazar k <= 0 en O(1).

        Se usa una lista cacheada porque el ranking cambia poco y una consulta
        frecuente no debe volver a contar los 140000 horarios.
        Retorna solamente nombres: [nombre1, nombre2, ...], como espera el
        front para R6. Los conteos internos siguen disponibles en _ranking.
        """
        if k <= 0:
            return []

        resultados = []
        posicion = 0
        while posicion < len(self._ranking) and len(resultados) < k:
            estacion = self._ranking[posicion]
            posicion_estado = self._posicion_estacion(estacion[0])
            if posicion_estado != -1 and self._abiertas[posicion_estado]:
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
        Cuenta entradas de horario por estacion y crea un ranking cacheado.

        Complejidad: O(h*u + u log u), donde h es el numero de horarios y u
        es la cantidad de estaciones unicas. La cuenta recorre una lista corta
        al cargar una sola vez y luego merge sort crea el ranking.

        Se eligio una lista cacheada porque es permitida y evita repetir este
        trabajo en cada consulta ranking(k). Sin cache, una consulta frecuente
        volveria a procesar todas las filas h en O(h).
        """
        conteos = []
        for fila in self._horarios:
            estacion = fila[1]
            posicion = self._buscar_conteo(conteos, estacion)
            if posicion == -1:
                conteos.append([estacion, 1])
            else:
                conteos[posicion][1] += 1

        return self._ordenar_ranking(conteos)

    def _buscar_conteo(self, conteos, estacion):
        # Busqueda lineal temporal de la lista de conteos.
        # El costo se acepta solo en la carga inicial; la consulta ranking usa
        # el resultado cacheado y tarda O(k).
        posicion = 0
        while posicion < len(conteos):
            if conteos[posicion][0] == estacion:
                return posicion
            posicion += 1
        return -1

    def _buscar_en_lista(self, valores, valor):
        posicion = 0
        while posicion < len(valores):
            if valores[posicion] == valor:
                return posicion
            posicion += 1
        return -1

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
        """
        Ordena [estacion, conteo] por conteo descendente y nombre ascendente.
        Complejidad O(u log u), con u estaciones unicas.
        """
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
