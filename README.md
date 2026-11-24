# Planeador TransMilenio

Aplicación de escritorio para consultar estaciones de TransMilenio. El motor y
la interfaz están separados para facilitar la incorporación de los requerimientos

## Ejecutar

Desde la carpeta raíz del repositorio, con Python 3:
```bash
python -m front
```
La aplicación lee `datos/estaciones.csv`.

### Estructura de datos

El motor usa **dos listas paralelas**, que son la estructura permitida para el
ejercicio:

- `_estaciones`: contiene los nombres distintos y ordenados alfabéticamente.
- `_abiertas`: contiene `True` o `False` en la misma posición que cada estación.

No se usan `dict`, `set`, `sorted`, `list.sort`, `heapq`, `bisect` ni otras
bibliotecas externas en `motor/`. Las búsquedas no distinguen mayúsculas ni
espacios externos. Aquí `n` significa la cantidad de estaciones distintas y
`r` significa la cantidad de estaciones producidas en un rango.

### R1 — Consultar estado

`Red.estado(nombre)` devuelve `(existe, abierta)`.

- Usa búsqueda binaria sobre `_estaciones`.
- Complejidad: **O(log n)**.
- La búsqueda binaria fue elegida porque la lista está ordenada. Evita revisar
  las estaciones una por una, como haría una búsqueda lineal en **O(n)**.

### R2 — Autocompletar junto con R1

`Red.autocompletar(prefijo, k)` devuelve hasta `k` estaciones abiertas que
comienzan por el prefijo, en orden alfabético.

- Usa búsqueda binaria para localizar el inicio y luego recorre coincidencias.
- Complejidad: **O(log n + m)**, donde `m` es la cantidad revisada hasta
  completar `k` resultados o terminar las coincidencias.
- Es más eficiente que revisar y comparar todas las estaciones desde el inicio,
  que sería **O(n)**.
- La interfaz usa una sola barra `Combobox`: al escribir llama R2 para mostrar
  sugerencias y llama R1 al escribir, seleccionar o presionar Enter.

### R3 — Listar rango

`Red.rango(desde, hasta)` devuelve las estaciones abiertas dentro de un intervalo
inclusive.

- Si `desde <= hasta`, usa recorrido ascendente.
- Si `desde > hasta`, usa recorrido descendente inverso.
- Usa búsqueda binaria para ubicar el extremo inicial.
- Complejidad: **O(log n + r)**.
- Crear la respuesta requiere recorrer las `r` estaciones; la alternativa de
  barrer toda la red desde la primera estación sería **O(n)**.

### R4 — Próximo bus

`Red.proximo_bus(estacion, bus, hora)` devuelve el primer horario posterior
o igual a la hora indicada, con formato `"HH:MM"`, o `None`.

- Los horarios se cargan en `_horarios` como
  `[ruta, estacion, minuto, texto]`.
- El usuario puede indicar el bus base, por ejemplo `B74`; el motor considera
  sus servicios identificados en el CSV como `B74-1`, `B74-2` y `B74-3`.
- La lista se ordena por ruta, estación y minuto con merge sort.
- Complejidad: **O(log b + v log h)**, donde `b` es la cantidad de buses
  únicos, `v` la cantidad de variantes del bus y `h` las filas de horarios.
- Es más eficiente que recorrer todos los horarios desde el inicio. Si se
  recorrieran secuencialmente, la consulta costaría **O(h)**.
- La pestaña "Próximo bus" recoge estación, bus y hora actual y usa esta
  función; solamente presenta el horario devuelto o un mensaje si no hay bus.

### R5 — Planear viaje

`Red.viaje(origen, destino)` devuelve una lista de segmentos
`[bus, estacion_subida, estacion_bajada]`, por ejemplo `["B74", "AGUAS",
"CALLE 19"]`.

- `_rutas_info` almacena cada servicio direccional y sus paradas como
  `[id_servicio, [paradas...]]`. El motor utiliza ese identificador para
  encontrar el recorrido, pero devuelve el nombre de bus al pasajero: por
  ejemplo, convierte `B74-1` y `B74-2` en `B74`.
- El motor evalúa los viajes directos y los de un transbordo, y devuelve el que
  recorre menos paradas. Solo cuenta trayectos que avanzan en el orden del
  servicio direccional, y el transbordo debe ser una estación abierta.
- Las paradas se guardan en listas en el orden del CSV. La búsqueda de una
  estación dentro de una lista es lineal, **O(P)**; se eligió porque las listas
  son la estructura permitida por las reglas del motor y conservan directamente
  el orden de recorrido. No se usan diccionarios, conjuntos ni índices externos.
- **Complejidad temporal de consulta: O(log n + R² × P² + R² × P × log n)**:
  se prueban pares de servicios y posibles transbordos con búsquedas lineales
  en sus listas, y se verifica si los transbordos están abiertos mediante
  búsqueda binaria. `n` es el número de estaciones, `R` el número de servicios
  direccionales y `P` la cantidad máxima de paradas por servicio. El caso
  directo cuesta O(R × P), dominado por las comparaciones de transbordos.
