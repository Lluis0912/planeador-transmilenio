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
