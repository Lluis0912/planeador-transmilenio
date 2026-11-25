# Planeador TransMilenio

Aplicación de escritorio en Python. El paquete `motor/` contiene la lógica de
R1–R10; `front/` recoge datos y presenta los resultados, sin recalcular reglas
del negocio.

## Ejecutar

Desde la carpeta del proyecto:

```bash
python -m front
```

La aplicación carga `datos/estaciones.csv`, `datos/rutas.csv` y
`datos/horarios.csv`.

## Reglas del motor

Dentro de `motor/` se usan listas, ciclos, funciones propias y los módulos
estándar `csv` y `random`. No se usan `dict`, `set`, `sorted`, `list.sort`,
`min`, `max`, búsquedas `in` sobre listas, `.index()`, `.count()`, `bisect`,
`heapq` ni módulos externos. Por eso los índices se implementan con listas y
búsqueda binaria o recorridos explícitos. Las búsquedas de texto consideran
mayúsculas y espacios externos equivalentes.

Notación: `N` estaciones, `R` servicios direccionales, `P` máximo de paradas
por servicio, `H` filas de horarios, `U` estaciones rankeadas, `J` pares
servicio-parada en los recorridos actuales, `T` minutos simulados, `G` grupos
de pasajeros. Los costos de comparar cadenas suponen
longitudes acotadas; si `L` es la longitud del texto, normalizarlo cuesta
`O(L)`.

| Req. | Función y estructura | Complejidad y motivo |
|---|---|---|
| R1 | `Red.estado`: listas paralelas ordenadas `_estaciones` y `_abiertas`. | Consulta `O(log N)` por búsqueda binaria; una lista sin ordenar requeriría `O(N)`. |
| R2 | `Red.autocompletar`: búsqueda binaria del primer prefijo y recorrido contiguo. La interfaz combina sugerencias y estado en una sola barra. | `O(log N + M)`, donde `M` son los nombres revisados para encontrar hasta `k` resultados. Evita examinar toda la red cuando el prefijo es selectivo. |
| R3 | `Red.rango`: la misma lista ordenada, búsqueda binaria del límite y recorrido en la dirección solicitada. | `O(log N + Q)`, donde `Q` son las estaciones examinadas en el rango; construir la salida es necesariamente proporcional a lo examinado. Admite orden alfabético inverso. |
| R4 | `Red.proximo_bus`: horarios ordenados por servicio, estación y minuto; dos búsquedas binarias. | `O(log B + V log H)`, donde `B` son identificadores de servicio, `V` las variantes del bus solicitado y `H` todas las filas de horarios. La búsqueda binaria evita escanear las horas anteriores. |
| R5 | `Red.viaje`: listas de paradas en orden de recorrido y búsqueda lineal de origen, destino y conexiones. Compara viajes directos y de un transbordo y devuelve el de menos paradas. | `O(log N + R²P² + R²P log N)`; las listas preservan el orden y cumplen las restricciones. Mantiene solo el mejor resultado, con un máximo de dos segmentos (`O(1)` espacio de salida). |
| R6 | `Red.ranking`: agrupa horarios por servicio, estima sus viajes diarios con la mayor frecuencia observada en una parada y asigna esa frecuencia a cada parada actual (incluidas las añadidas en R7). El ranking queda cacheado; el estado abierto se consulta en vivo. | Construcción `O(H + R + J log J + U log U + U log N)`; consulta `O(M)` para revisar `M` filas hasta reunir `k` estaciones abiertas. Cerrar/reabrir filtra el cache sin reconstruirlo; una edición R7 lo invalida y se reconstruye al consultar R6. R10 no lo modifica. |
| R7 | `Red.recorrido`, `agregar_parada` y `quitar_parada`: listas de paradas; solo se editan estaciones existentes y un servicio direccional a la vez. | Consultar `O(R + P)`; quitar `O(R + P)`; agregar `O(R + P + log N)` por validar que la estación existe. R9 guarda referencias a las versiones anterior/nueva, sin copiar el resto de la red. Una edición invalida las cachés de R6 y el índice horario R10; ambos se reconstruyen de forma diferida al consultar R6 o iniciar la siguiente simulación. |
| R8 | `Red.cerrar` y `Red.reabrir`: el estado se guarda en `_abiertas`, en paralelo con `_estaciones`. | Buscar la estación `O(log N)` y guardar el cambio delta en `O(1)`. La lista paralela permite encontrar y modificar el estado con el mismo índice. |
| R9 | `Red.deshacer` y `Red.rehacer`: dos listas de acciones delta usadas como pilas LIFO. | Aplicar y mover una acción cuesta `O(1)` amortizado: cambios de estado guardan un booleano; ediciones de ruta guardan referencias a las listas antes/después. Una edición/deshacer/rehacer de ruta invalida las cachés R6 y R10. Espacio `O(C + PΣ)`, donde `C` son cambios y `PΣ` la suma de paradas en versiones de ruta conservadas. |
| R10 | `Red.simular_dia`: eventos de horario, matriz de colas estación-servicio, listas FIFO de grupos, manifiestos de viaje, máscaras de bits de paradas y posiciones de salida precalculadas por minuto. | Ver el análisis de R10 abajo. Los grupos agregan pasajeros que llegan juntos y evitan crear una entrada por persona. |

