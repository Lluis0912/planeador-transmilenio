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
