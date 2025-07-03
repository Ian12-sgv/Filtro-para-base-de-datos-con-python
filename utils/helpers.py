import os
import platform
from pathlib import Path
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import logging

# Configurar logging para un mejor rastreo de la ejecución.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def get_desktop_folder() -> str:
    """
    Retorna la ruta del Escritorio del usuario dependiendo del sistema operativo.
    
    Returns:
        str: Ruta absoluta al Escritorio.
    """
    if platform.system() == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Desktop")
    else:
        return str(Path.home() / "Desktop")

def export_to_excel(data, output_file: str) -> None:
    """
    Exporta los datos proporcionados a un archivo Excel en la ruta especificada.

    Args:
        data: Lista de diccionarios con los datos a exportar.
              Cada diccionario representa una fila, donde las claves son los nombres de las columnas.
        output_file (str): Ruta absoluta y nombre del archivo Excel.
    """
    try:
        # Se obtiene un DataFrame con las columnas definidas por las claves del primer diccionario.
        df = pd.DataFrame(data, columns=data[0].keys()) if data else pd.DataFrame()
        with pd.ExcelWriter(output_file) as writer:
            df.to_excel(writer, sheet_name="Cruce", index=False)
        logging.info("Archivo guardado exitosamente en: %s", output_file)
    except Exception as e:
        logging.error("Error al exportar a Excel: %s", e)
        raise

def get_save_path(parent):
    """
    Abre un diálogo para guardar un archivo Excel, iniciando en el Escritorio.

    Args:
        parent (tk.Tk): La ventana padre para el diálogo.
    
    Returns:
        str: La ruta seleccionada (incluyendo la extensión .xlsx) o una cadena vacía si se cancela.
    """
    desktop_path = get_desktop_folder()
    
    # Creamos una ventana raíz temporal, aunque ya estamos utilizando un 'parent'
    # Si ya cuentas con 'parent', podrías usarlo directamente y no crear una ventana nueva.
    # Aquí usamos 'parent' para que el diálogo se muestre como hijo de dicha ventana.
    file_path = filedialog.asksaveasfilename(
        parent=parent,
        title="Guardar archivo Excel",
        initialdir=desktop_path,
        defaultextension=".xlsx",
        filetypes=[("Archivos Excel", "*.xlsx")]
    )
    return file_path

def obtener_datos_treeview(tree: tk.ttk.Treeview) -> list:
    """
    Extrae los datos actualmente visibles en el widget Treeview.

    Args:
        tree (tk.ttk.Treeview): Widget Treeview del cual extraer los datos.

    Returns:
        list: Lista de diccionarios, donde cada diccionario representa una fila del Treeview.
    """
    datos = []
    for item_id in tree.get_children():
        valores = tree.item(item_id)["values"]
        fila = dict(zip(tree["columns"], valores))
        datos.append(fila)
    return datos

if __name__ == '__main__':
    # Datos de ejemplo (esto simula la salida real que podrías extraer de un Treeview)
    data = [
        {"Columna1": "Dato 1", "Columna2": "Dato 2"},
        {"Columna1": "Dato 3", "Columna2": "Dato 4"}
    ]
    
    # Solicita la ruta donde se guardará el archivo Excel.
    output_file = get_save_path()
    if output_file:
        try:
            export_to_excel(data, output_file)
        except Exception as e:
            print("Ocurrió un error durante la exportación:", e)
    else:
        logging.info("Operación cancelada. No se ha guardado el archivo.")