- **Espacio de la respuesta: O(1)**, pues se conserva únicamente el mejor plan,
  que contiene como máximo dos segmentos. El almacenamiento de rutas ya
  cargadas es **O(R × P)**.
- Revisar todos los candidatos y comparar su cantidad de paradas es necesario
  para asegurar que un transbordo no gane a un viaje directo más corto.
- La pestaña "Planear viaje" muestra el bus de cada segmento; no calcula rutas ni
  transbordos dentro del frontend.

### R6 — Ranking

`Red.ranking(k)` devuelve una lista con los nombres de las `k` estaciones
abiertas con más registros de buses al día.

- `_ranking` es una lista cacheada `[estacion, conteo]`, ordenada por conteo
  descendente y nombre ascendente.
- Construcción: **O(h × u + u log u)** y consulta: **O(k)**, donde `h` cuenta
  filas de horarios y `u` estaciones únicas.
- El cache evita contar nuevamente los cientos de miles de horarios en cada
  consulta frecuente. Un conteo desde `horarios.csv` para cada solicitud sería
  innecesariamente lento.
- La pestaña "Ranking" pide solo `k` al motor y presenta los nombres devueltos.

### R7 — Consultar y editar recorridos

El panel "Operar red" permite elegir un bus y luego uno de sus servicios
direccionales (por ejemplo, `B74-1`). Muestra la secuencia del CSV y la misma
secuencia al revés. Al editar, se modifica solo el servicio seleccionado:

- `Red.recorrido(ruta, al_reves=False)` devuelve una copia del recorrido.
  Busca el servicio en una lista y copia sus `P` paradas: **O(R + P)**.
- `Red.agregar_parada(ruta, nueva, despues_de)` solo acepta estaciones que ya
  existen en `estaciones.csv`, y exige una parada siguiente para insertar la
  nueva entre dos paradas existentes. No crea una estación ni cambia otros
  recorridos.
- `Red.quitar_parada(ruta, estacion)` quita la parada de ese servicio, pero
  conserva la estación en la red y en los demás recorridos.
- Ambas modificaciones cuestan **O(R + P + N + S)** por localizar servicio y
  estación, reconstruir su lista y guardar el historial. `R` es la cantidad de
  servicios direccionales, `P` sus paradas máximas, `N` las estaciones y `S`
  todas las paradas almacenadas en la red.
- Las listas preservan el orden del servicio y cumplen las restricciones del
  motor; se usan recorridos lineales porque no se permite un índice `dict`/`set`.

### R8 — Cerrar y reabrir estaciones

`Red.cerrar(nombre)` y `Red.reabrir(nombre)` cambian el booleano asociado a la
estación en `_abiertas`. La estación sigue existiendo, pero las búsquedas y
operaciones que requieren una estación abierta respetan su estado.

- Encontrar la estación cuesta **O(log N)** mediante búsqueda binaria.
- Guardar el snapshot para que R9 pueda revertirlo cuesta **O(N + S)** tiempo y
  espacio por cambio: una copia de estados y de las listas de recorridos.
- El panel de operaciones deja disponible solo la acción válida (cerrar o
  reabrir) según el estado actual.

### R9 — Deshacer y rehacer

`Red.deshacer()` y `Red.rehacer()` usan dos listas como pilas LIFO. Cada cierre,
reapertura o edición guarda un snapshot de estaciones y recorridos. Deshacer
restaura el snapshot anterior; rehacer lo vuelve a aplicar. Un cambio nuevo
después de deshacer borra la pila de rehacer.

- Consultar si hay una acción en la pila y retirarla cuesta **O(1)**.
- Copiar el estado para undo/redo cuesta **O(N + S)** tiempo y espacio por
  operación; el historial completo puede ocupar **O(C × (N + S))**, con `C`
  cambios registrados.
- Los botones de flecha y Ctrl+Z/Ctrl+Y del panel llaman estos métodos del
  motor y refrescan los recorridos y el estado de estación mostrados.

### Operaciones internas importantes

- `Red.__init__`: lee el CSV y usa merge sort propio para ordenar las
  estaciones. Complejidad: **O(n log n)** y memoria auxiliar **O(n)** durante
  la mezcla.
- `_posicion_insercion`: búsqueda binaria del primer elemento no menor que el
  límite. Complejidad: **O(log n)**.
- `_ordenar`: merge sort elegido porque las operaciones `sorted`, `.sort`,
  `min` y `max` están prohibidas en `motor/`. Tiene **O(n log n)** en el mejor,
  promedio y peor caso, frente a **O(n²)** de un recorrido por burbuja.
- `_normalizar`: recorta espacios y convierte mayúsculas. Respecto a `n` es
  **O(1)** por consulta; si `L` es la longitud del nombre, su costo es **O(L)**.

Las pruebas de estos requisitos se ejecutan con:

```bash
python -m unittest pruebas.test_r1_r3
```
# EL PROFESOR NO VA A EVALUAR COSAS EN LA CARPETA DE PRUEBAS
