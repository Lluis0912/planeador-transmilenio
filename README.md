# Planeador TransMilenio

Aplicación de escritorio en Python. `motor/` implementa la lógica y `front/`
recibe datos y presenta resultados.

## Ejecutar
Desde la carpeta del proyecto o desde la terminal en vscode, usar este comando para iniciar el programa porfis:

```bash
python -m front
```

## para algunos computadores es mejor usar "py -m front" para iniciar el programa

La aplicación carga `datos/estaciones.csv`, `datos/rutas.csv` y `datos/horarios.csv`.

## Requisitos, estructuras y complejidad

Por las restricciones del ejercicio, el motor usa listas y ordenamientos
propios; no usa diccionarios, conjuntos ni los ordenamientos integrados. Se
ordenan las listas que requieren búsquedas frecuentes y se crean índices para
evitar recorridos repetidos. 
Esta elección es la mejor solamente bajo estas restricciones;
no afirma que las listas sean óptimas en cualquier implementación.

## Notacion y variables que van a estar presentes en los requerimientos (En especial R10):

`N` estaciones, `R` servicios, `P` máximo de paradas por servicio,
`H` filas de horarios, `J` pares servicio-parada, `U` estaciones del ranking,
`T` minutos, `A` pares estación-servicio con horarios y `V` viajes. En R4,
`b` son buses y `v` variantes del bus consultado. En R10, `C` son combinaciones
de tramos y `D` destinos por origen; `K` son grupos de itinerarios por origen.
`W` son salidas revisadas, `B` destinos comprobados, `Q` visitas de grupos a
colas y buses y `G` grupos de pasajeros en memoria. `M` son filas revisadas en
una consulta y `K_r` estaciones dentro del rango de R3.

## Aqui una tabla que se ve mas bonita en Github que explica los requerimientos, su estructura, el porque de la estructura, y su complejidad: 

| Req. | Estructura usada y por qué | Complejidad |
|---|---|---|
| R1 | `_estaciones` y `_abiertas`: listas ordenadas paralelas. La búsqueda binaria encuentra la estación y su estado por el mismo índice. | Consulta `O(log N)`. |
| R2 | La misma lista ordenada; búsqueda binaria del prefijo y recorrido solo de coincidencias. Evita revisar toda la red si hay pocos resultados. | `O(log N + M)`, donde `M` son los nombres revisados. |
| R3 | La misma lista; búsqueda binaria del límite y recorrido ordenado del rango. | `O(log N + K_r)`, donde `K_r` son las estaciones del rango. |
| R4 | Horarios ordenados por bus, estación y minuto; búsqueda binaria para saltar llegadas anteriores. | `O(log b + v log H)`, donde `b` son buses y `v` variantes del bus solicitado. |
| R5 | Recorridos como listas en orden de parada. Se comparan pares de servicios porque solo se permite un transbordo; el orden conserva el sentido sin otro índice. | `O(log N + R²P² + R²P log N)`. |
| R6 | Frecuencias agrupadas y ranking guardado en una lista ordenada. La caché evita recalcular el ranking en cada consulta; se invalida al editar rutas. | Construcción `O(H + R + J log J + U log U + U log N)`; consulta `O(M)`. |
| R7 | Una lista de paradas por servicio direccional. Se reemplaza solo la ruta editada; R9 guarda las versiones anterior y nueva para deshacer sin copiar la red. | Consultar o quitar `O(R + P)`; agregar `O(R + P + log N)`. |
| R8 | Estado en la lista paralela `_abiertas`. Comparte índice con la búsqueda ordenada de R1. | Buscar estación `O(log N)`; cambiar el booleano `O(1)`. |
| R9 | Dos listas como pilas LIFO. Cada acción guarda el estado cambiado o las versiones anterior y nueva de la ruta editada, no una copia de toda la red. | Deshacer/rehacer `O(1)` amortizado. |
| R10 | Eventos ordenados, índices por viaje/estación, matriz de colas FIFO por estación/servicio y lotes. Los índices evitan búsquedas repetidas; los lotes evitan crear un objeto por persona. | Preparar eventos: `O(H·P + H log N + H log H)` tiempo y `O(H + P)` espacio, una vez o tras editar rutas. Cada corrida: `O(NR + H + 1440A + VN + N(C + DK) + TN + W + B + Q)` tiempo y `O(H + VN + NR + 1440A + ND + G)` espacio. |
| R11 | Repite R10 con `n`, `2n`, `4n`, `8n` y `16n`; promedia tres corridas por tamaño y tres bases sin pasajeros. Reutiliza el mismo algoritmo para comparar tamaños. | Cada corrida tiene el Big O de R10. Con red fija, el total tiene el orden de la corrida de mayor costo; el benchmark ejecuta 18 corridas. |


## Sabemos que la eficiencia en espacio no es necesaria, pero mantenemos esto aca por si acaso: 

Merge sort ordena las listas en `O(X log X)` tiempo y `O(X)` espacio. Se usa
porque los ordenamientos integrados están restringidos y este mantiene un costo
predecible, a diferencia de un ordenamiento cuadrático.

### R10 y R11, porfa usar el programa primero para entender mejor esto.

R10 termina a medianoche. En modo flujo usa las tasas y los picos configurados;
genera un grupo cuando hay una salida utilizable dentro de 30 minutos. En modo
total fijo ignora las tasas y reparte exactamente el total entre slots de
estación-minuto de estaciones abiertas con al menos un destino alcanzable por
los recorridos disponibles. Los buses conservan su capacidad, por lo que algunos
pasajeros pueden seguir esperando al cierre.

`E` es la cantidad de slots elegibles: estaciones abiertas con al menos un
destino alcanzable por los recorridos disponibles, multiplicadas por los
minutos del intervalo. Sirve para repartir el total fijo.

## E no es una cantidad de pasajeros ni de buses, ni un término adicional del Big O. 

Con 147 estaciones elegibles y el día completo: `E=211.680`.

Al preparar eventos, R10 alinea las horas de cada parada por posición para reconstruir viajes. 
Es una aproximación a partir de los CSV.

`no_abordados` cuenta pasajeros que siguen en cola al cierre; pasajeros todavía
a bordo se cuentan en `pasajeros_en_red`.

R11 compara el total `n` generado por la última simulación R10 con tamaños
duplicados. <-- <-- Importante.
Si R10 se ejecutó en modo flujo, el benchmark usa ese conteo como
total fijo para poder comparar tamaños. La base permite distinguir el costo fijo
del trabajo adicional; Big O describe una tendencia, no garantiza que el tiempo
se duplique exactamente.

## Interfaz y pruebas, Las preubas se usaron principalmente como metodo de verificacion de la IA para que todo funcionara bien, y por nosotros al hacer un cambio grande, y verificar que todo siguiera funcionando

R10 muestra la configuración y los resultados. R11 grafica las mediciones con
escala log2 o regular. Las pruebas están en `pruebas/` y se ejecutan con:

```bash
python -m unittest discover
```
## en ciertos computadores, toca usar py <m unittest discover
