from pathlib import Path
import tkinter as tk
from tkinter import ttk

from motor import Red


class PlaneadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planeador TransMilenio")
        self.geometry("560x420")
        self.minsize(480, 360)
        carpeta_datos = Path(__file__).resolve().parents[1] / "datos"
        self.red = Red(carpeta_datos)

        pestañas = ttk.Notebook(self)
        pestañas.pack(fill="both", expand=True, padx=12, pady=12)

        self._crear_pestana_busqueda(pestañas)
        self._crear_pestana_rango(pestañas)
        self._crear_pestana_proximo(pestañas)
        self._crear_pestana_viaje(pestañas)
        self._crear_pestana_ranking(pestañas)

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


def main():
    app = PlaneadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