`Red.viaje` busca, según el alcance actual, viajes directos o con un único
transbordo. No promete encontrar itinerarios que necesiten más transbordos.
La consigna excluye R5 de la comparación de crecimiento al duplicar el tamaño
de la red; su estructura y complejidad siguen documentadas arriba.

### Ordenamientos usados

`_ordenar`, `_ordenar_rutas`, `_ordenar_horarios`, `_ordenar_eventos_horario`,
`_ordenar_nombres` y `_ordenar_ranking` implementan merge sort. Para `X` filas
cuesta `O(X log X)` tiempo y `O(X)` memoria auxiliar en el peor caso. Se elige
porque los ordenamientos integrados están prohibidos y merge sort garantiza
ese costo en todos los casos; un ordenamiento cuadrático sería `O(X²)`.

### R10 — detalle de simulación y costos

`simular_fila(llegadas, frecuencia, capacidad)` modela una sola cola FIFO:
devuelve `[abordados, espera_promedio, espera_maxima, cola_maxima,
no_abordados]`. Usa lotes `[minuto_de_llegada, cantidad]` y un índice de cabeza.
Cuesta `O(T + G)` tiempo y `O(G)` espacio.

`Red.simular_dia(semilla=None)` usa los horarios reales de `horarios.csv` y
simula 1440 minutos. La semilla hace repetible el sorteo. Cada grupo elige al
azar entre destinos alcanzables por las opciones directas o de un transbordo
que tienen salidas programadas utilizables. La primera salida debe estar
dentro de 30 minutos; para transbordos, la salida de conexión también debe
estar dentro de 30 minutos. Si no existe esa opción, no se genera el grupo.
El límite aplica a la espera por salida programada, no a la espera causada por
falta de capacidad.

Estructuras y costos:

- Los eventos `[minuto, viaje, estación, orden]` se ordenan una vez al cargar
  los datos. Construirlos cuesta `O(H·P + H log H)` y `O(H)` espacio: `P`
  representa la búsqueda de cada estación en el recorrido. Los CSV no tienen
  identificador de vehículo; los viajes se reconstruyen alineando la primera
  hora de cada parada, luego la segunda, etc. Si R7 cambia un recorrido, el
  índice se invalida y se reconstruye en la siguiente simulación, no en cada
  edición o acción de deshacer.
- Durante la simulación, los eventos se indexan por viaje/estación y las
  salidas por estación/servicio. Las máscaras de bits indican las estaciones
  posteriores de cada evento. El índice por viaje ocupa `O(VN)` para permitir
  consultar una conexión en `O(1)`, en vez de volver a recorrer sus paradas.
- Las posiciones de salida se precalculan por minuto para cada uno de los `A`
  pares estación-servicio con horarios: `O(NR + 1440A + H)` tiempo y
  `O(1440A)` espacio. Esta tabla evita búsquedas binarias repetidas en la
  consulta más frecuente.
- Los itinerarios directos y con un transbordo se preparan por origen. Si `C`
  es el total de combinaciones de tramos y `D·K` el trabajo de agrupar `D`
  destinos en `K` combinaciones de servicio, el costo es `O(C + D·K)` por
  origen activo. Precalcular evita reconstruir las combinaciones en cada
  minuto.
- R9 guarda acciones delta, no snapshots completos: deshacer/cerrar una
  estación no copia todas las estaciones y rutas. Al cambiar una ruta se marca
  el índice horario como desactualizado; se reconstruye antes de la siguiente
  simulación para que R7 y R10 vean el mismo recorrido.
- La simulación cuesta `O(1440N + W + B + Q)`, además de los índices y el
  precálculo. `W` cuenta salidas consideradas en las ventanas de espera, `B`
  destinos comprobados mediante máscaras y `Q` grupos recorridos en colas y
  manifiestos. Las colas se agrupan por estación y servicio; cada llegada de
  bus conserva en orden los grupos que no puede abordar. El procesamiento
  depende de grupos, no de pasajeros individuales.
- Espacio total: `O(H + VN + NR + 1440A + D + G)`, donde `G` es el número de
  grupos en espera o a bordo. La capacidad del bus se configura de forma
  universal.

El resumen R10 es
`[generados, abordajes, no_abordados, espera_promedio, espera_maxima,
cola_maxima, pasajeros_en_red, llegadas_a_destino]`. Cada fila de estación es
`[nombre, generados, esperando_al_final, cola_maxima, espera_promedio,
espera_maxima, no_abordados, llegadas_a_destino]`. El conteo de llegadas a
destino excluye bajadas de transbordo.

## Interfaz

`front/__main__.py` tiene una pestaña/panel por requisito: búsqueda R1–R2,
rango R3, próximo bus R4, plan R5, ranking R6, edición R7, estado R8,
deshacer/rehacer R9 y simulación R10. Los callbacks convierten entradas,
llaman a `Red` y muestran las respuestas; las decisiones, validaciones y
estructuras de datos permanecen en `motor/`.

Las pruebas locales están en `pruebas/`:

```bash
python -m unittest discover
```
