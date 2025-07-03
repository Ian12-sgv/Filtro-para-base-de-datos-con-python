import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from db.connection import get_db_connection, get_cruce_data

# Se supone que 'desired_cols' es la lista unificada de nombres de las columnas
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
    "CantidadInicial",    # Antes "Cantidad"
    "Cantidad_Inicial_Agrupada",   # Antes "CantidadTotal"
    "ExistenciaActual",   # Antes "Existencia_Total"
    "correccion",
    "NumeroTransferencia",
    "FechaLlegada",       # Fecha original (para ordenamiento)
    "observacion",
    "Queda",
    "Vendido"             # Nueva columna: ExistenciaActual / CantidadInicial
]

class MainView(ctk.CTk):
    def __init__(self, refresh_callback):
        super().__init__()
        self.title("Previsualización de Consulta Cruzada")
        self.refresh_callback = refresh_callback
        self.geometry("900x600")
        self.df_cruce = None  

        # Frame de botones superior
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(side="top", fill="x", padx=10, pady=10)

        self.import_btn = ctk.CTkButton(self.button_frame, text="Importar Datos", command=self.import_cruce)
        self.import_btn.pack(side="left", padx=5)
        
        # Agrupamos los filtros en un frame, incluyendo un selector de fechas
        self.filter_frame = None
        
        # Botón para seleccionar la opción de fecha a utilizar
        # Usaremos radiobuttons para que el usuario pueda seleccionar cuál filtro de fecha aplicar.
        self.fecha_option = tk.IntVar(value=2)  # Por defecto valor 2 (2024/01/01 hasta hoy)
        
        # Creamos un frame para alojar estos radiobuttons dentro del mismo panel de filtros.
        self.fecha_frame = ctk.CTkFrame(self.button_frame)
        self.fecha_frame.pack(side="left", padx=10)
        ctk.CTkLabel(self.fecha_frame, text="Filtro por fecha:").pack(side="top")
        # Opción 1: Desde 2023/01/01
        self.rb_fecha1 = ctk.CTkRadioButton(self.fecha_frame, text="2023/01/01 - Actual", variable=self.fecha_option, value=1)
        self.rb_fecha1.pack(side="left", anchor="w", padx="10")
        # Opción 2: Desde 2024/01/01
        self.rb_fecha2 = ctk.CTkRadioButton(self.fecha_frame, text="2024/01/01 - Actual", variable=self.fecha_option, value=2)
        self.rb_fecha2.pack(side="top", anchor="w")

        self.tabview = ctk.CTkTabview(self, width=500, height=450)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        self.tabview.add("Cruce")

        self.cruce_frame = self.tabview.tab("Cruce")
        self.cruce_container = tk.Frame(self.cruce_frame)
        self.cruce_container.pack(expand=True, fill="both", padx=10, pady=10)
        self.tree_cruce = ttk.Treeview(
            self.cruce_container, 
            columns=desired_cols, 
            show="headings", 
            height=20  # Ajusta este valor de acuerdo a tus necesidades
        )
        for col in desired_cols:
            self.tree_cruce.heading(col, text=col)
            self.tree_cruce.column(col, width=120, anchor="center")
        
        self.tree_cruce.grid(row=0, column=0, sticky="nsew")
        self.cruce_container.grid_rowconfigure(0, weight=1)
        self.cruce_container.grid_columnconfigure(0, weight=1)
        
        scrollbar_cruce = ttk.Scrollbar(self.cruce_container, orient="vertical", command=self.tree_cruce.yview)
        self.tree_cruce.configure(yscrollcommand=scrollbar_cruce.set)
        scrollbar_cruce.grid(row=0, column=1, sticky="ns")
        
        h_scrollbar_cruce = ttk.Scrollbar(self.cruce_container, orient="horizontal", command=self.tree_cruce.xview)
        self.tree_cruce.configure(xscrollcommand=h_scrollbar_cruce.set)
        h_scrollbar_cruce.grid(row=1, column=0, sticky="ew")

        self.tree_cruce.bind("<Button-3>", self.show_context_menu)

    def create_filter_frame(self):
        """
    Crea el panel de filtros una vez importados los datos.
    Se incluyen campos para: Código Barra, Referencia, Categoría, Línea, Código de Fábrica,
    y un bloque de filtro de fecha en línea (Fecha Inicio y Fecha Fin).
        """
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.pack(side="top", fill="x", padx=10, pady=10)

        self.codigo_barra_label = ctk.CTkLabel(self.filter_frame, text="Código Barra:", height=30)
        self.codigo_barra_label.pack(side="left", padx=(5, 2))
        self.codigo_barra_entry = ctk.CTkEntry(self.filter_frame)
        self.codigo_barra_entry.pack(side="left", padx=(2, 10))

        self.referencia_label = ctk.CTkLabel(self.filter_frame, text="Referencia:", height=30)
        self.referencia_label.pack(side="left", padx=(5, 2))
        self.referencia_entry = ctk.CTkEntry(self.filter_frame)
        self.referencia_entry.pack(side="left", padx=(2, 10))

        self.categoria_label = ctk.CTkLabel(self.filter_frame, text="Categoría:", height=30)
        self.categoria_label.pack(side="left", padx=(5, 2))
        self.categoria_entry = ctk.CTkEntry(self.filter_frame)
        self.categoria_entry.pack(side="left", padx=(2, 10))

        self.linea_label = ctk.CTkLabel(self.filter_frame, text="Línea:", height=30)
        self.linea_label.pack(side="left", padx=(5, 2))
        self.linea_entry = ctk.CTkEntry(self.filter_frame)
        self.linea_entry.pack(side="left", padx=(2, 10))

        self.fabrica_label = ctk.CTkLabel(self.filter_frame, text="Código de Fábrica:", height=30)
        self.fabrica_label.pack(side="left", padx=(5, 2))
        self.fabrica_entry = ctk.CTkEntry(self.filter_frame)
        self.fabrica_entry.pack(side="left", padx=(2, 10))
    
    # Asignamos peso a las columnas correspondientes a los Entry para que se expandan
        self.fecha_frame.grid_columnconfigure(1, weight=1)
        self.fecha_frame.grid_columnconfigure(3, weight=1)
    
        self.buscar_btn = ctk.CTkButton(self.filter_frame, text="Buscar", command=self.buscar_datos)
        self.buscar_btn.pack(side="left", padx=5)


    def import_cruce(self):
        try:
            engine = get_db_connection()
            # Inyectamos el valor de fecha_option desde el radiobutton
            fecha_option = self.fecha_option.get()
            data = get_cruce_data(engine, fecha_option=fecha_option)
            if data:
                df_cruce = pd.DataFrame(data)
                print("Columnas detectadas:", df_cruce.columns.tolist())
                # Seleccionamos sólo las columnas deseadas
                df_cruce = df_cruce[desired_cols]
            else:
                df_cruce = pd.DataFrame()
            self.df_cruce = df_cruce.copy()
            self.populate_tree(self.tree_cruce, self.df_cruce.values.tolist())
            messagebox.showinfo("Importación", "Datos importados correctamente.")
            if not self.filter_frame:
                self.create_filter_frame()
        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la importación: {e}")
            print("Error en la importación:", e)

    def buscar_datos(self):
        """
        Filtra los datos ya importados en memoria.
        """
        try:
            if self.df_cruce is None:
                messagebox.showwarning("Atención", "Primero importe los datos.")
                return

            df_filtrado = self.df_cruce.copy()

            codigo_barra = self.codigo_barra_entry.get().strip()
            referencia = self.referencia_entry.get().strip()
            categoria = self.categoria_entry.get().strip()
            linea = self.linea_entry.get().strip()
            fabrica = self.fabrica_entry.get().strip()

            if codigo_barra:
                df_filtrado = df_filtrado[df_filtrado["CodigoBarra"].astype(str) == codigo_barra]
            if referencia:
                ref_val = referencia.lower()
                df_filtrado = df_filtrado[df_filtrado["Referencia"].str.strip().str.lower() == ref_val]
            if categoria:
                cat_val = categoria.lower()
                df_filtrado = df_filtrado[df_filtrado["CategoriaNombre"].str.strip().str.lower() == cat_val]
            if linea:
                lin_val = linea.lower()
                df_filtrado = df_filtrado[df_filtrado["Linea"].str.strip().str.lower() == lin_val]
            if fabrica:
                df_filtrado = df_filtrado[df_filtrado["CodigoFabricante"].astype(str).str.strip() == fabrica]

            self.populate_tree(self.tree_cruce, df_filtrado.values.tolist())
            messagebox.showinfo("Búsqueda", "Búsqueda completada.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la búsqueda: {e}")
            print("Error en la búsqueda:", e)

    def populate_tree(self, tree, data):
        for item in tree.get_children():
            tree.delete(item)
        for row in data:
            tree.insert("", tk.END, values=row)

    def export_excel(self):
        try:
            if self.df_cruce is None:
                messagebox.showwarning("Atención", "Primero importe los datos.")
                return
            data = self.df_cruce.copy()
            data.to_excel("cruce.xlsx", index=False)
            messagebox.showinfo("Exportación", "Archivo Excel generado exitosamente como 'cruce.xlsx'.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la exportación: {e}")
            print("Error en la exportación:", e)

    def show_context_menu(self, event):
        row_id = self.tree_cruce.identify_row(event.y)
        column_id = self.tree_cruce.identify_column(event.x)
        if not row_id:
            return
        row_values = self.tree_cruce.item(row_id, "values")
        try:
            col_index = int(column_id.replace("#", "")) - 1
        except (ValueError, IndexError):
            col_index = 0
        cell_value = row_values[col_index] if row_values and col_index < len(row_values) else ""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copiar", command=lambda: self.copy_to_clipboard(cell_value))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Texto copiado al portapapeles:\n{text}")

def dummy_refresh_function():
    return None

if __name__ == '__main__':
    app = MainView(refresh_callback=dummy_refresh_function)
    app.mainloop()
