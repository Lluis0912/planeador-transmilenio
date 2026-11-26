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
estándar `csv`, `random` y `time` (este último solo para R11). No se usan
`dict`, `set`, `sorted`, `list.sort`, `min`, `max`, búsquedas `in` sobre listas,
`.index()`, `.count()`, `bisect`, `heapq` ni módulos externos. Por eso los
índices se implementan con listas y búsqueda binaria o recorridos explícitos.
Las búsquedas de texto consideran
mayúsculas y espacios externos equivalentes.

Notación: `N` estaciones, `R` servicios direccionales, `P` máximo de paradas
por servicio, `H` filas de horarios, `U` estaciones rankeadas, `J` pares
servicio-parada en los recorridos actuales, `T` minutos simulados, `G` grupos
de pasajeros, `P_total` pasajeros solicitados, `E` slots elegibles
estación-minuto (estaciones abiertas con ruta por minutos del intervalo) y `Q`
visitas de grupos a colas/manifiestos. `E` es la cantidad de lugares posibles
para distribuir el total fijo; no es una cantidad de pasajeros ni de buses, ni
un término adicional de la fórmula Big O. Con las 147 estaciones abiertas con
ruta y el día completo, `E=1440×147=211.680`. Los costos de comparar cadenas
suponen longitudes acotadas; si `L` es la longitud del texto, normalizarlo
cuesta `O(L)`.

| Req. | Función y estructura | Complejidad y motivo |
|---|---|---|
| R1 | `Red.estado`: listas paralelas ordenadas `_estaciones` y `_abiertas`. | Consulta `O(log N)` por búsqueda binaria; una lista sin ordenar requeriría `O(N)`. |
| R2 | `Red.autocompletar`: búsqueda binaria del primer prefijo y recorrido contiguo. La interfaz combina sugerencias y estado en una sola barra. | `O(log N + M)`, donde `M` son los nombres revisados para encontrar hasta `k` resultados. Evita examinar toda la red cuando el prefijo es selectivo. |
| R3 | `Red.rango`: la misma lista ordenada, búsqueda binaria del límite y recorrido en la dirección solicitada. | `O(log N + K)`, donde `K` son las estaciones examinadas en el rango; construir la salida es necesariamente proporcional a lo examinado. Admite orden alfabético inverso. |
| R4 | `Red.proximo_bus`: horarios ordenados por servicio, estación y minuto; dos búsquedas binarias. | `O(log B + V log H)`, donde `B` son identificadores de servicio, `V` las variantes del bus solicitado y `H` todas las filas de horarios. La búsqueda binaria evita escanear las horas anteriores. |
| R5 | `Red.viaje`: listas de paradas en orden de recorrido y búsqueda lineal de origen, destino y conexiones. Compara viajes directos y de un transbordo y devuelve el de menos paradas. | `O(log N + R²P² + R²P log N)`; las listas preservan el orden y cumplen las restricciones. Mantiene solo el mejor resultado, con un máximo de dos segmentos (`O(1)` espacio de salida). |
| R6 | `Red.ranking`: agrupa horarios por servicio, estima sus viajes diarios con la mayor frecuencia observada en una parada y asigna esa frecuencia a cada parada actual (incluidas las añadidas en R7). El ranking queda cacheado; el estado abierto se consulta en vivo. | Construcción `O(H + R + J log J + U log U + U log N)`; consulta `O(M)` para revisar `M` filas hasta reunir `k` estaciones abiertas. Cerrar/reabrir filtra el cache sin reconstruirlo; una edición R7 lo invalida y se reconstruye al consultar R6. R10 no lo modifica. |
| R7 | `Red.recorrido`, `agregar_parada` y `quitar_parada`: listas de paradas; solo se editan estaciones existentes y un servicio direccional a la vez. | Consultar `O(R + P)`; quitar `O(R + P)`; agregar `O(R + P + log N)` por validar que la estación existe. R9 guarda referencias a las versiones anterior/nueva, sin copiar el resto de la red. Una edición invalida las cachés de R6 y el índice horario R10; ambos se reconstruyen de forma diferida al consultar R6 o iniciar la siguiente simulación. |
| R8 | `Red.cerrar` y `Red.reabrir`: el estado se guarda en `_abiertas`, en paralelo con `_estaciones`. | Buscar la estación `O(log N)` y guardar el cambio delta en `O(1)`. La lista paralela permite encontrar y modificar el estado con el mismo índice. |
| R9 | `Red.deshacer` y `Red.rehacer`: dos listas de acciones delta usadas como pilas LIFO. | Aplicar y mover una acción cuesta `O(1)` amortizado: cambios de estado guardan un booleano; ediciones de ruta guardan referencias a las listas antes/después. Una edición/deshacer/rehacer de ruta invalida las cachés R6 y R10. Espacio `O(C + PΣ)`, donde `C` son cambios y `PΣ` la suma de paradas en versiones de ruta conservadas. |
| R10 | `Red.simular_dia`: eventos de horario, matriz de colas estación-servicio, lotes FIFO, manifiestos de viaje, máscaras de bits de paradas y posiciones de salida precalculadas por minuto. Acepta hora de inicio hasta medianoche y conserva el modo de flujos. | Ver el análisis abajo. Un lote representa pasajeros que llegan juntos; no se crea un objeto por persona. |
| R11 | No agrega otro simulador: `Red.medir_rendimiento_r10` repite `Red.simular_dia` usando el total real `n` de la última R10 y `2n`, `4n`, `8n`, `16n`. Hace 3 mediciones por tamaño y grafica el promedio. | Compara el mismo algoritmo, red, hora y capacidad. Una base sin pasajeros ayuda a separar el costo fijo; las mediciones son aproximadas, no deben duplicarse exactamente. |

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

