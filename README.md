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

### R10 — Simulación de red durante un día

`simular_fila(llegadas, frecuencia, capacidad)` simula una fila FIFO sencilla
y devuelve `[abordados, espera_promedio, espera_maxima, cola_maxima,
no_abordados]`. `llegadas[t]` es el número de pasajeros que aparece en el minuto
`t`; hay un bus en el minuto cero y cada `frecuencia` minutos. La fila se
representa con grupos `[minuto_de_llegada, cantidad]` y un índice de cabeza, así
se conserva el orden sin mover toda la lista tras cada abordaje.

- Es una función aislada para el ejercicio de una sola fila; el panel R10 usa
  `Red.simular_dia()` y los eventos reales de `horarios.csv`.
- Complejidad: **O(T + G)** tiempo y **O(G)** espacio, donde `T` es la duración
  en minutos y `G` los grupos de llegada.
- La espera promedio se pondera por pasajeros. Quienes siguen en la fila al
  cierre se cuentan como no abordados y su espera incompleta se mide hasta el
  final del periodo.

El panel "Simulación R10" ejecuta `Red.simular_dia()` por 1440 minutos y usa las
llegadas de los buses de `horarios.csv`, no una frecuencia sintética. El flujo
global genera pasajeros en todas las estaciones abiertas; cada estación puede
sobrescribir esa tasa. El botón "Aplicar a todas" aplica el flujo global y
restablece las sobrescrituras locales. Cada grupo generado en una estación
elige al azar, con probabilidad uniforme, entre los destinos que tienen un
itinerario topológico y un servicio programado utilizable. Solo se genera
demanda si algún bus que sirve el trayecto puede salir dentro de los siguientes
30 minutos y pasar por el destino; para un transbordo, el siguiente servicio
también debe salir dentro de 30 minutos de la conexión y llegar al destino.
Si no hay ningún itinerario así, no se genera ese grupo. El límite se aplica a la espera
por una salida programada, no a la espera total: con capacidad insuficiente,
un pasajero aún puede esperar más de 30 minutos.

El argumento opcional `semilla` de `simular_dia(semilla)` permite repetir el
mismo sorteo. Los aumentos por hora pico se suman al flujo en todas las
estaciones abiertas, pero también respetan la disponibilidad de los horarios.
`configurar_capacidad_universal(capacidad)` fija un único cupo que se aplica a
todos los buses y recorridos. La interfaz presenta el total de pasajeros y las
métricas por estación, incluida la cantidad que terminó su viaje en esa
estación (no cuenta bajadas de transbordo como destino final).

**Estructuras del motor:** `horarios.csv` se prepara como eventos
`[minuto, viaje, estación, orden_de_parada]` ordenados por merge sort. Cada
llegada identifica un viaje y hace avanzar su manifiesto. Las colas usan una
matriz de listas FIFO indexada por estación y servicio; cada lote contiene
`[minuto_llegada, destino_final, próxima_estación_de_bajada,
servicio_de_transbordo, cantidad]`. Un índice de cabeza permite consumir la
cola sin eliminar del inicio de la lista. Los pasajeros se guardan por grupos,
no como objetos individuales. Cada viaje mantiene la capacidad universal,
ocupación y su manifiesto; al llegar a un destino, los pasajeros completan el recorrido, y
quienes deben transbordar entran en la cola del siguiente servicio.
La métrica de llegadas a destino se acumula por estación al completar cada
lote, en **O(1)** por lote, y se devuelve como la última columna de cada fila
de estación; el último valor del resumen es su total en la red. Los itinerarios
se agrupan por servicio y transbordo. En cada minuto, máscaras de bits
identifican rápidamente qué destinos posteriores puede alcanzar cada salida.
Al abordar, el motor vuelve a validar el recorrido real del viaje para evitar
que un pasajero tome una salida que no llega a su destino o conexión. Si no
existe un itinerario con salidas dentro de la ventana permitida, ese grupo no
se genera.

El resumen de la simulación devuelve
`[generados, abordajes, no_abordados, espera_promedio, espera_maxima,
cola_maxima, pasajeros_en_red, llegadas_a_destino]`. Cada fila de estación
devuelve `[nombre, generados, esperando_al_final, cola_maxima, espera_promedio,
espera_maxima, no_abordados, llegadas_a_destino]`.

**Emparejamiento de viajes:** `horarios.csv` no contiene identificadores de
vehículo. Para reconstruir cada viaje, el motor asocia la primera hora de cada
parada al primer viaje, la segunda hora al segundo, etc. Esta es una
aproximación determinista de la información disponible, no una garantía de que
cada fila pertenezca al mismo vehículo. Los eventos fuera del día simulado se
omiten. Los archivos fuente no se modifican.

- Los eventos se indexan por viaje y estación, y las salidas por estación y
  servicio. Máscaras de bits guardan las estaciones posteriores de cada evento.
  Crear estos índices cuesta **O(H + V × N + N × R)** tiempo y espacio, donde
  `H` es la cantidad de eventos horarios, `V` los viajes reconstruidos, `N`
  las estaciones y `R` los servicios.
- Para no ejecutar una búsqueda binaria por cada destino y minuto, el motor
  precalcula la posición de la primera salida posterior a cada minuto para
  cada par estación-servicio con horarios. Si `S` es la cantidad de esos pares,
  este índice cuesta **O(1440 × S + H)** tiempo y **O(1440 × S)** espacio.
- Los itinerarios directos y de un transbordo se preparan una vez por origen.
  Si `C` cuenta los tramos candidatos y `D × K` el trabajo de agrupar `D`
  opciones de destino en `K` combinaciones de servicios, su coste es
  **O(C + D × K)** por origen con demanda posible. Esto evita reconstruir
  combinaciones de recorridos dentro de cada minuto.
- La simulación cuesta **O(1440 × N + W + B + Q)**, además de los índices y
  el precálculo anteriores. `W` cuenta las salidas examinadas por las
  combinaciones de servicio dentro de ventanas de 30 minutos, `B` las opciones
  de destino comprobadas con máscaras y `Q` los grupos de pasajeros revisados
  al llegar los buses. El número de pasajeros individuales no multiplica el
  trabajo: las llegadas y abordajes se procesan por lotes.
- El espacio total de la simulación es **O(H + V × N + N × R + 1440 × S + D
  + G)**, donde `G` es la cantidad de grupos en colas y manifiestos. El límite
  de 30 minutos restringe la espera por salida programada; una capacidad
  insuficiente todavía puede causar una espera mayor.
- La espera se pondera por cantidad de pasajeros. Los no abordados cuentan a
  quienes siguen esperando al cierre; pasajeros que ya abordaron pero siguen
  a bordo se incluyen en el total de personas en la red.

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
