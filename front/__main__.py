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


def main():
    app = PlaneadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