`Red.simular_dia(semilla=None, total_pasajeros=None, hora_inicio="00:00")`
usa horarios reales de `horarios.csv` y procesa desde la hora indicada hasta
medianoche. El modo de flujo preserva las tasas globales/locales y los picos;
solo genera un lote cuando existe una salida programada utilizable dentro de
30 minutos (también valida las conexiones). El modo de total fijo ignora las
tasas y los picos, asigna exactamente `P_total` a los slots con estación abierta
y ruta topológica, y puede generar espera inicial superior a 30 minutos. En
ambos modos los destinos se sortean por lote y el abordaje verifica el recorrido
y los transbordos reales. El total fijo no está limitado por la capacidad diaria
de los buses: puede dejar pasajeros esperando al cierre, sobre todo si la demanda
es alta o llega tarde. En modo flujo, la cantidad depende de la tasa configurada
y solo se genera si hay una salida utilizable dentro de 30 minutos. `no_abordados`
cuenta quienes siguen en cola al terminar el día.

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
  destinos comprobados mediante máscaras y `Q` visitas de grupos en colas y
  manifiestos. Las colas se agrupan por estación y servicio; cada llegada de
  bus conserva en orden los grupos que no puede abordar. El procesamiento
  depende de lotes, no de objetos por pasajero.
- R11 usa como `n` el total que realmente generó la última R10. Si R10 se
  ejecutó por flujo, el benchmark convierte ese conteo en total exacto para
  poder duplicarlo; conserva red, hora y capacidad. Cada corrida tiene la misma
  complejidad que R10. R11 hace 3 corridas base sin pasajeros y 3 corridas por
  cada tamaño (`n`, `2n`, `4n`, `8n`, `16n`): con la red fija, su orden
  asintótico es el de la corrida mayor, aunque el tiempo real suma las 18
  ejecuciones. Big O es una tendencia, no predice una duplicación exacta: hay
  costo fijo, lotes, capacidad, transferencias y ruido del equipo.
- Con los CSV actuales: `N=147` estaciones, `R=181` servicios, `H=140.492`
  horarios, `A=1.927` pares estación-servicio y `V=13.560` viajes. En un día,
  `T=1440`; por eso `T·N` son hasta `211.680` revisiones estación-minuto.
- Fórmula: `O(N·R + H + 1440·A + V·N + N·(C + D·K) + T·N + W + B + Q)`.
  Cada término significa:
  - `N·R`: preparar colas por estación y servicio.
  - `H`: procesar horarios y eventos.
  - `1440·A`: preparar salidas por minuto y par estación-servicio.
  - `V·N`: indexar viajes por estación.
  - `N·(C + D·K)`: preparar itinerarios posibles desde cada origen.
  - `T·N`: recorrer minutos y estaciones.
  - `E` (parámetro, no sumando de Big O): slots estación-minuto elegibles donde
    se distribuye el total fijo; cuando `P_total > E`, algunos slots reciben
    grupos de más de una persona.
  - `W`: revisar salidas y conexiones posibles.
  - `B`: comprobar destinos candidatos.
  - `Q`: procesar grupos en colas y buses; es el término que cambia con la
    carga, no se crea un registro por cada pasajero.
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
deshacer/rehacer R9 y simulación R10–R11. R10 presenta configuración y
resultados; R11 tiene una vista interna independiente para repetir y graficar
las mediciones sin ocultar la tabla de R10. La gráfica permite cambiar el eje X
entre escala log2 (predeterminada) y regular; en escala regular las distancias
son proporcionales al número de pasajeros. La vista R11 tiene desplazamiento
vertical y la gráfica incluye una barra horizontal para consultar las etiquetas
X cuando no caben en la ventana. La tabla de R10 también tiene desplazamiento
vertical. Los callbacks convierten entradas, llaman a `Red` y muestran las
respuestas; las decisiones, validaciones y estructuras permanecen en `motor/`.

Las pruebas locales están en `pruebas/`:

```bash
python -m unittest discover
```
