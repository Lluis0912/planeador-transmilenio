from pathlib import Path
import tkinter as tk
from tkinter import ttk

from motor import Red


class PlaneadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planeador TransMilenio")
        self.geometry("900x650")
        self.minsize(760, 520)
        carpeta_datos = Path(__file__).resolve().parents[1] / "datos"
        self.red = Red(carpeta_datos)

        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True, padx=12, pady=12)

        self._crear_pestana_busqueda(self.pestanas)
        self._crear_pestana_rango(self.pestanas)
        self._crear_pestana_proximo(self.pestanas)
        self._crear_pestana_viaje(self.pestanas)
        self._crear_pestana_ranking(self.pestanas)
        self._crear_pestana_operacion(self.pestanas)
        self._crear_pestana_simulacion(self.pestanas)
        self.bind_all("<Control-z>", self._atajo_deshacer)
        self.bind_all("<Control-y>", self._atajo_rehacer)
        self.bind_all("<Control-Shift-Z>", self._atajo_rehacer)

    def _crear_pestana_busqueda(self, pestañas):
        # R1 y R2 se muestran juntos: Combobox usa Red.autocompletar() mientras
        # escribe el usuario y Red.estado() al escribir, presionar Enter o elegir.
        pestaña = ttk.Frame(pestañas, padding=16)
        pestañas.add(pestaña, text="Buscar estación")

        ttk.Label(
            pestaña, text="Escribe o selecciona una estación"
        ).pack(anchor="w")
        self.busqueda = tk.StringVar()
        self.entrada_busqueda = ttk.Combobox(
            pestaña, textvariable=self.busqueda, state="normal"
        )
        self.entrada_busqueda.pack(fill="x", pady=(6, 12))
        self.entrada_busqueda.bind("<KeyRelease>", self._actualizar_busqueda)
        self.entrada_busqueda.bind(
            "<<ComboboxSelected>>", self._consultar_estado
        )
        self.entrada_busqueda.bind("<Return>", self._consultar_estado)

        self.resultado_estado = ttk.Label(pestaña, text="")
        self.resultado_estado.pack(anchor="w", pady=(4, 12))

    def _consultar_estado(self, evento=None):
        # Conexion R1: el resultado de Red.estado() controla el mensaje.
        # Toda la decision existe-abierta vive en motor/, no en el front.
        nombre = self.busqueda.get()
        existe, abierta = self.red.estado(nombre)
        if not existe:
            mensaje = "La estación no existe."
        elif abierta:
            mensaje = "La estación existe y está abierta."
        else:
            mensaje = "La estación existe y está cerrada."
        self.resultado_estado.configure(text=mensaje)

    def _actualizar_busqueda(self, evento):
        # Conexion R2: el texto actual se envia a Red.autocompletar()
        # como prefijo. El front solo muestra las opciones recibidas.
        prefijo = self.busqueda.get()
        resultados = self.red.autocompletar(prefijo, 10)
        self.entrada_busqueda.configure(values=resultados)
        self._consultar_estado()
        if prefijo and resultados:
            self.entrada_busqueda.event_generate("<Down>")

    def _crear_pestana_rango(self, pestañas):
        # R3: el front captura dos limites y delega todo el recorrido,
        # el orden y el filtrado de estaciones abiertas a Red.rango().
        pestaña = ttk.Frame(pestañas, padding=16)
        pestañas.add(pestaña, text="Rango alfabético")

        fila = ttk.Frame(pestaña)
        fila.pack(fill="x")
        ttk.Label(fila, text="Desde").grid(row=0, column=0, sticky="w")
        ttk.Label(fila, text="Hasta").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.desde = tk.StringVar()
        self.hasta = tk.StringVar()
        ttk.Entry(fila, textvariable=self.desde).grid(
            row=1, column=0, sticky="ew"
        )
        ttk.Entry(fila, textvariable=self.hasta).grid(
            row=1, column=1, sticky="ew", padx=(12, 0)
        )
        fila.columnconfigure(0, weight=1)
        fila.columnconfigure(1, weight=1)
        ttk.Button(
            pestaña, text="Listar estaciones", command=self._consultar_rango
        ).pack(anchor="w", pady=12)

        self.lista_rango = tk.Listbox(pestaña, height=14)
        self.lista_rango.pack(fill="both", expand=True)

    def _consultar_rango(self):
        # El motor decide el orden ascendente o inverso segun los limites.
        # El front solamente elimina resultados viejos y llena el Listbox.
        resultados = self.red.rango(self.desde.get(), self.hasta.get())
        self.lista_rango.delete(0, tk.END)
        for estacion in resultados:
            self.lista_rango.insert(tk.END, estacion)

    def _crear_pestana_proximo(self, pestañas):
        # R4: el front recoge estacion, bus y hora actual; Red.proximo_bus() hace
        # toda la conversion y busqueda sobre los horarios.
        pestaña = ttk.Frame(pestañas, padding=16)
        pestañas.add(pestaña, text="Próximo bus")

        ttk.Label(pestaña, text="Estación").grid(row=0, column=0, sticky="w")
        ttk.Label(pestaña, text="Bus (ej. B74)").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Label(pestaña, text="Hora (HH:MM)").grid(row=0, column=2, sticky="w", padx=(12, 0))

        self.bus_estacion = tk.StringVar()
        self.bus_codigo = tk.StringVar()
        self.bus_hora = tk.StringVar()
        ttk.Entry(pestaña, textvariable=self.bus_estacion).grid(row=1, column=0, sticky="ew")
        ttk.Entry(pestaña, textvariable=self.bus_codigo).grid(row=1, column=1, sticky="ew", padx=(12, 0))
        ttk.Entry(pestaña, textvariable=self.bus_hora).grid(row=1, column=2, sticky="ew", padx=(12, 0))
        pestaña.columnconfigure(0, weight=1)
        pestaña.columnconfigure(1, weight=1)
        pestaña.columnconfigure(2, weight=1)

        ttk.Button(pestaña, text="Consultar", command=self._consultar_proximo).grid(
            row=2, column=0, sticky="w", pady=12
        )
        self.resultado_proximo = ttk.Label(pestaña, text="")
        self.resultado_proximo.grid(row=3, column=0, columnspan=3, sticky="w")

    def _consultar_proximo(self):
        hora = self.red.proximo_bus(
            self.bus_estacion.get(),
            self.bus_codigo.get(),
            self.bus_hora.get(),
        )
        if hora is None:
            mensaje = "No hay un bus posterior con esos datos."
        else:
            mensaje = "Próximo bus: " + hora
        self.resultado_proximo.configure(text=mensaje)

    def _crear_pestana_viaje(self, pestañas):
        # R5: cada segmento recibido tiene [ruta, subida, bajada].
        # El front solo presenta el plan calculado por Red.viaje().
        pestaña = ttk.Frame(pestañas, padding=16)
        pestañas.add(pestaña, text="Planear viaje")

        ttk.Label(pestaña, text="Origen").grid(row=0, column=0, sticky="w")
        ttk.Label(pestaña, text="Destino").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.viaje_origen = tk.StringVar()
        self.viaje_destino = tk.StringVar()
        ttk.Entry(pestaña, textvariable=self.viaje_origen).grid(row=1, column=0, sticky="ew")
        ttk.Entry(pestaña, textvariable=self.viaje_destino).grid(row=1, column=1, sticky="ew", padx=(12, 0))
        pestaña.columnconfigure(0, weight=1)
        pestaña.columnconfigure(1, weight=1)

        ttk.Button(pestaña, text="Planear", command=self._consultar_viaje).grid(
            row=2, column=0, sticky="w", pady=12
        )
        self.lista_viaje = tk.Listbox(pestaña, height=10)
        self.lista_viaje.grid(row=3, column=0, columnspan=2, sticky="nsew")
        pestaña.rowconfigure(3, weight=1)

    def _consultar_viaje(self):
        segmentos = self.red.viaje(
            self.viaje_origen.get(),
            self.viaje_destino.get(),
        )
        self.lista_viaje.delete(0, tk.END)
        if len(segmentos) == 0:
            self.lista_viaje.insert(tk.END, "No existe un viaje directo o con un transbordo.")
        else:
            indice = 1
            for segmento in segmentos:
                texto = (
                    "Tramo " + str(indice)
                    + ": bus " + segmento[0]
                    + " desde " + segmento[1]
                    + " hasta " + segmento[2]
                )
                self.lista_viaje.insert(tk.END, texto)
                indice += 1

    def _crear_pestana_ranking(self, pestañas):
        # R6: el front solicita k nombres al motor; el motor usa el cache
        # ordenado sin volver a contar todos los horarios.
        pestaña = ttk.Frame(pestañas, padding=16)
        pestañas.add(pestaña, text="Ranking")

        fila = ttk.Frame(pestaña)
        fila.pack(fill="x")
        ttk.Label(fila, text="Cantidad").pack(side="left")
        self.ranking_k = tk.StringVar(value="10")
        ttk.Spinbox(fila, from_=1, to=147, width=5, textvariable=self.ranking_k).pack(
            side="left", padx=(8, 12)
        )
        ttk.Button(fila, text="Mostrar", command=self._consultar_ranking).pack(side="left")

        self.lista_ranking = tk.Listbox(pestaña, height=14)
        self.lista_ranking.pack(fill="both", expand=True, pady=(12, 0))

    def _consultar_ranking(self):
        try:
            cantidad = int(self.ranking_k.get())
        except ValueError:
            cantidad = 0
        resultados = self.red.ranking(cantidad)
        self.lista_ranking.delete(0, tk.END)
        posicion = 1
        for estacion in resultados:
            self.lista_ranking.insert(tk.END, str(posicion) + ". " + estacion)
            posicion += 1

    def _crear_pestana_operacion(self, pestañas):
        # R7-R9: botones y atajos llaman las funciones del motor. El front
        # muestra datos y mensajes, pero las validaciones/historial viven en Red.
        self.pestana_operacion = ttk.Frame(pestañas, padding=10)
        pestañas.add(self.pestana_operacion, text="Operar red")

        barra_historial = ttk.Frame(self.pestana_operacion)
        barra_historial.pack(fill="x", pady=(0, 8))
        ttk.Button(
            barra_historial, text="↶ Deshacer", command=self._deshacer_cambio
        ).pack(side="left")
        ttk.Button(
            barra_historial, text="↷ Rehacer", command=self._rehacer_cambio
        ).pack(side="left", padx=(6, 0))
        ttk.Label(
            barra_historial, text="Atajos: Ctrl+Z / Ctrl+Y"
        ).pack(side="left", padx=12)
        self.mensaje_historial = tk.StringVar(value="")
        ttk.Label(barra_historial, textvariable=self.mensaje_historial).pack(
            side="left", padx=8
        )

        self.pestanas_operacion = ttk.Notebook(self.pestana_operacion)
        self.pestanas_operacion.pack(fill="both", expand=True)
        self._crear_panel_rutas(self.pestanas_operacion)
        self._crear_panel_estaciones(self.pestanas_operacion)

    def _crear_panel_rutas(self, pestañas):
        panel = ttk.Frame(pestañas, padding=10)
        pestañas.add(panel, text="Editar recorridos (R7)")

        seleccion = ttk.Frame(panel)
        seleccion.pack(fill="x")
        ttk.Label(seleccion, text="Bus").pack(side="left")
        self.bus_edicion = tk.StringVar()
        self.selector_bus_edicion = ttk.Combobox(
            seleccion, textvariable=self.bus_edicion, state="readonly", width=16
        )
        self.selector_bus_edicion.pack(side="left", padx=(6, 16))
        self.selector_bus_edicion.bind(
            "<<ComboboxSelected>>", self._actualizar_servicios_edicion
        )
        ttk.Label(seleccion, text="Recorrido").pack(side="left")
        self.servicio_edicion = tk.StringVar()
        self.selector_servicio = ttk.Combobox(
            seleccion,
            textvariable=self.servicio_edicion,
            state="readonly",
            width=18,
        )
        self.selector_servicio.pack(side="left", padx=6)
        self.selector_servicio.bind(
            "<<ComboboxSelected>>", lambda evento: self._actualizar_listas_ruta()
        )

        columnas = ttk.Frame(panel)
        columnas.pack(fill="both", expand=True, pady=(10, 8))
        columna_ida = ttk.Frame(columnas)
        columna_vuelta = ttk.Frame(columnas)
        columna_ida.pack(side="left", fill="both", expand=True, padx=(0, 5))
        columna_vuelta.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ttk.Label(columna_ida, text="Recorrido del servicio").pack(anchor="w")
        ttk.Label(columna_vuelta, text="Mismo recorrido al revés").pack(anchor="w")
        self.lista_ida = tk.Listbox(columna_ida, height=9, exportselection=False)
        self.lista_vuelta = tk.Listbox(columna_vuelta, height=9, exportselection=False)
        self.lista_ida.pack(fill="both", expand=True)
        self.lista_vuelta.pack(fill="both", expand=True)

        controles = ttk.LabelFrame(panel, text="Modificar paradas existentes", padding=8)
        controles.pack(fill="x")
        ttk.Label(controles, text="Agregar estación").grid(row=0, column=0, sticky="w")
        ttk.Label(controles, text="Insertar después de").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.estacion_nueva = tk.StringVar()
        self.parada_previa = tk.StringVar()
        self.selector_estacion_nueva = ttk.Combobox(
            controles,
            textvariable=self.estacion_nueva,
            values=self.red.estaciones(),
            state="readonly",
        )
        self.selector_estacion_nueva.grid(row=1, column=0, sticky="ew")
        self.selector_parada_previa = ttk.Combobox(
            controles, textvariable=self.parada_previa, state="readonly"
        )
        self.selector_parada_previa.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(
            controles, text="Agregar parada", command=self._agregar_parada_ui
        ).grid(row=1, column=2, padx=(8, 0))
        ttk.Button(
            controles,
            text="Quitar seleccionada",
            command=self._quitar_parada_ui,
        ).grid(row=1, column=3, padx=(6, 0))
        controles.columnconfigure(0, weight=1)
        controles.columnconfigure(1, weight=1)

        self.mensaje_rutas = ttk.Label(panel, text="")
        self.mensaje_rutas.pack(anchor="w", pady=(6, 0))
        buses = self.red.buses_rutas()
        self.selector_bus_edicion.configure(values=buses)
        if buses:
            self.bus_edicion.set(buses[0])
            self._actualizar_servicios_edicion()

    def _actualizar_servicios_edicion(self, evento=None):
        servicios = self.red.servicios(self.bus_edicion.get())
        self.selector_servicio.configure(values=servicios)
        if servicios:
            self.servicio_edicion.set(servicios[0])
        else:
            self.servicio_edicion.set("")
        self._actualizar_listas_ruta()

    def _actualizar_listas_ruta(self):
        servicio = self.servicio_edicion.get()
        ida = self.red.recorrido(servicio)
        vuelta = self.red.recorrido(servicio, al_reves=True)
        self.lista_ida.delete(0, tk.END)
        self.lista_vuelta.delete(0, tk.END)
        for estacion in ida:
            self.lista_ida.insert(tk.END, estacion)
        for estacion in vuelta:
            self.lista_vuelta.insert(tk.END, estacion)

        opciones_insercion = ida[:-1] if len(ida) > 0 else []
        self.selector_parada_previa.configure(values=opciones_insercion)
        if opciones_insercion:
            self.parada_previa.set(opciones_insercion[0])
        else:
            self.parada_previa.set("")

    def _agregar_parada_ui(self):
        try:
            self.red.agregar_parada(
                self.servicio_edicion.get(),
                self.estacion_nueva.get(),
                self.parada_previa.get(),
            )
        except ValueError as error:
            self.mensaje_rutas.configure(text=str(error))
            return

        self.mensaje_rutas.configure(text="Parada agregada al recorrido.")
        self._actualizar_listas_ruta()

    def _quitar_parada_ui(self):
        seleccion = self.lista_ida.curselection()
        if seleccion:
            estacion = self.lista_ida.get(seleccion[0])
        else:
            seleccion = self.lista_vuelta.curselection()
            if not seleccion:
                self.mensaje_rutas.configure(
                    text="Selecciona una parada en cualquiera de los recorridos."
                )
                return
            estacion = self.lista_vuelta.get(seleccion[0])

        try:
            self.red.quitar_parada(self.servicio_edicion.get(), estacion)
        except ValueError as error:
            self.mensaje_rutas.configure(text=str(error))
            return

        self.mensaje_rutas.configure(text="Parada quitada del recorrido.")
        self._actualizar_listas_ruta()

    def _crear_panel_estaciones(self, pestañas):
        panel = ttk.Frame(pestañas, padding=12)
        pestañas.add(panel, text="Estaciones (R8)")
        ttk.Label(panel, text="Selecciona una estación existente").pack(anchor="w")
        self.estacion_operacion = tk.StringVar()
        self.selector_estacion_operacion = ttk.Combobox(
            panel,
            textvariable=self.estacion_operacion,
            values=self.red.estaciones(),
            state="readonly",
        )
        self.selector_estacion_operacion.pack(fill="x", pady=(6, 10))
        self.selector_estacion_operacion.bind(
            "<<ComboboxSelected>>", lambda evento: self._actualizar_estado_operacion()
        )

        botones = ttk.Frame(panel)
        botones.pack(anchor="w")
        self.boton_cerrar = ttk.Button(
            botones, text="Cerrar estación", command=self._cerrar_estacion_ui
        )
        self.boton_cerrar.pack(side="left")
        self.boton_reabrir = ttk.Button(
            botones, text="Reabrir estación", command=self._reabrir_estacion_ui
        )
        self.boton_reabrir.pack(side="left", padx=(8, 0))
        self.estado_operacion = ttk.Label(panel, text="")
        self.estado_operacion.pack(anchor="w", pady=(12, 0))
        estaciones = self.red.estaciones()
        if estaciones:
            self.selector_estacion_operacion.set(estaciones[0])
        self._actualizar_estado_operacion()

    def _actualizar_estado_operacion(self):
        nombre = self.estacion_operacion.get()
        existe, abierta = self.red.estado(nombre)
        if not existe:
            self.estado_operacion.configure(text="Selecciona una estación.")
            self.boton_cerrar.configure(state="disabled")
            self.boton_reabrir.configure(state="disabled")
        elif abierta:
            self.estado_operacion.configure(text="La estación está abierta.")
            self.boton_cerrar.configure(state="normal")
            self.boton_reabrir.configure(state="disabled")
        else:
            self.estado_operacion.configure(text="La estación está cerrada.")
            self.boton_cerrar.configure(state="disabled")
            self.boton_reabrir.configure(state="normal")

    def _cerrar_estacion_ui(self):
        try:
            self.red.cerrar(self.estacion_operacion.get())
        except ValueError as error:
            self.estado_operacion.configure(text=str(error))
            return
        self._actualizar_estado_operacion()

    def _reabrir_estacion_ui(self):
        try:
            self.red.reabrir(self.estacion_operacion.get())
        except ValueError as error:
            self.estado_operacion.configure(text=str(error))
            return
        self._actualizar_estado_operacion()

    def _deshacer_cambio(self, evento=None):
        if self.red.deshacer():
            mensaje = "Último cambio deshecho."
        else:
            mensaje = "No hay cambios para deshacer."
        self.mensaje_historial.set(mensaje)
        self.mensaje_rutas.configure(text=mensaje)
        self._actualizar_listas_ruta()
        self._actualizar_estado_operacion()
        return "break"

    def _rehacer_cambio(self, evento=None):
        if self.red.rehacer():
            mensaje = "Cambio rehecho."
        else:
            mensaje = "No hay cambios para rehacer."
        self.mensaje_historial.set(mensaje)
        self.mensaje_rutas.configure(text=mensaje)
        self._actualizar_listas_ruta()
        self._actualizar_estado_operacion()
        return "break"

    def _atajo_deshacer(self, evento):
        if self.pestanas.select() == str(self.pestana_operacion):
            return self._deshacer_cambio(evento)
        return None

    def _atajo_rehacer(self, evento):
        if self.pestanas.select() == str(self.pestana_operacion):
            return self._rehacer_cambio(evento)
        return None

    def _crear_pestana_simulacion(self, pestañas):
        # R10: formularios de demanda/capacidad y resultados; el motor genera,
        # enruta y simula pasajeros, buses, colas, esperas y transbordos.
        panel = ttk.Frame(pestañas, padding=10)
        pestañas.add(panel, text="Simulación R10")

        configuracion = ttk.LabelFrame(
            panel, text="Configuración de demanda para un día", padding=8
        )
        configuracion.pack(fill="x")

        ttk.Label(
            configuracion,
            text="Flujo global (pasajeros/min en cada estación)",
        ).grid(row=0, column=0, sticky="w")
        self.flujo_global_r10 = tk.StringVar(value="0")
        ttk.Entry(configuracion, textvariable=self.flujo_global_r10, width=9).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Button(
            configuracion,
            text="Aplicar a todas",
            command=self._configurar_demanda_global,
        ).grid(row=1, column=1, padx=(8, 0), sticky="w")
        ttk.Label(
            configuracion,
            text="Cada grupo elige al azar otra estación como destino.",
        ).grid(row=1, column=2, columnspan=3, padx=(12, 0), sticky="w")

        ttk.Separator(configuracion, orient="horizontal").grid(
            row=2, column=0, columnspan=5, sticky="ew", pady=7
        )
        ttk.Label(configuracion, text="Estación").grid(row=3, column=0, sticky="w")
        ttk.Label(configuracion, text="Flujo local/min (vacío = global)").grid(
            row=3, column=1, sticky="w", padx=(8, 0)
        )
        self.origen_local_r10 = tk.StringVar()
        self.flujo_local_r10 = tk.StringVar(value="")
        self.selector_origen_local_r10 = ttk.Combobox(
            configuracion,
            textvariable=self.origen_local_r10,
            values=self.red.estaciones(),
            state="readonly",
        )
        self.selector_origen_local_r10.grid(row=4, column=0, sticky="ew")
        ttk.Entry(configuracion, textvariable=self.flujo_local_r10, width=9).grid(
            row=4, column=1, sticky="ew", padx=(8, 0)
        )
        ttk.Button(
            configuracion,
            text="Aplicar estación",
            command=self._configurar_demanda_local,
        ).grid(row=4, column=2, padx=(8, 0))
        ttk.Button(
            configuracion,
            text="Usar global",
            command=self._quitar_demanda_local,
        ).grid(row=4, column=3, padx=(5, 0))

        ttk.Separator(configuracion, orient="horizontal").grid(
            row=5, column=0, columnspan=5, sticky="ew", pady=7
        )
        ttk.Label(configuracion, text="Pico desde").grid(row=6, column=0, sticky="w")
        ttk.Label(configuracion, text="hasta (exclusivo)").grid(
            row=6, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Label(configuracion, text="Extra pasajeros/min/estación").grid(
            row=6, column=2, sticky="w", padx=(8, 0)
        )
        self.pico_desde_r10 = tk.StringVar(value="14:00")
        self.pico_hasta_r10 = tk.StringVar(value="17:00")
        self.pico_extra_r10 = tk.StringVar(value="10")
        ttk.Entry(configuracion, textvariable=self.pico_desde_r10, width=9).grid(
            row=7, column=0, sticky="w"
        )
        ttk.Entry(configuracion, textvariable=self.pico_hasta_r10, width=9).grid(
            row=7, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Entry(configuracion, textvariable=self.pico_extra_r10, width=9).grid(
            row=7, column=2, sticky="w", padx=(8, 0)
        )
        ttk.Button(
            configuracion, text="Agregar pico", command=self._agregar_pico_r10
        ).grid(row=7, column=3, padx=(8, 0))
        ttk.Button(
            configuracion, text="Limpiar picos", command=self._limpiar_picos_r10
        ).grid(row=7, column=4, padx=(5, 0))

        self.lista_picos_r10 = tk.Listbox(configuracion, height=3)
        self.lista_picos_r10.grid(
            row=8, column=0, columnspan=5, sticky="ew", pady=(6, 0)
        )
        for columna in range(5):
            configuracion.columnconfigure(columna, weight=1)

        ejecucion = ttk.LabelFrame(panel, text="Buses y ejecución", padding=8)
        ejecucion.pack(fill="x", pady=(8, 0))
        ttk.Label(ejecucion, text="Llegadas y hora de cada bus: horarios.csv").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(ejecucion, text="Capacidad común para todos los buses").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.capacidad_universal_r10 = tk.StringVar(value="80")
        ttk.Label(ejecucion, text="Se usan horarios programados").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Entry(ejecucion, textvariable=self.capacidad_universal_r10, width=8).grid(
            row=1, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Button(
            ejecucion,
            text="Aplicar capacidad",
            command=self._configurar_capacidad_r10,
        ).grid(row=1, column=2, padx=(8, 0))
        ttk.Button(
            ejecucion, text="Simular 1 día", command=self._ejecutar_simulacion_r10
        ).grid(row=1, column=3, padx=(8, 0))
        for columna in range(4):
            ejecucion.columnconfigure(columna, weight=1)

        self.mensaje_r10 = ttk.Label(panel, text="")
        self.mensaje_r10.pack(anchor="w", pady=(5, 0))
        self.resumen_r10 = ttk.Label(
            panel, text="Configura demanda y ejecuta la simulación diaria."
        )
        self.resumen_r10.pack(anchor="w", pady=(2, 6))

        columnas = (
            "station", "generated", "waiting", "max_queue",
            "avg_wait", "max_wait", "not_boarded", "alighted",
        )
        self.tabla_r10 = ttk.Treeview(
            panel, columns=columnas, show="headings", height=8
        )
        titulos = (
            ("station", "Estación"),
            ("generated", "Generados"),
            ("waiting", "Esperan al final"),
            ("max_queue", "Cola máx."),
            ("avg_wait", "Espera prom. min"),
            ("max_wait", "Espera máx. min"),
            ("not_boarded", "No abordaron"),
            ("alighted", "Llegaron a destino"),
        )
        for columna, titulo in titulos:
            self.tabla_r10.heading(columna, text=titulo)
            self.tabla_r10.column(columna, width=115, anchor="center")
        self.tabla_r10.column("station", width=190, anchor="w")
        self.tabla_r10.pack(fill="both", expand=True)

        estaciones = self.red.estaciones()
        if estaciones:
            self.origen_local_r10.set(estaciones[0])

    def _configurar_demanda_global(self):
        try:
            flujo = int(self.flujo_global_r10.get())
            self.red.aplicar_flujo_global_a_estaciones(flujo)
        except ValueError as error:
            self.mensaje_r10.configure(text=str(error))
            return
        self.mensaje_r10.configure(
            text="Flujo global aplicado a todas las estaciones abiertas."
        )

    def _configurar_demanda_local(self):
        try:
            texto_flujo = self.flujo_local_r10.get().strip()
            flujo = int(texto_flujo) if texto_flujo != "" else None
            self.red.configurar_demanda_estacion(
                self.origen_local_r10.get(),
                flujo,
            )
        except ValueError as error:
            self.mensaje_r10.configure(text=str(error))
            return
        self.mensaje_r10.configure(
            text="Flujo local aplicado; los destinos se eligen aleatoriamente."
        )

    def _quitar_demanda_local(self):
        if self.red.quitar_demanda_estacion(self.origen_local_r10.get()):
            mensaje = "La estación vuelve a usar el flujo global."
        else:
            mensaje = "La estación ya usa el flujo global."
        self.mensaje_r10.configure(text=mensaje)

    def _agregar_pico_r10(self):
        try:
            extra = int(self.pico_extra_r10.get())
            self.red.agregar_hora_pico(
                self.pico_desde_r10.get(),
                self.pico_hasta_r10.get(),
                extra,
            )
        except ValueError as error:
            self.mensaje_r10.configure(text=str(error))
            return
        texto = (
            self.pico_desde_r10.get() + "–" + self.pico_hasta_r10.get()
            + ": +" + str(extra) + " pasajeros/minuto/estación"
        )
        self.lista_picos_r10.insert(tk.END, texto)
        self.mensaje_r10.configure(text="Periodo pico agregado.")

    def _limpiar_picos_r10(self):
        self.red.limpiar_horas_pico()
        self.lista_picos_r10.delete(0, tk.END)
        self.mensaje_r10.configure(text="Se eliminaron todos los periodos pico.")

    def _configurar_capacidad_r10(self):
        try:
            capacidad = int(self.capacidad_universal_r10.get())
            self.red.configurar_capacidad_universal(capacidad)
        except ValueError as error:
            self.mensaje_r10.configure(text=str(error))
            return
        self.mensaje_r10.configure(
            text="Capacidad universal aplicada a todos los buses."
        )

    def _ejecutar_simulacion_r10(self):
        try:
            self.red.configurar_capacidad_universal(
                int(self.capacidad_universal_r10.get())
            )
            resultado = self.red.simular_dia()
        except ValueError as error:
            self.mensaje_r10.configure(text=str(error))
            return

        resumen = resultado[0]
        self.resumen_r10.configure(
            text=(
                "Pasajeros generados: " + str(resumen[0])
                + " | Abordajes (incluye transbordos): " + str(resumen[1])
                + " | No abordaron al cierre: " + str(resumen[2])
                + " | Espera promedio: " + format(resumen[3], ".1f") + " min"
                + " | Espera máxima: " + str(resumen[4]) + " min"
                + " | Cola máxima por estación: " + str(resumen[5])
                + " | Pasajeros en la red al cierre: " + str(resumen[6])
                + " | Llegaron a su destino: " + str(resumen[7])
            )
        )
        for elemento in self.tabla_r10.get_children():
            self.tabla_r10.delete(elemento)
        for fila in resultado[1]:
            self.tabla_r10.insert(
                "",
                tk.END,
                values=(
                    fila[0],
                    fila[1],
                    fila[2],
                    fila[3],
                    format(fila[4], ".1f"),
                    fila[5],
                    fila[6],
                    fila[7],
                ),
            )
        self.mensaje_r10.configure(text="Simulación de un día completada.")


def main():
    app = PlaneadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
