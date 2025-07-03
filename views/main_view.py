"""
Versión “responsive” completa de tu visor de datos.
Requiere:
  pip install pandas customtkinter
  y tu módulo db.connection con get_db_connection / get_cruce_data
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from db.connection import get_db_connection, get_cruce_data

# ------------------------- CONFIGURACIÓN GLOBAL ---------------------------
ctk.set_appearance_mode("light")     # “dark” u “auto” si prefieres
ctk.set_default_color_theme("blue")  # o el tema que uses habitualmente

desired_cols = [
    "CodigoBarra",
    "Referencia",
    "CodigoMarca",
    "Marca",
    "Nombre",
    "Nombre_Fabricante",
    "CodigoFabricante",
    "CategoriaCodigo",
    "CategoriaNombre",
    "Linea",
    "CantidadInicial",
    "Cantidad_Inicial_Agrupada",
    "ExistenciaActual",
    "correccion",
    "NumeroTransferencia",
    "FechaLlegada",
    "observacion",
    "Queda",
    "Vendido"
]

# -------------------------------------------------------------------------


class MainView(ctk.CTk):

    def __init__(self, refresh_callback):
        super().__init__()
        self.title("Previsualización de Consulta Cruzada")
        self.geometry("900x600")
        self.refresh_callback = refresh_callback
        self.df_cruce = None

        # ---------- *GRID* PRINCIPAL (3 filas) ----------------------------
        self.grid_rowconfigure(0, weight=0)      # Botonera
        self.grid_rowconfigure(1, weight=0)      # Filtros (se crea después)
        self.grid_rowconfigure(2, weight=1)      # Datos (Treeview)
        self.grid_columnconfigure(0, weight=1)

        # ---------- 1 · BOTONES + RADIOBOTONES ---------------------------
        self._build_button_bar()

        # ---------- 2 · TABVIEW DATOS ------------------------------------
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.tabview.add("Cruce")
        self.cruce_frame = self.tabview.tab("Cruce")
        self._build_treeview(self.cruce_frame)

        # El frame de filtros se insertará tras la primera importación
        self.filter_frame = None

    # ---------------------------------------------------------------------
    #   CONSTRUCCIÓN DE COMPONENTES
    # ---------------------------------------------------------------------

    # Botonera superior ----------------------------------------------------
    def _build_button_bar(self):
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.button_frame.grid_columnconfigure(0, weight=0)
        self.button_frame.grid_columnconfigure(1, weight=1)

        # Botón «Importar Datos»
        self.import_btn = ctk.CTkButton(
            self.button_frame, text="Importar Datos", command=self.import_cruce
        )
        self.import_btn.grid(row=0, column=0, sticky="w")

        # Selector de rango de fechas
        self.fecha_option = tk.IntVar(value=2)
        self.fecha_frame = ctk.CTkFrame(self.button_frame)
        self.fecha_frame.grid(row=0, column=1, sticky="e", padx=20)

        ctk.CTkLabel(self.fecha_frame, text="Filtro por fecha:").pack(anchor="w")
        ctk.CTkRadioButton(
            self.fecha_frame, text="2023/01/01 - Actual", variable=self.fecha_option, value=1
        ).pack(anchor="w")
        ctk.CTkRadioButton(
            self.fecha_frame, text="2024/01/01 - Actual", variable=self.fecha_option, value=2
        ).pack(anchor="w")

    # Treeview + scrollbars ------------------------------------------------
    def _build_treeview(self, parent):
        container = tk.Frame(parent)
        container.pack(expand=True, fill="both")

        self.tree_cruce = ttk.Treeview(
            container,
            columns=desired_cols,
            show="headings"
        )
        for col in desired_cols:
            self.tree_cruce.heading(col, text=col)
            self.tree_cruce.column(col, width=120, anchor="center", stretch=True)

        self.tree_cruce.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree_cruce.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree_cruce.xview)
        self.tree_cruce.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.bind("<Configure>", self._auto_resize_columns)
        self.tree_cruce.bind("<Button-3>", self.show_context_menu)

    # Ajusta el ancho de cada columna cuando cambie el contenedor
    def _auto_resize_columns(self, event):
        total = event.width
        col_w = max(90, int(total / len(desired_cols)))
        for col in desired_cols:
            self.tree_cruce.column(col, width=col_w)

    # Filtros (se crea solo una vez) --------------------------------------
    def create_filter_frame(self):
        self.label_font = ctk.CTkFont(size=11)

        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Columnas etiqueta / campo
        for c in range(0, 6, 2):
            self.filter_frame.grid_columnconfigure(c, weight=0)
            self.filter_frame.grid_columnconfigure(c + 1, weight=1, uniform="entry")

        # Helper para pares etiqueta-campo
        def _pair(r, c, text):
            ctk.CTkLabel(self.filter_frame, text=text,
                         font=self.label_font, height=24)\
                .grid(row=r, column=c, padx=(2, 2), pady=2, sticky="w")
            entry = ctk.CTkEntry(self.filter_frame)
            entry.grid(row=r, column=c + 1, padx=(2, 10), pady=2, sticky="ew")
            return entry

        # ---- Fila 0 ----
        self.codigo_barra_entry = _pair(0, 0, "Código Barra:")
        self.referencia_entry   = _pair(0, 2, "Referencia:")
        self.categoria_entry    = _pair(0, 4, "Categoría:")

        # ---- Fila 1 ----
        self.linea_entry   = _pair(1, 0, "Línea:")
        self.fabrica_entry = _pair(1, 2, "Código de Fábrica:")

        # ---- Sub-frame de fechas ----
        fecha_frame = ctk.CTkFrame(self.filter_frame)
        fecha_frame.grid(row=1, column=4, columnspan=2, sticky="ew")

        fecha_frame.grid_columnconfigure(1, weight=1)
        fecha_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(fecha_frame, text="Desde:", font=self.label_font).grid(
            row=0, column=0, padx=2, sticky="w"
        )
        self.fecha_ini = ctk.CTkEntry(fecha_frame)
        self.fecha_ini.grid(row=0, column=1, padx=(2, 10), sticky="ew")

        ctk.CTkLabel(fecha_frame, text="Hasta:", font=self.label_font).grid(
            row=0, column=2, padx=2, sticky="w"
        )
        self.fecha_fin = ctk.CTkEntry(fecha_frame)
        self.fecha_fin.grid(row=0, column=3, padx=(2, 10), sticky="ew")

        # ---- Botón Buscar ----
        self.buscar_btn = ctk.CTkButton(
            self.filter_frame, text="Buscar", command=self.buscar_datos
        )
        self.buscar_btn.grid(row=2, column=0, columnspan=6, pady=(8, 0), sticky="e")

    # ---------------------------------------------------------------------
    #   LÓGICA DE NEGOCIO
    # ---------------------------------------------------------------------

    def import_cruce(self):
        try:
            engine = get_db_connection()
            data = get_cruce_data(engine, fecha_option=self.fecha_option.get())
            df = pd.DataFrame(data) if data else pd.DataFrame()
            print("Columnas detectadas:", df.columns.tolist())

            self.df_cruce = df[desired_cols].copy() if not df.empty else df
            self.populate_tree(self.df_cruce.values.tolist())

            messagebox.showinfo("Importación", "Datos importados correctamente.")

            if not self.filter_frame:
                self.create_filter_frame()

        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la importación: {e}")
            print("Error en la importación:", e)

    def buscar_datos(self):
        if self.df_cruce is None:
            messagebox.showwarning("Atención", "Primero importe los datos.")
            return

        df = self.df_cruce.copy()
        filtros = {
            "CodigoBarra": self.codigo_barra_entry.get().strip(),
            "Referencia": self.referencia_entry.get().strip().lower(),
            "CategoriaNombre": self.categoria_entry.get().strip().lower(),
            "Linea": self.linea_entry.get().strip().lower(),
            "CodigoFabricante": self.fabrica_entry.get().strip()
        }

        if filtros["CodigoBarra"]:
            df = df[df["CodigoBarra"].astype(str) == filtros["CodigoBarra"]]
        if filtros["Referencia"]:
            df = df[df["Referencia"].str.strip().str.lower() == filtros["Referencia"]]
        if filtros["CategoriaNombre"]:
            df = df[df["CategoriaNombre"].str.strip().str.lower() == filtros["CategoriaNombre"]]
        if filtros["Linea"]:
            df = df[df["Linea"].str.strip().str.lower() == filtros["Linea"]]
        if filtros["CodigoFabricante"]:
            df = df[df["CodigoFabricante"].astype(str).str.strip() == filtros["CodigoFabricante"]]

        self.populate_tree(df.values.tolist())
        messagebox.showinfo("Búsqueda", "Búsqueda completada.")

    # ---------------------------------------------------------------------
    #   UTILIDADES
    # ---------------------------------------------------------------------

    def populate_tree(self, rows):
        self.tree_cruce.delete(*self.tree_cruce.get_children())
        for r in rows:
            self.tree_cruce.insert("", tk.END, values=r)

    def export_excel(self):
        if self.df_cruce is None:
            messagebox.showwarning("Atención", "Primero importe los datos.")
            return
        try:
            self.df_cruce.to_excel("cruce.xlsx", index=False)
            messagebox.showinfo("Exportación", "Archivo Excel generado: cruce.xlsx")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la exportación: {e}")

    # Menú contextual ------------------------------------------------------
    def show_context_menu(self, event):
        row_id = self.tree_cruce.identify_row(event.y)
        col_id = self.tree_cruce.identify_column(event.x)
        if not row_id:
            return
        try:
            idx = int(col_id.lstrip("#")) - 1
        except ValueError:
            idx = 0

        values = self.tree_cruce.item(row_id, "values")
        cell = values[idx] if idx < len(values) else ""

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copiar", command=lambda: self.copy_to_clipboard(cell))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Texto copiado:\n{text}")


# -------------------------------------------------------------------------
def dummy_refresh_function():
    """Placeholder para compatibilidad con tu arquitectura."""
    return None


if __name__ == "__main__":
    app = MainView(refresh_callback=dummy_refresh_function)
    app.mainloop()
